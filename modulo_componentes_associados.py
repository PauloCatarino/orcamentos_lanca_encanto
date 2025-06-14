# modulo_componentes_associados.py
# -*- coding: utf-8 -*-

"""
Módulo: modulo_componentes_associados.py

Objetivo:
---------
Este módulo contém a lógica para gerenciar componentes associados na tabela 'tab_def_pecas'.
Isso inclui identificar componentes associados (lendo do Excel) e calcular a sua quantidade (QT_und).

Funcionalidades:
----------------
1. Identifica componentes associados para uma linha principal, lendo do ficheiro Excel.
   Esta função é chamada pelo orquestrador para recolher a lista de associados a inserir.
2. Insere uma linha básica para um componente, preenchendo campos mínimos e aplicando cor.
   Esta função é chamada pelo orquestrador durante a fase de inserção de associados.
3. Calcula a quantidade (QT_und) para uma linha específica, se for um componente associado,
   baseado nas regras definidas e nos dados da peça principal acima.
   Esta função é chamada pelo orquestrador na fase de cálculo.
4. Funções auxiliares para ler dados da tabela de forma segura.

O processo de inserção de associados e cálculo é orquestrado por `modulo_orquestrador`.

Dependências:
-------------
- `pandas`: Para ler o ficheiro Excel.
- `os`: Para manipulação de caminhos de ficheiros.
- `PyQt5.QtWidgets`: QTableWidgetItem, QMessageBox, QPushButton (para o botão MP).
- `PyQt5.QtCore`: Qt, QColor.
- `utils.py`: Funções utilitárias como safe_item_text, get_valor_numero.
# Importações locais são usadas onde apropriado para evitar ciclos de importação.
"""

import os
import pandas as pd
from PyQt5.QtWidgets import QTableWidgetItem, QMessageBox, QPushButton
from PyQt5.QtCore import Qt       # Para Qt.Checked, etc.
from PyQt5.QtGui import QColor    # Importar QColor para ajustar cor do MODULO

# Importar funções utilitárias
from utils import safe_item_text, converter_texto_para_valor, set_item # get_valor_numero já existia no seu código


# --- Constantes de Índices das Colunas ---
# Índices fixos para as colunas usadas e preenchidas na tabela "tab_def_pecas" (0-based)
IDX_DEF_PECA = 2             # Tipo de peça
IDX_QT_MOD = 4               # Quantidade modificada (QT_mod) - coluna 4
IDX_QT_UND = 5               # Quantidade unitária (a ser calculada para associados)
IDX_COMP = 6                 # Coluna COMP
IDX_BLK = 12                 # Checkbox BLK - Bloqueia atualização automática
IDX_MAT_DEFAULT = 13         # Mat_Default
IDX_TAB_DEFAULT = 14         # Tab_Default
IDX_IDS = 15                 # ids (Item Orçamento)
IDX_NUM_ORC = 16             # num_orc
IDX_VER_ORC = 17             # ver_orc
IDX_COMP_RES = 50            # Resultado do Comprimento (mm) da peça principal
IDX_LARG_RES = 51            # Resultado da Largura (mm) da peça principal
IDX_ESP_RES = 52             # Resultado da Espessura (mm) da peça principal
IDX_QT_TOTAL = 49            # Quantidade Total (Qt_mod * Qt_und) da peça principal (usado em algumas regras QT_und associado)
IDX_MP_BUTTON = 33           # Coluna onde fica o botão "Escolher" Material/Preço
IDX_GRAVAR_MODULO = 53       # Checkbox Gravar Modulo
IDX_ACB_SUP = 59             # Checkbox Acabamento Superior
IDX_ACB_INF = 60             # Checkbox Acabamento Inferior
IDX_COMP_ASS_1 = 34          # Coluna COMP_ASS_1 (Nome do 1º componente associado)
IDX_COMP_ASS_2 = 35          # Coluna COMP_ASS_2 (Nome do 2º componente associado)
IDX_COMP_ASS_3 = 36          # Coluna COMP_ASS_3 (Nome do 3º componente associado)


# --- Cores para identificar tipos de linha ---
COLOR_ASSOCIATED_BG = QColor(230, 240, 255) # Azul claro para linhas de componentes associados
COLOR_PRIMARY_WITH_ASS_BG = QColor(180, 200, 255) # Azul mais escuro para linha principal com associados
COLOR_MODULO_BG = QColor(220, 220, 220) # Cinza claro para linhas MODULO


##########################################################################
# 1. Identifica componentes associados para uma linha principal
##########################################################################
def identificar_componentes_associados_para_linha(ui, row, df_excel_cp):
    """
    Chamada pelo orquestrador.
    Para uma linha `row` (potencialmente uma linha principal):
      - Lê o tipo de peça (Def_Peca).
      - Procura no DataFrame `df_excel_cp` (carregado do Excel) se há
        componentes associados (COMP_ASS_1, COMP_ASS_2, COMP_ASS_3) definidos.
      - Preenche as colunas 34, 35, 36 na linha atual com os nomes dos associados encontrados.
      - Retorna uma LISTA com os nomes dos componentes associados que devem ser
        inseridos como novas linhas na tabela.

    NÃO insere as linhas AQUI. APENAS IDENTIFICA e RETORNA a lista.
    NÃO altera a cor de fundo da linha principal AQUI (feito no orquestrador
    após coletar todos os associados a serem inseridos).

    Respeita a flag BLK (coluna 12). Se BLK estiver True, a busca no Excel
    para COMP_ASS_x é saltada, e uma lista vazia é retornada. Os valores
    existentes nas colunas 34-36 são mantidos.

    Parâmetros:
    -----------
    ui : objeto Ui_MainWindow
        A interface principal.
    row : int
        O índice da linha a ser verificada.
    df_excel_cp : pandas.DataFrame
        DataFrame carregado do ficheiro Excel 'TAB_DEF_PECAS.xlsx'.

    Retorna:
    --------
    list: Uma lista de strings, cada uma sendo o nome de um componente
          associado a ser inserido, ou uma lista vazia.
    """
    table = ui.tab_def_pecas

    associados_definidos_para_principal = [] # Nomes lidos do Excel (se não BLK) ou das cols 34-36 (se BLK)

    # --- Obter Def_Peca da linha principal ---
    def_peca_principal_val = safe_item_text(table, row, IDX_DEF_PECA).strip().upper()
    if not def_peca_principal_val:
        return [] # Linha principal sem Def_Peca, não pode ter associados

    # --- Verificar BLK ---
    blk_item = table.item(row, IDX_BLK)
    linha_principal_bloqueada = blk_item and blk_item.checkState() == Qt.Checked

    if linha_principal_bloqueada:
        #print(f"[ID_ASSOC] Linha Principal {row+1} ('{def_peca_principal_val}') está BLK. Lendo COMP_ASS_x das células.")
        for col_idx in [IDX_COMP_ASS_1, IDX_COMP_ASS_2, IDX_COMP_ASS_3]:
            comp_name = safe_item_text(table, row, col_idx).strip()
            if comp_name:
                associados_definidos_para_principal.append(comp_name)
    else:
        # Não BLK: Ler do Excel e preencher colunas 34-36
        if df_excel_cp is None or df_excel_cp.empty:
            return []
        
        # Assegurar que a coluna de busca existe e está limpa
        # (Esta lógica de criação de 'DEF_PECA_CLEAN' deve ser robusta)
        # CORREÇÃO: esta lógica de criação de coluna clean deve ser feita com cuidado.
        # Idealmente, o df_excel_cp já viria com esta coluna ou seria tratada de forma mais central.
        # Por agora, mantendo a lógica como estava na sua versão original

        if 'DEF_PECA_CLEAN' not in df_excel_cp.columns:
            if "DEF_PECA" in df_excel_cp.columns:
                df_excel_cp['DEF_PECA_CLEAN'] = df_excel_cp['DEF_PECA'].astype(str).str.strip().str.upper()
            elif df_excel_cp.shape[1] > 0:
                df_excel_cp['DEF_PECA_CLEAN'] = df_excel_cp.iloc[:, 0].astype(str).str.strip().str.upper()
            else:
                # DataFrame está realmente vazio ou sem colunas apropriadas
                 #print("[AVISO] DataFrame do Excel está vazio ou não tem coluna 'DEF_PECA' ou primeira coluna para busca.")
                return []
        
        row_excel = df_excel_cp[df_excel_cp['DEF_PECA_CLEAN'] == def_peca_principal_val]

        if row_excel.empty:
            # Limpar colunas 34-36 na UI se não encontrar no Excel
            # table.blockSignals(True) # O orquestrador pode bloquear sinais se necessário
            # try:
            #     for col_idx in [IDX_COMP_ASS_1, IDX_COMP_ASS_2, IDX_COMP_ASS_3]:
            #          set_item(table, row_principal, col_idx, "")
            # finally:
            #      table.blockSignals(False)
            return []

        row_excel_data = row_excel.iloc[0]
        comp_col_names_excel = ['COMP_ASS_1', 'COMP_ASS_2', 'COMP_ASS_3']
        
        # table.blockSignals(True) # Orquestrador pode gerir bloqueio de sinais
        try:
            for i, col_name_excel in enumerate(comp_col_names_excel):
                val = row_excel_data.get(col_name_excel)
                val_str = str(val).strip() if pd.notna(val) and isinstance(val, str) else ""
                
                col_idx_ui = IDX_COMP_ASS_1 + i
                set_item(table, row, col_idx_ui, val_str) # Preenche cols 34-36 da principal
                if val_str:
                    associados_definidos_para_principal.append(val_str)
        finally:
            pass # table.blockSignals(False)

    # --- Verificar quais dos `associados_definidos_para_principal` já existem e estão formatados ---
    associados_a_inserir_agora = []
    if not associados_definidos_para_principal:
        return []

    #print(f"[ID_ASSOC] Linha Principal {row_principal+1} ('{def_peca_principal_val}'). Associados definidos: {associados_definidos_para_principal}")

    # Contar quantas linhas de cada associado definido já existem E ESTÃO FORMATADAS abaixo
    # Itera pelos nomes únicos para evitar problemas se o mesmo associado estiver listado várias vezes
    for nome_assoc_esperado in list(dict.fromkeys(associados_definidos_para_principal)): # Nomes únicos
        # Quantas vezes este nome_assoc_esperado está na lista original (para saber quantos deveriam existir)
        ocorrencias_esperadas = associados_definidos_para_principal.count(nome_assoc_esperado)
        ocorrencias_encontradas_e_formatadas = 0

        # Procurar em TODAS as linhas abaixo da principal
        for r_check in range(row + 1, table.rowCount()):
            # Parar de procurar se encontrarmos outra linha principal ou MODULO
            # (assumindo que associados de uma principal não se misturam com os da próxima)
            item_def_check_stop = table.item(r_check, IDX_DEF_PECA)
            if item_def_check_stop:
                cor_fundo_stop = item_def_check_stop.background().color()
                nome_peca_stop = item_def_check_stop.text().strip().upper() # Obter nome para verificar "MODULO"
                if cor_fundo_stop.name() == COLOR_PRIMARY_WITH_ASS_BG.name() or \
                   cor_fundo_stop.name() == COLOR_MODULO_BG.name() or \
                   nome_peca_stop == "MODULO": # Verificar também pelo nome "MODULO"
                    #print(f"[ID_ASSOC] Stop search for '{nome_assoc_esperado}' at L{r_check+1} (nova principal/modulo)")
                    break 
            
            item_def_check = table.item(r_check, IDX_DEF_PECA)
            if item_def_check:
                texto_peca_check = item_def_check.text().strip().upper()
                cor_fundo_check = item_def_check.background().color()
                
                if texto_peca_check == nome_assoc_esperado.upper() and \
                   cor_fundo_check.name() == COLOR_ASSOCIATED_BG.name():
                    ocorrencias_encontradas_e_formatadas += 1
        
        # Quantos faltam inserir para este nome_assoc_esperado
        faltam_inserir = ocorrencias_esperadas - ocorrencias_encontradas_e_formatadas
        if faltam_inserir > 0:
            #print(f"[ID_ASSOC] Para '{nome_assoc_esperado}': Esperados={ocorrencias_esperadas}, Encontrados Form.={ocorrencias_encontradas_e_formatadas}. Faltam={faltam_inserir}")
            for _ in range(faltam_inserir):
                associados_a_inserir_agora.append(nome_assoc_esperado)
    
    # if associados_a_inserir_agora:
    #    print(f"[ID_ASSOC] Linha Principal {row_principal+1} ('{def_peca_principal_val}'). FINALMENTE A INSERIR: {associados_a_inserir_agora}")
    return associados_a_inserir_agora


##########################################################################
# 2. Insere linha básica para um componente (chamada pelo orquestrador)
##########################################################################
# Esta função já foi adaptada no módulo tabela_def_pecas_items.py.
# Vamos apenas garantir que a versão correta está sendo usada.
# Ela deve apenas inserir a linha, preencher colunas 0-17, 33, 53, 59, 60,
# e aplicar a cor azul clara e o grupo no UserRole.
# NÃO deve chamar outras funções de cálculo ou atualização.

# from tabela_def_pecas_items import inserir_linha_componente # Já importado no topo


##########################################################################
# 3. 3. Cálculo / formatação de QT_und, QT_mod e QT_Total para COMPONENTES
#    ASSOCIADOS (linhas a azul-claro)
##########################################################################
def processar_qt_und_associado_para_linha(ui, row):
    """
    Processa UMA linha que seja componente associado.

    * Identifica a linha principal imediatamente acima;
    * Vai buscar as medidas COMP_res / LARG_res da principal **em texto**;
    * Aplica a regra em `regras_qt_und` → devolve (qt_calc, tooltip);
    * Preenche:
        –  QT_und   (col. 5)
        –  QT_mod   (col. 4)  ►   QT_mod_módulo × QT_und_principal × QT_und_associado
        –  QT_Total (col. 49) ►   produto dos três factores
    Todas as células ganham um tooltip descritivo.
    """
    # ------------- atalhos úteis ------------------------------------------------
    t          = ui.tab_def_pecas
    col        = lambda c: safe_item_text(t, row, c)            # texto célula actual
    col_up     = lambda r,c: safe_item_text(t, r, c)            # texto célula qualquer
    is_assoc   = lambda r: t.item(r, IDX_DEF_PECA)              \
                            and t.item(r, IDX_DEF_PECA).background().color().getRgb()[:3] \
                                == COLOR_ASSOCIATED_BG.getRgb()[:3]
    # Se não for associado --> nada a fazer
    if not is_assoc(row):
        return

    # Linha bloqueada?  (BLK ✓)
    if t.item(row, IDX_BLK) and t.item(row, IDX_BLK).checkState() == Qt.Checked:
        return                                                # respeitamos o bloqueio

    # -------- 1) Localiza a LINHA PRINCIPAL (primeira acima que não é associada) --
    linha_principal = None
    for r in range(row-1, -1, -1):
        if not is_assoc(r):                                   # primeira não-associada acima
            linha_principal = r
            break
    if linha_principal is None:
        set_item(t, row, IDX_QT_UND, "0")
        t.item(row, IDX_QT_UND).setToolTip("Erro: peça principal não encontrada.")
        return

    # -------- 2) Medidas da peça principal (TEXTO, sem converter para float) -----
    medidas_principal = {
        "COMP": col_up(linha_principal, IDX_COMP_RES),        # ex. "500"
        "LARG": col_up(linha_principal, IDX_LARG_RES),
        "ESP" : col_up(linha_principal, IDX_ESP_RES),
    }

    # -------- 3) Quantidades de contexto ----------------------------------------
    qt_und_principal = converter_texto_para_valor(
                           col_up(linha_principal, IDX_QT_UND), "moeda") or 1

    #   • QT_mod_MÓDULO  == coluna 4 da ÚLTIMA linha "MODULO" acima da principal
    qt_mod_modulo = 1
    linha_modulo  = None
    for r in range(linha_principal-1, -1, -1):
        if col_up(r, IDX_DEF_PECA).upper() == "MODULO":
            linha_modulo = r
            break
    if linha_modulo is not None:
        # O número do módulo está em QT_mod (col-4) – não em QT_und!
        qt_mod_modulo = converter_texto_para_valor(
                            col_up(linha_modulo, IDX_QT_MOD).split(" x ")[0], "moeda") or 1

    # -------- 4) Calcula QT_und do associado ------------------------------------
    def_peca_associado  = col(IDX_DEF_PECA).upper()
    def_peca_principal  = col_up(linha_principal, IDX_DEF_PECA).upper()

    qt_calc, tt_regra = calcular_qt_und_componente(
                            def_peca_associado,
                            medidas_principal,
                            def_peca_principal,
                            qt_und_principal,
                            ui)

    qt_und_associado = int(round(qt_calc))

    if def_peca_associado == "VARAO ROUPEIRO":
        valor_comp = medidas_principal.get("COMP", "")
        set_item(t, row, IDX_COMP, valor_comp)

    # -------- 5) Escreve QT_und (col. 5) ----------------------------------------
    set_item(t, row, IDX_QT_UND, str(qt_und_associado))
    t.item(row, IDX_QT_UND).setToolTip(tt_regra)

    # -------- 6) Fórmula QT_mod  -------------------------------------------------
    qt_mod_texto = f"{int(qt_mod_modulo)} x {int(qt_und_principal)} x {qt_und_associado}"
    qt_mod_val   = qt_mod_modulo * qt_und_principal * qt_und_associado

    item_qm = t.item(row, IDX_QT_MOD) or QTableWidgetItem()
    item_qm.setText(qt_mod_texto)
    item_qm.setFlags(item_qm.flags() & ~Qt.ItemIsEditable)
    item_qm.setToolTip(f"{qt_mod_texto}  =  {int(qt_mod_val)}")
    t.setItem(row, IDX_QT_MOD, item_qm)

    # -------- 7) QT_Total --------------------------------------------------------
    set_item(t, row, IDX_QT_TOTAL, str(int(qt_mod_val)))
    t.item(row, IDX_QT_TOTAL).setToolTip(f"QT_Total = {qt_mod_texto} = {int(qt_mod_val)}")


##############################################
# Parte 6.1: Lógica para calcular QT_und de componentes associados (Regras)
##############################################
# =======================================================
# Dicionário com regras de cálculo por tipo de componente
# =======================================================
# Mantido como estava, apenas a função que o usa (calcular_qt_und_componente) foi adaptada.
regras_qt_und = {
    "PES_1": {
        "formula": lambda m: 4 if m["COMP"] < 650 and m["LARG"] < 800 else \
                              6 if m["COMP"] >= 650 and m["LARG"] < 800 else 8,
        "tooltip": "4 se COMP<650 & LARG<800 | 6 se COMP≥650 & LARG<800 | 8 caso contrário"
    },

    "SUPORTE PRATELEIRA": {
        "formula": lambda m: 8 if m["COMP"] >= 1100 and m["LARG"] >= 800 else \
                              6 if m["COMP"] >= 1100 else 4,
        "tooltip": "4 por defeito | 6 se COMP≥1100 | 8 se COMP≥1100 & LARG≥800"
    },

    "VARAO ROUPEIRO": {
        "default": 1,
        "tooltip": "1 varão por peça principal. (COMP é herdado para cálculo de ML)"
    },

    "SUPORTE VARAO": {
        "default": 2,
        "tooltip": "2 suportes por varão (assumindo 1 varão por peça principal)"
    },

    "DOBRADICA": {
        "formula": lambda m: (
            # Lógica base dependendo do COMP
            (
                2 if float(m.get("COMP", 0)) < 850 else
                3 if float(m.get("COMP", 0)) < 1600 else
                # Cálculo para COMP >= 1600: 2 + parte inteira de ((COMP - 240) / 750)
                # Usamos m.get("COMP", 0) para segurança caso a chave não exista
                2 + int((float(m.get("COMP", 0)) - 2 * 120) / 750)
            )
            # Adiciona 1 se LARG >= 605
            + (1 if float(m.get("LARG", 0)) >= 605 else 0)
        ),
        "tooltip": "2 se COMP<850mm, 3 se COMP<1600mm, >=1600mm: 2+(úteis/750mm) +1 se LARG >= 605mm"
    },

    "PUXADOR": {
        # NOTA: Regra original usava qt_und da porta. Isso é feito abaixo na função.
        "default": 1, # Valor base antes de multiplicar pelo QT_und do principal
        "tooltip": "1 puxador por porta Quantidade = QT_und da peça principal."
    }
}


##########################################################################
# 4. Função que calcula a quantidade (QT_und) de componente associado (Adaptada)
##########################################################################
def calcular_qt_und_componente(nome_componente, medidas_principal, def_peca_principal, qt_und_principal=1, ui=None):
    """
    Calcula a quantidade (QT_und) para um componente associado com base no seu tipo
    e nos dados da peça principal.

    Parâmetros:
    -----------
    nome_componente : str
        Nome do componente associado (ex: "DOBRADICA").
    medidas_principal : dict
        Dicionário com medidas ('COMP', 'LARG', 'ESP') e 'QT_TOTAL' da peça principal (como strings).
    def_peca_principal : str
        Texto "Def_Peca" da peça principal.
    qt_und_principal : int or float
        Quantidade unitária (QT_und) da peça principal.
    ui : objeto Ui_MainWindow (opcional, passado mas não deve ser usado para modificar UI aqui)

    Retorna:
    --------
    tuple (float, str): Uma tupla contendo a quantidade calculada (float) e um texto de tooltip.
    """
    try:
        nome_upper = nome_componente.strip().upper()
        regra = regras_qt_und.get(nome_upper)

        if not regra:
            return (1, f"Sem regra definida para '{nome_upper}'. Valor por defeito: 1")

        tooltip = regra.get("tooltip", "")
        qt_calc = 1

        # Prepara dicionário de medidas como floats válidos
        medidas_float = {
            "COMP": converter_texto_para_valor(medidas_principal.get("COMP", 0), "moeda") or 0.0,
            "LARG": converter_texto_para_valor(medidas_principal.get("LARG", 0), "moeda") or 0.0,
            "ESP": converter_texto_para_valor(medidas_principal.get("ESP", 0), "moeda") or 0.0,
        }

        if callable(regra.get("formula")):
            try:
                qt_calc = regra["formula"](medidas_float)
            except Exception as e:
                return (1, f"Erro na regra '{nome_upper}': {e}")
        elif "default" in regra:
            qt_calc = regra["default"]
        else:
            qt_calc = 1

        
        # =============================
        # Novo comportamento controlado por regra
        # =============================
        # Se a regra tiver "multiplica_qt_und_principal", aplicamos multiplicação
        multiplica_qt_und = regra.get("multiplica_qt_und_principal", False)

        if multiplica_qt_und:
            print(f"[DEBUG] {nome_upper} - Multiplicando QT_calc={qt_calc} por QT_und principal={qt_und_principal}")
            qt_calc *= qt_und_principal
            tooltip += f"\nMultiplicado pelo QT_und da peça principal ({qt_und_principal})"

        # Exibir valor final
        print(f"[QT_UND Calculado] {nome_upper} = {qt_calc} → {tooltip}")
        return (qt_calc, tooltip)
        


    except Exception as e:
        # Captura erros durante o cálculo da quantidade
        print(f"[ERRO] Cálculo de QT_und para componente associado '{nome_upper}': {e}")
        # Importar traceback localmente se necessário para ver a stack trace completa
        # import traceback
        # traceback.print_exc()
        return float(qt_und_principal), f"Erro no cálculo. Usando QT_und Principal ({int(round(qt_und_principal))})." # Retorna QT_und principal como fallback


# As funções auxiliares abaixo (get_valor_numero, obter_valores_componente_principal, obter_qt_und_linha_base)
# são usadas por processar_qt_und_associado_para_linha e estão corretas.
# Mantidas ou importadas de utils.py.

# =======================================================
# 4. Função auxiliar para converter item de célula em número
# =======================================================
# from utils import get_valor_numero # Já importado no topo


# =======================================================
# 5. Leitura segura das medidas da peça principal (linha base)
# =======================================================
def obter_valores_componente_principal(tabela, linha_base):
    """
    Lê de forma segura as medidas resultantes (Comp_res, Larg_res, Esp_res) e o Qt_Total
    da peça principal (linha_base).

    Retorna um dicionário com esses valores como STRINGS (como estão na UI).
    A conversão para número deve ser feita pela função que usa este dicionário.
    """
    # Índices das colunas de resultado e quantidade total na UI
    comp_res_idx = IDX_COMP_RES
    larg_res_idx = IDX_LARG_RES
    esp_res_idx = IDX_ESP_RES
    qt_total_idx = IDX_QT_TOTAL

    # Usa safe_item_text para obter o texto, com default ""
    comp_res_text = safe_item_text(tabela, linha_base, comp_res_idx, "")
    larg_res_text = safe_item_text(tabela, linha_base, larg_res_idx, "")
    esp_res_text = safe_item_text(tabela, linha_base, esp_res_idx, "")
    qt_total_text = safe_item_text(tabela, linha_base, qt_total_idx, "1") # Default "1" para Qt_Total

    # Retorna um dicionário com os valores como strings
    return {
        "COMP": comp_res_text,
        "LARG": larg_res_text,
        "ESP": esp_res_text,
        "QT_TOTAL": qt_total_text
    }


##########################################################################
# 6. Obter QT_und da Linha Base (Principal)
##########################################################################
def obter_qt_und_linha_base(tabela, linha_base):
    """
    Obtém o valor numérico (inteiro, arredondado) da coluna QT_und (índice 5)
    da linha principal (linha_base).

    Retorna um inteiro (arredondado). Retorna 1.0 se a célula estiver vazia ou inválida.
    """
    # Usa safe_item_text para obter o texto e converter_texto_para_valor para converter para número
    qt_und_text = safe_item_text(tabela, linha_base, IDX_QT_UND, "1") # Default "1"

    # Converte o texto para um número float
    qt_und_float = converter_texto_para_valor(qt_und_text, "moeda") # Assume que QT_und pode ter casas decimais na UI (embora deva ser inteiro)

    # Retorna a parte inteira (arredondada)
    return float(int(round(qt_und_float))) # Retorna float para consistência em cálculos