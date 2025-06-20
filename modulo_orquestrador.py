# modulo_orquestrador.py
# -*- coding: utf-8 -*-

"""
Módulo: modulo_orquestrador.py

Objetivo:
---------
Este módulo atua como o orquestrador central para atualizar a tabela 'tab_def_pecas'.
Coordena a chamada de funções de outros módulos para garantir que:
  - Dados adicionais da base de dados são carregados para cada linha (se não bloqueada).
  - Fórmulas de quantidades e dimensões são avaliadas.
  - Cálculos de orlas são realizados.
  - Cálculos de custos (materiais, máquinas, acabamentos) são efetuados.
  - Componentes associados são identificados e inseridos como novas linhas.
  - As linhas são formatadas e os Delegates são aplicados/reaplicados.

A função principal, `atualizar_tudo`, implementa um ciclo de processamento para lidar
corretamente com a inserção dinâmica de componentes associados e a subsequente
necessidade de processar essas novas linhas.

Dependências:
-------------
- `modulo_dados_definicoes.py`: Para atualizar chaves na tab_modulo_medidas (embora menos central aqui agora).
- `modulo_quantidades.py`: Para processar fórmulas e quantidades.
- `calculo_orlas.py`: Para cálculos de orlas.
- `modulo_calculos_custos.py`: Para cálculos de custos (inclui leitura do Excel CPxx).
- `modulo_componentes_associados.py`: Para identificar e calcular quantidade de associados.
- `tabela_def_pecas_items.py`: Para atualizar dados adicionais da linha, inserir linhas básicas,
  atualizar IDs e configurar Delegates.
- `utils.py`: Funções utilitárias gerais.
- `pandas`: Necessário para ler o Excel no módulo_calculos_custos, importado aqui para passar para a função.
"""

import pandas as pd # Para carregar o Excel
import os # Para construir o caminho do Excel
from PyQt5.QtCore import Qt # Necessário para flags, etc.
from PyQt5.QtGui import QColor # Importar QColor de QtGui
from PyQt5.QtWidgets import QTableWidgetItem, QMessageBox, QApplication, QComboBox # Necessário para manipular itens na tabela UI

# --- Importar funções que serão chamadas pelo orquestrador ---
# Funções de processamento por linha (adaptadas nos módulos respectivos)
from modulo_quantidades import atualizar_dados_modulos # Esta itera internamente agora
# from modulo_quantidades import processar_formulas_e_quantidades_para_linha # Não chamada diretamente aqui

from calculo_orlas import calcular_orlas # Esta itera internamente agora
# from calculo_orlas import calcular_orlas_para_linha # Não chamada diretamente aqui

from modulo_calculos_custos import atualizar_calculos_custos # Esta itera internamente agora
# from modulo_calculos_custos import processar_calculos_para_linha # Não chamada diretamente aqui

# Importar funções que o orquestrador ainda chama diretamente (para inserção de associados e atualização de dados base)
from modulo_componentes_associados import identificar_componentes_associados_para_linha # Identifica associados para UMA linha principal
from modulo_componentes_associados import processar_qt_und_associado_para_linha # Processa QT_und para UMA linha associada (chamada pelo orquestrador após outros calculos)



# Funções auxiliares
from utils import safe_item_text, set_item # Para ler células de forma segura

# --- Constantes de Índices das Colunas (duplicadas por segurança/clareza) ---
# Estas constantes definem a estrutura da tabela para este módulo.
IDX_DEF_PECA   = 2
IDX_COMP       = 6
IDX_LARG       = 7
IDX_ESP        =8
IDX_QT_MOD    = 4 # Coluna QT_mod (número de módulos)

IDX_QT_UND     = 5
IDX_BLK        = 12 # Checkbox BLK
IDX_MAT_DEFAULT = 13 # Mat_Default
IDX_TAB_DEFAULT = 14 # Tab_Default
IDX_IDS = 15
IDX_NUM_ORC = 16
IDX_VER_ORC = 17
IDX_COMP_ASS_1 = 34 # Coluna COMP_ASS_1 (Nome do 1º componente associado)
IDX_COMP_ASS_2 = 35 # Coluna COMP_ASS_2 (Nome do 2º componente associado)
IDX_COMP_ASS_3 = 36 # Coluna COMP_ASS_3 (Nome do 3º componente associado)

# Índices de colunas de resultados de cálculo
IDX_COMP_RES = 50
IDX_LARG_RES = 51
IDX_ESP_RES = 52
IDX_QT_TOTAL = 49
IDX_AREA_M2 = 54


# --- Cores para identificar tipos de linha (duplicadas por segurança/clareza) ---
COLOR_ASSOCIATED_BG = QColor(230, 240, 255) # Azul claro para linhas de componentes associados
COLOR_PRIMARY_WITH_ASS_BG = QColor(180, 200, 255) # Azul mais escuro para linha principal com associados
COLOR_MODULO_BG = QColor(220, 220, 220) # Cinza claro para linhas MODULO


##############################################
# 1. Função: atualizar_tudo (Orquestrador Principal)
##############################################
def atualizar_tudo(ui):
    """
    Função principal do orquestrador.
    
    Realiza múltiplos ciclos de processamento da tabela 'tab_def_pecas' até que
    nenhum novo componente associado seja inserido. Cada ciclo inclui:
      1. Leitura de dados globais (variáveis do módulo, Excel CPxx).
      2. Iteração pelas linhas atuais para:
         - Identificar linhas MODULO e coletar variáveis locais e QT_mod.
         - Chamar funções de atualização/cálculo por linha (respeitando BLK):
           - atualizar_dados_def_peca (dados adicionais da BD de itens)
           - processar_formulas_e_quantidades_para_linha (fórmulas, _res, Qt_Total) - CHAMADA IMPLÍCITA DENTRO DE atualizar_dados_modulos
           - calcular_orlas_para_linha (orlas, ML, custos orla) - CHAMADA IMPLÍCITA DENTRO DE calcular_orlas
           - processar_calculos_para_linha (custos CPxx, somas, acabamentos) - CHAMADA IMPLÍCITA DENTRO DE atualizar_calculos_custos
           - processar_qt_und_associado_para_linha (QT_und para associados)
           - identificar_componentes_associados_para_linha (coleta nomes para inserir)
         - Ajustar cores de fundo e tooltips para linhas especiais (MODULO, Principal com Associado).
      3. Inserir as novas linhas de componentes associados coletadas.
      4. Atualizar IDs e reaplicar Delegates.
      5. Verificar se novas linhas foram adicionadas. Se sim, repete o ciclo.
    
    Esta função é chamada por:
      - Botão "Inserir Peças Selecionadas" (depois de inserir as básicas).
      - Botão "Atualizar Preços".
      - carregar_dados_def_pecas (depois de carregar da BD).
      - Delegates (DefPecaDelegate, CelulaEdicaoDelegate) após edição relevante.
      - on_mp_button_clicked (após seleção de material).
      - Menu de contexto (após inserir/excluir linhas).
    """
    # Funções do tabela_def_pecas_items
    from tabela_def_pecas_items import (
        atualizar_dados_def_peca, # Atualiza dados adicionais de UMA linha da BD de itens (chamada pelo orquestrador antes dos calculos principais)
        inserir_linha_componente, # Insere UMA linha básica (para associado)
        update_ids, # Renumera IDs
        setup_context_menu, # Reaplica Delegates e menu de contexto
        aplicar_combobox_mat_default # Reaplica ComboBox Mat_Default
        # from tabela_def_pecas_items import CelulaEdicaoDelegate # Não é chamado diretamente aqui
        # from tabela_def_pecas_items import DefPecaDelegate # Não é chamado diretamente aqui
        # from tabela_def_pecas_items import on_mp_button_clicked # Não é chamado diretamente aqui
    )
    
    print("\n--- Iniciando ciclo(s) de atualização completa da tabela 'tab_def_pecas' ---")
    table = ui.tab_def_pecas
    
    # Usar uma flag na tabela para indicar que a atualização está em andamento
    # Isso pode ajudar a prevenir chamadas recursivas indesejadas de sinais itemChanged
    # e pode ser verificado em funções como on_item_changed_def_pecas.
    if table.property("atualizando_tudo"):
        print("[INFO] Atualização já em andamento. Saindo.")
        return # Sai para evitar reentrada

    table.setProperty("atualizando_tudo", True) # Define a flag

    try:
        # Iniciar o loop de ciclos de processamento
        novas_linhas_adicionadas_neste_ciclo = True
        ciclos_executados = 0

        while novas_linhas_adicionadas_neste_ciclo and ciclos_executados < 10: # Limite de ciclos para segurança
            ciclos_executados += 1
            print(f"\n-- Executando Ciclo de Processamento #{ciclos_executados} --")
            
            novas_linhas_adicionadas_neste_ciclo = False
            linhas_no_inicio_do_ciclo = table.rowCount()
            
            # Lista para coletar nomes de componentes associados a serem inseridos NESTE ciclo
            componentes_associados_a_inserir_neste_ciclo = []

            # --- Passo A: Carregar dados globais (feita uma vez por ciclo) ---
            # Variáveis do módulo (H, L, P, etc.) - lidas internamente por atualizar_dados_modulos
            # Dados do Excel (CPxx, COMP_ASS_x) - carregados internamente por modulo_calculos_custos
            # A função `atualizar_dados_modulos` e `atualizar_calculos_custos` já cuidam do carregamento.

            # Re-aplicar delegates e menu de contexto no início de cada ciclo para garantir que estão corretos
            # após possíveis inserções de linhas no ciclo anterior.
            # setup_context_menu(ui, None) # Isso pode ser custoso. Pode ser feito apenas uma vez no final, exceto se houver problemas.
            # Vamos fazer no final, após todos os ciclos.
            # aplicar_combobox_mat_default(ui) # Isso também pode ser custoso. Fazer no final.

            # --- Passo B: Iterar pelas linhas existentes para atualizar e coletar associados ---
            # Usamos uma cópia dos índices das linhas para evitar problemas se linhas forem removidas
            # (embora neste fluxo, apenas adicionamos linhas).
            # Iteramos pelo range atual, novas linhas só serão adicionadas depois.
            linhas_atuais_indices = list(range(table.rowCount()))

            # Variáveis de contexto para processamento de fórmulas
            linha_modulo_atual_idx = None
            vars_modulo_local_atual = {}
            qt_mod_modulo_atual = 1 # Default 1 se não houver MODULO acima

            # Carregar o Excel uma vez para este ciclo para passar para as funções que precisam
            df_excel_cp = None
            try:
                 caminho_base = ui.lineEdit_base_dados.text().strip()
                 folder = os.path.dirname(caminho_base)
                 excel_file = os.path.join(folder, "TAB_DEF_PECAS.XLSX")
                 df_excel_cp = pd.read_excel(excel_file, header=4)
            except Exception as e:
                 print(f"[ERRO] Ciclo {ciclos_executados}: Não foi possível carregar/ler o ficheiro Excel '{excel_file}': {e}")
                 df_excel_cp = pd.DataFrame() # Use DataFrame vazio para evitar erros

            # --- ETAPA DE REVALIDAÇÃO DE CORES ---
            # Garante que as cores de fundo estão corretas antes de identificar associados.
            # Isto é crucial para a lógica em `identificar_componentes_associados_para_linha`
            # que verifica a cor para evitar reinserir associados existentes.
            print(f"[INFO] Ciclo {ciclos_executados}: Revalidando cores de fundo...")
            ultima_principal_para_cor = -1
            comps_da_ultima_principal_para_cor = set()
            cor_fundo_padrao_tabela = table.palette().base()

            for r_cor in range(table.rowCount()):
                item_def_peca_cor = table.item(r_cor, IDX_DEF_PECA)
                if not item_def_peca_cor: continue
                
                texto_def_peca_cor = item_def_peca_cor.text().strip().upper()
                
                # Aplicar cor MODULO
                if texto_def_peca_cor == "MODULO":
                    for c_item_cor in range(table.columnCount()):
                        it = table.item(r_cor, c_item_cor) or QTableWidgetItem()
                        if table.item(r_cor, c_item_cor) is None: table.setItem(r_cor, c_item_cor, it)
                        it.setBackground(COLOR_MODULO_BG)
                    ultima_principal_para_cor = -1 # Reset para MODULO
                    comps_da_ultima_principal_para_cor.clear()
                    continue

                # Determinar se é associado da principal anterior
                e_associado_atual = False
                if ultima_principal_para_cor != -1 and \
                   r_cor > ultima_principal_para_cor and \
                   texto_def_peca_cor in comps_da_ultima_principal_para_cor:
                    e_associado_atual = True
                
                cor_a_aplicar_nesta_linha = cor_fundo_padrao_tabela
                if e_associado_atual:
                    cor_a_aplicar_nesta_linha = COLOR_ASSOCIATED_BG
                else:
                    # É uma nova linha principal (ou independente)
                    ultima_principal_para_cor = r_cor
                    comps_da_ultima_principal_para_cor.clear()
                    comp1 = safe_item_text(table, r_cor, IDX_COMP_ASS_1).strip().upper()
                    comp2 = safe_item_text(table, r_cor, IDX_COMP_ASS_2).strip().upper()
                    comp3 = safe_item_text(table, r_cor, IDX_COMP_ASS_3).strip().upper()
                    if comp1: comps_da_ultima_principal_para_cor.add(comp1)
                    if comp2: comps_da_ultima_principal_para_cor.add(comp2)
                    if comp3: comps_da_ultima_principal_para_cor.add(comp3)

                    if comps_da_ultima_principal_para_cor:
                        cor_a_aplicar_nesta_linha = COLOR_PRIMARY_WITH_ASS_BG
                    # else: cor_fundo_padrao_tabela (já definida)
                
                blk_item_cor = table.item(r_cor, IDX_BLK)
                linha_blk_ativa = blk_item_cor and blk_item_cor.checkState() == Qt.Checked

                for c_item_cor in range(table.columnCount()):
                    # Se a linha está com BLK ativo, preserva a cor das colunas 18-32
                    if linha_blk_ativa and 18 <= c_item_cor <= 32:
                        continue

                    it = table.item(r_cor, c_item_cor) or QTableWidgetItem()
                    if table.item(r_cor, c_item_cor) is None:
                        table.setItem(r_cor, c_item_cor, it)
                    it.setBackground(cor_a_aplicar_nesta_linha)
            print(f"[INFO] Ciclo {ciclos_executados}: Revalidação de cores de fundo concluída.")
            # --- FIM ETAPA DE REVALIDAÇÃO DE CORES ---

            # --- Passo A: Identificar Componentes Associados a serem inseridos (Itera sobre linhas atuais) ---
            # Coleta nomes de componentes associados a serem inseridos NESTE ciclo
            componentes_associados_a_inserir_neste_ciclo_com_origem = []
            
            for row_idx_ident in range(table.rowCount()): # Usar rowCount atualizado
                 # Primeiro, atualizar dados da BD para a linha (respeita BLK)
                 atualizar_dados_def_peca(ui, row_idx_ident) 

                 item_def_peca_orq = table.item(row_idx_ident, IDX_DEF_PECA)
                 if item_def_peca_orq:
                     cor_fundo_atual_orq = item_def_peca_orq.background().color()
                     nome_peca_orq = item_def_peca_orq.text().strip().upper()

                     # Só tenta identificar associados se a linha NÃO for MODULO e NÃO for já um associado
                     if nome_peca_orq != "MODULO" and cor_fundo_atual_orq.name() != COLOR_ASSOCIATED_BG.name():
                         #print(f"[ORQ Ciclo {ciclos_executados}] Candidata a principal: L{row_idx_ident+1} '{nome_peca_orq}' Cor: {cor_fundo_atual_orq.name()}")
                         # A função `identificar_componentes_associados_para_linha` agora
                         # verifica internamente se os associados já existem e estão formatados.
                         associated_names_to_insert = identificar_componentes_associados_para_linha(ui, row_idx_ident, df_excel_cp)
                         if associated_names_to_insert: # Apenas se houver algo REALMENTE para inserir
                             for name in associated_names_to_insert:
                                 componentes_associados_a_inserir_neste_ciclo_com_origem.append((name, row_idx_ident))


            # --- Passo B: Inserir novas linhas para componentes associados coletados ---
            if componentes_associados_a_inserir_neste_ciclo_com_origem:
                print(f"[INFO] Ciclo {ciclos_executados}: Inserindo {len(componentes_associados_a_inserir_neste_ciclo_com_origem)} linhas de componentes associados.")
                for nome_associado, linha_origem_debug in componentes_associados_a_inserir_neste_ciclo_com_origem:

                    # Esta função insere uma linha básica, mas NÃO A PROCESSA COMPLETAMENTE AINDA.
                    inserir_linha_componente(ui, nome_associado)
                    novas_linhas_adicionadas_neste_ciclo = True
                print(f"[INFO] Ciclo {ciclos_executados}: Inserção de linhas associadas concluída.")

            # --- Passo C: Atualizar IDs e Reaplicar Delegates ---
            # Isto é crucial após a adição de novas linhas
            update_ids(table) # Renumera IDs
            # ---------------------------------------------
            # 🔐 ETAPA FINAL: PRESERVAR VALORES DO COMBOBOX
            # ---------------------------------------------
            # Antes de aplicar novamente o ComboBox, guardar os valores escolhidos manualmente

            mat_default_user_values = {}  # Dicionário para guardar valores personalizados
            for row in range(table.rowCount()):
                widget = table.cellWidget(row, IDX_MAT_DEFAULT)
                if isinstance(widget, QComboBox):
                    mat_default_user_values[row] = widget.currentText()
                else:
                    item = table.item(row, IDX_MAT_DEFAULT)
                    if item:
                        mat_default_user_values[row] = item.text().strip()

            # -----------------------------------------------
            # 🧩 REAPLICAR O COMBOBOX MAT_DEFAULT
            # -----------------------------------------------
            aplicar_combobox_mat_default(ui)  # Recria os combobox em todas as linhas

            # ----------------------------------------------------
            # 🔁 Restaurar o valor do utilizador no QComboBox final
            # ----------------------------------------------------
            for r_combo, val_pers in mat_default_user_values.items():
                    if r_combo < table.rowCount(): # Segurança
                        widget = table.cellWidget(r_combo, IDX_MAT_DEFAULT)
                        if isinstance(widget, QComboBox):
                            idx = widget.findText(val_pers, Qt.MatchFixedString)
                            if idx >= 0: widget.setCurrentIndex(idx)
                            elif val_pers:
                                widget.insertItem(1, val_pers)
                                widget.setItemData(1, QColor("red"), Qt.TextColorRole)
                                widget.setItemData(1, "Valor não na BD", Qt.ToolTipRole)
                                widget.setCurrentIndex(1)

            # -----------------------------------------------
            # Reaplica o menu de contexto e delegates finais
            # -----------------------------------------------
            setup_context_menu(ui, None)

            print("\n[INFO] Atualização completa da tabela concluída.")


            # --- Passo D: Processar TODAS as linhas com a lógica principal de cálculo/atualização ---
            # Estas funções agora iteram INTERNAMENTE sobre todas as linhas atuais.
            print(f"[INFO] Ciclo {ciclos_executados}: Processando todas as linhas (Quantidades, Orlas, Custos, QT_und Associados)...")

            # 1. Processar Quantidades/Fórmulas (_res, Qt_Total, lógica MODULO)
            # Esta função lê variáveis globais/locais e itera, chamando processar_formulas_e_quantidades_para_linha.
            atualizar_dados_modulos(ui)

            # 2. Calcular Orlas, ML, Custo_ML
            # Esta função itera, chamando calcular_orlas_para_linha.
            calcular_orlas(ui)

            # 3. Processar Cálculos de Custos (CPxx, Custo MP, Somas, Acabamentos)
            #    Calcular QT_und, QT_mod e FINALIZAR QT_Total para Componentes Associados
            #    Esta função itera e usa o df_excel_cp carregado, chamando processar_calculos_para_linha.
            print(f"[INFO] Ciclo {ciclos_executados}: Finalizando QT_Total para componentes associados...")
            for row_idx_assoc_qt in range(table.rowCount()):
                 processar_qt_und_associado_para_linha(ui, row_idx_assoc_qt)

            # 4. Processar Cálculos de Custos (CPxx, Custo MP, Somas, Acabamentos)
            # Agora, CUSTO_MP_Total para associados usará o QT_Total correto.
            atualizar_calculos_custos(ui)

            print(f"[INFO] Ciclo {ciclos_executados}: Processamento de Quantidades, Orlas e Custos concluído.")


            # --- Passo E: Verificar se foram adicionadas novas linhas e repetir o loop se necessário ---
            linhas_no_fim_do_ciclo = table.rowCount()
            # `novas_linhas_adicionadas_neste_ciclo` já foi definida em Passo B
            if not novas_linhas_adicionadas_neste_ciclo and linhas_no_fim_do_ciclo > linhas_no_inicio_do_ciclo:
                # Caso raro: linhas foram adicionadas por outro mecanismo não rastreado por Passo B
                print(f"[AVISO] Ciclo {ciclos_executados}: Novas linhas detectadas ({linhas_no_fim_do_ciclo - linhas_no_inicio_do_ciclo}) por contagem, mas não pela flag de inserção.")
                novas_linhas_adicionadas_neste_ciclo = True

            if novas_linhas_adicionadas_neste_ciclo:
                print(f"[INFO] Ciclo {ciclos_executados}: Novas linhas presentes. Repetindo ciclo.")
            else:
                print(f"[INFO] Ciclo {ciclos_executados}: Nenhuma nova linha adicionada/detectada. Fim dos ciclos de atualização.")

            if ciclos_executados >= 10:
                 print("[AVISO] Limite máximo de ciclos de atualização atingido (10). Interrompendo.")
                 QMessageBox.warning(ui, "Aviso de Processamento", "O processamento atingiu o limite de ciclos. Pode haver um problema na definição de componentes associados.")
                 break  # Sair do loop while se atingir o limite


    except Exception as e:
        print(f"[ERRO CRÍTICO] Erro inesperado durante a orquestração: {e}")
        import traceback
        traceback.print_exc()
        # Exibir mensagem de erro crítica para o utilizador
        # Usar a janela principal (obtida da tabela) como parent para a QMessageBox
        parent_widget = ui.tab_def_pecas.window()
        if parent_widget is None: # Fallback caso window() não funcione como esperado
            # Tenta a janela activa da aplicação
            parent_widget = QApplication.activeWindow()
            if parent_widget is None:
                 print("[ERRO] Não foi possível obter a janela pai para a QMessageBox, nem mesmo a janela activa.")
                 parent_widget = None # Mantém None se não encontrar nenhuma janela activa


        # A mensagem de erro já foi mostrada no log, mostra uma versão simplificada na QMessageBox
        # O erro específico "atualizar_calculos_custos() takes 1 positional argument but 2 were given"
        # será mostrado no log completo pela exceção capturada.
        # Apenas exibe uma mensagem genérica de erro crítico de actualização.
        QMessageBox.critical(parent_widget, "Erro Crítico de Actualização", f"Ocorreu um erro crítico durante a actualização dos dados.\n{e}\nPor favor, verifique o log para detalhes.")


    finally:
        # Garantir que a flag é redefinida mesmo em caso de erro
        table.setProperty("atualizando_tudo", False)
        print("--- Flag 'atualizando_tudo' redefinida para False ---")


# As funções dos outros módulos são importadas e chamadas por atualizar_tudo.
# Não há mais código executável diretamente neste módulo fora da função atualizar_tudo.