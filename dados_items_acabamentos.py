"""
Módulo: dados_items_acabamentos.py
Descrição:
  Este módulo configura a tabela "Tab_Acabamentos_12", destinada ao controle
  de acabamentos no orçamento (laca, verniz, tratamento de faces etc.).
  Segue a mesma lógica de outros módulos (ferragens, materiais), mas
  com colunas e linhas específicas para acabamentos.

  Principais funcionalidades:
    - Definição de colunas (ACABAMENTOS_COLUNAS) e linhas (ACABAMENTOS_LINHAS).
    - Configuração de widgets (ComboBox, botões, campos editáveis) na Tab_Acabamentos_12.
    - Cálculo automático do campo 'pliq' (preço líquido) com base em 'ptab' e descontos ('desc1_plus', 'desc2_minus').
    - Funções para carregar, importar e guardar dados no banco (tabela dados_items_acabamentos).
    - Limpeza de uma linha selecionada (“Limpar Linha”), facilitando correções.
    - Seleção de acabamentos via diálogo (MaterialSelectionDialog).

Autor: Paulo Catarino
Data: 20/03/2025
"""

from PyQt5.QtWidgets import (QTableWidgetItem, QComboBox, QPushButton, QMessageBox, QHeaderView, QAbstractItemView, QDialog)
from PyQt5.QtCore import Qt
import mysql.connector # Adicionado para erros específicos

# Utilitários de formatação e conversão
from utils import (formatar_valor_moeda, formatar_valor_percentual, converter_texto_para_valor, get_distinct_values_with_filter, adicionar_menu_limpar)

# Diálogo de seleção de material/ferragem/ssitemascorrer/acabamentos
from dados_gerais_materiais_escolher import MaterialSelectionDialog

# Conexão ao banco de dados
from db_connection import obter_cursor

# Formatar a versão do orçamento
from configurar_guardar_dados_gerais_orcamento import formatar_versao

###############################################################
# Definições específicas para Acabamentos
###############################################################
ACABAMENTOS_COLUNAS = [
    {'nome': 'material',             'tipo': 'TEXT',    'visivel': True,  'editavel': False},
    {'nome': 'descricao',               'tipo': 'TEXT',    'visivel': True,  'editavel': True},
    {'nome': 'id_acb',                  'tipo': 'INTEGER', 'visivel': True,  'editavel': False},
    {'nome': 'num_orc',                 'tipo': 'INTEGER', 'visivel': True,  'editavel': False},
    {'nome': 'ver_orc',                 'tipo': 'INTEGER', 'visivel': True,  'editavel': False},
    {'nome': 'ref_le',                  'tipo': 'TEXT',    'visivel': True,  'editavel': False},
    {'nome': 'descricao_no_orcamento',  'tipo': 'TEXT',    'visivel': True,  'editavel': True},

    {'nome': 'ptab',                    'tipo': 'REAL',    'visivel': True,  'editavel': True},
    {'nome': 'pliq',                    'tipo': 'REAL',    'visivel': True,  'editavel': True},
    {'nome': 'desc1_plus',              'tipo': 'REAL',    'visivel': True,  'editavel': True},
    {'nome': 'desc2_minus',             'tipo': 'REAL',    'visivel': True,  'editavel': True},
    {'nome': 'und',                     'tipo': 'TEXT',    'visivel': True,  'editavel': True},
    {'nome': 'desp',                    'tipo': 'REAL',    'visivel': True,  'editavel': True},
    {'nome': 'corres_orla_0_4',         'tipo': 'TEXT',    'visivel': True,  'editavel': True},
    {'nome': 'corres_orla_1_0',         'tipo': 'TEXT',    'visivel': True,  'editavel': True},

    {
        'nome': 'tipo',
        'tipo': 'TEXT',
        'visivel': True,
        'editavel': True,
        'combobox': True,
        'opcoes': lambda: get_distinct_values_with_filter("TIPO", "FAMILIA", "ACABAMENTOS")
    },
    {
        'nome': 'familia',
        'tipo': 'TEXT',
        'visivel': True,
        'editavel': True,
        'combobox': True,
        'opcoes': lambda: ["ACABAMENTOS"]
    },
    {'nome': 'comp_mp', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'larg_mp', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'esp_mp',  'tipo': 'REAL', 'visivel': True, 'editavel': True},

    {
        'nome': 'MP',
        'tipo': 'TEXT',
        'visivel': True,
        'botao': True,
        'texto_botao': 'Escolher',
        'funcao_botao': None  # Será atribuído abaixo
    }
]
###############################################################
# Definição das linhas para a tabela de Acabamentos
###############################################################
# Cada linha representa um tipo de acabamentos (verniz, lacagem, etc.)
# que poderá ser orçado e exibido na Tab_Acabamentos_12.
###############################################################
ACABAMENTOS_LINHAS = [
    'Acab_Lacar',
    'Acab_Verniz',
    'Acab_Face_1',
    'Acab_Face_2',
]


def escolher_acabamentos_item(ui, linha_tab):
    """
    Abre o diálogo (MaterialSelectionDialog) para o usuário escolher um acabamento.
    Ao confirmar, os valores são inseridos na linha 'linha_tab' de Tab_Acabamentos_12.
    Recalcula o 'pliq' com base em ptab e descontos.

    Retorna True se foi selecionado algum acabamento, False caso contrário.
    """
    tbl_item = ui.Tab_Acabamentos_12
    tbl_item.blockSignals(True)

    # Índices das colunas 'tipo' e 'familia', para eventual pré-filtro
    tipo_col_idx = 15
    familia_col_idx = 16
    pre_tipo = ""
    pre_familia = ""

    if tbl_item.cellWidget(linha_tab, tipo_col_idx):
        pre_tipo = tbl_item.cellWidget(linha_tab, tipo_col_idx).currentText()
    if tbl_item.cellWidget(linha_tab, familia_col_idx):
        pre_familia = tbl_item.cellWidget(linha_tab, familia_col_idx).currentText()

    dialog = MaterialSelectionDialog(ui.tableWidget_materias_primas, pre_tipo, pre_familia)
    if dialog.exec_() == QDialog.Accepted:
        row_idx = dialog.selected_row

        # Mapeamento: define como as colunas do diálogo serão copiadas para a Tab_Acabamentos_12
        col_map = {
            'ref_le':                 (3, 5),
            'descricao_no_orcamento': (5, 6),
            'ptab':                   (6, 7),
            'desc1_plus':             (7, 9),
            'desc2_minus':            (8, 10),
            'und':                    (10, 11),
            'desp':                   (11, 12),
            'corres_orla_0_4':        (16, 13),
            'corres_orla_1_0':        (17, 14),
            'comp_mp':                (19, 17),
            'larg_mp':                (20, 18),
            'esp_mp':                 (12, 19)
        }

        # Limpa as células antes de preencher
        for campo, (src_idx, tgt_idx) in col_map.items():
            tbl_item.setItem(linha_tab, tgt_idx, QTableWidgetItem(""))

        def set_item(row, col_idx, texto):
            item = tbl_item.item(row, col_idx)
            if not item:
                item = QTableWidgetItem()
                tbl_item.setItem(row, col_idx, item)
            item.setText(texto)

        ptab_valor = 0.0
        dplus = 0.0
        dminus = 0.0

        # Preenche cada célula a partir do que foi selecionado no diálogo
        for campo, (src_idx, tgt_idx) in col_map.items():
            valor = ""
            cell = dialog.table.item(row_idx, src_idx)
            if cell:
                valor = cell.text()
            set_item(linha_tab, tgt_idx, valor)
            # Armazena ptab e descontos, para em seguida calcular o pliq

            if campo == 'ptab':
                ptab_valor = converter_texto_para_valor(valor, "moeda")
            elif campo == 'desc1_plus':
                dplus = converter_texto_para_valor(valor, "percentual")
            elif campo == 'desc2_minus':
                dminus = converter_texto_para_valor(valor, "percentual")

        # Calcula pliq = (PRECO_TABELA*(1-DESC2_MINUS))*(1+DESC1_PLUS)
        novo_pliq = round((ptab_valor * (1 + dminus)) * (1 - dplus), 2)
        set_item(linha_tab, 8, formatar_valor_moeda(novo_pliq))

        tbl_item.blockSignals(False)
        return True

    tbl_item.blockSignals(False)
    return False
########################################
# Callback de edição e cálculo dos valores (ajustado)
########################################


def on_item_changed_items_acabamentos(item):
    """
    Callback disparado quando o usuário altera uma célula na Tab_Acabamentos_12.
    Recalcula o 'pliq' se as colunas ptab, desc1_plus ou desc2_minus forem editadas.
    """
    if not item:
        return
    tabela = item.tableWidget()
    if tabela.property("importando"):
        return

    row = item.row()
    col = item.column()

    # ptab: col 7, pliq: col 8, desc1_plus: col 9, desc2_minus: col 10
    if col in [7, 9, 10]:
        try:
            ptab_item = tabela.item(row, 7)
            ptab_text = ptab_item.text() if ptab_item else "0"
            ptab_valor = converter_texto_para_valor(ptab_text, "moeda")

            desc1_item = tabela.item(row, 9)
            desc2_item = tabela.item(row, 10)
            desc1_text = desc1_item.text() if desc1_item else "0%"
            desc2_text = desc2_item.text() if desc2_item else "0%"
            dplus = converter_texto_para_valor(desc1_text, "percentual")
            dminus = converter_texto_para_valor(desc2_text, "percentual")

            novo_pliq = round((ptab_valor * (1 + dminus)) * (1 - dplus), 2)
        except Exception:
            novo_pliq = 0.0
        # Atualiza a célula pliq
        tabela.blockSignals(True)
        pliq_item = tabela.item(row, 8)
        if not pliq_item:
            pliq_item = QTableWidgetItem()
            tabela.setItem(row, 8, pliq_item)
        pliq_item.setText(formatar_valor_moeda(novo_pliq))
        tabela.blockSignals(False)

        # Formata também os campos editados (ptab, desc1_plus e desc2_minus) após edição
        if col == 9:
            # desc1_plus
            tabela.blockSignals(True)
            item.setText(formatar_valor_percentual(dplus))
            tabela.blockSignals(False)
        elif col == 10:
            # desc2_minus
            tabela.blockSignals(True)
            item.setText(formatar_valor_percentual(dminus))
            tabela.blockSignals(False)
        elif col == 7:
            # ptab
            tabela.blockSignals(True)
            item.setText(formatar_valor_moeda(ptab_valor))
            tabela.blockSignals(False)

    elif col == 8:
        # Caso seja editado diretamente o pliq
        try:
            novo_valor = float(item.text().replace("€", "").replace(",", ".").strip())
        except Exception:
            novo_valor = 0.0
        tabela.blockSignals(True)
        item.setText(f"{novo_valor:.2f}€")
        tabela.blockSignals(False)


########################################
# Função para o botão "Escolher" (coluna MP)
########################################
def on_mp_button_clicked(ui, row, nome_tabela):
    """
    Chamado quando o usuário clica no botão "Escolher" (coluna MP)
    na Tab_Acabamentos_12. Abre o diálogo de seleção de acabamentos.
    """
    if escolher_acabamentos_item(ui, row):
        QMessageBox.information(None, "Acabamentos", f"Acabamento selecionado na linha {row+1}.")


# Atribui a função do botão "Escolher" à coluna MP
for col in ACABAMENTOS_COLUNAS:
    if col['nome'] == 'MP':
        col['funcao_botao'] = on_mp_button_clicked


########################################
# Função para definir larguras fixas para as colunas de Tab_Acabamentos_12
########################################
def definir_larguras_tab_acabamentos_item(ui):
    """
    Ajusta larguras fixas das colunas da Tab_Acabamentos_12
    para melhorar a apresentação visual.
    """
    tabela = ui.Tab_Acabamentos_12
    header = tabela.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.Fixed)
    header.setStretchLastSection(False)
    # Larguras definidas para cada coluna (ajuste conforme necessidade real)

    larguras = [200, 200, 50, 110, 50, 100, 400, 60, 60, 60, 60, 50, 50, 180, 110, 120, 120, 90, 90, 90, 100]
    num_cols = tabela.columnCount()
    if len(larguras) < num_cols:
        larguras += [100] * (num_cols - len(larguras))
    for idx in range(num_cols):
        tabela.setColumnWidth(idx, larguras[idx])


def importar_dados_item_tab_acabamentos(parent):
    """
    Reaproveita a lógica de importar_dados_gerais_com_opcao para preencher
    a Tab_Acabamentos_12, redirecionando temporariamente ui.Tab_Acabamentos
    para ui.Tab_Acabamentos_12.
    """
    ui = parent.ui
    mapeamento = {
        'descricao':              1,
        'ref_le':                 5,
        'descricao_no_orcamento': 6,
        'ptab':                   7,
        'pliq':                   8,
        'desc1_plus':             9,
        'desc2_minus':            10,
        'und':                    11,
        'desp':                   12,
        'corres_orla_0_4':        13,
        'corres_orla_1_0':        14,
        'tipo':                   15,
        'familia':                16,
        'comp_mp':                17,
        'larg_mp':                18,
        'esp_mp':                 19
    }

    # Importa a função de importação já existente para dados gerais
    from dados_gerais_manager import importar_dados_gerais_com_opcao

    # Redireciona tabela "acabamentos" para Tab_Acabameentos_12
    original_tab = ui.Tab_Acabamentos
    ui.Tab_Acabamentos = ui.Tab_Acabamentos_12

    try:
        # Importa usando a função genérica, passando "acabamentos" como tipo e nosso mapeamento
        importar_dados_gerais_com_opcao(parent, "acabamentos", mapeamento)
    finally:
        # Restaura para não atrapalhar outras partes do código
        ui.Tab_Acabamentos = original_tab

########################################
# Função principal para configurar a Tab_Acabamentos_12 (Dados do Item)
########################################

def configurar_tabela_acabamentos(parent):
    """
    Cria e configura a tabela Tab_Acabamentos_12, definindo colunas, linhas,
    widgets, callbacks e botões de importação.
    """
    ui = parent.ui
    tabela = ui.Tab_Acabamentos_12
    tabela.clear()

    num_cols = len(ACABAMENTOS_COLUNAS)
    num_rows = len(ACABAMENTOS_LINHAS)
    tabela.setColumnCount(num_cols)
    tabela.setRowCount(num_rows)

    # Define o nome das colunas no cabeçalho
    headers = [col['nome'] for col in ACABAMENTOS_COLUNAS]
    tabela.setHorizontalHeaderLabels(headers)
    tabela.verticalHeader().setVisible(False)

    # Preenche a primeira coluna (col 0) com o nome de cada linha (ex.: Acab_Lacar_Face_Sup)
    for row_idx, nome_linha in enumerate(ACABAMENTOS_LINHAS):
        item = QTableWidgetItem(nome_linha)
        tabela.setItem(row_idx, 0, item)

    # Preenche as colunas restantes
    for col_idx, col_def in enumerate(ACABAMENTOS_COLUNAS):
        if col_idx == 0:
            continue  # Já usado para os nomes das linhas
        for row_idx in range(num_rows):
            if col_def.get('combobox'):
                combo = QComboBox()
                opcoes = col_def.get('opcoes', [])
                if callable(opcoes):
                    opcoes = opcoes()
                combo.addItems(opcoes)
                tabela.setCellWidget(row_idx, col_idx, combo)
            # Verifica se a coluna deve ter um botão
            elif col_def.get('botao'):
                botao = QPushButton(col_def.get('texto_botao', 'Escolher'))

                def criar_callback(r, func=col_def['funcao_botao']):
                    return lambda: func(ui, r, "Tab_Acabamentos_12")

                botao.clicked.connect(criar_callback(row_idx))
                tabela.setCellWidget(row_idx, col_idx, botao)
            else:
                # Se for campo normal (texto editável ou não)
                item = QTableWidgetItem("")
                if col_def.get('editavel', False):
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                # Formatação padrão
                if col_def.get('formato') == 'moeda':
                    item.setText(formatar_valor_moeda(0))
                elif col_def.get('formato') == 'percentual':
                    item.setText(formatar_valor_percentual(0))
                tabela.setItem(row_idx, col_idx, item)

    # Conecta o callback para recalcular pliq após edição
    tabela.itemChanged.connect(on_item_changed_items_acabamentos)

    # Ajusta tamanho das colunas e linhas
    tabela.resizeColumnsToContents()
    tabela.resizeRowsToContents()
    # Define larguras personalizadas dp item
    definir_larguras_tab_acabamentos_item(ui)
    # Configura a tabela de Dados do Item na interface na coluna familia preenche com 'ACABAMENTOS' & coluna tipo sem filtro
    from utils import apply_row_selection_style
    tabela = ui.Tab_Acabamentos_12
    familia_idx = next((i for i, c in enumerate(ACABAMENTOS_COLUNAS) if c['nome'] == 'familia'), None)
    tipo_idx = next((i for i, c in enumerate(ACABAMENTOS_COLUNAS) if c['nome'] == 'tipo'), None)
    for r in range(tabela.rowCount()):
        if familia_idx is not None:
            combo = tabela.cellWidget(r, familia_idx)
            if isinstance(combo, QComboBox):
                idx = combo.findText('ACABAMENTOS')
                if idx >= 0:
                    combo.setCurrentIndex(idx)
        if tipo_idx is not None:
            combo_t = tabela.cellWidget(r, tipo_idx)
            if isinstance(combo_t, QComboBox):
                combo_t.setCurrentIndex(-1)
    apply_row_selection_style(tabela)

# =============================================================================
# Função para limpar as colunas da linha selecionada na Tab_Acabamentos_12 com o botão "Limpar Linha Selecionada" 
# =============================================================================
def limpar_linha_tab_acabamentos(obj):
    """
    Limpa (apaga) o conteúdo de uma linha selecionada na Tab_Acabamentos_12,
    como ref_le, ptab, pliq, descontos etc.
    """
    if hasattr(obj, "ui"):
        ui = obj.ui
        parent_widget = obj
    else:
        ui = obj
        parent_widget = obj

    tabela = ui.Tab_Acabamentos_12

    # Define que a seleção será por linha
    tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
    selection = tabela.selectionModel().selectedRows()
    if not selection:
        QMessageBox.warning(parent_widget, "Aviso", "Nenhuma linha selecionada!")
        return

    row_index = selection[0].row()
    # Colunas que devem ser limpas (ref_le, descrição_no_orcamento, ptab, pliq, descontos, etc.)
    COLUNAS_LIMPAR_ACABAMENTOS = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, 19]

    tabela.blockSignals(True)
    # Iterar sobre cada coluna e limpar o conteúdo
    for col in COLUNAS_LIMPAR_ACABAMENTOS:
        # Tenta obter um widget na célula
        widget = tabela.cellWidget(row_index, col)
        if widget:
            # Se o widget possuir o método setCurrentText (ex.: QComboBox), usá-lo para limpar
            if hasattr(widget, "setCurrentText"):
                widget.setCurrentText("")
            # Se tiver um método clear (ex.: QLineEdit ou outros), chama-o
            elif hasattr(widget, "clear"):
                widget.clear()
        else:
            # Se não houver widget, trata o QTableWidgetItem da célula
            item = tabela.item(row_index, col)
            if item:
                item.setText("")
            else:
                # Se o item não existir, cria um novo com texto vazio
                tabela.setItem(row_index, col, QTableWidgetItem(""))
    # Reabilitar os sinais da tabela
    tabela.blockSignals(False)

def criar_tabela_dados_items_acabamentos():
    """
    Cria a tabela 'dados_items_acabamentos' no banco de dados,
    se ela não existir, para armazenar os registros de acabamentos
    (id_acb, ptab, pliq, etc.) para cada item do orçamento.
    """
    #print("Verificando/Criando tabela 'dados_items_acabamentos'...")
    try:
        with obter_cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'dados_items_acabamentos'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE dados_items_acabamentos (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        num_orc VARCHAR(50) NOT NULL,
                        ver_orc VARCHAR(10) NOT NULL,
                        id_acb VARCHAR(50) NOT NULL, -- Chave do item do orçamento
                        linha INT NOT NULL,         -- Índice da linha na UI (0 a N-1)
                        material TEXT NULL,         -- Nome da linha (ex: Acab_Lacar)
                        descricao TEXT NULL,
                        ref_le VARCHAR(100) NULL,
                        descricao_no_orcamento TEXT NULL,
                        ptab DOUBLE NULL DEFAULT 0.0,
                        pliq DOUBLE NULL DEFAULT 0.0,
                        desc1_plus DOUBLE NULL DEFAULT 0.0,  -- Fração 0-1
                        desc2_minus DOUBLE NULL DEFAULT 0.0, -- Fração 0-1
                        und VARCHAR(20) NULL,
                        desp DOUBLE NULL DEFAULT 0.0,        -- Fração
                        corres_orla_0_4 VARCHAR(50) NULL,
                        corres_orla_1_0 VARCHAR(50) NULL,
                        tipo VARCHAR(100) NULL,
                        familia VARCHAR(100) NULL,
                        comp_mp DOUBLE NULL DEFAULT 0.0,
                        larg_mp DOUBLE NULL DEFAULT 0.0,
                        esp_mp DOUBLE NULL DEFAULT 0.0,
                        UNIQUE KEY idx_item_acb_unico (num_orc, ver_orc, id_acb, linha),
                        INDEX idx_item_acb_lookup (num_orc, ver_orc, id_acb)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                print("Tabela 'dados_items_acabamentos' criada.")
            else:
                 print("Tabela 'dados_items_acabamentos' já existe.")   # pretendo eliminar esta linha
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao criar/verificar 'dados_items_acabamentos': {err}")
    except Exception as e:
        print(f"Erro inesperado ao criar/verificar 'dados_items_acabamentos': {e}")


########################################
# FUNÇÃO: Guardar os dados dos itens do orçamento
########################################
def guardar_dados_item_orcamento_tab_acabamentos(parent):
    """
    Percorre a Tab_Acabamentos_12, extrai os dados e salva na tabela
    dados_items_acabamentos. Se já existir registro para (num_orc, ver_orc, id_acb),
    pergunta se o usuário deseja sobrescrever.
    """
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = formatar_versao(ui.lineEdit_versao_orcamento.text())
    id_acb = ui.lineEdit_item_orcamento.text().strip()
    MOSTRAR_AVISOS = False     # ATENÇÃO: Muda para True quando quiser ver as mensagens

    if not num_orc or not ver_orc or not id_acb:
        QMessageBox.warning(parent, "Aviso", "Preencha os campos 'Num Orçamento', 'Versão' e 'Item'!")
        return

    tabela = ui.Tab_Acabamentos_12
    num_rows = tabela.rowCount()
    if num_rows == 0: return
    # Lista de colunas no BD (ordem do INSERT)

    col_names_db = [
        'num_orc', 'ver_orc', 'id_acb', 'linha',
        'material', 'descricao', 'ref_le', 'descricao_no_orcamento',
        'ptab', 'pliq', 'desc1_plus', 'desc2_minus',
        'und', 'desp', 'corres_orla_0_4', 'corres_orla_1_0',
        'tipo', 'familia', 'comp_mp', 'larg_mp', 'esp_mp'
    ]

    ui_to_db_mapping = {
        'num_orc':        3,
        'ver_orc':        4,
        'id_acb':         2,
        'material':    0,
        'descricao':      1,
        'ref_le':         5,
        'descricao_no_orcamento': 6,
        'ptab':           7,
        'pliq':           8,
        'desc1_plus':     9,
        'desc2_minus':    10,
        'und':            11,
        'desp':           12,
        'corres_orla_0_4':13,
        'corres_orla_1_0':14,
        'tipo':           15,
        'familia':        16,
        'comp_mp':        17,
        'larg_mp':        18,
        'esp_mp':         19
    }
    # Conjuntos para conversão de valores formatados

    campos_moeda = {"ptab", "pliq"}
    campos_percentual = {"desc1_plus", "desc2_minus", "desp"}

    dados_para_salvar = []
    for r in range(num_rows):
        dados_linha = {'num_orc': num_orc, 'ver_orc': ver_orc, 'id_acb': id_acb, 'linha': r}
        for key_db in col_names_db:
            if key_db in dados_linha: continue
            col_ui = ui_to_db_mapping.get(key_db);
            if col_ui is None: continue
            widget = tabela.cellWidget(r, col_ui)
            if isinstance(widget, QComboBox):
                valor_str = widget.currentText().strip()
            else:
                cell = tabela.item(r, col_ui)
                valor_str = cell.text().strip() if cell else ""
            valor_final = None
            if key_db in campos_moeda:
                try: valor_final = converter_texto_para_valor(valor_str, "moeda") if valor_str else None
                except: valor_final = None
            elif key_db in campos_percentual:
                try: valor_final = converter_texto_para_valor(valor_str, "percentual") if valor_str else None
                except: valor_final = None
            else: valor_final = valor_str if valor_str else None
            dados_linha[key_db] = valor_final
        dados_para_salvar.append(tuple(dados_linha.get(cn, None) for cn in col_names_db))

    # Interação com a BD usando obter_cursor
    try:
        count = 0
        with obter_cursor() as cursor_check:
            cursor_check.execute(
                "SELECT COUNT(*) FROM dados_items_acabamentos WHERE num_orc=%s AND ver_orc=%s AND id_acb=%s",
                (num_orc, ver_orc, id_acb)
            )
            count = cursor_check.fetchone()[0]

        if count > 0:
            resposta = QMessageBox.question(parent, "Dados Existentes",
                                            "Já existem dados para este item (Acabamentos). Deseja substituí-los?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resposta == QMessageBox.No: return
            else:
                with obter_cursor() as cursor_del:
                    cursor_del.execute(
                        "DELETE FROM dados_items_acabamentos WHERE num_orc=%s AND ver_orc=%s AND id_acb=%s",
                        (num_orc, ver_orc, id_acb)
                    )
                    print(f"{cursor_del.rowcount} registos antigos de acabamentos eliminados.")

        linhas_inseridas = 0
        with obter_cursor() as cursor_insert:
            placeholders = ", ".join(["%s"] * len(col_names_db))
            query_insert = f"INSERT INTO dados_items_acabamentos ({', '.join(col_names_db)}) VALUES ({placeholders})"
            for row_data in dados_para_salvar:
                try:
                    cursor_insert.execute(query_insert, row_data)
                    linhas_inseridas += 1
                except mysql.connector.Error as insert_err:
                     print(f"Erro MySQL ao inserir linha {row_data[3]} para item {id_acb}: {insert_err}")
                     QMessageBox.warning(parent, "Erro ao Inserir", f"Falha ao guardar linha {row_data[3]+1}: {insert_err}")

        if MOSTRAR_AVISOS: QMessageBox.information(parent, "Sucesso", f"{linhas_inseridas} linha(s) de Acabamentos guardada(s).")
        print(f"{linhas_inseridas} linha(s) de Acabamentos guardada(s).")

    except mysql.connector.Error as err:
        QMessageBox.critical(parent, "Erro Base de Dados", f"Erro ao guardar dados: {err}")
        print(f"Erro MySQL (guardar acabamentos): {err}")
    except Exception as e:
        QMessageBox.critical(parent, "Erro Inesperado", f"Erro ao guardar dados: {e}")
        import traceback; traceback.print_exc()


# =============================================================================
# Função carregar_dados_items(parent) 
# =============================================================================
def carregar_dados_items_acabamentos(parent):
    """
    Carrega na Tab_Acabamentos_12 os dados de acabamentos salvos na tabela
    dados_items_acabamentos, filtrando por (num_orc, ver_orc, id_acb).
    Se não encontrar, pode tentar buscar em dados_gerais_acabamentos ou algo similar,
    caso exista. Se não, apenas preenche colunas fixas.
    """
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = ui.lineEdit_versao_orcamento.text().strip()
    id_acb = ui.lineEdit_item_orcamento.text().strip()
    MOSTRAR_AVISOS = False  # ATENÇÃO: Muda para True quando quiser ver as mensagens

    tabela = ui.Tab_Acabamentos_12
    tabela.blockSignals(True)

    # Limpa colunas relevantes
    clear_cols = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,17,18,19]
    key_cols = {2: id_acb, 3: num_orc, 4: ver_orc}
    for r in range(tabela.rowCount()):
        for c in clear_cols:
            widget = tabela.cellWidget(r, c)
            if widget and isinstance(widget, QComboBox): widget.setCurrentIndex(-1)
            elif widget and hasattr(widget, 'clear'): widget.clear()
            else: 
                item = tabela.item(r, c)
                if item: item.setText("")
                else: tabela.setItem(r, c, QTableWidgetItem(""))
        for c_key, val_key in key_cols.items():
             item = tabela.item(r, c_key)
             if not item: item = QTableWidgetItem(); tabela.setItem(r, c_key, item)
             item.setText(str(val_key) if val_key is not None else "")
             item.setFlags(item.flags() & ~Qt.ItemIsEditable)

    tipo_idx = next((i for i, c in enumerate(ACABAMENTOS_COLUNAS) if c['nome'] == 'tipo'), None)
    familia_idx = next((i for i, c in enumerate(ACABAMENTOS_COLUNAS) if c['nome'] == 'familia'), None)
    for r in range(tabela.rowCount()):
        if familia_idx is not None:
            combo_f = tabela.cellWidget(r, familia_idx)
            if isinstance(combo_f, QComboBox):
                idx = combo_f.findText('ACABAMENTOS')
                if idx >= 0:
                    combo_f.setCurrentIndex(idx)
        if tipo_idx is not None:
            combo_t = tabela.cellWidget(r, tipo_idx)
            if isinstance(combo_t, QComboBox):
                combo_t.setCurrentIndex(-1)

    # Mapeamentos para os índices das colunas das tabelas do banco de dados:
    # Para a tabela dados_items_acabamentos (índices conforme definição)
    db_mapping_items = {
        'linha': 4,  # <--- ADICIONAR ESTA LINHA. Mapeia o campo 'linha' para o índice 4
        'material':  5, # Nota: O nome 'material' é usado aqui para consistência, mas refere-se ao 'acabamento' da UI
        'descricao':    6,
        'id_acb':       3,
        'num_orc':      1,
        'ver_orc':      2,
        'ref_le':       7,
        'descricao_no_orcamento': 8,
        'ptab':         9,
        'pliq':         10,
        'desc1_plus':   11,
        'desc2_minus':  12,
        'und':          13,
        'desp':         14,
        'corres_orla_0_4': 15,
        'corres_orla_1_0': 16,
        'tipo':         17,
        'familia':      18,
        'comp_mp':      19,
        'larg_mp':      20,
        'esp_mp':       21
    }

    # Caso houvesse "dados_gerais_acabamentos", ajustaria aqui.
    # Mas se for para reaproveitar "dados_gerais_acabamentos" ou outro, adaptar o mapeamento.
    # Exemplo de reuso (similar ao ferragens):
    db_mapping_gerais = {
        'descricao': 4, 'id_acb': 5, 'num_orc': 6, 'ver_orc': 7,
        'ref_le': 8, 'descricao_no_orcamento': 9, 'ptab': 10, 'pliq': 11,
        'desc1_plus': 12, 'desc2_minus': 13, 'und': 14, 'desp': 15,
        'corres_orla_0_4': 16, 'corres_orla_1_0': 17, 'tipo': 18,
        'familia': 19, 'comp_mp': 20, 'larg_mp': 21, 'esp_mp': 22
    }
    # Mapeamento para a interface Tab_Acabamentos_12: chave = nome do campo, valor = coluna

    tab_mapping = {
        'descricao': 1, 'id_acb': 2, 'num_orc': 3, 'ver_orc': 4,
        'ref_le': 5, 'descricao_no_orcamento': 6, 'ptab': 7, 'pliq': 8,
        'desc1_plus': 9, 'desc2_minus': 10, 'und': 11, 'desp': 12,
        'corres_orla_0_4': 13, 'corres_orla_1_0': 14, 'tipo': 15,
        'familia': 16, 'comp_mp': 17, 'larg_mp': 18, 'esp_mp': 19
    }

    registros_items = []
    registros_gerais = []
    try:
        # 1. Tenta carregar de dados_items_acabamentos
        with obter_cursor() as cursor_items:
            cursor_items.execute("""
                SELECT * FROM dados_items_acabamentos
                WHERE num_orc = %s AND ver_orc = %s AND id_acb = %s
                ORDER BY linha
            """, (num_orc, ver_orc, id_acb))
            registros_items = cursor_items.fetchall()

        if registros_items:
            #print(f"Carregados {len(registros_items)} registos de dados_items_acabamentos.")
            # Preenche com dados dos itens (lógica mantida)
            for registro in registros_items:
                linha_idx = registro[db_mapping_items['linha']]
                if 0 <= linha_idx < tabela.rowCount():
                    for campo, col_tab_ui in tab_mapping.items():
                        if campo in ['num_orc', 'ver_orc', 'id_acb']: continue
                        db_idx = db_mapping_items.get(campo);
                        if db_idx is None or db_idx >= len(registro): continue # Segurança
                        valor_bd = registro[db_idx]; texto_formatado = ""
                        if valor_bd is not None:
                            if campo in ["ptab", "pliq"]: texto_formatado = formatar_valor_moeda(valor_bd)
                            elif campo in ["desc1_plus", "desc2_minus", "desp"]: texto_formatado = formatar_valor_percentual(valor_bd)
                            else: texto_formatado = str(valor_bd)
                        widget = tabela.cellWidget(linha_idx, col_tab_ui)
                        if isinstance(widget, QComboBox):
                            idx_combo = widget.findText(texto_formatado, Qt.MatchFixedString); widget.setCurrentIndex(idx_combo if idx_combo >= 0 else -1)
                        else:
                            item = tabela.item(linha_idx, col_tab_ui);
                            if not item: item = QTableWidgetItem(); tabela.setItem(linha_idx, col_tab_ui, item)
                            item.setText(texto_formatado)
                else: print(f"[AVISO] Índice de linha inválido ({linha_idx}) no registo de item.")
            if MOSTRAR_AVISOS: QMessageBox.information(parent, "Dados Carregados", "Dados do item (Acabamentos) carregados.")

        else:
            # 2. Tenta carregar de dados_gerais_acabamentos
            print("Nenhum dado de item encontrado, tentando carregar dados gerais...")
            try:
                with obter_cursor() as cursor_geral:
                    cursor_geral.execute("""
                        SELECT * FROM dados_gerais_acabamentos
                        WHERE num_orc = %s AND ver_orc = %s -- Ajustar filtro!
                        ORDER BY id
                    """, (num_orc, ver_orc))
                    registros_gerais = cursor_geral.fetchall()
            except mysql.connector.Error as err_geral:
                 if err_geral.errno == 1146: print("Tabela 'dados_gerais_acabamentos' não encontrada.")
                 else: print(f"Erro MySQL ao buscar dados gerais de acabamentos: {err_geral}"); QMessageBox.warning(parent, "Erro BD", f"Erro ao buscar dados gerais: {err_geral}")

            if registros_gerais:
                print(f"Carregando {len(registros_gerais)} registos de dados_gerais_acabamentos.")
                # Lógica de preenchimento (mantida)
                for row_idx, registro in enumerate(registros_gerais):
                     if row_idx >= tabela.rowCount(): break
                     material_geral = registro[db_mapping_gerais.get('material', 0)]
                     linha_ui_destino = -1
                     for r_ui in range(tabela.rowCount()):
                          if tabela.item(r_ui, 0).text() == material_geral: linha_ui_destino = r_ui; break
                     if linha_ui_destino == -1: continue
                     for campo, col_tab_ui in tab_mapping.items():
                         if campo in ['num_orc', 'ver_orc', 'id_acb']: continue
                         db_idx = db_mapping_gerais.get(campo);
                         if db_idx is None or db_idx >= len(registro): continue
                         valor_bd = registro[db_idx]; texto_formatado = ""
                         if valor_bd is not None:
                             if campo in ["ptab", "pliq"]: texto_formatado = formatar_valor_moeda(valor_bd)
                             elif campo in ["desc1_plus", "desc2_minus", "desp"]: texto_formatado = formatar_valor_percentual(valor_bd)
                             else: texto_formatado = str(valor_bd)
                         widget = tabela.cellWidget(linha_ui_destino, col_tab_ui)
                         if isinstance(widget, QComboBox):
                             idx_combo = widget.findText(texto_formatado, Qt.MatchFixedString); widget.setCurrentIndex(idx_combo if idx_combo >= 0 else -1)
                         else:
                             item = tabela.item(linha_ui_destino, col_tab_ui);
                             if not item: item = QTableWidgetItem(); tabela.setItem(linha_ui_destino, col_tab_ui, item)
                             item.setText(texto_formatado)
                if MOSTRAR_AVISOS: QMessageBox.information(parent, "Dados Carregados", "Dados gerais de Acabamentos importados.")
            else:
                 if MOSTRAR_AVISOS: QMessageBox.information(parent, "Dados Vazios", "Nenhum dado específico ou geral encontrado para este item (Acabamentos).")
                 print("Nenhum dado específico ou geral encontrado para Acabamentos.")

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao carregar dados de acabamentos: {err}")
        QMessageBox.critical(parent, "Erro Base de Dados", f"Erro ao carregar dados: {err}")
    except Exception as e:
        print(f"Erro inesperado ao carregar dados de acabamentos: {e}")
        QMessageBox.critical(parent, "Erro Inesperado", f"Erro ao carregar dados: {e}")
        import traceback; traceback.print_exc()
    finally:
        tabela.blockSignals(False) # Garante desbloqueio


def configurar_dados_items_orcamento_acabamentos(parent):
    """
    Cria (se necessário) a tabela dados_items_acabamentos no BD,
    carrega dados para (num_orc, ver_orc, id_acb) e alterna a
    interface para a aba "orcamento_items".
    """
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = ui.lineEdit_versao_orcamento.text().strip()
    id_acb = ui.lineEdit_item_orcamento.text().strip()

    if ui.Tab_Acabamentos_12.columnCount() == 0:  # tabela ainda não configurada
        configurar_tabela_acabamentos(parent)     # cria colunas, linhas, widgets
    
    if not num_orc or not ver_orc or not id_acb:
        QMessageBox.warning(parent, "Aviso", "Preencha os campos 'Num Orçamento', 'Versão' e 'Item'!")
        return

    criar_tabela_dados_items_acabamentos()
    carregar_dados_items_acabamentos(parent)

    # Muda para a aba "orcamento_items"
    for i in range(ui.tabWidget_orcamento.count()):
        widget = ui.tabWidget_orcamento.widget(i)
        if widget.objectName() == "orcamento_items":
            ui.tabWidget_orcamento.setCurrentIndex(i)
            break

########################################
# Função para inicializar as configurações e conectar o botão de guardar
########################################
def inicializar_dados_items_acabamentos(parent):
    """
    Função principal para inicializar a Tab_Acabamentos_12.
    - Cria as colunas/linhas,
    - Conecta os botões "Guardar" e "Limpar Linha",
    - Prepara a tabela para importação e manipulação dos dados de acabamentos.
    """
    ui = parent.ui
    configurar_tabela_acabamentos(parent)

    # Conecta o botão de guardar (interface: guardar_dados_item_orcamento_tab_acabamentos_4)
    ui.guardar_dados_item_orcamento_tab_acabamentos_4.clicked.connect(lambda: guardar_dados_item_orcamento_tab_acabamentos(parent))

    # Conecta o botão de limpar_linha_tab_sistemas_correr_2
    ui.limpar_linha_tab_acabamentos_3.clicked.connect(lambda: limpar_linha_tab_acabamentos(parent))

    # Botão para importar dados
    ui.importar_dados_item_tab_acabamentos_4.clicked.connect(lambda: importar_dados_item_tab_acabamentos(parent))
    adicionar_menu_limpar(ui.Tab_Acabamentos_12, lambda: limpar_linha_tab_acabamentos(parent))
