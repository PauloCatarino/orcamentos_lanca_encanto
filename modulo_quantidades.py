# modulo_quantidades.py
# -*- coding: utf-8 -*-

"""
Módulo: modulo_quantidades.py

Objetivo:
---------
Este módulo contém a lógica para processar as fórmulas de quantidades e dimensões
inseridas nas colunas 'Comp', 'Larg', 'Esp' e 'QT_mod' da tabela 'tab_def_pecas'.

As fórmulas podem conter:
  - Números (ex: "1000")
  - Variáveis globais definidas na 'tab_modulo_medidas' (H, L, P, H1...P4)
  - Variáveis locais definidas na linha 'MODULO' imediatamente anterior (HM, LM, PM)
  - Operadores aritméticos (+, -, *, /)

Funcionalidades:
----------------
1. `processar_formulas_e_quantidades_para_linha`: Processa UMA ÚNICA linha da tabela,
   avaliando as fórmulas nas colunas 'Comp', 'Larg', 'Esp', 'QT_mod', substituindo
   as variáveis pelas suas respetivas medidas.
2. `atualizar_dados_modulos`: Itera sobre a tabela 'tab_def_pecas', identifica as linhas
   'MODULO' para coletar as variáveis locais (HM, LM, PM), e chama a função de processamento
   por linha para todas as outras linhas, aplicando as variáveis corretas e as globais.
   Calcula também o 'Qt_Total' e formata a coluna 'QT_mod' para linhas não-MODULO.

Dependências:
-------------
- `utils.py`: Para funções como `converter_texto_para_valor`, `avaliar_formula_segura`,
  `validar_expressao_modulo`, e `VARIAVEIS_VALIDAS`.
"""

import re
from PyQt5.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt5.QtCore import Qt       # Para Qt.Checked, etc.
from PyQt5.QtGui import QColor    # Importar QColor para ajustar cor do MODULO
# Importa constantes de cores de outro módulo
from modulo_componentes_associados import COLOR_ASSOCIATED_BG, COLOR_MODULO_BG, COLOR_PRIMARY_WITH_ASS_BG # Importa as cores
from utils import converter_texto_para_valor, avaliar_formula_segura, validar_expressao_modulo, VARIAVEIS_VALIDAS, safe_item_text, set_item
from modulo_componentes_associados import (COLOR_ASSOCIATED_BG, COLOR_MODULO_BG, IDX_COMP_ASS_1, IDX_COMP_ASS_2, IDX_COMP_ASS_3)

# Definição dos índices importantes das colunas da tabela "tab_def_pecas"
IDX_DEF_PECA   = 2   # Coluna que contém o tipo de peça (Def_Peca)
IDX_QT_MOD     = 4   # Coluna que contém a quantidade modificada (QT_mod)
IDX_QT_UND     = 5   # Coluna que contém a quantidade unitária (QT_und)
IDX_COMP       = 6   # Coluna para COMP (comprimento, etc.) - Fórmula
IDX_LARG       = 7   # Coluna para LARG (largura) - Fórmula
IDX_ESP        = 8   # Coluna para ESP (espesura) - Fórmula
IDX_QT_TOTAL   = 49  # Coluna para o cálculo do total (QT_TOTAL) - Resultado
IDX_COMP_RES   = 50  # Coluna para o resultado de COMP (comp_res) - Resultado
IDX_LARG_RES   = 51  # Coluna para o resultado de LARG (larg_res) - Resultado
IDX_ESP_RES    = 52  # Coluna para o resultado de ESP (esp_res) - Resultado
IDX_BLK        = 12  # Coluna BLK (checkbox) - Bloqueia atualização automática


###########################################################################
# 1. Função: processar_formulas_e_quantidades_para_linha (NOVA)
###########################################################################
def processar_formulas_e_quantidades_para_linha(ui, row, vars_globais, vars_modulo_local, qt_mod_modulo_atual):
    """
    Processa as fórmulas nas colunas Comp, Larg, Esp e QT_mod para uma ÚNICA linha.

    Avalia as fórmulas, substitui variáveis globais e locais, calcula resultados,
    preenche as colunas _res e calcula o Qt_Total.

    Avalia fórmulas em Comp, Larg, Esp e QT_mod, preenche colunas _res,
    formata QT_mod e actualiza QT_Total.
    Agora QT_Total das linhas **principais** (aquelas que têm comps associados
    nas colunas 34‑36) passa a ser:
        QT_Total = qt_mod_modulo_atual × QT_und
    """
    tabela = ui.tab_def_pecas

    # Não processar linhas vazias ou a própria linha MODULO aqui
    def_peca_item = tabela.item(row, IDX_DEF_PECA)
    if not def_peca_item or not def_peca_item.text().strip():
        return # Ignora linhas vazias

    texto_def_peca = def_peca_item.text().strip().upper()
    linha_modulo = texto_def_peca == "MODULO"
  
    # --- Verifica o checkbox BLK (coluna 12) ---
    blk_item = tabela.item(row, IDX_BLK)
    # Define uma flag para saber se a linha está bloqueada
    linha_bloqueada = blk_item and blk_item.checkState() == Qt.Checked

    # Lê a unidade de medida (ex: M2, ML, UND)
    und = safe_item_text(tabela, row, IDX_QT_UND, "UND").strip().upper()

    # Flags que controlam se vamos calcular ou obrigar preenchimento nas colunas
    calcular_comp = calcular_larg = calcular_esp = True
    obrigatorio_comp = obrigatorio_larg = False

    # Define lógica com base na unidade de medida
    if und == "UND":
        calcular_comp = calcular_larg = calcular_esp = False
    elif und == "ML":
        calcular_larg = calcular_esp = False
        obrigatorio_comp = True
    elif und == "M2":
        calcular_comp = calcular_larg = True
        obrigatorio_comp = obrigatorio_larg = True

    # Processar fórmulas e _res SEMPRE, independentemente de BLK
    for nome_col, idx_formula, idx_res, calcular, obrigatorio in [
        ('Comp', IDX_COMP, IDX_COMP_RES, calcular_comp, obrigatorio_comp),
        ('Larg', IDX_LARG, IDX_LARG_RES, calcular_larg, obrigatorio_larg),
        ('Esp', IDX_ESP, IDX_ESP_RES, calcular_esp, False),
        ('QT_mod', IDX_QT_MOD, None, True, False)
    ]:
        # Garante que a célula existe
        cel_formula = tabela.item(row, idx_formula)
        if not cel_formula:
            cel_formula = QTableWidgetItem("")
            tabela.setItem(row, idx_formula, cel_formula)

        formula_original = cel_formula.text().strip().upper()
        if cel_formula.text() != formula_original:
            cel_formula.setText(formula_original)

        # Alerta se for obrigatório preencher e estiver vazio
        if obrigatorio and formula_original == "":
            QMessageBox.warning(ui, "Aviso", f"Linha {row+1}: A coluna {nome_col} deve ser preenchida porque a unidade é '{und}'.")

        formula_avaliada = formula_original

        # Substitui variáveis locais (HM, LM, PM) para peças diferentes de MODULO
        if not linha_modulo:
            for vbase, subst_var in zip(['H', 'L', 'P'], ['HM', 'LM', 'PM']):
                val_mod = vars_modulo_local.get(subst_var, "0").strip()
                if val_mod and converter_texto_para_valor(val_mod, "moeda") is not None:
                    formula_avaliada = re.sub(rf'\b{subst_var}\b', val_mod, formula_avaliada)

        # Substitui variáveis globais (H, L, P...)
        for var, val in vars_globais.items():
            if val and converter_texto_para_valor(val, "moeda") is not None:
                formula_avaliada = re.sub(rf'\b{var}\b', val, formula_avaliada)

        # Converte vírgula decimal e avalia a expressão
        #formula_para_eval = formula_avaliada.replace(",", ".")
        formula_para_eval = formula_avaliada.replace(",", ".").replace(" X ", " * ")
        resultado_num = avaliar_formula_segura(formula_para_eval)

        # Preenche colunas _res (resultado) apenas se necessário
        if idx_res is not None and calcular:
            resultado_str = ""
            tooltip_texto = ""
            if resultado_num is not None:
                resultado_str = f"{resultado_num:.2f}"
                tooltip_texto = (
                    f"Fórmula Original: {nome_col} = {formula_original}\n"
                    f"Com Variáveis Substituídas: {formula_avaliada}\n"
                    f"Resultado Calculado: {resultado_str}"
                )
                set_item(tabela, row, idx_res, resultado_str)
                item_res = tabela.item(row, idx_res)
                if item_res:
                    item_res.setBackground(Qt.white)
                    item_res.setToolTip(tooltip_texto)
            else:
                # Se houver erro na fórmula, deixa a célula vermelha
                set_item(tabela, row, idx_res, "")
                item_res = tabela.item(row, idx_res)
                if item_res:
                    item_res.setBackground(Qt.red)
                    item_res.setToolTip(f"Erro ao calcular: {formula_original}")

            # Tooltip adicional diretamente na célula de fórmula (IDX_COMP, IDX_LARG, IDX_ESP)
            item_formula = tabela.item(row, idx_formula)
            if item_formula:
                item_formula.setToolTip(tooltip_texto)
            

    # Cálculo do QT_TOTAL = QT_mod * QT_und
    qt_mod_text = safe_item_text(tabela, row, IDX_QT_MOD, "1").strip()
    qt_mod_parte_numerica_str = qt_mod_text.split(" x ")[0]
    qt_mod_cel_val = converter_texto_para_valor(qt_mod_parte_numerica_str, "moeda") or 1.0
    qt_und_cel_val = converter_texto_para_valor(safe_item_text(tabela, row, IDX_QT_UND, "1"), "moeda") or 1.0


    # Corrigir valores inválidos
    if qt_mod_cel_val <= 0:
        qt_mod_cel_val = 1.0
    if qt_und_cel_val <= 0:
        qt_und_cel_val = 1.0

    # Depois: podes calcular o QT_Total
    #tem_associados = any(safe_item_text(tabela, row, idx).strip() for idx in (IDX_COMP_ASS_1, IDX_COMP_ASS_2, IDX_COMP_ASS_3))

    linha_tem_modulo_acima = qt_mod_modulo_atual > 1  # Já vem da função iteradora
    if not linha_modulo and linha_tem_modulo_acima:
        # Formato especial baseado em MODULO acima
        qt_total_calculado = int(qt_mod_modulo_atual * qt_und_cel_val)
    else:
        # Formato normal (usado se a linha for MODULO ou se for independente)
        qt_total_calculado = int(qt_mod_cel_val * qt_und_cel_val)

    # Finalmente: preencher a célula QT_TOTAL
    set_item(tabela, row, IDX_QT_TOTAL, str(qt_total_calculado))
    item_qt_total = tabela.item(row, IDX_QT_TOTAL)
    if item_qt_total:
        item_qt_total.setToolTip(f"QT_Total calculado = {qt_total_calculado}")




    # —— Formatação de QT_mod ——
    item_qt_mod = tabela.item(row, IDX_QT_MOD) or QTableWidgetItem()
    if not linha_modulo:
        item_qt_mod.setText(f"{int(qt_mod_modulo_atual)} x {int(qt_und_cel_val)}")
        item_qt_mod.setFlags(item_qt_mod.flags() & ~Qt.ItemIsEditable)
        tooltip_qt_mod = (
        "Cálculo Automático:\n"
        f"QT_mod = QT_mod do módulo ({int(qt_mod_modulo_atual)}) × QT_und ({int(qt_und_cel_val)})\n"
        f"Resultado: {int(qt_mod_modulo_atual * qt_und_cel_val)}"
        )
        item_qt_mod.setToolTip(tooltip_qt_mod)
    else:
        item_qt_mod.setToolTip("Linha MODULO: QT_mod definido manualmente.")
    tabela.setItem(row, IDX_QT_MOD, item_qt_mod)

    if not linha_modulo:
        item_qt_und = tabela.item(row, IDX_QT_UND)
        if item_qt_und:
            item_qt_und.setText(str(int(qt_und_cel_val)))
            item_qt_und.setToolTip(f"Valor QT_und = {qt_und_cel_val:.0f}, inserido manualmente ou herdado.")

    elif linha_modulo:
        item_qt_und = tabela.item(row, IDX_QT_UND)
        if item_qt_und and item_qt_und.text().strip():
            item_qt_und.setBackground(Qt.red)
            item_qt_und.setToolTip("Linha MODULO: a coluna QT_und deve ficar vazia.")


    # Retornar valores calculados se necessário para outros módulos (opcional)
    # return resultado_comp_res, resultado_larg_res, resultado_esp_res, qt_total_calculado # Exemplo


###########################################################################
# 2. Função: atualizar_dados_modulos (Iterador para chamar a função por linha)
###########################################################################
def atualizar_dados_modulos(ui):
    """
    Itera sobre a tabela 'tab_def_pecas', identifica as linhas MODULO,
    coleta as variáveis locais (HM, LM, PM) e a quantidade do módulo (QT_mod).
    
    
    Para cada linha encontrada (incluindo MODULO e não-MODULO), chama a função
    `processar_formulas_e_quantidades_para_linha` para avaliar as fórmulas
    usando as variáveis globais e locais corretas.

    Aplica a cor cinza claro às linhas MODULO e garante cor branca para as outras (exceto associados com cor azul clara).

    
    É chamada pelo orquestrador (`modulo_orquestrador.py`).
    """
    print("[INFO] Iniciando atualização de dados de módulos (fórmulas e quantidades)...")

    tabela = ui.tab_def_pecas
    medidas_table = ui.tab_modulo_medidas

    total_linhas = tabela.rowCount()
    if total_linhas == 0:
        print("[INFO] Tabela de peças vazia. Nenhuma fórmula para processar.")
        return

    # 1. Lê as variáveis globais da tab_modulo_medidas (1ª linha apenas)
    vars_globais = {}
    if medidas_table.rowCount() > 0:
        for i in range(medidas_table.columnCount()):
            header_item = medidas_table.horizontalHeaderItem(i)
            if header_item is None: continue
            var_name = header_item.text().strip().upper() # Nome da variável (H, L, P, H1, etc.)
            val_item = medidas_table.item(0, i)
            val_text = safe_item_text(medidas_table, 0, i).strip().upper() # Valor da variável
            # Apenas adiciona variáveis que estão na lista VARIAVEIS_VALIDAS
            if var_name in VARIAVEIS_VALIDAS:
                 vars_globais[var_name] = val_text
            # HM, LM, PM não vêm da tabela global, mas da linha MODULO.

    #print(f"[DEBUG] Variáveis globais lidas da tab_modulo_medidas: {vars_globais}")


    linha_modulo = None # Índice da última linha MODULO encontrada
    vars_modulo_local = {} # Variáveis HM, LM, PM da última linha MODULO
    qt_mod_modulo_atual = 1 # QT_mod da última linha MODULO

    # 2. Itera por cada linha da tabela de peças
    for row in range(total_linhas):
        def_peca_item = tabela.item(row, IDX_DEF_PECA)
        # item_def_peca_color = tabela.item(row, IDX_DEF_PECA) # Usado para verificar cor

        # Ignora linhas vazias
        if not def_peca_item or not def_peca_item.text().strip():
            # O orquestrador já deve limpar linhas vazias, mas podemos adicionar segurança aqui
            continue

        texto_def_peca = def_peca_item.text().strip().upper()

        # 🔳 Processa a linha MODULO: armazena variáveis locais e QT_mod
        if texto_def_peca == "MODULO":
            linha_modulo = row # Atualiza a referência para a linha MODULO
            
            # Obtém o valor numérico de QT_mod da célula (coluna 4)
            qt_mod_item = tabela.item(row, IDX_QT_MOD)
            try:
                 # Tenta converter para inteiro, tratando "" ou não numéricos
                 qt_mod_modulo_atual = int(safe_item_text(tabela, row, IDX_QT_MOD, "1").strip().split(" x ")[0]) # Tenta obter o número antes do " x "
                 if qt_mod_modulo_atual <= 0: qt_mod_modulo_atual = 1 # Garante que é pelo menos 1
            except (ValueError, IndexError):
                 print(f"[AVISO] Linha {row+1} (MODULO): QT_mod '{safe_item_text(tabela, row, IDX_QT_MOD)}' inválido. Usando 1.")
                 qt_mod_modulo_atual = 1
            
            # Coleta variáveis locais HM, LM, PM das colunas Comp, Larg, Esp do MODULO
            # Os valores HM, LM, PM vêm das colunas Comp, Larg, Esp (6, 7, 8) da LINHA MODULO
            # Estes valores podem ser fórmulas ou números. Precisamos dos VALORES FINAIS CALCULADOS (_res).
            # NOVO: HM/LM/PM devem ser os resultados das colunas _res da linha MODULO.
            # Para a linha MODULO, Comp, Larg, Esp são calculados usando variáveis GLOBAIS.
            # O orquestrador chama `processar_formulas_e_quantidades_para_linha` para a linha MODULO primeiro (ou nesta iteração).
            # Devemos usar os valores calculados nas colunas _res para HM, LM, PM.
            # Se as colunas _res ainda não foram preenchidas para esta linha MODULO nesta iteração,
            # podemos usar os valores das colunas Comp, Larg, Esp (fórmulas originais) como fallback,
            # ou assumir que o processamento anterior já preencheu os _res.
            # Vamos assumir que processar_formulas_e_quantidades_para_linha JÁ preencheu os _res para esta linha MODULO.
            # E usamos os resultados _res para HM, LM, PM.

            # Obter os VALORES DE RESULTADO de Comp, Larg, Esp da linha MODULO
            comp_mod_res = safe_item_text(tabela, row, IDX_COMP_RES).strip()
            larg_mod_res = safe_item_text(tabela, row, IDX_LARG_RES).strip()
            esp_mod_res = safe_item_text(tabela, row, IDX_ESP_RES).strip()

            # Armazenar estes VALORES RESULTADO sob as chaves HM, LM, PM
            # Use "" em vez de "0" se estiver vazio/Erro, pois a substituição regex lida melhor com string vazia vs "0" literal
            # A substituição acima já foi ajustada para lidar com valores locais inválidos/vazios.
            vars_modulo_local = {
                 'HM': comp_mod_res if comp_mod_res and comp_mod_res.upper() != "ERRO CÁLCULO" else "",
                 'LM': larg_mod_res if larg_mod_res and larg_mod_res.upper() != "ERRO CÁLCULO" else "",
                 'PM': esp_mod_res if esp_mod_res and esp_mod_res.upper() != "ERRO CÁLCULO" else ""
            }

            # print(f"[DEBUG] Linha {row+1} (MODULO): QT_mod={qt_mod_modulo_atual}, Vars Locais (dos _res)={vars_modulo_local}")

            # Cor cinza claro para MODULO
            # Aplica a cor a TODAS as células da linha MODULO, sem sobrescrever cores de associados (se houver algum erro anterior)
            tabela.blockSignals(True) # Bloqueia sinais
            try:
                 for c in range(tabela.columnCount()):
                     item_c = tabela.item(row, c) # Obtém item (garantido por set_item ou inserção inicial)
                     if item_c: # Garante que o item existe
                         # Não sobrescreve cor azul de associados (se já aplicada por engano)
                         if item_c.background().color().name() != COLOR_ASSOCIATED_BG.name():
                              item_c.setBackground(COLOR_MODULO_BG) # Cinza mais claro
                         # setItem NÃO é necessário aqui
            finally:
                 tabela.blockSignals(False)


            # A linha MODULO também precisa ter suas próprias fórmulas processadas (Comp, Larg, Esp, QT_mod)
            # Estas fórmulas USAM AS VARIÁVEIS GLOBAIS (H, L, P...)
            # E o QT_mod desta linha é usado para o cálculo das linhas associadas ABAIXO.
            # Então, chamamos o processador por linha para a própria linha MODULO,
            # mas usando as variáveis GLOBAIS para avaliar as fórmulas Comp/Larg/Esp/QT_mod.
            # Passamos vars_globais e um dicionário vazio para vars_modulo_local (MODULO não usa HM/LM/PM próprios)
            # E passamos o QT_mod da PRÓPRIA linha MODULO (qt_mod_modulo_atual) que será usado para formatar a coluna 4 dela.
            # print(f"[DEBUG] Processando fórmulas para a própria linha MODULO {row+1}...")
            processar_formulas_e_quantidades_para_linha( ui, row, vars_globais, {}, qt_mod_modulo_atual)


        # Para as linhas NÃO-MODULO:
        # 1) Chama a função de processamento por linha com as variáveis corretas.
        # 2) Garante cor de fundo correta (branco, a menos que seja associado com cor azul clara).
        else:
             # Determina as variáveis locais a serem usadas (do último MODULO encontrado)
             current_vars_modulo_local = vars_modulo_local
             current_qt_mod_modulo = qt_mod_modulo_atual

             # Se não houver MODULO acima, usa HM/LM/PM vazios e QT_mod=1
             if linha_modulo is None:
                 current_vars_modulo_local = {}
                 current_qt_mod_modulo = 1

             # Chama a função de processamento por linha para linhas não-MODULO
             # print(f"[DEBUG] Processando fórmulas para linha {row+1} (não-MODULO)...")
             processar_formulas_e_quantidades_para_linha(
                 ui, row, vars_globais, current_vars_modulo_local, current_qt_mod_modulo
             )

             # Garante que a cor de fundo NÃO é cinza para linhas não-MODULO
             # Verifica a cor de fundo atual. Se for cinza (MODULO) e não deveria ser, muda para branco.
             # A cor azul clara de associado (COLOR_ASSOCIATED_BG) é definida no modulo_componentes_associados.
             # Não sobrescrever a cor azul clara aqui.
             item_def_check_color = tabela.item(row, IDX_DEF_PECA)
             if item_def_check_color: # Garante item existe
                  current_color = item_def_check_color.background().color()
                  # Se a cor é cinza (COLOR_MODULO_BG) E o texto da peça NÃO é "MODULO", então remove a cor cinza
                  if current_color.name() == COLOR_MODULO_BG.name() and texto_def_peca != "MODULO":
                       tabela.blockSignals(True) # Bloqueia sinais para mudar cor em todas as células
                       try:
                            for c in range(tabela.columnCount()):
                                 item_c = tabela.item(row, c) # Obtém item
                                 if item_c:
                                     # Apenas remove a cor cinza se ela for a cor atual
                                     if item_c.background().color().name() == COLOR_MODULO_BG.name():
                                         item_c.setBackground(Qt.white) # Volta para branco
                       finally:
                            tabela.blockSignals(False)

    for row in range(tabela.rowCount()):
        def_peca = safe_item_text(tabela, row, IDX_DEF_PECA).strip().upper()
        if def_peca == "MODULO":
            continue  # Ignora linhas do tipo MODULO

        # Verifica se algum dos campos COMP_ASS_1/2/3 está preenchido
        tem_associados = any(
            safe_item_text(tabela, row, idx).strip()
            for idx in (IDX_COMP_ASS_1, IDX_COMP_ASS_2, IDX_COMP_ASS_3)
        )

        if tem_associados:
            for col in range(tabela.columnCount()):
                item = tabela.item(row, col)
                if item:
                    item.setBackground(COLOR_PRIMARY_WITH_ASS_BG)  # Aplicar cor de fundo azul escuro na linha completa que tem o componente principal e avaliar se alguma cas colunas COMP_ASS_1/2/3  tem componentes associados


    print("[INFO] Atualização de dados de módulos (fórmulas e quantidades) concluída.")


# As funções auxiliares get_valor_numero, obter_valores_componente_principal,
# obter_qt_und_linha_base, get_cell_value (importada de utils) são usadas pela
# lógica de componentes associados (modulo_componentes_associados) e podem permanecer.
# Elas não precisam ser refatoradas se já operam por linha.

# As funções de validação (validar_input_modulo, validar_expressao_modulo)
# são usadas pelos Delegates e pelo próprio modulo_quantidades. Estão em utils.py
# e no Delegate em tabela_def_pecas_items.py.