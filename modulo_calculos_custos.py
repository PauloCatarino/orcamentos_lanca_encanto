# modulo_calculos_custos.py
# -*- coding: utf-8 -*-

"""
Módulo: modulo_calculos_custos.py

Objetivo:
---------
Este módulo é responsável por realizar todos os cálculos de custos para cada linha
da tabela 'tab_def_pecas', com base nas dimensões, quantidades, dados de materiais
e referências de custos definidos no ficheiro Excel "TAB_DEF_PECAS.xlsx".

Funcionalidades:
----------------
1. Lê os valores de custo base (CPxx) do ficheiro Excel 'TAB_DEF_PECAS.xlsx'.
2. Calcula diversos indicadores e custos por unidade de peça (ex: Área, ML SPP, Custo MP, Custo Máquinas, Custo Acabamentos).
3. Calcula os custos totais por linha (Custo MP Total, Soma Custo Total, Soma Custo Acabamentos).
4. Preenche as colunas correspondentes na tabela 'tab_def_pecas' com os resultados.
5. Adiciona tooltips para explicar as fórmulas e valores usados nos cálculos.
6. Respeita a flag BLK (coluna 12) para saltar os cálculos em linhas bloqueadas.

A atualização é despoletada pelo módulo 'modulo_orquestrador', que chama a função
principal `atualizar_calculos_custos`. Esta função carrega o Excel uma vez e
itera pelas linhas, chamando a função `processar_calculos_para_linha` para cada uma.

Dependências:
-------------
- `pandas`: Para ler o ficheiro Excel.
- `os`: Para manipulação de caminhos de ficheiros.
- `PyQt5.QtWidgets`: Para QTableWidgetItem, QMessageBox.
- `PyQt5.QtCore`: Para Qt (flags, etc.).
- `utils.py`: Para funções utilitárias como `converter_texto_para_valor`,
  `formatar_valor_moeda`, `safe_item_text`.
"""

import os
import pandas as pd
from PyQt5.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt5.QtCore import Qt, QCoreApplication # QCoreApplication para processEvents
# Importar funções utilitárias
from utils import formatar_valor_moeda, converter_texto_para_valor, safe_item_text, set_item

# Variáveis configuráveis - os valores poderão ser alterados via interface futuramente
VALOR_SECCIONADORA = 1.0            # €/ML para a máquina Seccionadora
VALOR_ORLADORA = 0.70              # €/ML para a máquina Orladora
CNC_PRECO_PECA_BAIXO = 2.0          # €/peça se AREA_M2_und <= 0.7
CNC_PRECO_PECA_MEDIO = 2.5         # €/peça se AREA_M2_und < 1 (mas > 0.7)
CNC_PRECO_PECA_ALTO = 3.0          # €/peça se AREA_M2_und >= 1
VALOR_ABD = 0.80                 # €/peça para a máquina ABD
EUROS_HORA_PRENSA = 22.0          # €/hora para a máquina Prensa
EUROS_HORA_ESQUAD = 20.0          # €/hora para a máquina Esquadrejadora
EUROS_EMBALAGEM_M3 = 50.0         # €/M³ para Embalagem
EUROS_HORA_MO = 22.0              # €/hora para Mão de Obra

# --- Constantes de Índices das Colunas ---
# Índices fixos para as colunas usadas e preenchidas na tabela "tab_def_pecas" (0-based)
IDX_DEF_PECA = 2             # Tipo de peça (para lookup no Excel)
IDX_UND = 24                 # Unidade (M2, ML, UND)
IDX_MAT_DEFAULT = 13         # Mat_Default (para regra CP09)
IDX_TAB_DEFAULT = 14          # Tabela Default (para regra CP09)
IDX_PTAB = 20                # Preço Tabela (€)
IDX_PLIQ = 21                # Preço Líquido (€)
IDX_DESP_PECA = 25           # Desperdício da peça principal (%)
IDX_BLK = 12                 # Checkbox BLK - Bloqueia atualização automática

# Índices de colunas de resultados/dados calculados por outros módulos ou importados
IDX_COMP_RES = 50            # Resultado do Comprimento (mm)
IDX_LARG_RES = 51            # Resultado da Largura (mm)
IDX_ESP_RES = 52             # Resultado da Espessura (mm) da peça
IDX_QT_TOTAL = 49            # Quantidade Total (Qt_mod * Qt_und)
IDX_ML_C1 = 41               # Metros Lineares Orla C1
IDX_ML_C2 = 42               # Metros Lineares Orla C2
IDX_ML_L1 = 43               # Metros Lineares Orla L1
IDX_ML_L2 = 44               # Metros Lineares Orla L2
IDX_CUSTO_ML_C1 = 45         # Custo ML Orla C1
IDX_CUSTO_ML_C2 = 46         # Custo ML Orla C2
IDX_CUSTO_ML_L1 = 47         # Custo ML Orla L1
IDX_CUSTO_ML_L2 = 48         # Custo ML Orla L2

# Índices das colunas CPxx base (lidos do Excel)
IDX_CP01_SEC_BASE = 63       # CP01_SEC (do Excel)
IDX_CP02_ORL_BASE = 65       # CP02_ORL (do Excel)
IDX_CP03_CNC_BASE = 67       # CP03_CNC (do Excel)
IDX_CP04_ABD_BASE = 69       # CP04_ABD (do Excel)
IDX_CP05_PRENSA_BASE = 71    # CP05_PRENSA (do Excel)
IDX_CP06_ESQUAD_BASE = 73    # CP06_ESQUAD (do Excel)
IDX_CP07_EMBALAGEM_BASE = 75 # CP12_EMBALAGEM (do Excel)
IDX_CP08_MAO_DE_OBRA_BASE = 77 # CP08_MAO_DE_OBRA (do Excel)

# Índices das colunas de resultados dos cálculos (a serem preenchidas)
IDX_AREA_M2 = 54             # AREA_M2_und
IDX_SPP_ML_UND = 55          # SPP_ML_und
IDX_CP09_CUSTO_MP = 56       # CP09_CUSTO_MP (Flag 0 ou 1)
IDX_CUSTO_MP_UND = 57        # CUSTO_MP_und
IDX_CUSTO_MP_TOTAL = 58      # CUSTO_MP_Total
IDX_ACB_SUP = 59             # Checkbox Acabamento Superior
IDX_ACB_INF = 60             # Checkbox Acabamento Inferior
IDX_ACB_SUP_UND = 61         # ACB_SUP_und
IDX_ACB_INF_UND = 62         # ACB_INF_und
IDX_CP01_SEC_UND = 64        # CP01_SEC_und
IDX_CP02_ORL_UND = 66        # CP02_ORL_und
IDX_CP03_CNC_UND = 68        # CP03_CNC_und
IDX_CP04_ABD_UND = 70        # CP04_ABD_und
IDX_CP05_PRENSA_UND = 72     # CP05_PRENSA_und
IDX_CP06_ESQUAD_UND = 74     # CP06_ESQUAD_und
IDX_CP07_EMBALAGEM_UND = 76  # CP07_EMBALAGEM_und
IDX_CP08_MAO_DE_OBRA_UND = 78 # CP08_MAO_DE_OBRA_und
IDX_SOMA_CUSTO_UND = 79      # Soma_Custo_und (Soma dos CPxx_und das máquinas)
IDX_SOMA_CUSTO_TOTAL = 80    # Soma_Custo_Total (Soma_Custo_und + Custo_MP_Total + Custo_Orlas_Total) * Qt_Total
IDX_SOMA_CUSTO_ACB = 81      # Soma_Custo_ACB (ACB_SUP_und + ACB_INF_und) * Qt_Total


# --- Mapeamento de colunas CP base do Excel para colunas na tabela UI ---
# Chave: Nome da coluna no DataFrame do Excel (após header=4, ex: 'CP01_SEC')
# Valor: Índice da coluna correspondente na tab_def_pecas
MAP_EXCEL_CP_TO_UI = {
    'CP01_SEC': IDX_CP01_SEC_BASE,
    'CP02_ORL': IDX_CP02_ORL_BASE,
    'CP03_CNC': IDX_CP03_CNC_BASE,
    'CP04_ABD': IDX_CP04_ABD_BASE,
    'CP05_PRENSA': IDX_CP05_PRENSA_BASE,
    'CP06_ESQUAD': IDX_CP06_ESQUAD_BASE,
    # Atenção: A descrição original tinha CP12_EMBALAGEM no Excel para CP07_EMBALAGEM na UI
    # Mantenho o nome do Excel aqui como chave
    'CP12_EMBALAGEM': IDX_CP07_EMBALAGEM_BASE, # Mapeia nome do Excel para índice da UI
    'CP08_MAO_DE_OBRA': IDX_CP08_MAO_DE_OBRA_BASE
}


# --- Função auxiliar: garantir item e definir texto ---
# Já existe em utils.py, vamos usar a de lá (set_item)
from utils import set_item # Já importado no topo


# --- Função auxiliar: calcular área em m² ---
def calcular_area_m2_para_linha(table, row):
    """
    Calcula a área da peça em m² para a linha especificada.

    Baseia-se nas dimensões de resultado (Comp_res, Larg_res) e na unidade (und).
    Se a unidade for "M2", calcula (Comp_res/1000) * (Larg_res/1000).
    Caso contrário, retorna 0.0.

    Parâmetros:
    -----------
    table : QTableWidget
        A tabela 'tab_def_pecas'.
    row : int
        O índice da linha.

    Retorna:
    --------
    float: A área em m².
    """
    und_val = safe_item_text(table, row, IDX_UND).strip().upper()
    comp_res = converter_texto_para_valor(safe_item_text(table, row, IDX_COMP_RES), "moeda") # mm
    larg_res = converter_texto_para_valor(safe_item_text(table, row, IDX_LARG_RES), "moeda") # mm

    area = 0.0
    if und_val == "M2" and comp_res > 0 and larg_res > 0:
        area = (comp_res / 1000.0) * (larg_res / 1000.0) # Converte mm para m e calcula área

    # print(f"  [DEBUG] Linha {row+1}: Área calculada ({und_val}, {comp_res}x{larg_res}) = {area:.4f} m²") # Debug
    return area

# --- Função auxiliar: calcular ML SPP ---
def calcular_spp_ml_para_linha(table, row):
    """
    Calcula os Metros Lineares SPP (Superfície por Perfil?) para a linha especificada.

    Se a unidade for "ML" (case-insensitive), calcula Comp_res / 1000.
    Caso contrário, retorna 0.0.

    Parâmetros:
    -----------
    table : QTableWidget
        A tabela 'tab_def_pecas'.
    row : int
        O índice da linha.

    Retorna:
    --------
    float: O valor de SPP_ML_und em metros.
    """
    und_val = safe_item_text(table, row, IDX_UND).strip().upper()
    comp_res = converter_texto_para_valor(safe_item_text(table, row, IDX_COMP_RES), "moeda") # mm

    spp_ml = 0.0
    if und_val == "ML" and comp_res > 0:
        spp_ml = comp_res / 1000.0 # Converte mm para m

    # print(f"  [DEBUG] Linha {row+1}: SPP_ML calculado ({und_val}, {comp_res}) = {spp_ml:.2f} m") # Debug
    return spp_ml


# --- Função principal de cálculo por linha ---
def processar_calculos_para_linha(ui, row, df_excel_cp):
    """
    Realiza todos os cálculos de custos para uma única linha da tabela 'tab_def_pecas'.

    Se a linha estiver marcada como BLK=True, os valores base CPxx não são lidos do Excel,
    mas os cálculos (Area, Custo MP, Custos Maquina, Somas) são executados usando
    os valores *atuais* da linha na tabela UI.

    Caso contrário (BLK=False), usa os dados padrão e os valores base do Excel.

    Parâmetros:
    -----------
    ui : objeto Ui_MainWindow
        A interface principal.
    row : int
        O índice da linha a ser processada na tabela 'tab_def_pecas'.
    df_excel_cp : pandas.DataFrame
        DataFrame carregado do ficheiro Excel 'TAB_DEF_PECAS.xlsx'.
    """
    table = ui.tab_def_pecas # Obtém a referência da tabela

    # --- Verifica o checkbox BLK (coluna 12) ---
    # Se linha BLK está bloqueada com visto
    # --- Verificar origem da edição nos tooltips (manual vs escolher) ---
    blk_item = table.item(row, IDX_BLK)
    linha_bloqueada = blk_item and blk_item.checkState() == Qt.Checked

     # A verificação de origem ("manual" ou "escolher") já não é necessária aqui
    # para decidir se calcula ou não. O cálculo será sempre feito.
    # A flag linha_bloqueada agora só determina se lê CPxx base do Excel.

    # --- Obter dados COMUNS da linha (necessários em todos os casos) ---
    def_peca_val = safe_item_text(table, row, IDX_DEF_PECA).strip().upper()
    und_val = safe_item_text(table, row, IDX_UND).strip().upper()
    tab_default_val = safe_item_text(table, row, IDX_TAB_DEFAULT).strip().upper()
    comp_res = converter_texto_para_valor(safe_item_text(table, row, IDX_COMP_RES), "moeda") # mm
    larg_res = converter_texto_para_valor(safe_item_text(table, row, IDX_LARG_RES), "moeda") # mm
    esp_res = converter_texto_para_valor(safe_item_text(table, row, IDX_ESP_RES), "moeda")  # mm
    qt_total = converter_texto_para_valor(safe_item_text(table, row, IDX_QT_TOTAL, "1"), "moeda") # Qt_Total
    if qt_total <= 0: qt_total = 1.0 # Assegura qt_total >= 1

    # Obter valores atuais de pliq e desp da tabela (serão usados nos cálculos)
    pliq = converter_texto_para_valor(safe_item_text(table, row, IDX_PLIQ), "moeda")
    desp_peca_fracao = converter_texto_para_valor(safe_item_text(table, row, IDX_DESP_PECA), "percentual")

    # Obter valores de orla da tabela (calculados previamente)
    ml_c1 = converter_texto_para_valor(safe_item_text(table, row, IDX_ML_C1), "moeda")
    ml_c2 = converter_texto_para_valor(safe_item_text(table, row, IDX_ML_C2), "moeda")
    ml_l1 = converter_texto_para_valor(safe_item_text(table, row, IDX_ML_L1), "moeda")
    ml_l2 = converter_texto_para_valor(safe_item_text(table, row, IDX_ML_L2), "moeda")
    custo_ml_c1 = converter_texto_para_valor(safe_item_text(table, row, IDX_CUSTO_ML_C1), "moeda")
    custo_ml_c2 = converter_texto_para_valor(safe_item_text(table, row, IDX_CUSTO_ML_C2), "moeda")
    custo_ml_l1 = converter_texto_para_valor(safe_item_text(table, row, IDX_CUSTO_ML_L1), "moeda")
    custo_ml_l2 = converter_texto_para_valor(safe_item_text(table, row, IDX_CUSTO_ML_L2), "moeda")

    # --- Carregar valores base CPxx do Excel APENAS se a linha NÃO estiver bloqueada ---
    if not linha_bloqueada:
        #print(f"[INFO] Linha {row+1} NÃO bloqueada. Lendo CPxx base do Excel.")
        cp_base_values = {}
        if df_excel_cp is not None and not df_excel_cp.empty:
            # Garantir que a coluna de busca existe e está limpa
            if 'DEF_PECA_CLEAN' not in df_excel_cp.columns:
                 if "DEF_PECA" in df_excel_cp.columns:
                     df_excel_cp['DEF_PECA_CLEAN'] = df_excel_cp['DEF_PECA'].astype(str).str.strip().str.upper()
                 else:
                     df_excel_cp['DEF_PECA_CLEAN'] = df_excel_cp.iloc[:, 0].astype(str).str.strip().str.upper()

            row_excel = df_excel_cp[df_excel_cp['DEF_PECA_CLEAN'] == def_peca_val]

            if not row_excel.empty:
                row_data = row_excel.iloc[0]
                for cp_excel_name, ui_col_idx in MAP_EXCEL_CP_TO_UI.items():
                    valor = row_data.get(cp_excel_name)
                    try:
                        cp_base_values[cp_excel_name] = float(valor) if pd.notna(valor) else 0.0
                    except (ValueError, TypeError):
                        cp_base_values[cp_excel_name] = 0.0
            else: # Peça não encontrada no Excel
                for cp_name in MAP_EXCEL_CP_TO_UI.keys():
                    cp_base_values[cp_name] = 0.0
        else: # DataFrame do Excel vazio ou None
            for cp_name in MAP_EXCEL_CP_TO_UI.keys():
                 cp_base_values[cp_name] = 0.0

        # Preenche as colunas CPxx base na tabela UI (APENAS SE NÃO BLOQUEADO)
        table.blockSignals(True)
        try:
            for cp_excel_name, ui_col_idx in MAP_EXCEL_CP_TO_UI.items():
                 valor = cp_base_values.get(cp_excel_name, 0.0)
                 set_item(table, row, ui_col_idx, f"{int(round(valor))}")
                 item_cp = table.item(row, ui_col_idx)
                 #if item_cp: item_cp.setToolTip(f"Valor base lido do Excel: {valor}") # Tooltip Opcional
        finally:
            table.blockSignals(False)
    # else:
        # print(f"[INFO] Linha {row+1} BLOQUEADA. Usando valores CPxx base existentes na tabela.")
        # Se a linha está bloqueada, os valores CPxx base nas colunas 63, 65, etc.,
        # já existentes na tabela serão usados pelos cálculos abaixo.


    # --- 2. Calcular indicadores e custos unitários (colunas 54-78) ---
    
    # AREA_M2_und (col 54)
    area_m2 = calcular_area_m2_para_linha(table, row)
    set_item(table, row, IDX_AREA_M2, f"{area_m2:.2f}") # Formata com 2 decimais para área
    # Tooltip Área (mantido do código original, pode ser ajustado)
    tooltip_area = (
        "<html><body>"
        "<p><b>Fórmula:</b> (Comp_res/1000) * (Larg_res/1000)</p>"
        f"<p>= ({comp_res:.2f}/1000) * ({larg_res:.2f}/1000) = {area_m2:.2f} m²</p>"
        "</body></html>"
    )
    set_item(table, row, IDX_AREA_M2, f"{area_m2:.2f}")
    item_area = table.item(row, IDX_AREA_M2) # Get item after setting text
    if item_area: item_area.setToolTip(tooltip_area)
    

    # SPP_ML_und (col 55)
    spp_ml = calcular_spp_ml_para_linha(table, row)
    set_item(table, row, IDX_SPP_ML_UND, f"{spp_ml:.2f}")
    # Tooltip SPP_ML (mantido)
    tooltip_spp_ml = (
        "<html><body>"
        "<p><b>Fórmula:</b> SPP_ML_und = Comp_res / 1000 (Se und='ML')</p>"
        f"<p>= ({comp_res:.2f}) / 1000 = {spp_ml:.2f}</p>"
        "</body></html>"
    )
    item_spp = table.item(row, IDX_SPP_ML_UND)
    if item_spp: item_spp.setToolTip(tooltip_spp_ml)


    # CP09_CUSTO_MP (col 56) - Flag 0 ou 1 para Custo MP
    # Regra: 1 se und in ["M2", "ML", "UND"] E Mat_Default != "TAB_ACABAMENTOS_12", senão 0
    custo_mp_flag = 0
    if und_val in ["M2", "ML", "UND"]:
        if und_val == "M2" and tab_default_val == "TAB_ACABAMENTOS_12":
            custo_mp_flag = 0 # Exceção para M2 em Acabamentos
        else:
            custo_mp_flag = 1
    set_item(table, row, IDX_CP09_CUSTO_MP, str(custo_mp_flag)) # Exibe como string "0" ou "1"
    item_cp09 = table.item(row, IDX_CP09_CUSTO_MP)
    if item_cp09: item_cp09.setToolTip("Fórmula: 1 se Und in [M2, ML, UND] E Mat_Default != TAB_ACABAMENTOS_12; 0 caso contrário.")

    # CUSTO_MP_und (col 57) - Custo de Matéria-Prima por unidade
    # Regra: Depende de und, usando AREA_M2, SPP_ML, PliQ, Desp_Peca. É 0 se CP09_CUSTO_MP < 1 ou MPs checkbox ativo.
    cp09_val_numeric = converter_texto_para_valor(safe_item_text(table, row, IDX_CP09_CUSTO_MP), "moeda") # Pega o valor 0/1 como número

    custo_mp_und = 0.0
    formula_exp = "0"
    formula_valores = ""
    formula_final = "0.00€"

    if cp09_val_numeric >= 1:
        if und_val == "M2":
            custo_mp_und = area_m2 * (1 + desp_peca_fracao) * pliq
            formula_exp = "AREA_M2_und * (1 + Desp_Peca) * PliQ"
            formula_valores = f"{area_m2:.3f} * (1 + {desp_peca_fracao:.2f}) * {pliq:.2f}"
        elif und_val == "ML":
            custo_mp_und = spp_ml * (1 + desp_peca_fracao) * pliq
            formula_exp = "SPP_ML_und * (1 + Desp_Peca) * PliQ"
            formula_valores = f"{spp_ml:.3f} * (1 + {desp_peca_fracao:.2f}) * {pliq:.2f}"
        elif und_val == "UND":
            custo_mp_und = pliq * (1 + desp_peca_fracao)
            formula_exp = "PliQ * (1 + Desp_Peca)"
            formula_valores = f"{pliq:.2f} * (1 + {desp_peca_fracao:.2f})"
        formula_final = f"{custo_mp_und:.2f}€"

    # Se o checkbox MPs (coluna 9) estiver ativo, custo é 0
    item_mps_chk = table.item(row, 9)
    if item_mps_chk and item_mps_chk.checkState() == Qt.Checked:
        custo_mp_und = 0.0
        formula_exp = "0 (MPs checkbox ativo)"
        formula_valores = ""
        formula_final = "0.00€"

    # Gravar o custo e o novo tooltip
    set_item(table, row, IDX_CUSTO_MP_UND, formatar_valor_moeda(round(custo_mp_und, 2)))
    item_custo_mp_und = table.item(row, IDX_CUSTO_MP_UND)
    if item_custo_mp_und:
        tooltip = (
            f"<b>Fórmula:</b> {formula_exp}<br>"
            f"<b>Valores:</b> {formula_valores}<br>"
            f"<b>Resultado:</b> {formula_final}"
        )
        item_custo_mp_und.setToolTip(tooltip)


    # CUSTO_MP_Total (col 58) = CUSTO_MP_und * Qt_Total
    # Este cálculo usa o CUSTO_MP_und JÁ CALCULADO/AJUSTADO acima
    custo_mp_total = custo_mp_und * qt_total
    set_item(table, row, IDX_CUSTO_MP_TOTAL, formatar_valor_moeda(round(custo_mp_total, 2))) # Formata como moeda
    item_custo_mp_total = table.item(row, IDX_CUSTO_MP_TOTAL)
    if item_custo_mp_total: # Garante que o item existe
        item_custo_mp_total.setToolTip(f"Fórmula: CUSTO_MP_und * Qt_Total\n= {round(custo_mp_und, 2):.2f}€ * {qt_total:.0f} = {round(custo_mp_total, 2):.2f}€")


    # --- Cálculos de Custo de Máquinas por unidade (colunas 64-78) ---
    # Estes cálculos usam os valores CPxx base (lidos do Excel e preenchidos acima)
    # e as dimensões/quantidades/variáveis fixas (ex: VALOR_SECCIONADORA).

    # CP01_SEC_und (col 64)
    cp01_sec_base = converter_texto_para_valor(safe_item_text(table, row, IDX_CP01_SEC_BASE), "moeda")
    sec_und = 0.0
    perimetro_mm = 0.0
    if cp01_sec_base >= 1 and comp_res > 0 and larg_res > 0:
            perimetro_mm = 2 * (comp_res + larg_res) if comp_res and larg_res else 0
            perimetro_m = perimetro_mm / 1000.0 # Perímetro em metros
            sec_und = VALOR_SECCIONADORA * perimetro_m
    set_item(table, row, IDX_CP01_SEC_UND, formatar_valor_moeda(round(sec_und, 2))) # Formata como moeda
    item_sec_und = table.item(row, IDX_CP01_SEC_UND) # Obtém item
    if perimetro_mm:
        item_sec_und.setToolTip(
            f"Fórmula: VALOR_SECCIONADORA * (Perímetro em m)\n"
            f"= {VALOR_SECCIONADORA:.2f} €/ML * ({perimetro_mm:.0f} mm / 1000)"
            f" = {round(sec_und, 2):.2f}€"
        )
    
    # CP02_ORL_und (col 66)
    cp02_orl_base = converter_texto_para_valor(safe_item_text(table, row, IDX_CP02_ORL_BASE), "moeda")
    orl_und = 0.0
    # Verifica se o checkbox Orla (coluna 11) está ativo
    item_orla_chk = table.item(row, 11)
    orla_checkbox_ativo = item_orla_chk and item_orla_chk.checkState() == Qt.Checked
    soma_ml_orlas = converter_texto_para_valor(safe_item_text(table, row, IDX_ML_C1), "moeda") + \
                    converter_texto_para_valor(safe_item_text(table, row, IDX_ML_C2), "moeda") + \
                    converter_texto_para_valor(safe_item_text(table, row, IDX_ML_L1), "moeda") + \
                    converter_texto_para_valor(safe_item_text(table, row, IDX_ML_L2), "moeda") # Soma ML orlas (calculado em modulo_calculo_orlas)

    if not orla_checkbox_ativo and cp02_orl_base >= 1 and soma_ml_orlas > 0 and qt_total > 0: # Qt_Total usado como divisor? Regra original confusa. Custo Orla por Peça / Qt_Total?
            # Regra original: CP02_ORL_und = (Soma ML orlas) * Orladora / QT_TOTAL
            # Isto parece CUSTO TOTAL orla para o item / QT_TOTAL de peças.
            # MAS a descrição diz custo por PEÇA, não por ITEM.
            # Custo Orladora por ML é VALOR_ORLADORA (€/ML).
            # Custo TOTAL de orla para UMA peça = Soma ML * VALOR_ORLADORA.
            # O QT_TOTAL é a quantidade de PEÇAS. A regra original parece dividir o custo TOTAL pela quantidade de peças.
            # Vamos calcular o Custo TOTAL de orla para o ITEM e dividir por QT_TOTAL como na regra original.
            # Soma Custo ML orlas (col 45-48) já inclui preço e desperdício da orla!
            # Regra original pode estar a usar CUSTO_ML_Cx/Lx que já está em €/Peça (unidade de orla).
            # Se for isso: Soma Custo ML (col 45-48) já é custo por peça. Soma (CUSTO_ML_C1 + .. + CUSTO_ML_L2) é custo TOTAL orla por peça.
            # Vamos usar a soma dos Custo_ML_xx (col 45-48) que já é o custo da orla por peça.
            soma_custo_ml_orlas_und = converter_texto_para_valor(safe_item_text(table, row, IDX_CUSTO_ML_C1), "moeda") + \
                                    converter_texto_para_valor(safe_item_text(table, row, IDX_CUSTO_ML_C2), "moeda") + \
                                    converter_texto_para_valor(safe_item_text(table, row, IDX_CUSTO_ML_L1), "moeda") + \
                                    converter_texto_para_valor(safe_item_text(table, row, IDX_CUSTO_ML_L2), "moeda")
            # Regra original: CP02_ORL_und = (Soma dos ML dos lados) * Orladora / QT_TOTAL
            # Isto parece usar a soma dos ML e MULTIPLICAR por VALOR_ORLADORA (€/ML) e depois dividir por QT_TOTAL.
            # Vamos seguir essa regra literal, assumindo que Soma dos ML dos lados refere-se à soma_ml_orlas.
            # É estranho dividir por QT_TOTAL se o custo deve ser POR UNIDADE DE PEÇA.
            # Talvez a regra original quisesse dizer Custo por ITEM / QT_TOTAL?
            # Custo por ITEM = (Soma ML * VALOR_ORLADORA). Custo por PEÇA = Custo por ITEM / QT_TOTAL. Sim, parece ser isso.
            custo_orla_total_item = soma_ml_orlas * VALOR_ORLADORA # Custo total de orla para 1 ITEM (todas as peças)
            orl_und = custo_orla_total_item / qt_total # Custo de orla por PEÇA
            formula_orl_tooltip = f"(Soma ML * VALOR_ORLADORA) / Qt_Total\n= ({soma_ml_orlas:.2f} m * {VALOR_ORLADORA:.2f} €/ML) / {qt_total:.0f} = {round(orl_und, 2):.2f}€"
    else:
        if orla_checkbox_ativo:
            orl_und = 0.0
            formula_orl_tooltip = "0 (Orla checkbox ativo)"
        else:
            orl_und = 0.0
            formula_orl_tooltip = "0"

    set_item(table, row, IDX_CP02_ORL_UND, formatar_valor_moeda(round(orl_und, 2))) # Formata como moeda
    item_orl_und = table.item(row, IDX_CP02_ORL_UND) # Obtém item
    if item_orl_und: item_orl_und.setToolTip(f"Fórmula: {formula_orl_tooltip}")


    # CP03_CNC_und (col 68)
    cp03_cnc_base = converter_texto_para_valor(safe_item_text(table, row, IDX_CP03_CNC_BASE), "moeda")
    cnc_und = 0.0
    area_m2_for_cnc = converter_texto_para_valor(safe_item_text(table, row, IDX_AREA_M2), "moeda") # Usa a área calculada
    cnc_formula_tooltip = "0"
    if cp03_cnc_base >= 1:
        if area_m2_for_cnc > 0: # Apenas calcula se a área for maior que zero
            if area_m2_for_cnc <= 0.7:
                cnc_und = CNC_PRECO_PECA_BAIXO
                cnc_formula_tooltip = f"{CNC_PRECO_PECA_BAIXO:.2f} €/peça (Área <= 0.7 m²)"
            elif area_m2_for_cnc < 1.0: # Entre 0.7 e 1.0
                cnc_und = CNC_PRECO_PECA_MEDIO
                cnc_formula_tooltip = f"{CNC_PRECO_PECA_MEDIO:.2f} €/peça (0.7 < Área < 1.0 m²)"
            else: # >= 1.0
                cnc_und = CNC_PRECO_PECA_ALTO
                cnc_formula_tooltip = f"{CNC_PRECO_PECA_ALTO:.2f} €/peça (Área >= 1.0 m²)"
        # else: Área é 0, cnc_und permanece 0.0
    set_item(table, row, IDX_CP03_CNC_UND, formatar_valor_moeda(round(cnc_und, 2))) # Formata como moeda
    item_cnc_und = table.item(row, IDX_CP03_CNC_UND) # Obtém item
    if item_cnc_und: item_cnc_und.setToolTip(f"Fórmula: {cnc_formula_tooltip}")


    # CP04_ABD_und (col 70)
    cp04_abd_base = converter_texto_para_valor(safe_item_text(table, row, IDX_CP04_ABD_BASE), "moeda")
    abd_und = VALOR_ABD if cp04_abd_base >= 1 else 0.0
    set_item(table, row, IDX_CP04_ABD_UND, formatar_valor_moeda(round(abd_und, 2))) # Formata como moeda
    item_abd_und = table.item(row, IDX_CP04_ABD_UND) # Obtém item
    if item_abd_und: item_abd_und.setToolTip(f"Fórmula: Se CP04_ABD >= 1, então VALOR_ABD\n= {VALOR_ABD:.2f} €/peça")


    # CP05_PRENSA_und (col 72)
    # A descrição da coluna CP05_PRENSA no Excel original pode ser "Tempo Prensa (min)" ou "Nr Operacoes Prensa"?
    # Se for "Nr Operacoes", a fórmula faz sentido: Nr_Op * (€/Hora / 60 min/Hora).
    # Vamos assumir que cp05_prensa_base representa um valor que, multiplicado por (€/H / 60), dá o custo unitário.
    # Se CP05_PRENSA no Excel for, por exemplo, "2" (significa 2 minutos), a fórmula seria 2 * (22/60).
    # Se CP05_PRENSA for "1" (sim/não ou 1 operação), a fórmula seria 1 * (22/60) para cada peça?
    # A descrição "Se CP05_PRENSA >= 1" sugere que o valor no Excel é usado diretamente na fórmula, não apenas como flag.
    # Vamos assumir que CP05_PRENSA no Excel é um fator de tempo/operação.
    cp05_prensa_base = converter_texto_para_valor(safe_item_text(table, row, IDX_CP05_PRENSA_BASE), "moeda")
    prensa_und = 0.0
    prensa_formula_tooltip = "0"
    if cp05_prensa_base >= 1:
        prensa_und = (cp05_prensa_base * EUROS_HORA_PRENSA / 60.0)
        prensa_formula_tooltip = (
             f"(CP05_PRENSA_Tab * EUROS_HORA_PRENSA / 60)\n"
             f"= ({cp05_prensa_base:.2f} * {EUROS_HORA_PRENSA:.2f}€/H) / 60\n"
             f"= {round(prensa_und, 2):.2f}€"
        )
    set_item(table, row, IDX_CP05_PRENSA_UND, formatar_valor_moeda(round(prensa_und, 2)))
    item_prensa_und = table.item(row, IDX_CP05_PRENSA_UND)
    if item_prensa_und: item_prensa_und.setToolTip(prensa_formula_tooltip)

    # CP06_ESQUAD_und (col 74)
    cp06_esquad_base_tabela = converter_texto_para_valor(safe_item_text(table, row, IDX_CP06_ESQUAD_BASE), "moeda")
    esquad_und = 0.0
    esquad_formula_tooltip = "0"
    if cp06_esquad_base_tabela >= 1:
        esquad_und = (cp06_esquad_base_tabela * EUROS_HORA_ESQUAD / 60.0)
        esquad_formula_tooltip = (
            f"(CP06_ESQUAD_Tab * EUROS_HORA_ESQUAD / 60)\n"
            f"= ({cp06_esquad_base_tabela:.2f} * {EUROS_HORA_ESQUAD:.2f}€/H) / 60\n"
            f"= {round(esquad_und, 2):.2f}€"
        )
    set_item(table, row, IDX_CP06_ESQUAD_UND, formatar_valor_moeda(round(esquad_und, 2)))
    item_esquad_und = table.item(row, IDX_CP06_ESQUAD_UND)
    if item_esquad_und: item_esquad_und.setToolTip(esquad_formula_tooltip)


    # CP07_EMBALAGEM_und (col 76)
    cp07_embal_base = converter_texto_para_valor(safe_item_text(table, row, IDX_CP07_EMBALAGEM_BASE), "moeda")
    embal_und = 0.0
    volume_m3 = 0.0
    embal_formula_tooltip = "0"
    if cp07_embal_base >= 1 and comp_res > 0 and larg_res > 0 and esp_res > 0:
        volume_m3 = (comp_res * larg_res * esp_res) / 1e9
        embal_und = volume_m3 * EUROS_EMBALAGEM_M3
        embal_formula_tooltip = (
            f"Volume(m³) * EUROS_EMBALAGEM_M3 (Se CP07_EMBALAGEM_Tab >= 1)\n"
            f"= ({comp_res:.0f}x{larg_res:.0f}x{esp_res:.0f} mm³/1e9) * {EUROS_EMBALAGEM_M3:.2f} €/m³\n"
            f"= {round(embal_und, 2):.2f}€"
        )
    set_item(table, row, IDX_CP07_EMBALAGEM_UND, formatar_valor_moeda(round(embal_und, 2)))
    item_embal_und = table.item(row, IDX_CP07_EMBALAGEM_UND)
    if item_embal_und: item_embal_und.setToolTip(embal_formula_tooltip)


    # CP08_MAO_DE_OBRA_und (col 78) - Lógica similar à da Prensa
    cp08_mo_base = converter_texto_para_valor(safe_item_text(table, row, IDX_CP08_MAO_DE_OBRA_BASE), "moeda") # Assume fator/tempo
    mo_und = 0.0
    mo_formula_tooltip = "0"
    if cp08_mo_base >= 1:
        mo_und = (cp08_mo_base * EUROS_HORA_MO / 60.0)
        mo_formula_tooltip = (
            f"(CP08_MAO_DE_OBRA_Tab * EUROS_HORA_MO / 60)\n"
            f"= ({cp08_mo_base:.2f} * {EUROS_HORA_MO:.2f}€/H) / 60\n"
            f"= {round(mo_und, 2):.2f}€"
        )
    set_item(table, row, IDX_CP08_MAO_DE_OBRA_UND, formatar_valor_moeda(round(mo_und, 2)))
    item_mo_und = table.item(row, IDX_CP08_MAO_DE_OBRA_UND)
    if item_mo_und: item_mo_und.setToolTip(mo_formula_tooltip)

    # --- Cálculos de Soma Unitária e Total ---
    # Soma_Custo_und (col 79) - Soma dos custos unitários das máquinas
    sec_cost = converter_texto_para_valor(safe_item_text(table, row, IDX_CP01_SEC_UND), "moeda")
    orl_cost = converter_texto_para_valor(safe_item_text(table, row, IDX_CP02_ORL_UND), "moeda")
    cnc_cost = converter_texto_para_valor(safe_item_text(table, row, IDX_CP03_CNC_UND), "moeda")
    abd_cost = converter_texto_para_valor(safe_item_text(table, row, IDX_CP04_ABD_UND), "moeda")
    prensa_cost = converter_texto_para_valor(safe_item_text(table, row, IDX_CP05_PRENSA_UND), "moeda")
    esquad_cost = converter_texto_para_valor(safe_item_text(table, row, IDX_CP06_ESQUAD_UND), "moeda")
    embal_cost = converter_texto_para_valor(safe_item_text(table, row, IDX_CP07_EMBALAGEM_UND), "moeda")
    mao_cost = converter_texto_para_valor(safe_item_text(table, row, IDX_CP08_MAO_DE_OBRA_UND), "moeda")

    soma_custo_und_maquinas = sec_cost + orl_cost + cnc_cost + abd_cost + prensa_cost + esquad_cost + embal_cost + mao_cost

    # NOVA VERIFICAÇÃO: Se o checkbox MO (coluna 10) estiver marcado, Soma_Custo_und (soma das máquinas) passa a ser 0.
    item_mo_chk = table.item(row, 10)
    if item_mo_chk and item_mo_chk.checkState() == Qt.Checked:
        soma_custo_und_maquinas = 0.0
        mo_formula_tooltip = "0 (MO checkbox ativo)"
    else:
            mo_formula_tooltip = (
                "Soma Custos Máquinas Unitários = CP01_SEC_und + ... + CP08_MAO_DE_OBRA_und\n"
                f"= {sec_cost:.2f} + {orl_cost:.2f} + {cnc_cost:.2f} + {abd_cost:.2f} + {prensa_cost:.2f} + {esquad_cost:.2f} + {embal_cost:.2f} + {mao_cost:.2f} = {round(soma_custo_und_maquinas, 2):.2f}€"
            )

    set_item(table, row, IDX_SOMA_CUSTO_UND, formatar_valor_moeda(round(soma_custo_und_maquinas, 2))) # Formata como moeda
    item_soma_und = table.item(row, IDX_SOMA_CUSTO_UND) # Obtém item
    if item_soma_und: item_soma_und.setToolTip(mo_formula_tooltip) # Tooltip da MO (se checkbox ativo)


    # Custo TOTAL das orlas por unidade de peça (Soma dos CUSTO_ML_xx, col 45-48)
    # Estes já estão em € por UNIDADE de peça
    custo_orla_total_und = custo_ml_c1 + custo_ml_c2 + custo_ml_l1 + custo_ml_l2
    if orla_checkbox_ativo:
        custo_orla_total_und = 0.0

    # Soma_Custo_Total (col 80) = (Soma_Custo_und (máquinas) + CUSTO_MP_und + Custo_Orla_Total_und) * Qt_Total
    # NOTA: O CUSTO_MP_und (col 57) JÁ FOI CALCULADO E AJUSTADO (respeitando CP09 e MPs checkbox)
    custo_mp_und_calculado = converter_texto_para_valor(safe_item_text(table, row, IDX_CUSTO_MP_UND), "moeda")

    soma_custo_und_total = soma_custo_und_maquinas + custo_mp_und_calculado + custo_orla_total_und # Soma dos custos UNITÁRIOS (máquinas + MP + orla)
    soma_custo_total_calculado = soma_custo_und_total * qt_total # Custo TOTAL para o ITEM (por peça * quantidade)

    set_item(table, row, IDX_SOMA_CUSTO_TOTAL, formatar_valor_moeda(round(soma_custo_total_calculado, 2))) # Formata como moeda
    #item_soma_total = table.item(row, IDX_SOMA_CUSTO_TOTAL)
    tooltip_soma_total = (
        "<html><body>"
        "<p><b>Fórmula:</b> (Soma_Custo_Und_Máquinas + CUSTO_MP_und + Custo_Orla_Total_und) * Qt_Total</p>"
        f"<p>= ({round(soma_custo_und_maquinas,2):.2f}€ + {round(custo_mp_und_calculado,2):.2f}€ + {round(custo_orla_total_und,2):.2f}€) * {qt_total:.0f}</p>"
        f"<p>= {round(soma_custo_und_total, 2):.2f}€/Und * {qt_total:.0f} = {round(soma_custo_total_calculado, 2):.2f}€</p>"
        "</body></html>"
    )
    item_soma_total = table.item(row, IDX_SOMA_CUSTO_TOTAL) # Obtém item
    if item_soma_total: item_soma_total.setToolTip(tooltip_soma_total)


    # --- Cálculos de Acabamentos ---

    # ACB_SUP_und (col 61) e ACB_INF_und (col 62)
    # Regra: Se checkbox ACB_SUP/INF (col 59/60) estiver marcado -> AREA_M2_und * pliq * (1+desp_peca)
    # A consulta dos checkboxes deve ser feita AGORA para determinar o cálculo
    acb_sup_chk = table.item(row, IDX_ACB_SUP)
    acb_inf_chk = table.item(row, IDX_ACB_INF)

    acb_sup_und = 0.0
    tooltip_acb_sup = "0"
    if acb_sup_chk and acb_sup_chk.checkState() == Qt.Checked and area_m2 > 0 and pliq > 0:
            acb_sup_und = area_m2 * pliq * (1 + desp_peca_fracao)
            tooltip_acb_sup = f"AREA_M2_und * PliQ * (1+Desp_Peca)\n= {area_m2:.2f} * {pliq:.2f}€ * (1 + {desp_peca_fracao:.2%}) = {round(acb_sup_und, 2):.2f}€"

    acb_inf_und = 0.0
    tooltip_acb_inf = "0"
    if acb_inf_chk and acb_inf_chk.checkState() == Qt.Checked and area_m2 > 0 and pliq > 0:
            acb_inf_und = area_m2 * pliq * (1 + desp_peca_fracao) # A fórmula é a mesma para sup e inf? Assumindo que sim.
            tooltip_acb_inf = f"AREA_M2_und * PliQ * (1+Desp_Peca)\n= {area_m2:.2f} * {pliq:.2f}€ * (1 + {desp_peca_fracao:.2%}) = {round(acb_inf_und, 2):.2f}€"

    # NOVA PROTEÇÃO: Se Mat_Default não for "TAB_ACABAMENTOS_12", forçar 0 para ACB_SUP_und e ACB_INF_und
    # E desmarcar checkboxes 59 e 60.
    if tab_default_val != "TAB_ACABAMENTOS_12":
        acb_sup_und = 0.0
        acb_inf_und = 0.0
        tooltip_acb_sup = "0 (Mat_Default != TAB_ACABAMENTOS_12)"
        tooltip_acb_inf = "0 (Mat_Default != TAB_ACABAMENTOS_12)"
        # Desmarca checkboxes 59 e 60 (se existirem)
        if acb_sup_chk: acb_sup_chk.setCheckState(Qt.Unchecked)
        if acb_inf_chk: acb_inf_chk.setCheckState(Qt.Unchecked)
        # Bloquear a edição dos checkboxes se Mat_Default != TAB_ACABAMENTOS_12? (Futuro)


    set_item(table, row, IDX_ACB_SUP_UND, formatar_valor_moeda(round(acb_sup_und, 2))) # Formata como moeda
    item_acb_sup_und = table.item(row, IDX_ACB_SUP_UND) # Obtém item
    if item_acb_sup_und: item_acb_sup_und.setToolTip(tooltip_acb_sup)

    set_item(table, row, IDX_ACB_INF_UND, formatar_valor_moeda(round(acb_inf_und, 2))) # Formata como moeda
    item_acb_inf_und = table.item(row, IDX_ACB_INF_UND) or QTableWidgetItem()
    if item_acb_inf_und: item_acb_inf_und.setToolTip(tooltip_acb_inf)


    # Soma_Custo_ACB (col 81) = (ACB_SUP_und + ACB_INF_und) * Qt_Total
    soma_custo_acb_calculado = (acb_sup_und + acb_inf_und) * qt_total
    set_item(table, row, IDX_SOMA_CUSTO_ACB, formatar_valor_moeda(round(soma_custo_acb_calculado, 2))) # Formata como moeda
    item_soma_acb = table.item(row, IDX_SOMA_CUSTO_ACB) or QTableWidgetItem()
    tooltip_soma_acb = (
        "<html><body>"
        "<p><b>Fórmula:</b> (ACB_SUP_und + ACB_INF_und) * Qt_Total</p>"
        f"<p>= ({round(acb_sup_und, 2):.2f}€ + {round(acb_inf_und, 2):.2f}€) * {qt_total:.0f}</p>"
        f"<p>= {round(acb_sup_und + acb_inf_und, 2):.2f}€/Und * {qt_total:.0f} = {round(soma_custo_acb_calculado, 2):.2f}€</p>"
        "</body></html>"
    )
    item_soma_acb.setToolTip(tooltip_soma_acb)
        

    """
    # --- Se a linha ESTÁ bloqueada (linha_bloqueada is True), garantir que os campos de cálculo de custo estão limpos ou 0. ---
    # Vamos optar por garantir que estão limpos ou 0 para evitar confusão.
    # A leitura de valores acima já pegou os valores existentes, mas se BLK=True,
    # estes campos não devem refletir *cálculos*, mas sim dados fixos ou 0.
    # Vamos sobrescrever os campos de resultado de cálculo com 0 formatado,
    # mantendo apenas os CPxx base (que podem vir do Excel ou ser editados manualmente)
    # e os resultados que o usuário possa ter inserido.
    # A abordagem mais segura é redefinir para 0 formatado as colunas de resultado que
    # deveriam ser calculadas por esta função.
    if linha_bloqueada:
         cols_to_reset_if_blk = [
             IDX_AREA_M2, IDX_SPP_ML_UND, IDX_CP09_CUSTO_MP,
             IDX_CUSTO_MP_UND, IDX_CUSTO_MP_TOTAL,
             IDX_CP01_SEC_UND, IDX_CP02_ORL_UND, IDX_CP03_CNC_UND,
             IDX_CP04_ABD_UND, IDX_CP05_PRENSA_UND, IDX_CP06_ESQUAD_UND,
             IDX_CP07_EMBALAGEM_UND, IDX_CP08_MAO_DE_OBRA_UND,
             IDX_SOMA_CUSTO_UND, IDX_SOMA_CUSTO_TOTAL,
             IDX_ACB_SUP_UND, IDX_ACB_INF_UND, IDX_SOMA_CUSTO_ACB
             # Não resetar CPxx_BASE (63, 65..), ML_xx (41..), CUSTO_ML_xx (45..) pois podem ser preenchidos/editados manualmente com BLK
         ]
         table.blockSignals(True) # Bloqueia sinais para redefinir campos
         try:
             for col_idx in cols_to_reset_if_blk:
                 # Define o valor como "0.00€" ou "0" dependendo da formatação esperada
                 if col_idx in [IDX_CUSTO_MP_UND, IDX_CUSTO_MP_TOTAL,
                               IDX_CP01_SEC_UND, IDX_CP02_ORL_UND, IDX_CP03_CNC_UND,
                               IDX_CP04_ABD_UND, IDX_CP05_PRENSA_UND, IDX_CP06_ESQUAD_UND,
                               IDX_CP07_EMBALAGEM_UND, IDX_CP08_MAO_DE_OBRA_UND,
                               IDX_SOMA_CUSTO_UND, IDX_SOMA_CUSTO_TOTAL,
                               IDX_ACB_SUP_UND, IDX_ACB_INF_UND, IDX_SOMA_CUSTO_ACB]:
                     set_item(table, row, col_idx, formatar_valor_moeda(0.0)) # Formata como moeda
                 elif col_idx in [IDX_AREA_M2, IDX_SPP_ML_UND]:
                      set_item(table, row, col_idx, "0.00") # Formata float com 2 casas (ou 4 para area)
                 elif col_idx == IDX_CP09_CUSTO_MP:
                      set_item(table, row, col_idx, "0") # Formata como inteiro "0"

         finally:
             table.blockSignals(False) # Desbloqueia sinais
    """# --- Fim do processamento de linha ---


# --- Função principal: itera e chama o processamento por linha ---
def atualizar_calculos_custos(ui):
    """
    Carrega os dados de custos base do ficheiro Excel "TAB_DEF_PECAS.xlsx"
    e, para cada linha na tabela 'tab_def_pecas', chama a função
    `processar_calculos_para_linha` para realizar todos os cálculos de custos.

    Esta função é chamada pelo orquestrador (`modulo_orquestrador.py`).
    """
    print("[INFO] Iniciando atualização de todos os cálculos de custos...")
    table = ui.tab_def_pecas
    total_linhas = table.rowCount()

    if total_linhas == 0:
        print("[INFO] Tabela de peças vazia. Nenhum cálculo de custo para realizar.")
        return

    # --- Carregar o ficheiro Excel uma vez ---
    caminho_base = ui.lineEdit_base_dados.text().strip()
    folder = os.path.dirname(caminho_base)
    excel_file = os.path.join(folder, "TAB_DEF_PECAS.XLSX")

    df_excel_cp = None
    try:
        # header=4 significa que a 5ª linha do Excel é o cabeçalho (índice 4)
        df_excel_cp = pd.read_excel(excel_file, header=4)
        print(f"[INFO] Ficheiro Excel '{excel_file}' carregado com sucesso para cálculos de custos.")
        # Opcional: Imprimir cabeçalhos lidos para debug
        # print(f"[DEBUG] Cabeçalhos do Excel: {df_excel_cp.columns.tolist()}")
    except FileNotFoundError:
        print(f"[ERRO] Ficheiro Excel '{excel_file}' não encontrado. Cálculos de custos não serão baseados no Excel.")
        QMessageBox.warning(ui, "Ficheiro Não Encontrado", f"O ficheiro de definições de peças '{excel_file}' não foi encontrado.\nOs custos base (CPxx) não serão atualizados a partir do Excel.")
        # Cria um DataFrame vazio para evitar erros posteriores
        df_excel_cp = pd.DataFrame()
    except Exception as e:
        print(f"[ERRO] Erro ao ler o ficheiro Excel '{excel_file}': {e}")
        QMessageBox.critical(ui, "Erro ao Ler Excel", f"Não foi possível ler o ficheiro de definições de peças '{excel_file}':\n{e}\nOs custos base (CPxx) podem estar incorretos.")
        # Cria um DataFrame vazio para evitar erros posteriores
        df_excel_cp = pd.DataFrame()


    # --- Iterar por cada linha e processar os cálculos ---
    for row in range(total_linhas):
        try:
            # print(f"[DEBUG] Chamando processar_calculos_para_linha para linha {row+1}...") # Debug verbose
            # Passa o DataFrame carregado para a função por linha
            processar_calculos_para_linha(ui, row, df_excel_cp)
        except Exception as e:
            # Captura e loga exceções específicas por linha sem parar todo o processo
            print(f"[ERRO INESPERADO] Erro ao processar cálculos na linha {row+1}: {e}")
            import traceback
            traceback.print_exc() # Imprime a stack trace para debug

    print("[INFO] Atualização de todos os cálculos de custos concluída.")


if __name__ == "__main__":
    # Bloco para testes unitários independentes, se necessário.
    # Aqui você simularia um objeto 'ui' e chamaria as funções.
    print("Módulo modulo_calculos_custos.py executado diretamente. Nenhuma ação de UI simulada.")