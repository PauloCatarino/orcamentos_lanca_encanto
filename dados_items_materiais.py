"""
Módulo: dados_items_materiais.py
Descrição:
  Este módulo configura a tabela "Tab_Material_11", destinada ao gerenciamento de materiais
  dentro de um orçamento. Ele segue uma lógica similar ao módulo de ferragens, mas adaptada
  especificamente para lidar com materiais (placas, acabamentos, laterais, etc.).

  Principais funcionalidades:
    - Definição das colunas (MATERIAIS_COLUNAS) e linhas (MATERIAIS_LINHAS) para a tabela de materiais.
    - Configuração dos widgets (ComboBox, botões e campos editáveis) na Tab_Material_11.
    - Cálculo automático do campo 'pliq' (preço líquido) com base no preço de tabela (ptab) e descontos.
    - Funções para carregar, importar e guardar os dados de materiais no banco de dados.
    - Função para limpar o conteúdo de uma linha selecionada (útil para corrigir lançamentos incorretos).
    - Função para selecionar materiais (“Escolher”) abrindo um diálogo de seleção (MaterialSelectionDialog).

Autor: Paulo Catarino
Data: 20/03/2025
"""
import mysql.connector # Adicionado para capturar erros
from PyQt5.QtWidgets import (QTableWidgetItem, QComboBox, QPushButton, QMessageBox,  QHeaderView, QAbstractItemView, QDialog)
from PyQt5.QtCore import Qt

# Importações de funções utilitárias (formatação/conversão de valores, filtros de dados etc.)
from utils import (formatar_valor_moeda, formatar_valor_percentual, converter_texto_para_valor, get_distinct_values_with_filter,adicionar_menu_limpar)

# Diálogo de seleção de material
from dados_gerais_materiais_escolher import MaterialSelectionDialog

# Função de conexão com o banco de dados
from db_connection import obter_cursor

# Para formatar a versão do orçamento
from configurar_guardar_dados_gerais_orcamento import formatar_versao

###############################################################
# Definição das colunas para Tab_Material_11
###############################################################
# Cada dicionário no array MATERIAIS_COLUNAS representa uma coluna
# da tabela de materiais, especificando nome, tipo de dado,
# se é editável, se terá combobox, botão, etc.
###############################################################
MATERIAIS_COLUNAS = [
    {'nome': 'material',               'tipo': 'TEXT',   'visivel': True,  'editavel': False},
    {'nome': 'descricao',              'tipo': 'TEXT',   'visivel': True,  'editavel': True},
    {'nome': 'id_mat',                 'tipo': 'INTEGER','visivel': True,  'editavel': False},
    {'nome': 'num_orc',                'tipo': 'INTEGER','visivel': True,  'editavel': False},
    {'nome': 'ver_orc',                'tipo': 'INTEGER','visivel': True,  'editavel': False},
    {'nome': 'ref_le',                 'tipo': 'TEXT',   'visivel': True,  'editavel': False},
    {'nome': 'descricao_no_orcamento', 'tipo': 'TEXT',   'visivel': True,  'editavel': True},
    {'nome': 'ptab',                   'tipo': 'REAL',   'visivel': True,  'editavel': True},
    {'nome': 'pliq',                   'tipo': 'REAL',   'visivel': True,  'editavel': True},
    {'nome': 'desc1_plus',             'tipo': 'REAL',   'visivel': True,  'editavel': True},
    {'nome': 'desc2_minus',            'tipo': 'REAL',   'visivel': True,  'editavel': True},
    {'nome': 'und',                    'tipo': 'TEXT',   'visivel': True,  'editavel': True},
    {'nome': 'desp',                   'tipo': 'REAL',   'visivel': True,  'editavel': True},
    {'nome': 'corres_orla_0_4',        'tipo': 'TEXT',   'visivel': True,  'editavel': True},
    {'nome': 'corres_orla_1_0',        'tipo': 'TEXT',   'visivel': True,  'editavel': True},
    {
        'nome': 'tipo',
        'tipo': 'TEXT',
        'visivel': True,
        'editavel': True,
        'combobox': True,
        'opcoes': lambda: get_distinct_values_with_filter("TIPO", "FAMILIA", "PLACAS")
    },
    {
        'nome': 'familia',
        'tipo': 'TEXT',
        'visivel': True,
        'editavel': True,
        'combobox': True,
        'opcoes': lambda: ["PLACAS"]
    },
    {'nome': 'comp_mp', 'tipo': 'REAL', 'visivel': True,  'editavel': True},
    {'nome': 'larg_mp', 'tipo': 'REAL', 'visivel': True,  'editavel': True},
    {'nome': 'esp_mp',  'tipo': 'REAL', 'visivel': True,  'editavel': True},
    {
        'nome': 'MP',
        'tipo': 'TEXT',
        'visivel': True,
        'botao': True,
        'texto_botao': 'Escolher',
        'funcao_botao': None  # Será atribuído mais abaixo
    }
]

###############################################################
# Definição das linhas para a tabela de Materiais
###############################################################
# Cada item dessa lista representa uma linha na Tab_Material_11, ou seja,
# um tipo de material a ser orçado (p. ex. Mat_Costas, Mat_Laterais etc.).
###############################################################
MATERIAIS_LINHAS = [
    'Mat_Costas', 'Mat_Laterais', 'Mat_Divisorias', 'Mat_Tetos', 'Mat_Fundos',
    'Mat_Prat_Fixas', 'Mat_Prat_Amoviveis', 'Mat_Portas_Abrir', 'Mat_Laterais_Acabamento',
    'Mat_Fundos_Acabamento', 'Mat_Costas_Acabamento', 'Mat_Tampos_Acabamento',
    'Mat_Remates_Verticais', 'Mat_Remates_Horizontais', 'Mat_Guarnicoes_Verticais',
    'Mat_Guarnicoes_Horizontais', 'Mat_Enchimentos_Guarnicao', 'Mat_Rodape_AGL',
    'Mat_Gavetas_Frentes', 'Mat_Gavetas_Caixa', 'Mat_Gavetas_Fundo',
    'Mat_Livre_1', 'Mat_Livre_2', 'Mat_Livre_3', 'Mat_Livre_4', 'Mat_Livre_5'
]

def escolher_material_item(ui, linha_tab):
    """
    Abre um diálogo (MaterialSelectionDialog) para o usuário escolher um material.
    Em caso de confirmação, os dados do material selecionado são mapeados
    para a linha (linha_tab) na tabela Tab_Material_11.

    Retorna:
        True se o usuário selecionou algum material,
        False se a operação foi cancelada.
    """
    tbl_item = ui.Tab_Material_11
    tbl_item.blockSignals(True)
    
    # Identifica as colunas de "tipo" e "familia" para pré-filtrar o diálogo:
    tipo_col_idx = 15
    familia_col_idx = 16
    pre_tipo = ""
    pre_familia = ""
    if tbl_item.cellWidget(linha_tab, tipo_col_idx):
        pre_tipo = tbl_item.cellWidget(linha_tab, tipo_col_idx).currentText()
    if tbl_item.cellWidget(linha_tab, familia_col_idx):
        pre_familia = tbl_item.cellWidget(linha_tab, familia_col_idx).currentText()
    
    # Abre o diálogo, usando ui.tableWidget_materias_primas como fonte de dados
    dialog = MaterialSelectionDialog(ui.tableWidget_materias_primas, pre_tipo, pre_familia)
    if dialog.exec_() == QDialog.Accepted:
        row_idx = dialog.selected_row

        # Mapeamento para preencher a linha no Tab_Material_11
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

        # Limpa as células que serão preenchidas
        for campo, (src_idx, tgt_idx) in col_map.items():
            tbl_item.setItem(linha_tab, tgt_idx, QTableWidgetItem(""))
        # Função local para auxiliar na atribuição de texto em cada célula
        def set_item(row, col_idx, texto):
            item = tbl_item.item(row, col_idx)
            if not item:
                item = QTableWidgetItem()
                tbl_item.setItem(row, col_idx, item)
            item.setText(texto)
        
        ptab_valor = 0.0
        dplus = 0.0
        dminus = 0.0

        # Copia os valores selecionados para a linha apropriada
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

        # Calcula o preço líquido (pliq)
        novo_pliq = round((ptab_valor * (1 + dminus)) * (1 - dplus), 2)
        set_item(linha_tab, 8, formatar_valor_moeda(novo_pliq))
        
        tbl_item.blockSignals(False)
        return True

    tbl_item.blockSignals(False)
    return False

########################################
# Callback de edição e cálculo dos valores (ajustado)
########################################
def on_item_changed_items_materiais(item):
    """
    Callback disparado quando o usuário altera alguma célula na Tab_Material_11.
    Recalcula o 'pliq' (preço líquido) caso as colunas relevantes (ptab, desc1_plus,
    desc2_minus) sejam editadas, e formata os valores como moeda ou percentual.

    Fórmula:
      pliq = (PRECO_TABELA*(1-DESC2_MINUS))*(1+DESC1_PLUS)

    Se o usuário editar a própria coluna pliq, o sistema apenas formata 
    o valor como moeda.
    """
    if not item:
        return
    tabela = item.tableWidget()
    if tabela.property("importando"):
        # Se estiver em modo de importação, não faz nada para evitar loops de sinais.
        return
    
    row = item.row()
    col = item.column()

    # Índices relevantes:
    # ptab (col 7), desc1_plus (col 9), desc2_minus (col 10), pliq (col 8).
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
        pliq_item = tabela.item(row, 8);
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
        # Se o usuário editar diretamente o campo pliq
        try:
            novo_valor = float(item.text().replace("€", "").replace(",", ".").strip())
        except Exception:
            novo_valor = 0.0
        tabela.blockSignals(True)
        item.setText(f"{novo_valor:.2f}€")
        tabela.blockSignals(False)

####################################
# Função para o botão "Escolher" (coluna MP)
########################################
def on_mp_button_clicked(ui, row, nome_tabela):
    """
    Chamado quando o usuário clica no botão "Escolher" da coluna MP.
    Invoca a função escolher_material_item para abrir o diálogo de
    seleção de materiais e, se confirmado, exibe uma mensagem de sucesso.
    """
    if escolher_material_item(ui, row):
        QMessageBox.information(None, "Material", f"Material selecionado para a linha {row+1}.")

# Atribui a função do botão "Escolher" à coluna MP
for col in MATERIAIS_COLUNAS:
    if col['nome'] == 'MP':
        col['funcao_botao'] = on_mp_button_clicked

########################################
# Função para definir larguras fixas para as colunas de Tab_Ferragens_11
########################################
def definir_larguras_tab_material_item(ui):
    """
    Define larguras fixas para cada coluna da Tab_Material_11,
    melhorando a apresentação visual.
    """
    tabela = ui.Tab_Material_11
    header = tabela.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.Fixed)
    header.setStretchLastSection(False)

    # Ajustar conforme as necessidades do layout
    larguras = [200, 200, 50, 110, 50, 100, 400, 60, 60, 60, 60, 50, 50, 180, 110, 120, 120, 90, 90, 90, 100]
    num_cols = tabela.columnCount()
    if len(larguras) < num_cols:
        larguras += [100] * (num_cols - len(larguras))
    for idx in range(num_cols):
        tabela.setColumnWidth(idx, larguras[idx])

def importar_dados_item_orcamento_tab_material(parent):
    """
    Importa dados de materiais para a Tab_Material_11, reutilizando
    a função importar_dados_gerais_com_opcao (de dados_gerais_manager).

    Temporariamente, redireciona ui.Tab_Material para ui.Tab_Material_11
    e chama a função de importação, restaurando depois.
    """
    ui = parent.ui
    # Mapeamento de colunas para a Tab_Material_11 (colunas começam em 0, mas 0 é nome da linha)
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
        'esp_mp':                 19,
    }
    # Importa a função de importação já existente para dados gerais   
    from dados_gerais_manager import importar_dados_gerais_com_opcao

    # Redireciona tabela "material" para Tab_Material_11
    original_tab = ui.Tab_Material
    ui.Tab_Material = ui.Tab_Material_11

    try:
        # Importa usando a função genérica, passando "materiais" como tipo e nosso mapeamento
        importar_dados_gerais_com_opcao(parent, "materiais", mapeamento)
    finally:
        ui.Tab_Material = original_tab

########################################
# Função principal para configurar a Tab_Material_11 (Dados do Item)
########################################
def configurar_tabela_material(parent):
    """
    Configura a tabela Tab_Material_11:
      - Cria as colunas definidas em MATERIAIS_COLUNAS.
      - Cria as linhas definidas em MATERIAIS_LINHAS.
      - Conecta o callback on_item_changed_items_materiais para recalcular pliq.
      - Define larguras e acopla a função de importação via botão.
    """
    ui = parent.ui
    tabela = ui.Tab_Material_11
    tabela.clear()

    num_cols = len(MATERIAIS_COLUNAS)
    num_rows = len(MATERIAIS_LINHAS)
    tabela.setColumnCount(num_cols)
    tabela.setRowCount(num_rows)

    # Define cabeçalhos horizontais (nomes das colunas)
    headers = [col['nome'] for col in MATERIAIS_COLUNAS]
    tabela.setHorizontalHeaderLabels(headers)
    tabela.verticalHeader().setVisible(False)

    # Preenche a coluna 0 com o nome de cada linha
    for row_idx, nome_linha in enumerate(MATERIAIS_LINHAS):
        item = QTableWidgetItem(nome_linha)
        tabela.setItem(row_idx, 0, item)

    # Preenche as demais colunas
    for col_idx, col_def in enumerate(MATERIAIS_COLUNAS):
        if col_idx == 0:
            continue  # A coluna 0 já foi preenchida com o nome da linha
        for row_idx in range(num_rows):
            if col_def.get('combobox'):
                combo = QComboBox()
                opcoes = col_def.get('opcoes', [])
                if callable(opcoes):
                    opcoes = opcoes()
                combo.addItems(opcoes)
                tabela.setCellWidget(row_idx, col_idx, combo)
            elif col_def.get('botao'):
                botao = QPushButton(col_def.get('texto_botao', 'Escolher'))
                def criar_callback(r, func=col_def['funcao_botao']):
                    return lambda: func(ui, r, "Tab_Material_11")
                botao.clicked.connect(criar_callback(row_idx))
                tabela.setCellWidget(row_idx, col_idx, botao)
            else:
                # Coluna normal (texto editável ou não)
                item = QTableWidgetItem("");
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

    # Conecta o callback para recalcular o pliq após edições
    tabela.itemChanged.connect(on_item_changed_items_materiais)

    # Ajusta tamanhos e larguras
    tabela.resizeColumnsToContents()
    tabela.resizeRowsToContents()
    # Define larguras personalizadas
    definir_larguras_tab_material_item(ui)
    # Configura a tabela de Dados do Item na interface na coluna familia preenche com 'PLACAS' & coluna tipo sem filtro
    from utils import apply_row_selection_style
    familia_idx = next((i for i, c in enumerate(MATERIAIS_COLUNAS) if c['nome'] == 'familia'), None)
    tipo_idx = next((i for i, c in enumerate(MATERIAIS_COLUNAS) if c['nome'] == 'tipo'), None)
    for r in range(tabela.rowCount()):
        if familia_idx is not None:
            combo = tabela.cellWidget(r, familia_idx)
            if isinstance(combo, QComboBox):
                idx = combo.findText('PLACAS')
                if idx >= 0:
                    combo.setCurrentIndex(idx)
        if tipo_idx is not None:
            combo_t = tabela.cellWidget(r, tipo_idx)
            if isinstance(combo_t, QComboBox):
                combo_t.setCurrentIndex(-1)
    apply_row_selection_style(tabela)

        
# =============================================================================
# Função para limpar as colunas da linha selecionada na Tab_Material_11 com o botão "Limpar Linha Selecionada" 
# =============================================================================
def limpar_linha_tab_material(obj):
    """
    Limpa (esvazia) o conteúdo de uma linha selecionada na Tab_Material_11.
    Isso inclui remover texto de colunas como ref_le, ptab, pliq, descontos etc.
    """
    if hasattr(obj, "ui"):
        ui = obj.ui
        parent_widget = obj
    else:
        ui = obj
        parent_widget = obj

    tabela = ui.Tab_Material_11
    tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
    selection = tabela.selectionModel().selectedRows()
    if not selection:
        QMessageBox.warning(parent_widget, "Aviso", "Nenhuma linha selecionada!")
        return

    row_index = selection[0].row()

    # Colunas que devem ser limpas (ref_le, descrição_no_orcamento, ptab, pliq, descontos, etc.)
    COLUNAS_LIMPAR_MATERIAIS = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, 19]

    tabela.blockSignals(True)
    # Iterar sobre cada coluna e limpar o conteúdo
    for col in COLUNAS_LIMPAR_MATERIAIS:
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


def criar_tabela_dados_items_materiais():
    """
    Cria a tabela 'dados_items_materiais' no banco de dados,
    se ela ainda não existir, para armazenar registros de
    materiais referentes a cada item do orçamento.
    """
    #print("Verificando/Criando tabela 'dados_items_materiais'...")
    try:
        with obter_cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'dados_items_materiais'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE dados_items_materiais (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        num_orc VARCHAR(50) NOT NULL,
                        ver_orc VARCHAR(10) NOT NULL,
                        id_mat VARCHAR(50) NOT NULL, -- Chave do item do orçamento
                        linha INT NOT NULL,         -- Índice da linha na UI (0 a N-1)
                        material TEXT NULL,         -- Nome da linha (ex: Mat_Costas)
                        descricao TEXT NULL,
                        ref_le VARCHAR(100) NULL,
                        descricao_no_orcamento TEXT NULL,
                        ptab DOUBLE NULL DEFAULT 0.0,
                        pliq DOUBLE NULL DEFAULT 0.0,
                        desc1_plus DOUBLE NULL DEFAULT 0.0,  -- Fração 0-1
                        desc2_minus DOUBLE NULL DEFAULT 0.0, -- Fração 0-1
                        und VARCHAR(20) NULL,        -- Aumentado tamanho
                        desp DOUBLE NULL DEFAULT 0.0,        -- Fração
                        corres_orla_0_4 VARCHAR(50) NULL,
                        corres_orla_1_0 VARCHAR(50) NULL,
                        tipo VARCHAR(100) NULL,
                        familia VARCHAR(100) NULL,
                        comp_mp DOUBLE NULL DEFAULT 0.0,
                        larg_mp DOUBLE NULL DEFAULT 0.0,
                        esp_mp DOUBLE NULL DEFAULT 0.0,
                        UNIQUE KEY idx_item_mat_unico (num_orc, ver_orc, id_mat, linha),
                        INDEX idx_item_mat_lookup (num_orc, ver_orc, id_mat)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                #print("Tabela 'dados_items_materiais' criada.")
            else:
                 print("Tabela 'dados_items_materiais' já existe.")      # Pretendo eliminar esta linha mas dá erro
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao criar/verificar 'dados_items_materiais': {err}")
    except Exception as e:
        print(f"Erro inesperado ao criar/verificar 'dados_items_materiais': {e}")

########################################
# FUNÇÃO: Guardar os dados dos itens do orçamento
########################################
def guardar_dados_item_orcamento_tab_material(parent):
    """
    Percorre a Tab_Material_11 e salva os dados no banco de dados
    (tabela 'dados_items_materiais'). Caso já existam registros
    para (num_orc, ver_orc, id_mat), pergunta se quer sobrescrever.
    """
    MOSTRAR_AVISOS = False  # Muda para True quando quiser ver as mensagens
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = formatar_versao(ui.lineEdit_versao_orcamento.text())
    id_mat = ui.lineEdit_item_orcamento.text().strip()

    if not num_orc or not ver_orc or not id_mat:
        QMessageBox.warning(parent, "Aviso", "Preencha os campos 'Num Orçamento', 'Versão' e 'Item'!")
        return

    tabela = ui.Tab_Material_11
    num_rows = tabela.rowCount()
    if num_rows == 0: return

    col_names_db = [ # Ordem para INSERT
        'num_orc', 'ver_orc', 'id_mat','linha', 'material', 'descricao',
        'ref_le','descricao_no_orcamento', 'ptab', 'pliq', 'desc1_plus',
        'desc2_minus', 'und', 'desp', 'corres_orla_0_4', 'corres_orla_1_0',
        'tipo', 'familia', 'comp_mp', 'larg_mp', 'esp_mp'
    ]

    ui_to_db_mapping = {# Campo BD -> Coluna UI
        'num_orc': 3,
        'ver_orc': 4,
        'id_mat': 2,
        'material': 0,
        'descricao': 1,
        'ref_le': 5,
        'descricao_no_orcamento': 6,
        'ptab': 7,
        'pliq': 8,
        'desc1_plus': 9,
        'desc2_minus': 10,
        'und': 11,
        'desp': 12,
        'corres_orla_0_4': 13,
        'corres_orla_1_0': 14,
        'tipo': 15,
        'familia': 16,
        'comp_mp': 17,
        'larg_mp': 18,
        'esp_mp': 19
    }
    # Conjuntos para conversão de valores formatados

    campos_moeda = {"ptab", "pliq"}
    campos_percentual = {"desc1_plus", "desc2_minus", "desp"}

    dados_para_salvar = []
    for r in range(num_rows):
        dados_linha = {'num_orc': num_orc, 'ver_orc': ver_orc, 'id_mat': id_mat, 'linha': r}
        for key_db in col_names_db:
            if key_db in dados_linha: continue
            col_ui = ui_to_db_mapping.get(key_db)
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

    try:
        count = 0
        with obter_cursor() as cursor_check:
            cursor_check.execute(
                "SELECT COUNT(*) FROM dados_items_materiais WHERE num_orc=%s AND ver_orc=%s AND id_mat=%s",
                (num_orc, ver_orc, id_mat)
            )
            count = cursor_check.fetchone()[0]

        if count > 0:
            resposta = QMessageBox.question(parent, "Dados Existentes",
                                            "Já existem dados para este item (Materiais). Deseja substituí-los?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resposta == QMessageBox.No: return
            else:
                with obter_cursor() as cursor_del:
                    cursor_del.execute(
                        "DELETE FROM dados_items_materiais WHERE num_orc=%s AND ver_orc=%s AND id_mat=%s",
                        (num_orc, ver_orc, id_mat)
                    )
                    print(f"{cursor_del.rowcount} registos antigos de materiais eliminados.")

        linhas_inseridas = 0
        with obter_cursor() as cursor_insert:
            placeholders = ", ".join(["%s"] * len(col_names_db))
            query_insert = f"INSERT INTO dados_items_materiais ({', '.join(col_names_db)}) VALUES ({placeholders})"
            for row_data in dados_para_salvar:
                try:
                    cursor_insert.execute(query_insert, row_data)
                    linhas_inseridas += 1
                except mysql.connector.Error as insert_err:
                    print(f"Erro MySQL ao inserir linha {row_data[3]} para item {id_mat}: {insert_err}")
                    QMessageBox.warning(parent, "Erro ao Inserir", f"Falha ao guardar linha {row_data[3]+1}: {insert_err}")

        if MOSTRAR_AVISOS: QMessageBox.information(parent, "Sucesso", f"{linhas_inseridas} linha(s) de Materiais guardada(s).")
        print(f"{linhas_inseridas} linha(s) de Materiais guardada(s).")

    except mysql.connector.Error as err:
        QMessageBox.critical(parent, "Erro Base de Dados", f"Erro ao guardar dados: {err}")
        print(f"Erro MySQL (guardar materiais): {err}")
    except Exception as e:
        QMessageBox.critical(parent, "Erro Inesperado", f"Erro ao guardar dados: {e}")
        import traceback; traceback.print_exc()


# =============================================================================
# Função carregar_dados_items(parent) 
# =============================================================================
def carregar_dados_items(parent):
    """
    Carrega dados na Tab_Material_11, pesquisando no banco de dados se
    já existem informações registradas em dados_items_materiais para
    (num_orc, ver_orc, id_mat). Caso não encontre, tenta buscar em
    dados_gerais_materiais. Se ainda assim não houver, deixa as colunas
    fixas e limpa o restante.
    """
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = ui.lineEdit_versao_orcamento.text().strip()
    id_mat = ui.lineEdit_item_orcamento.text().strip()
    MOSTRAR_AVISOS = False  # Altere para True quando quiser que os avisos voltem a aparecer
                            # Quando o software estiver ok devo voltar ativar para TRUE o MOSTRAR_AVISOS nos 4 modulos dados_items_materiais.py | dados_items_ferragens.py | dados_items_acabamentos.py | dados_items_sistemas_correr.py
                            # "Dados Items", "Dados dos itens MATERIAIS carregados com sucesso.")

    tabela = ui.Tab_Material_11
    tabela.blockSignals(True)

    # Limpa colunas editáveis/preenchíveis e preenche chaves fixas
    clear_cols = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,17,18,19] # Coluna 0 (material) é fixa
    key_cols = {2: id_mat, 3: num_orc, 4: ver_orc} # Coluna UI -> Valor Chave
    for r in range(tabela.rowCount()):
        for c in clear_cols:
            widget = tabela.cellWidget(r, c)
            if widget and isinstance(widget, QComboBox): widget.setCurrentIndex(-1)
            elif widget and hasattr(widget, 'clear'): widget.clear()
            else:
                item = tabela.item(r, c);
                if item: item.setText("")
                else: tabela.setItem(r, c, QTableWidgetItem(""))
        for c_key, val_key in key_cols.items():
             item = tabela.item(r, c_key)
             if not item: item = QTableWidgetItem(); tabela.setItem(r, c_key, item)
             item.setText(str(val_key) if val_key is not None else "")
             item.setFlags(item.flags() & ~Qt.ItemIsEditable) # Tornar não editável

    tipo_idx = next((i for i, c in enumerate(MATERIAIS_COLUNAS) if c['nome'] == 'tipo'), None)
    familia_idx = next((i for i, c in enumerate(MATERIAIS_COLUNAS) if c['nome'] == 'familia'), None)
    for r in range(tabela.rowCount()):
        if familia_idx is not None:
            combo = tabela.cellWidget(r, familia_idx)
            if isinstance(combo, QComboBox):
                idx = combo.findText('PLACAS')
                if idx >= 0:
                    combo.setCurrentIndex(idx)
        if tipo_idx is not None:
            combo_t = tabela.cellWidget(r, tipo_idx)
            if isinstance(combo_t, QComboBox):
                combo_t.setCurrentIndex(-1)

    # Mapeamentos para os índices das colunas das tabelas do banco de dados:
    # Para a tabela dados_items_materiais (índices conforme definição)
    db_mapping_items = {
        'linha': 4,  # <--- ADICIONAR ESTA LINHA. Mapeia o campo 'linha' para o índice 4
        'material': 5,'descricao': 6, 'id_mat': 3, 'num_orc': 1, 'ver_orc': 2,
        'ref_le': 7, 'descricao_no_orcamento': 8, 'ptab': 9, 'pliq': 10,
        'desc1_plus': 11, 'desc2_minus': 12, 'und': 13, 'desp': 14,
        'corres_orla_0_4': 15, 'corres_orla_1_0': 16, 'tipo': 17,
        'familia': 18, 'comp_mp': 19, 'larg_mp': 20, 'esp_mp': 21
    }
    # Para a tabela dados_gerais_materiais (índices conforme informado)
    db_mapping_gerais = {
        'descricao': 4, 'id_mat': 5, 'num_orc': 6, 'ver_orc': 7,
        'ref_le': 8, 'descricao_no_orcamento': 9, 'ptab': 10, 'pliq': 11,
        'desc1_plus': 12, 'desc2_minus': 13, 'und': 14, 'desp': 15,
        'corres_orla_0_4': 16, 'corres_orla_1_0': 17, 'tipo': 18,
        'familia': 19, 'comp_mp': 20, 'larg_mp': 21, 'esp_mp': 22
    }
    # Mapeamento para a interface Tab_Material_11: chave = nome do campo, valor = coluna
    tab_mapping = {
        'descricao': 1, 'id_mat': 2, 'num_orc': 3, 'ver_orc': 4,
        'ref_le': 5, 'descricao_no_orcamento': 6, 'ptab': 7, 'pliq': 8,
        'desc1_plus': 9, 'desc2_minus': 10, 'und': 11, 'desp': 12,
        'corres_orla_0_4': 13, 'corres_orla_1_0': 14, 'tipo': 15,
        'familia': 16, 'comp_mp': 17, 'larg_mp': 18, 'esp_mp': 19
    }

    registros_items = []
    registros_gerais = []
    try:
        # 1. Tenta carregar de dados_items_materiais
        with obter_cursor() as cursor_items:
            cursor_items.execute("""
                SELECT * FROM dados_items_materiais
                WHERE num_orc = %s AND ver_orc = %s AND id_mat = %s
                ORDER BY linha
            """, (num_orc, ver_orc, id_mat))
            registros_items = cursor_items.fetchall()

        if registros_items:
            #print(f"Carregados {len(registros_items)} registos de dados_items_materiais.")
            # Preenche com dados dos itens
            for registro in registros_items:
                linha_idx = registro[db_mapping_items['linha']]
                if 0 <= linha_idx < tabela.rowCount():
                    for campo, col_tab_ui in tab_mapping.items():
                        if campo in ['num_orc', 'ver_orc', 'id_mat']: continue
                        db_idx = db_mapping_items.get(campo);
                        if db_idx is None: continue
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
            if MOSTRAR_AVISOS: QMessageBox.information(parent, "Dados Carregados", "Dados do item (Materiais) carregados.")

        else:
            # 2. Se não há dados de item, tenta carregar de dados_gerais_materiais
            print("Nenhum dado de item encontrado, tentando carregar dados gerais...")
            try:
                with obter_cursor() as cursor_geral:
                    # Ajustar query se a tabela geral tiver estrutura diferente ou precisar de outro filtro
                    cursor_geral.execute("""
                        SELECT * FROM dados_gerais_materiais
                        WHERE num_orc = %s AND ver_orc = %s -- Filtro exemplo, ajustar!
                        ORDER BY id -- Ou pela coluna 'material' se existir?
                    """, (num_orc, ver_orc)) # Usar o filtro correto!
                    registros_gerais = cursor_geral.fetchall()
            except mysql.connector.Error as err_geral:
                 if err_geral.errno == 1146: print("Tabela 'dados_gerais_materiais' não encontrada.")
                 else: print(f"Erro MySQL ao buscar dados gerais de materiais: {err_geral}"); QMessageBox.warning(parent, "Erro BD", f"Erro ao buscar dados gerais: {err_geral}")

            if registros_gerais:
                print(f"Carregando {len(registros_gerais)} registos de dados_gerais_materiais.")
                for row_idx, registro in enumerate(registros_gerais):
                     if row_idx >= tabela.rowCount(): break
                     # Precisa mapear o nome do material da tabela geral para a linha correta na UI
                     material_geral = registro[db_mapping_gerais.get('material', 0)] # Ajustar índice se necessário
                     linha_ui_destino = -1
                     for r_ui in range(tabela.rowCount()):
                          if tabela.item(r_ui, 0).text() == material_geral:
                               linha_ui_destino = r_ui; break
                     if linha_ui_destino == -1: continue # Pula se não encontrar a linha correspondente

                     for campo, col_tab_ui in tab_mapping.items():
                         if campo in ['num_orc', 'ver_orc', 'id_mat']: continue
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
                if MOSTRAR_AVISOS: QMessageBox.information(parent, "Dados Carregados", "Dados gerais de materiais importados.")
            else:
                 if MOSTRAR_AVISOS: QMessageBox.information(parent, "Dados Vazios", "Nenhum dado específico ou geral encontrado para este item (Materiais).")
                 print("Nenhum dado específico ou geral encontrado para Materiais.")

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao carregar dados de materiais: {err}")
        QMessageBox.critical(parent, "Erro Base de Dados", f"Erro ao carregar dados: {err}")
    except Exception as e:
        print(f"Erro inesperado ao carregar dados de materiais: {e}")
        QMessageBox.critical(parent, "Erro Inesperado", f"Erro ao carregar dados: {e}")
        import traceback; traceback.print_exc()
    finally:
        tabela.blockSignals(False) # Garante desbloqueio

def configurar_dados_items_orcamento_materiais(parent):
    """
    Cria (se necessário) a tabela dados_items_materiais no BD e
    carrega dados para (num_orc, ver_orc, id_mat). Por fim,
    alterna para a aba "orcamento_items" na interface.
    """
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = ui.lineEdit_versao_orcamento.text().strip()
    id_mat = ui.lineEdit_item_orcamento.text().strip()

    if ui.Tab_Material_11.columnCount() == 0:  # tabela ainda não configurada
        configurar_tabela_material(parent)     # cria colunas, linhas, widgets

    if not num_orc or not ver_orc or not id_mat:
        QMessageBox.warning(parent, "Aviso", "Preencha os campos 'Num Orçamento', 'Versão' e 'Item'!")
        return

    criar_tabela_dados_items_materiais()
    carregar_dados_items(parent)

    # Alterna para a aba "orcamento_items"
    for i in range(ui.tabWidget_orcamento.count()):
        widget = ui.tabWidget_orcamento.widget(i)
        if widget.objectName() == "orcamento_items":
            ui.tabWidget_orcamento.setCurrentIndex(i)
            break

########################################
# Função para inicializar as configurações e conectar o botão de guardar
########################################
def inicializar_dados_items_material(parent):
    """
    Função principal para inicializar a Tabela de Materiais (Tab_Material_11).
    - Cria as colunas/linhas (MATERIAIS_COLUNAS, MATERIAIS_LINHAS).
    - Conecta botões de "Guardar" e "Limpar Linha".
    - Prepara a tabela para importação, edição e cálculo (pliq).
    """
    ui = parent.ui
    configurar_tabela_material(parent)
    # Conecta o botão de guardar (definido na interface como 'guardar_dados_item_orcamento_tab_material')
    ui.guardar_dados_item_orcamento_tab_material.clicked.connect(lambda: guardar_dados_item_orcamento_tab_material(parent))
    # Conectar o botão 'limpar_linha_tab_materiais' à função:
    ui.limpar_linha_tab_material.clicked.connect(lambda: limpar_linha_tab_material(parent))
    # Conecta o botão "Importar Dados Item Tabela Material"
    ui.importar_dados_item_tab_material.clicked.connect(lambda: importar_dados_item_orcamento_tab_material(parent))
    adicionar_menu_limpar(ui.Tab_Material_11, lambda: limpar_linha_tab_material(parent))
