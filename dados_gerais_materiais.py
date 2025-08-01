"""
dados_gerais_materiais.py
=========================
Módulo específico para configurar a tabela de Dados Gerais para Materiais.
Este módulo define:
  - A estrutura das colunas (MATERIAIS_COLUNAS) e das linhas (MATERIAIS_LINHAS)
    que serão exibidas no separador "Material".
  - Funções para configurar o QTableWidget, criar a tabela no banco de dados e
    tratar a seleção de materiais via diálogo.
  - Um callback para tratar alterações (cálculos e formatações) na tabela.
  
Observação:
  As operações de banco de dados utilizam MySQL, via a função get_connection()
  importada do módulo db_connection.py.
"""
import mysql.connector # Para capturar erros específicos
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QMessageBox, QLineEdit, QComboBox, QHeaderView)
from PyQt5.QtCore import Qt
# Importa a função de conexão do banco de dados a partir do módulo db_connection.py

from dados_gerais_base import criar_tabela_dados_gerais, configurar_tabela_dados_gerais_ui, get_distinct_values
# Diálogo de seleção de material (já implementado em outro módulo)
from dados_gerais_materiais_escolher import MaterialSelectionDialog
from utils import (formatar_valor_moeda,formatar_valor_percentual,original_pliq_values, converter_texto_para_valor, get_distinct_values_with_filter, install_header_width_menu)
from dados_gerais_mp import COLUNAS_LIMPAR_MATERIAIS  # Lista de colunas para limpeza, se necessário

# Definição das colunas para a tabela de Materiais
MATERIAIS_COLUNAS = [
    {'nome': 'material', 'tipo': 'TEXT', 'visivel': True, 'editavel': False},
    {'nome': 'descricao', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'id_mat', 'tipo': 'INTEGER', 'visivel': False},
    {'nome': 'num_orc', 'tipo': 'INTEGER', 'visivel': False},
    {'nome': 'ver_orc', 'tipo': 'INTEGER', 'visivel': False},
    {'nome': 'ref_le', 'tipo': 'TEXT', 'visivel': True, 'editavel': False},
    {'nome': 'descricao_no_orcamento', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'ptab', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'pliq', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'desc1_plus', 'tipo': 'REAL', 'visivel': True, 'editavel': True, 'header': 'Margem'},
    {'nome': 'desc2_minus', 'tipo': 'REAL', 'visivel': True, 'editavel': True, 'header': 'Desconto'},
    {'nome': 'und', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'desp', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'corres_orla_0_4', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'corres_orla_1_0', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'tipo', 'tipo': 'TEXT', 'visivel': True, 'editavel': True, 'combobox': True, 'opcoes': lambda: get_distinct_values_with_filter("TIPO", "FAMILIA", "PLACAS")},
    {'nome': 'familia', 'tipo': 'TEXT', 'visivel': True, 'editavel': True, 'combobox': True, 'opcoes': lambda: ["PLACAS"]},
    {'nome': 'comp_mp', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'larg_mp', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'esp_mp', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'MP', 'tipo': 'TEXT', 'visivel': True, 'botao': True, 'texto_botao': 'Escolher', 'funcao_botao': None},
    {'nome': 'nao_stock', 'tipo': 'INTEGER', 'visivel': True, 'checkbox': True}
]

#larguras = [200, 300, 50, 70, 50, 100, 500, 60, 60, 60, 60, 50, 50, 90, 90, 110, 120, 70, 70, 60, 100, 60] # Larguras em pixels para cada coluna
    #material;descricao;id_mat;num_orc;ver_orc;ref_le;descricao_no_orcamento;ptab;pliq;desc1_plus;desc2_minus;und;desp;corres_orla_0_4;corres_orla_1_0;tipo;familia;comp_mp;larg_mp;esp_mp;MP;nao_stock

# Definição das larguras fixas para cada coluna da tabela de Materiais
# As larguras são definidas em pixels e podem ser ajustadas conforme necessário.
MATERIAIS_COLUNAS_LARGURAS = [
    (0,  'material',                180),
    (1,  'descricao',               400),
    (2,  'id_mat',                   50),
    (3,  'num_orc',                 80),
    (4,  'ver_orc',                  50),
    (5,  'ref_le',                  110),
    (6,  'descricao_no_orcamento',  400),
    (7,  'ptab',                     80),
    (8,  'pliq',                     80),
    (9,  'desc1_plus',               60),
    (10, 'desc2_minus',              60),
    (11, 'und',                      50),
    (12, 'desp',                     50),
    (13, 'corres_orla_0_4',         90),
    (14, 'corres_orla_1_0',         90),
    (15, 'tipo',                    120),
    (16, 'familia',                 120),
    (17, 'comp_mp',                  90),
    (18, 'larg_mp',                  90),
    (19, 'esp_mp',                   90),
    (20, 'MP',                      100), # Coluna para o botão "Escolher"
    (21, 'nao_stock',                60), # Coluna para checkbox "Não Stock"
]

# Definição dos nomes das linhas (exemplo fixo)
MATERIAIS_LINHAS = [
    'Mat_Costas', 'Mat_Laterais', 'Mat_Divisorias', 'Mat_Tetos', 'Mat_Fundos',
    'Mat_Prat_Fixas', 'Mat_Prat_Amoviveis', 'Mat_Portas_Abrir', 'Mat_Laterais_Acabamento',
    'Mat_Fundos_Acabamento', 'Mat_Costas_Acabamento', 'Mat_Tampos_Acabamento',
    'Mat_Remates_Verticais', 'Mat_Remates_Horizontais', 'Mat_Guarnicoes_Verticais',
    'Mat_Guarnicoes_Horizontais', 'Mat_Enchimentos_Guarnicao', 'Mat_Rodape_AGL',
    'Mat_Gavetas_Frentes', 'Mat_Gavetas_Caixa', 'Mat_Gavetas_Fundo',
    'Mat_Livre_1', 'Mat_Livre_2', 'Mat_Livre_3', 'Mat_Livre_4', 'Mat_Livre_5'
]

def escolher_material(ui, linha_tab, nome_tabela):
    """
    Abre o diálogo para seleção de material, aplicando pré-filtros (tipo e família) se disponíveis.
    Após a seleção, mapeia os dados da linha selecionada para a linha correspondente na Tab_Material,
    e recalcula o valor de 'pliq' utilizando a fórmula:
         pliq = (PRECO_TABELA*(1-DESC2_MINUS))*(1+DESC1_PLUS)
    Retorna True se um material foi selecionado, False caso contrário.
    """
    from PyQt5.QtWidgets import QTableWidgetItem, QDialog
    tbl_materiais = ui.Tab_Material
    tbl_materiais.blockSignals(True)
    
    # Obter pré-filtros para 'tipo' e 'familia'
    tipo_col_idx = next((i for i, col in enumerate(MATERIAIS_COLUNAS) if col['nome'] == 'tipo'), None)
    familia_col_idx = next((i for i, col in enumerate(MATERIAIS_COLUNAS) if col['nome'] == 'familia'), None)
    pre_tipo = (tbl_materiais.cellWidget(linha_tab, tipo_col_idx).currentText()
                if (tipo_col_idx is not None and tbl_materiais.cellWidget(linha_tab, tipo_col_idx))
                else "")
    pre_familia = (tbl_materiais.cellWidget(linha_tab, familia_col_idx).currentText()
                   if (familia_col_idx is not None and tbl_materiais.cellWidget(linha_tab, familia_col_idx))
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
        # Limpa os campos de destino na linha selecionada da Tab_Material
        for campo, (src_idx, tgt_idx) in col_map.items():
            tbl_materiais.setItem(linha_tab, tgt_idx, QTableWidgetItem(""))

        def set_item(row, col_idx, texto):
            item = tbl_materiais.item(row, col_idx)
            if not item:
                from PyQt5.QtWidgets import QTableWidgetItem
                item = QTableWidgetItem()
                tbl_materiais.setItem(row, col_idx, item)
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
        
        novo_pliq = round((ptab_valor * (1 - dminus)) * (1 + dplus), 2)
        set_item(linha_tab, 8, formatar_valor_moeda(novo_pliq))

        # Atualiza a coluna 'nao_stock' com base na coluna STOCK da tabela de
        # matérias-primas (1 = marcar, caso contrário desmarcar)
        nao_stock_idx = next((i for i, col in enumerate(MATERIAIS_COLUNAS)
                              if col['nome'] == 'nao_stock'), None)
        if nao_stock_idx is not None:
            stock_cell = dialog.table.item(row_idx, 25)
            stock_val = stock_cell.text().strip() if stock_cell else ""
            chk_item = tbl_materiais.item(linha_tab, nao_stock_idx)
            if not chk_item:
                chk_item = QTableWidgetItem()
                chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                tbl_materiais.setItem(linha_tab, nao_stock_idx, chk_item)
            chk_item.setCheckState(Qt.Checked if stock_val == "1" else Qt.Unchecked)

        tbl_materiais.blockSignals(False)
        return True
    tbl_materiais.blockSignals(False)
    return False

def definir_larguras_tab_material(ui):
    """
    Define larguras padrão para cada coluna da Tab_Material, mas só aplica as larguras padrão
    se ainda não existir valor guardado nas preferências do utilizador.
    Permite ajuste manual e ativa persistência.
    """
    tabela = ui.Tab_Material
    header = tabela.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.Interactive)
    header.setStretchLastSection(False)
    
    from utils import enable_column_width_persistence
    # Chama para restaurar as larguras do utilizador (se existirem) e ligar a persistência
    enable_column_width_persistence(tabela, "Tab_Material_column_widths")
    
    # Só aplica larguras padrão se ainda não houver valores guardados (primeira vez)
    from PyQt5.QtCore import QSettings
    settings = QSettings("LANCA ENCANTO", "Orcamentos")
    key = "Tab_Material_column_widths"
    stored_widths = settings.value(key)

    if not stored_widths:
        larguras = [l[2] if isinstance(l, tuple) else l for l in MATERIAIS_COLUNAS_LARGURAS]
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
    if escolher_material(ui, row, nome_tabela):
        QMessageBox.information(None, "Material", f"Material selecionado para a linha {row+1}.")

# Atribui a função do botão "Escolher" à coluna MP
for col in MATERIAIS_COLUNAS:
    if col['nome'] == 'MP':
        col['funcao_botao'] = on_mp_button_clicked

def configurar_materiais_ui(ui):
    """
    Configura a tabela de Dados Gerais para Materiais:
      - Cria a tabela no banco de dados (se não existir) usando as definições.
      - Configura o QTableWidget para exibir os dados conforme as definições.
      - Define larguras fixas para as colunas da Tab_Material.
    Deve ser chamada durante a inicialização da interface.
    """
    #print("DEBUG: Executando configurar_materiais_ui para material.")
    criar_tabela_dados_gerais('materiais', MATERIAIS_COLUNAS, MATERIAIS_LINHAS)
    # Configura a tabela de Dados Gerais na interface na coluna familia preenche com 'PLACAS' & coluna tipo sem filtro
    configurar_tabela_dados_gerais_ui(ui, 'materiais', MATERIAIS_COLUNAS, MATERIAIS_LINHAS)
    definir_larguras_tab_material(ui)
    install_header_width_menu(ui.Tab_Material)

    from utils import apply_row_selection_style
    tabela = ui.Tab_Material
    familia_idx = next((i for i, c in enumerate(MATERIAIS_COLUNAS) if c['nome'] == 'familia'), None)
    if familia_idx is not None:
        for r in range(tabela.rowCount()):
            combo = tabela.cellWidget(r, familia_idx)
            if isinstance(combo, QComboBox):
                idx = combo.findText('PLACAS')
                if idx >= 0:
                    combo.setCurrentIndex(idx)
    apply_row_selection_style(tabela)

def on_item_changed_materiais(item):
    """
    Callback para tratar alterações na tabela de Materiais.
    Se o usuário editar as células dos campos 'ptab' (col. 7), 'desc1_plus' (col. 9)
    ou 'desc2_minus' (col. 10), recalcula 'pliq' (col. 8) usando:
         pliq = ptab * (1 + desc1_plus) * (1 - desc2_minus)
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
            # ptab (col 7), desc1_plus (col 9), desc2_minus (col 10), pliq (col 8).
            desc1_item = table.item(row, 9) # coluna desc1_plus
            desc2_item = table.item(row, 10) # coluna desc2_minus
            desc1_text = desc1_item.text() if desc1_item else "0%" # valor percentual
            desc2_text = desc2_item.text() if desc2_item else "0%" # valor percentual
            dplus = converter_texto_para_valor(desc1_text, "percentual")
            dminus = converter_texto_para_valor(desc2_text, "percentual")
            # Recalcula PLIQ usando a fórmula:
            # PLIQ = (PRECO_TABELA*(1-DESC2_MINUS))*(1+DESC1_PLUS)           
            novo_pliq = round((ptab_valor * (1 - dminus)) * (1 + dplus), 2)
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
