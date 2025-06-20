# calculo_orlas.py
# -*- coding: utf-8 -*-

"""
Módulo: calculo_orlas.py

Objetivo:
---------
Este módulo é responsável por calcular e preencher as colunas relacionadas
à aplicação de orlas na tabela 'tab_def_pecas'.

Os cálculos são feitos por linha, com base:
  - No código de orla presente na coluna 'Def_Peca' (ex: [2111]).
  - Nas dimensões finais da peça ('Comp_res', 'Larg_res', 'Esp_res').
  - Nos dados de referência da orla (espessura, preço, desperdício) consultados
    na tabela de matérias-primas ('materias_primas') da base de dados,
    usando as referências ('corres_orla_0_4', 'corres_orla_1_0').
  - No fator de conversão de €/m² para €/ml, que depende da espessura da peça.

As colunas calculadas e preenchidas são:
  - ORLA_C1, ORLA_C2, ORLA_L1, ORLA_L2 (espessura da orla).
  - ML_C1, ML_C2, ML_L1, ML_L2 (metros lineares por lado, por unidade de peça).
  - CUSTO_ML_C1, CUSTO_ML_C2, CUSTO_ML_L1, CUSTO_ML_L2 (custo por lado, por unidade de peça).

A atualização é despoletada pelo módulo 'modulo_orquestrador', que chama a função
`calcular_orlas` para processar todas as linhas. Cada linha é processada
individualmente pela função `calcular_orlas_para_linha`.

A atualização dos dados da orla para uma linha é saltada se o checkbox BLK
(coluna 12) estiver marcado.

Dependências:
-------------
- `db_connection.py`: Para obter conexões à base de dados MySQL.
- `utils.py`: Para funções de formatação e conversão de valores.
"""

import mysql.connector
import re
from PyQt5.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt5.QtCore import Qt # Necessário para acessar flags como Qt.Checked
# Importar funções utilitárias
from utils import converter_texto_para_valor, formatar_valor_moeda, safe_item_text, set_item
# Importar a função de acesso à base de dados
from db_connection import obter_cursor 


# --- Constantes de Índices das Colunas ---
# Índices fixos para as colunas usadas e preenchidas na tabela "tab_def_pecas" (0-based)
IDX_DEF_PECA = 2             # Coluna onde está o código da orla [XXXX]
IDX_COMP_RES = 50            # Resultado do Comprimento (mm)
IDX_LARG_RES = 51            # Resultado da Largura (mm)
IDX_ESP_RES = 52             # Resultado da Espessura (mm) da peça (usado para fator orla)
IDX_QT_TOTAL = 49            # Quantidade Total (Qt_mod * Qt_und)
IDX_UND = 24                 # Unidade (M2, ML, UND)
IDX_DESP_PECA = 25           # Desperdício da peça principal (%) - Atenção: não confundir com desperdício da orla
IDX_REF_ORLA_FINA = 26       # Referência da orla fina (código 1)
IDX_REF_ORLA_GROSSA = 27     # Referência da orla grossa (código 2)
IDX_BLK = 12                 # Checkbox BLK - Bloqueia atualização automática

# Índices das colunas a serem preenchidas com dados/cálculos da orla
IDX_ORLA_C1 = 37
IDX_ORLA_C2 = 38
IDX_ORLA_L1 = 39
IDX_ORLA_L2 = 40
IDX_ML_C1 = 41  # ML por unidade de peça (C1) Lado do comprimento em C1
IDX_ML_C2 = 42  # ML por unidade de peça (C2) Lado do comprimento em C2
IDX_ML_L1 = 43  # ML por unidade de peça (L1) Lado da largura em L1
IDX_ML_L2 = 44  # ML por unidade de peça (L2) Lado da largura em L2
DESPERDICIO_ORLA_PADRAO = 0.10  # 10% de desperdício padrão para orlas (pode ser alterado pelo utilizador)
# CUSTO_ML_C1, CUSTO_ML_C2, CUSTO_ML_L1, CUSTO_ML_L2 (custo por lado, por unidade de peça)
IDX_CUSTO_ML_C1 = 45
IDX_CUSTO_ML_C2 = 46
IDX_CUSTO_ML_L1 = 47
IDX_CUSTO_ML_L2 = 48

# Lista dos índices das colunas ML para facilitar a iteração ou soma
ML_COLUMNS_IDX = [IDX_ML_C1, IDX_ML_C2, IDX_ML_L1, IDX_ML_L2]
CUSTO_ML_COLUMNS_IDX = [IDX_CUSTO_ML_C1, IDX_CUSTO_ML_C2, IDX_CUSTO_ML_L1, IDX_CUSTO_ML_L2]


# --- Função auxiliar: extrai o código de orla [XXXX] ---
def extract_orla_code(text):
    """
    Procura uma sequência de 4 dígitos entre colchetes no texto (case-insensitive).
    Se encontrada, retorna o código (string de 4 dígitos, ex.: "2111");
    caso contrário, retorna a string "0000".
    """
    if not isinstance(text, str): # Verifica se a entrada é uma string
        return "0000"
    match = re.search(r'\[(\d{4})\]', text)
    if match:
        return match.group(1)
    return "0000"

# --- Função auxiliar: determina largura orla (mm) e fator preço ---
def get_orla_width_factor(esp_peca):
    """
    Determina a largura de orla associada (em mm) e um fator de conversão
    de €/m² para €/ml com base na espessura da PEÇA (esp_peca).
    
    Parâmetros:
    -----------
    esp_peca : float
        A espessura da peça em mm.
        
    Retorna:
    --------
    tuple (float, float): Uma tupla contendo a largura da orla em mm e o fator.
    O fator é aproximadamente 1000 / largura_orla.
    Ex: (23, 43) se esp_peca < 20.
    Retorna (0, 0) se esp_peca for inválida ou não se enquadrar nas regras.
    """
    # Trata casos de espessura inválida ou zero
    if not isinstance(esp_peca, (int, float)) or esp_peca <= 0:
        # print(f"[AVISO] get_orla_width_factor: Espessura da peça inválida/zero ({esp_peca}). Retornando fator zero.")
        return 0, 0 # Largura, Fator

    if esp_peca < 20:
        return 23, 43 # 1000 / 23 ≈ 43.478
    elif esp_peca < 31:
        return 35, 28 # 1000 / 35 ≈ 28.571
    elif esp_peca < 40:
        return 45, 22 # 1000 / 45 ≈ 22.222
    else: # esp_peca >= 40 (Ajustado de >= 45 conforme descrição)
          # A descrição original tinha 45mm mas o cálculo parece usar >=40
          # Vamos usar 40 como limite inferior para 60mm.
        return 60, 16 # 1000 / 60 ≈ 16.667 # Confere com descrição original (16)
    # Adicionei casas decimais aos fatores para maior precisão no cálculo.


# --- Função auxiliar: consulta dados da orla na DB ---
def get_orla_data(ref_phc):
    """
    Consulta a tabela 'materias_primas' na base de dados para obter
    a espessura (ESP_MP), preço líquido (pliq) em €/m², e desperdício (desp)
    de um material de orla com base na sua referência (REF_PHC).

    Parâmetros:
    -----------
    ref_phc : str
        A referência do material de orla a procurar.

    Retorna:
    --------
    tuple (float, float, float): Uma tupla contendo a espessura (mm),
    o preço líquido (€/m²), e o desperdício (fração, ex: 0.06 para 6%).
    Retorna (0.0, 0.0, 0.0) se a referência for inválida ou não encontrada.
    """
    # Trata referência vazia ou inválida
    if not ref_phc or not isinstance(ref_phc, str) or not ref_phc.strip():
        # print(f"[AVISO] get_orla_data: Referência de orla inválida/vazia ({ref_phc}).")
        return 0.0, 0.0, 0.0

    esp_mp = 0.0
    pliq_val = 0.0
    desp_orla_fracao = 0.0 # Desperdício como fração (0.06)

    try:
        # Utiliza o gestor de contexto para obter e fechar cursor/conexão
        with obter_cursor() as cursor:
            # Usar backticks para nomes de colunas/tabelas se contiverem caracteres especiais ou forem palavras reservadas
            query = "SELECT `ESP_MP`, `pliq`, `desp` FROM `materias_primas` WHERE `REF_PHC` = %s"
            cursor.execute(query, (ref_phc,))
            result = cursor.fetchone()

        # Processa o resultado FORA do bloco 'with'
        if result:
            # Converte os resultados para float, tratando None
            try: esp_mp = float(result[0]) if result[0] is not None else 0.0
            except (ValueError, TypeError): esp_mp = 0.0

            try: pliq_val = float(result[1]) if result[1] is not None else 0.0
            except (ValueError, TypeError): pliq_val = 0.0

            # A coluna 'desp' na BD é DECIMAL(5,2), representa a *percentagem* (ex: 6.00 para 6%)
            # Precisamos converter para fração (ex: 0.06)
            try:
                desp_bd = float(result[2]) if result[2] is not None else 0.0
                desp_orla_fracao = desp_bd # Divide por 100 para obter a fração
            except (ValueError, TypeError):
                desp_orla_fracao = 0.0

            # print(f"[DEBUG] get_orla_data: REF_PHC '{ref_phc}' encontrado. Esp={esp_mp}, PliQ={pliq_val}, Desp(fracao)={desp_orla_fracao}") # Debug
            return esp_mp, pliq_val, desp_orla_fracao
        else:
            # print(f"[AVISO] get_orla_data: REF_PHC '{ref_phc}' não encontrado na DB 'materias_primas'.") # Debug/Aviso
            return 0.0, 0.0, 0.0 # Retorna zeros se não encontrar a referência
            
    except mysql.connector.Error as db_err:
        print(f"[ERRO DB] Erro ao consultar DB 'materias_primas' para REF_PHC '{ref_phc}': {db_err}")
        # Não mostrar QMessageBox aqui, pois pode ser chamado muitas vezes no loop
        return 0.0, 0.0, 0.0 # Retorna zeros em caso de erro de base de dados
    except Exception as e:
        print(f"[ERRO INESPERADO] em get_orla_data para REF_PHC '{ref_phc}': {e}")
        import traceback
        traceback.print_exc() # Para ver a stack trace
        return 0.0, 0.0, 0.0 # Retorna zeros em caso de erro inesperado


# --- Função que calcula e preenche os valores de orla para UMA linha ---
def calcular_orlas_para_linha(ui, row):
    """
    Calcula e preenche todas as colunas relacionadas à orla para a linha 'row'
    na tabela 'tab_def_pecas'.

    Inclui:
      - Leitura do código de orla [XXXX].
      - Consulta na DB para espessura, preço (€/m²) e desperdício da orla.
      - Cálculo dos metros lineares (ML_xx) por lado.
      - Cálculo do custo por lado (CUSTO_ML_xx) por unidade de peça.
      - Preenchimento das colunas ORLA_xx, ML_xx, CUSTO_ML_xx.

    Esta função verifica a flag BLK (coluna 12). Se BLK estiver True,
    todos os cálculos e preenchimento das colunas de orla SÃO SALTADOS,
    mantendo os valores que estavam na linha (editados manualmente).

    Parâmetros:
    -----------
    ui : objeto Ui_MainWindow
        A interface principal.
    row : int
        O índice da linha a ser processada na tabela 'tab_def_pecas'.
    """
    table = ui.tab_def_pecas # Obtém a referência da tabela


    # --- Obter dados necessários da linha ---
    # Usa safe_item_text e converter_texto_para_valor para obter valores numéricos de forma segura
    comp_res = converter_texto_para_valor(safe_item_text(table, row, IDX_COMP_RES), "moeda") # Comp. Resultado (mm)
    larg_res = converter_texto_para_valor(safe_item_text(table, row, IDX_LARG_RES), "moeda") # Larg. Resultado (mm)
    esp_res = converter_texto_para_valor(safe_item_text(table, row, IDX_ESP_RES), "moeda")  # Esp. Resultado (mm) da peça
    qt_total_val = converter_texto_para_valor(safe_item_text(table, row, IDX_QT_TOTAL), "moeda")
    if qt_total_val <= 0:
        qt_total_val = 1  # Para evitar multiplicar por zero, assume 1 como fallback # Qt_Total pode ser zero se não houver peças a calcular.
    # Se a quantidade total for zero ou inválida, não faz sentido calcular orlas
    # Verifica se a coluna Orla (checkbox - col 11) está ativa
    orla_chk_item = table.item(row, 11)
    orla_checkbox_ativo = orla_chk_item and orla_chk_item.checkState() == Qt.Checked

    # Obtém o texto da coluna Def_Peca para extrair o código da orla
    def_peca_text = safe_item_text(table, row, IDX_DEF_PECA)
    orla_code = extract_orla_code(def_peca_text)  # Retorna string "XXXX" ou "0000"

    # Obtém as referências de orla fina e grossa da linha
    ref_orla_fina = safe_item_text(table, row, IDX_REF_ORLA_FINA).strip()
    ref_orla_grossa = safe_item_text(table, row, IDX_REF_ORLA_GROSSA).strip()

    # Se o checkbox Orla estiver ativo, todas as colunas de orla devem ser 0
    if orla_checkbox_ativo:
        for idx in [IDX_ORLA_C1, IDX_ORLA_C2, IDX_ORLA_L1, IDX_ORLA_L2]:
            set_item(table, row, idx, "")
        for idx in ML_COLUMNS_IDX:
            set_item(table, row, idx, "0.0")
        for idx in CUSTO_ML_COLUMNS_IDX:
            set_item(table, row, idx, formatar_valor_moeda(0.0))
        return

    # --- Processar cada lado da orla ---
    # Define os mapeamentos de lado para dígito no código e referência de orla
    lados = {
        'C1': {'digit_idx': 0, 'dim': comp_res},
        'C2': {'digit_idx': 1, 'dim': comp_res},
        'L1': {'digit_idx': 2, 'dim': larg_res},
        'L2': {'digit_idx': 3, 'dim': larg_res}
    }

    # Determina o fator de preço com base na espessura da PEÇA (esp_res)
    _, price_factor = get_orla_width_factor(esp_res)
    # Evitar divisão por zero se o fator for 0 (ex: esp_res inválida)
    # Se price_factor é 0, pliq_orla_m2/price_factor dará erro ou infinidade.
    # A lógica de custo abaixo deve ser robusta para pliq_orla_m2=0 ou price_factor=0.
    # Se price_factor é 0, o custo deve ser 0. Não precisamos mudar price_factor para 1.

    # Itera por cada lado para calcular e preencher
    table.blockSignals(True) # Bloqueia sinais para o preenchimento da linha
    try:
        for lado, dados_lado in lados.items():
            # Obtém o dígito correspondente no código da orla
            dígito = orla_code[dados_lado['digit_idx']] if dados_lado['digit_idx'] < len(orla_code) else '0'

            esp_orla_lado = 0.0
            ml_lado = 0.0
            custo_lado = 0.0
            pliq_orla_m2 = 0.0 
            desp_orla_fracao = 0.10 # Inicializa desperdício da orla com 10% (valor padrão)

            if dígito != '0':
                # Determina a referência da orla com base no dígito
                ref_orla_lado = ref_orla_fina if dígito == '1' else ref_orla_grossa

                # Consulta a base de dados para obter dados da orla
                 # get_orla_data retorna (espessura, pliq_m2, desperdicio_fracao)
                esp_mp_orla, pliq_orla_m2, desp_orla_fracao = get_orla_data(ref_orla_lado)

                # Realiza os cálculos APENAS se os dados da orla forem válidos e o fator de preço for válido
                # (pliq_orla_m2 > 0 E price_factor > 0)
                # A espessura da orla (esp_orla_lado) pode ser preenchida mesmo se o preço for zero.
                esp_orla_lado = esp_mp_orla # A espessura da orla vem direta da DB

                if pliq_orla_m2 > 0 and price_factor > 0 and dados_lado['dim'] > 0:
                    # Metros Lineares: dimensão da peça (em mm) convertida para metros
                    ml_por_unidade = dados_lado['dim'] / 1000.0  # ML por uma unidade de peça
                    ml_lado = ml_por_unidade * qt_total_val     # Multiplicado pela quantidade total

                    # Custo por ML de orla: (preço €/m² / fator €/ml para 1 €/m²) * (1 + desperdício da orla)
                    # Custo = ML * (Preço_Orla_m2 / Fator_Conversao) * (1 + Desperdicio_Orla)
                    # ml_lado já é em metros.
                    # custo_lado é o custo da orla para UM lado de UMA unidade de peça.
                    # Custo por ML de orla: inclui desperdício
                    custo_lado = ml_lado * (pliq_orla_m2 / price_factor) * (1 + desp_orla_fracao if desp_orla_fracao > 0 else DESPERDICIO_ORLA_PADRAO)


            # --- Preencher colunas na tabela ---
            # Colunas de Espessura da Orla (ORLA_Cx/Lx)
            idx_orla = globals()[f'IDX_ORLA_{lado}'] # Obtém o índice da constante global
            # Formata com 1 decimal se a espessura for > 0, senão vazio
            set_item(table, row, idx_orla, f"{esp_orla_lado:.1f}" if esp_orla_lado > 0 else "") # Usa set_item

            # Colunas de Metros Lineares (ML_Cx/Lx)
            idx_ml = globals()[f'IDX_ML_{lado}']
            # Formata com 1 decimais, mesmo se for 0
            set_item(table, row, idx_ml, f"{ml_lado:.1f}") # Usa set_item

            # Colunas de Custo (CUSTO_ML_Cx/Lx)
            idx_custo_ml = globals()[f'IDX_CUSTO_ML_{lado}']
            # Formata como moeda, arredonda para 2 decimais, mesmo se for 0
            set_item(table, row, idx_custo_ml, formatar_valor_moeda(round(custo_lado, 2))) # Usa set_item

            # Adicionar tooltip com a fórmula e valores para CUSTO_ML
            tooltip_custo = (
                f"Fórmula Custo {lado}: (Dimensão / 1000 * Qt_Total) * (PliQ_Orla / Fator) * (1 + Desp_Orla)\n"
                f"= ({dados_lado['dim']} mm / 1000) * {qt_total_val} * ({pliq_orla_m2:.2f} €/m² / {price_factor:.3f}) * (1 + {desp_orla_fracao:.2%})\n"
                f"= {round(custo_lado, 2):.2f} €"
            )
            # Certifica-se que o item existe antes de definir o tooltip
            item_custo = table.item(row, idx_custo_ml) # Obtém o item que set_item criou ou usou
            if item_custo: # Verifica se a obtenção foi bem sucedida
                item_custo.setToolTip(tooltip_custo)
                # Remova esta linha: table.setItem(row, idx_custo_ml, item_custo) # <-- REMOVER


    finally:
        table.blockSignals(False) # Desbloqueia sinais SEMPRE

    #print(f"[INFO] Cálculos de orla concluídos para linha {row+1}.")



# --- Função principal: itera e chama o cálculo por linha ---
def calcular_orlas(ui):
    """
    Itera sobre todas as linhas da tabela 'tab_def_pecas' e chama
    `calcular_orlas_para_linha` para cada uma.
    
    Esta função é chamada pelo orquestrador (`modulo_orquestrador.py`).
    """
    print("[INFO] Iniciando cálculo de orlas para todas as linhas...")
    table = ui.tab_def_pecas
    total_linhas = table.rowCount()

    if total_linhas == 0:
        print("[INFO] Tabela de peças vazia. Nenhuma orla para calcular.")
        return

    for row in range(total_linhas):
        try:
            #print(f"[DEBUG] Chamando calcular_orlas_para_linha para linha {row+1}...") # Debug verbose
            calcular_orlas_para_linha(ui, row)
        except Exception as e:
            # Captura e loga exceções específicas por linha sem parar todo o processo
            print(f"[ERRO INESPERADO] Erro ao calcular orlas na linha {row+1}: {e}")
            import traceback
            traceback.print_exc() # Imprime a stack trace para debug


    print("[INFO] Cálculo de orlas concluído para todas as linhas processadas.")


# Helper function to set item text safely (avoid creating multiple items)
# Esta função já existe em utils.py, vamos usar a de lá.
# def set_item(table, row, col, text): ...
# Re-importar set_item do utils.py para garantir que está disponível
# from utils import set_item # (Já incluído na importação de utils no topo)


if __name__ == "__main__":
    # Bloco para testes unitários independentes, se necessário.
    # Aqui você simularia um objeto 'ui' e chamaria as funções.
    print("Módulo calculo_orlas.py executado diretamente. Nenhuma ação de UI simulada.")