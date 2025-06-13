# dados_gerais_sistemas_correr.py

"""
Módulo: dados_gerais_sistemas_correr.py
Descrição: Configura a interface e lógica para a aba "Sistemas Correr" nos Dados Gerais.
Refatorado: Removida importação direta de get_connection. As operações de BD
            são realizadas por funções importadas que devem usar obter_cursor().
... (restante do docstring mantido) ...
"""
import mysql.connector # Para capturar erros específicos

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QMessageBox, QLineEdit, QComboBox, QHeaderView)
from PyQt5.QtCore import Qt

# Adicionado (se necessário por alguma função importada, embora não diretamente usado aqui):
# from db_connection import obter_cursor
from dados_gerais_base import criar_tabela_dados_gerais, configurar_tabela_dados_gerais_ui, get_distinct_values
# mostrar diálogo de seleção de material um menu onde utilizador pode escolher o material da tabela das materias primas
from dados_gerais_materiais_escolher import MaterialSelectionDialog
from utils import formatar_valor_moeda, formatar_valor_percentual, original_pliq_values, converter_texto_para_valor, get_distinct_values_with_filter
# Importa a lista de colunas a limpar (agora definida em dados_gerais_mp.py)
from dados_gerais_mp import COLUNAS_LIMPAR_SISTEMAS_CORRER

# Definições específicas para Sistemas de Correr
SISTEMAS_CORRER_COLUNAS = [
    {'nome': 'sistemas_correr', 'tipo': 'TEXT', 'visivel': True, 'editavel': False},
    {'nome': 'descricao', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'id_sc', 'tipo': 'INTEGER', 'visivel': False},
    {'nome': 'num_orc', 'tipo': 'INTEGER', 'visivel': False},
    {'nome': 'ver_orc', 'tipo': 'INTEGER', 'visivel': False},
    {'nome': 'ref_le', 'tipo': 'TEXT', 'visivel': True, 'editavel': False},
    {'nome': 'descricao_no_orcamento', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},

    {'nome': 'ptab', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'pliq', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'desc1_plus', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'desc2_minus', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'und', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'desp', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'corres_orla_0_4', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'corres_orla_1_0', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'tipo', 'tipo': 'TEXT', 'visivel': True, 'editavel': True,
    'combobox': True, 'opcoes': lambda: get_distinct_values_with_filter("TIPO", "FAMILIA", "FERRAGENS")},
    {'nome': 'familia', 'tipo': 'TEXT', 'visivel': True, 'editavel': True,
    'combobox': True, 'opcoes': lambda: ["FERRAGENS"]},
    {'nome': 'comp_mp', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'larg_mp', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'esp_mp', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'MP', 'tipo': 'TEXT', 'visivel': True, 'botao': True,
        'texto_botao': 'Escolher', 'funcao_botao': None},  # Função será atribuída abaixo
]

# Definição dos nomes das linhas para a tabela de Sistemas Correr
SISTEMAS_CORRER_LINHAS = [
    'SC_Puxador_Vertical_SPP', 'SC_Calha_Superior_SPP', 'SC_Calha_Inferior_SPP_1',
    'SC_Calha_Inferior_SPP_2', 'SC_Calha_Porta_Horizontal_H_SPP',
    'SC_Calha_Porta_Horizontal_Sup_SPP', 'SC_Calha_Porta_Horizontal_Inf_SPP',
    'SC_Painel_Porta_Correr_1', 'SC_Painel_Porta_Correr_2',
    'SC_Painel_Porta_Correr_3', 'SC_Painel_Porta_Correr_4',
    'SC_Espelho_Porta_Correr_1', 'SC_Espelho_Porta_Correr_2',
    'SC_Acessorio_1', 'SC_Acessorio_2', 'SC_Acessorio_3',
    'SC_Acessorio_4_SPP', 'SC_Acessorio_5_SPP'
]

def escolher_sistemas_correr(ui, linha_tab, nome_tabela):
    """
    Abre o diálogo para seleção de material, aplicando pré-filtros (tipo e família) se disponíveis.
    Após a seleção, mapeia os dados da linha selecionada para a linha correspondente na Tab_Sistemas_Correr,
    e recalcula o valor de 'pliq' utilizando a fórmula:
         pliq = (PRECO_TABELA*(1-DESC2_MINUS))*(1+DESC1_PLUS)
    Retorna True se um material foi selecionado, False caso contrário.
    """
    from PyQt5.QtWidgets import QTableWidgetItem, QDialog
    tbl_sistemas_correr = ui.Tab_Sistemas_Correr
    tbl_sistemas_correr.blockSignals(True)
    
    # Obter pré-filtros para 'tipo' e 'familia'
    tipo_col_idx = next((i for i, col in enumerate(SISTEMAS_CORRER_COLUNAS) if col['nome'] == 'tipo'), None)
    familia_col_idx = next((i for i, col in enumerate(SISTEMAS_CORRER_COLUNAS) if col['nome'] == 'familia'), None)
    pre_tipo = (tbl_sistemas_correr.cellWidget(linha_tab, tipo_col_idx).currentText()
                if (tipo_col_idx is not None and tbl_sistemas_correr.cellWidget(linha_tab, tipo_col_idx))
                else "")
    pre_familia = (tbl_sistemas_correr.cellWidget(linha_tab, familia_col_idx).currentText()
                   if (familia_col_idx is not None and tbl_sistemas_correr.cellWidget(linha_tab, familia_col_idx))
                   else "")
    
    dialog = MaterialSelectionDialog(ui.tableWidget_materias_primas, pre_tipo, pre_familia)
    if dialog.exec_() == QDialog.Accepted:
        row_idx = dialog.selected_row
        # Mapeamento: (source_index, target_index)
        col_map = {
            'ref_le': (3, 5),
            'descricao_no_orcamento': (5, 6),
            'ptab': (6, 7),
            'desc1_plus': (7, 9),
            'desc2_minus': (8, 10),
            'und': (10, 11),
            'desp': (11, 12),
            'corres_orla_0_4': (16, 13),
            'corres_orla_1_0': (17, 14),
            'comp_mp': (19, 17),
            'larg_mp': (20, 18),
            'esp_mp': (12, 19)
        }
        # Limpa os campos de destino na linha selecionada da Tab_Sistemas_Correr
        for campo, (src_idx, tgt_idx) in col_map.items():
            tbl_sistemas_correr.setItem(linha_tab, tgt_idx, QTableWidgetItem(""))

        def set_item(row, col_idx, texto):
            item = tbl_sistemas_correr.item(row, col_idx)
            if not item:
                from PyQt5.QtWidgets import QTableWidgetItem
                item = QTableWidgetItem()
                tbl_sistemas_correr.setItem(row, col_idx, item)
            item.setText(texto)

        ptab_valor = 0.0
        dplus = 0.0
        dminus = 0.0

        for campo, (source_idx, target_idx) in col_map.items():
            valor = ""
            cell = dialog.table.item(row_idx, source_idx)
            if cell:
                valor = cell.text()
            set_item(linha_tab, target_idx, valor)
            if campo == 'ptab':
                ptab_valor = converter_texto_para_valor(valor, "moeda")
            elif campo == 'desc1_plus':
                dplus = converter_texto_para_valor(valor, "percentual")
            elif campo == 'desc2_minus':
                dminus = converter_texto_para_valor(valor, "percentual")
        
        novo_pliq = round(ptab_valor * (1 + dminus) * (1 - dplus), 2)
        set_item(linha_tab, 8, formatar_valor_moeda(novo_pliq))
        
        tbl_sistemas_correr.blockSignals(False)
        return True
    tbl_sistemas_correr.blockSignals(False)
    return False


def definir_larguras_tab_sistemas_correr(ui):
    """
    Define larguras fixas para cada coluna da Tab_Sistemas_Correr.
    Ajuste os valores conforme necessário.
    """
    tabela = ui.Tab_Sistemas_Correr
    header = tabela.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.Fixed)
    header.setStretchLastSection(False)

    larguras = [200, 200, 50, 110, 50, 100, 400, 60, 60, 60, 60, 50, 50, 180, 110, 120, 120, 90, 90, 90, 100]
    num_cols = tabela.columnCount()
    if len(larguras) < num_cols:
        larguras += [100] * (num_cols - len(larguras))
    for idx in range(num_cols):
         tabela.setColumnWidth(idx, larguras[idx])


def on_mp_button_clicked(ui, row, nome_tabela):
    """
    Função chamada ao clicar o botão "Escolher" (coluna MP).
    Abre o diálogo para seleção de material e, se um material for escolhido,
    exibe uma mensagem informando que o material foi selecionado.
    """
    if escolher_sistemas_correr(ui, row, nome_tabela):
        QMessageBox.information(None, "Sistemas_Correr", f"Sistemas_Correr selecionado para a linha {row+1}.")

    else:
        QMessageBox.warning(None, "Sistemas_Correr", "Nenhum sistemas_correr foi selecionado.")

# Atribui a função do botão "Escolher" à coluna MP
for col in SISTEMAS_CORRER_COLUNAS:
    if col['nome'] == 'MP':
        col['funcao_botao'] = on_mp_button_clicked


def configurar_sistemas_correr_ui(ui):
    """
    Configura a tabela de Dados Gerais para Sistemas Correr:
      - Cria a tabela no banco de dados (se não existir) usando as definições.
      - Configura o QTableWidget para exibir os dados conforme as definições.
      - Define larguras fixas para as colunas da Tab_Sistemas_Correr.
    Deve ser chamada durante a inicialização da interface.
    """
    #print("DEBUG: Executando configurar_sistemas_correr_ui para sistemas Correr.")
    criar_tabela_dados_gerais('sistemas_correr', SISTEMAS_CORRER_COLUNAS, SISTEMAS_CORRER_LINHAS)
    # Configura a tabela de Dados Gerais na interface na coluna familia preenche com 'FERRAGENS' & coluna tipo preenche com 'ROUPEIROS CORRER'
    configurar_tabela_dados_gerais_ui(ui, 'sistemas_correr', SISTEMAS_CORRER_COLUNAS,SISTEMAS_CORRER_LINHAS)
    definir_larguras_tab_sistemas_correr(ui)

    from utils import apply_row_selection_style
    tabela = ui.Tab_Sistemas_Correr

    # Índices das colunas
    tipo_idx = next((i for i,c in enumerate(SISTEMAS_CORRER_COLUNAS) if c['nome']=='tipo'), None)
    familia_idx = next((i for i,c in enumerate(SISTEMAS_CORRER_COLUNAS) if c['nome']=='familia'), None)

    # Linhas que devem ficar com 'tipo' vazio
    linhas_tipo_vazio = {
        'SC_Painel_Porta_Correr_1',
        'SC_Painel_Porta_Correr_2',
        'SC_Painel_Porta_Correr_3',
        'SC_Painel_Porta_Correr_4',
        'SC_Espelho_Porta_Correr_1',
        'SC_Espelho_Porta_Correr_2'
    }

    for r in range(tabela.rowCount()):
        nome_linha = tabela.item(r, 0).text()

        # --- Coluna TIPO ---
        if tipo_idx is not None:
            combo = tabela.cellWidget(r, tipo_idx)
            if isinstance(combo, QComboBox):
                # 1) Garante opção vazia no início (se ainda não existir)
                if combo.findText("") < 0:
                    combo.insertItem(0, "")
                # 2) Se for uma das linhas especiais, deixa selecionado o item vazio (índice 0)
                if nome_linha in linhas_tipo_vazio:
                    combo.setCurrentIndex(0)
                else:
                    # 3) Senão, procura 'ROUPEIROS CORRER' (case-insensitive)
                    idx = combo.findText('ROUPEIROS CORRER',
                                         Qt.MatchFixedString | Qt.MatchCaseInsensitive)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)

        # --- Coluna FAMILIA (mantém sempre 'FERRAGENS') ---
        if familia_idx is not None:
            combo_f = tabela.cellWidget(r, familia_idx)
            if isinstance(combo_f, QComboBox):
                idx = combo_f.findText('FERRAGENS',
                                       Qt.MatchFixedString | Qt.MatchCaseInsensitive)
                if idx >= 0:
                    combo_f.setCurrentIndex(idx)

    apply_row_selection_style(tabela)

####################################################################################

# -------------------------------------------
# INÍCIO: funções de formatação, conversão e gerenciamento do preço base
# -------------------------------------------

# -------------------------------------------
# Slot para tratar alterações (edições) na tabela sistemas_correr
# -------------------------------------------
def on_item_changed_sistemas_correr(item):
    """
    Callback para tratar alterações na tabela de Sistemas Correr.
    Se o usuário editar as células dos campos 'ptab' (col. 7), 'desc1_plus' (col. 9)
    ou 'desc2_minus' (col. 10), recalcula 'pliq' (col. 8) usando:
         pliq = (PRECO_TABELA*(1-DESC2_MINUS))*(1+DESC1_PLUS)
    Aplica também formatação de moeda e percentual conforme necessário.
    """
    if not item:
        return

    table = item.tableWidget()
    if table.property("importando"):
        return

    row = item.row()
    col = item.column()

    if col in [7, 9, 10]:
        try:
            ptab_item = table.item(row, 7)
            ptab_text = ptab_item.text() if ptab_item else "0"
            ptab_valor = converter_texto_para_valor(ptab_text, "moeda")
            
            desc1_item = table.item(row, 9)
            desc2_item = table.item(row, 10)
            desc1_text = desc1_item.text() if desc1_item else "0%"
            desc2_text = desc2_item.text() if desc2_item else "0%"
            dplus = converter_texto_para_valor(desc1_text, "percentual")
            dminus = converter_texto_para_valor(desc2_text, "percentual")
            # Recalcula PLIQ usando a fórmula:
            # PLIQ = (PRECO_TABELA*(1-DESC2_MINUS))*(1+DESC1_PLUS)
            novo_pliq = round((ptab_valor * (1 + dminus)) * (1 - dplus), 2)
        except Exception:
            novo_pliq = 0.0

        table.blockSignals(True)
        pliq_item = table.item(row, 8)
        if not pliq_item:
            from PyQt5.QtWidgets import QTableWidgetItem
            pliq_item = QTableWidgetItem()
            table.setItem(row, 8, pliq_item)
        pliq_item.setText(formatar_valor_moeda(novo_pliq))
        table.blockSignals(False)

        # Se o usuário editou uma das porcentagens, formata a célula como percentual
        if col == 9:
            table.blockSignals(True)
            item.setText(formatar_valor_percentual(dplus))
            table.blockSignals(False)
        elif col == 10:
            table.blockSignals(True)
            item.setText(formatar_valor_percentual(dminus))
            table.blockSignals(False)
        if col == 7:
            table.blockSignals(True)
            item.setText(formatar_valor_moeda(ptab_valor))
            table.blockSignals(False)
    elif col == 8:
        # Se PLIQ for editado diretamente, apenas formata como moeda
        try:
            novo_valor = float(item.text().replace("€", "").replace(",", ".").strip())
        except Exception:
            novo_valor = 0.0
        table.blockSignals(True)
        item.setText(f"{novo_valor:.2f}€")
        table.blockSignals(False)

# -------------------------------------------
# Fim das funções novas de formatação e cálculo
# -------------------------------------------