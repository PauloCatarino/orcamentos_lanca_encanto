"""
Módulo: dados_items_sistemas_correr.py
Descrição:
  Este módulo configura a tabela "Tab_Sistemas_Correr_11", destinada ao orçamento de sistemas de correr
  (por exemplo, calhas, puxadores verticais, acessórios e componentes para portas de correr).
  Ele segue a mesma filosofia dos módulos de materiais e ferragens, mas com colunas e linhas
  específicas para sistemas de correr.

  Principais funcionalidades:
    - Definição das colunas (SISTEMAS_CORRER_COLUNAS) e linhas (SISTEMAS_CORRER_LINHAS).
    - Configuração da tabela e dos widgets (ComboBox, botões, campos editáveis).
    - Cálculo automático do campo 'pliq' com base em ptab e descontos (desc1_plus, desc2_minus).
    - Funções para carregar, importar e guardar os dados de sistemas de correr no banco de dados.
    - Função para limpar o conteúdo de uma linha selecionada (corrigir lançamentos errados).
    - Função de seleção (“Escolher”) que abre um diálogo de materiais, permitindo mapear os dados
      selecionados para a linha correspondente.

Autor: Paulo Catarino
Data: 20/03/2025
"""

from PyQt5.QtWidgets import (QTableWidgetItem, QComboBox, QPushButton, QMessageBox, QHeaderView, QAbstractItemView, QDialog)
from PyQt5.QtCore import Qt
import mysql.connector # Importar para capturar erros específicos

# Funções utilitárias (formatação/conversão de valores e filtros)
from utils import (formatar_valor_moeda, formatar_valor_percentual, converter_texto_para_valor, get_distinct_values_with_filter, adicionar_menu_limpar)

# Diálogo de seleção de material/ferragem/ssitemascorrer/acabamentos
from dados_gerais_materiais_escolher import MaterialSelectionDialog

# Conexão com o banco de dados
from db_connection import obter_cursor

# Formatar versão do orçamento
from configurar_guardar_dados_gerais_orcamento import formatar_versao

###############################################################
# Definições específicas para Sistemas de Correr
###############################################################
# Esta lista define a estrutura das colunas que aparecerão na
# tabela dedicada às sistemas correr, com informações como tipo de dado,
# se a coluna é editável, se possui ComboBox, botão, etc.
###############################################################
SISTEMAS_CORRER_COLUNAS = [
    {'nome': 'sistemas_correr', 'tipo': 'TEXT', 'visivel': True, 'editavel': False},
    {'nome': 'descricao',       'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'id_sc',           'tipo': 'INTEGER', 'visivel': True, 'editavel': False},
    {'nome': 'num_orc',         'tipo': 'INTEGER', 'visivel': True, 'editavel': False},
    {'nome': 'ver_orc',         'tipo': 'INTEGER', 'visivel': True, 'editavel': False},
    {'nome': 'ref_le',          'tipo': 'TEXT', 'visivel': True, 'editavel': False},
    {'nome': 'descricao_no_orcamento', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},

    {'nome': 'ptab',            'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'pliq',            'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'desc1_plus',      'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'desc2_minus',     'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'und',             'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'desp',            'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'corres_orla_0_4', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'corres_orla_1_0', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},

    {
        'nome': 'tipo',
        'tipo': 'TEXT',
        'visivel': True,
        'editavel': True,
        'combobox': True,
        'opcoes': lambda: get_distinct_values_with_filter("TIPO", "FAMILIA", "FERRAGENS")
    },
    {
        'nome': 'familia',
        'tipo': 'TEXT',
        'visivel': True,
        'editavel': True,
        'combobox': True,
        'opcoes': lambda: ["FERRAGENS"]
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
        'funcao_botao': None  # Será atribuído depois
    }
]

# Definição dos nomes das linhas para a tabela de Sistemas Correr
# Cada linha representa um tipo de sistema correr (calha puxador, rodizios, etc.)
# que poderá ser orçado e exibido na Tab_Sistemas_Correr_11.
###############################################################
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
# --- Funções de UI e Lógica (sem acesso direto à BD - mantidas) ---
def escolher_sistemas_correr_item(ui, linha_tab):
    """
    Abre um diálogo (MaterialSelectionDialog) para o usuário escolher um sistema de correr,
    retornando os dados selecionados e preenchendo-os na linha correspondente (linha_tab)
    da Tab_Sistemas_Correr_11.

    Retorna True se houve seleção, False caso contrário.
    """
    tbl_item = ui.Tab_Sistemas_Correr_11
    tbl_item.blockSignals(True)

    # Índices das colunas onde armazenamos "tipo" e "familia"
    # (necessários para pré-filtrar o diálogo, se desejado)
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

        # Mapeamento: definimos como cada coluna do diálogo será transportada para Tab_Sistemas_Correr_11
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

        # Limpa as células que serão sobreescritas
        for campo, (src_idx, tgt_idx) in col_map.items():
            tbl_item.setItem(linha_tab, tgt_idx, QTableWidgetItem(""))

        def set_item(row, col_idx, texto):
            item = tbl_item.item(row, col_idx);
            if not item:
                item = QTableWidgetItem()
                tbl_item.setItem(row, col_idx, item)
            item.setText(texto)

        ptab_valor = 0.0
        dplus = 0.0
        dminus = 0.0

        # Copia os valores do diálogo para a tabela
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

        # Calcula pliq com base no ptab e descontos
        novo_pliq = round((ptab_valor * (1 + dminus)) * (1 - dplus), 2)
        set_item(linha_tab, 8, formatar_valor_moeda(novo_pliq))

        tbl_item.blockSignals(False)
        return True

    tbl_item.blockSignals(False)
    return False

########################################
# Callback de edição e cálculo dos valores (ajustado)
########################################
def on_item_changed_items_sistemas_correr(item):
    """
    Callback acionado sempre que uma célula da Tab_Sistemas_Correr_11 é editada.
    Se a coluna for ptab (7), desc1_plus (9) ou desc2_minus (10), recalcula pliq
    conforme a fórmula: pliq = ptab * (1 + desc1_plus) * (1 - desc2_minus).
    """
    if not item:
        return
    tabela = item.tableWidget()
    if tabela.property("importando"):
        # Se estiver no modo de importação, ignoramos para não gerar loops.
        return

    row = item.row()
    col = item.column()

    # Colunas relevantes:
    # ptab: 7, pliq: 8, desc1_plus: 9, desc2_minus: 10
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
        # Se o usuário editar diretamente o pliq
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
    Chamado ao clicar no botão "Escolher" (coluna MP) na Tab_Sistemas_Correr_11.
    Abre o diálogo de seleção de material, e se confirmada a escolha, exibe mensagem.
    """
    if escolher_sistemas_correr_item(ui, row):
        QMessageBox.information(None, "Sistemas de Correr", f"Sistema de correr selecionado para a linha {row+1}.")

# Atribui a função do botão "Escolher" à respectiva coluna MP
for col in SISTEMAS_CORRER_COLUNAS:
    if col['nome'] == 'MP':
        col['funcao_botao'] = on_mp_button_clicked

########################################
# Função para definir larguras fixas para as colunas de Tab_Sistemas_Correr_11
########################################
def definir_larguras_tab_sistemas_correr(ui):
    """
    Ajusta larguras fixas das colunas da tabela Tab_Sistemas_Correr_11
    para melhorar a aparência.
    """
    tabela = ui.Tab_Sistemas_Correr_11
    header = tabela.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.Fixed)
    header.setStretchLastSection(False)
    # Larguras definidas para cada coluna (ajuste conforme necessidade real)

    larguras = [200, 200, 50, 110, 50, 100, 400, 60, 60, 60, 60, 50, 50, 180, 110, 120, 120, 90, 90, 90, 100]
    num_cols = tabela.columnCount();
    if len(larguras) < num_cols:
        larguras += [100] * (num_cols - len(larguras))
    for idx in range(num_cols):
        tabela.setColumnWidth(idx, larguras[idx])

def importar_dados_item_tab_sistemas_correr_3(parent):
    """
    Reaproveita a função importar_dados_gerais_com_opcao para importar dados
    para Tab_Sistemas_Correr_11. Redireciona temporariamente ui.Tab_Sistemas_Correr
    para ui.Tab_Sistemas_Correr_11 e restaura em seguida.
    """
    ui = parent.ui

    # Mapeamento de colunas para a Tab_Sistemas_Correr_11 (colunas começam em 0, mas 0 é nome da linha)
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

    # Redireciona tabela "sistemas_correr" para Tab_Sistemas_Correr_11
    original_tab = ui.Tab_Sistemas_Correr
    ui.Tab_Sistemas_Correr = ui.Tab_Sistemas_Correr_11

    try:
            # Importa usando a função genérica, passando "sistemas_correr" como tipo e nosso mapeamento
        importar_dados_gerais_com_opcao(parent, "sistemas_correr", mapeamento)
    finally:
        # Restaura para não atrapalhar outras partes do código
        ui.Tab_Sistemas_Correr = original_tab

########################################
# Função principal para configurar a Tab_Sistemas_Correr_11 (Dados do Item)
########################################

def configurar_tabela_sistemas_correr(parent):
    """
    Cria e configura a tabela Tab_Sistemas_Correr_11 (linhas e colunas),
    define cabeçalhos, atribui widgets (ComboBox, botões) e conecta o
    callback de edição.
    """
    ui = parent.ui
    tabela = ui.Tab_Sistemas_Correr_11
    tabela.clear()

    num_cols = len(SISTEMAS_CORRER_COLUNAS)
    num_rows = len(SISTEMAS_CORRER_LINHAS)
    tabela.setColumnCount(num_cols)
    tabela.setRowCount(num_rows)

    # Define cabeçalhos
    headers = [col['nome'] for col in SISTEMAS_CORRER_COLUNAS]
    tabela.setHorizontalHeaderLabels(headers)
    tabela.verticalHeader().setVisible(False)

    # Preenche a primeira coluna com o nome de cada linha
    for row_idx, nome_linha in enumerate(SISTEMAS_CORRER_LINHAS):
        item = QTableWidgetItem(nome_linha)
        tabela.setItem(row_idx, 0, item)

    # Preenche as colunas seguintes
    for col_idx, col_def in enumerate(SISTEMAS_CORRER_COLUNAS):
        if col_idx == 0:
            continue
        for row_idx in range(num_rows):
            # Verifica se a coluna deve ser um combobox
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
                    return lambda: func(ui, r, "Tab_Sistemas_Correr_11")

                botao.clicked.connect(criar_callback(row_idx))
                tabela.setCellWidget(row_idx, col_idx, botao)
            else:
                # Campo de texto (editável ou não)
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

    # Conecta o callback de edição
    tabela.itemChanged.connect(on_item_changed_items_sistemas_correr)
    # Ajusta tamanho das colunas e linhas
    tabela.resizeColumnsToContents()
    tabela.resizeRowsToContents()
    # Define larguras personalizadas
    definir_larguras_tab_sistemas_correr(ui)
    # Configura a tabela de Dados do Item na interface na coluna familia preenche com 'FERRAGENS' & coluna tipo preenche com 'ROUPEIROS CORRER'
    from utils import apply_row_selection_style
    tabela = ui.Tab_Sistemas_Correr_11
    tipo_idx = next((i for i, c in enumerate(SISTEMAS_CORRER_COLUNAS) if c['nome'] == 'tipo'), None)
    familia_idx = next((i for i, c in enumerate(SISTEMAS_CORRER_COLUNAS) if c['nome'] == 'familia'), None)
    for r in range(tabela.rowCount()):
        if tipo_idx is not None:
            combo = tabela.cellWidget(r, tipo_idx)
            if isinstance(combo, QComboBox):
                idx = combo.findText('ROUPEIROS CORRER')
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                else:
                    combo.setCurrentIndex(-1)
        if familia_idx is not None:
            combo = tabela.cellWidget(r, familia_idx)
            if isinstance(combo, QComboBox):
                idx = combo.findText('FERRAGENS')
                if idx >= 0:
                    combo.setCurrentIndex(idx)
    apply_row_selection_style(tabela)

def criar_tabela_dados_items_sistemas_correr():
    """
    Cria a tabela 'dados_items_sistemas_correr' no banco de dados,
    se ainda não existir, para armazenar os registros relativos a
    sistemas de correr selecionados para cada item do orçamento.
    """
    #print("Verificando/Criando tabela 'dados_items_sistemas_correr'...")
    try:
        with obter_cursor() as cursor:
            # Verifica se a tabela existe
            cursor.execute("SHOW TABLES LIKE 'dados_items_sistemas_correr'")
            tabela_existe = cursor.fetchone()

            if not tabela_existe:
                # Query CREATE TABLE (com tipos MySQL e NULL/DEFAULT apropriados)
                cursor.execute("""
                    CREATE TABLE dados_items_sistemas_correr (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        num_orc VARCHAR(50) NOT NULL,
                        ver_orc VARCHAR(10) NOT NULL,
                        id_sc VARCHAR(50) NOT NULL,  -- Chave do item do orçamento
                        linha INT NOT NULL,          -- Índice da linha na UI (0 a N-1)
                        material TEXT NULL,          -- Nome da linha (ex: SC_Puxador_Vertical_SPP)
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
                        UNIQUE KEY idx_item_unico (num_orc, ver_orc, id_sc, linha), -- Garante unicidade
                        INDEX idx_item_lookup (num_orc, ver_orc, id_sc) -- Índice para buscas
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                #print("Tabela 'dados_items_sistemas_correr' criada.")
            else:
                print("Tabela 'dados_items_sistemas_correr' já existe.")  #Pretendo eliminar esta linhas mas dá erro
        # Commit automático ao sair do 'with'
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao criar/verificar 'dados_items_sistemas_correr': {err}")
        # É importante notificar o utilizador aqui, talvez com QMessageBox
    except Exception as e:
        print(f"Erro inesperado ao criar/verificar 'dados_items_sistemas_correr': {e}")

########################################
# FUNÇÃO: Guardar os dados dos itens do orçamento
########################################
def guardar_dados_item_orcamento_tab_sistemas_correr_3(parent):
    """
    Percorre a Tab_Sistemas_Correr_11 e salva os dados no banco,
    na tabela dados_items_sistemas_correr. Se já existir registro
    para (num_orc, ver_orc, id_sc), pergunta ao usuário se quer sobrescrever.
    """
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = formatar_versao(ui.lineEdit_versao_orcamento.text())
    id_sc = ui.lineEdit_item_orcamento.text().strip()
    MOSTRAR_AVISOS = False  # Muda para True quando quiser ver as mensagens

    if not num_orc or not ver_orc or not id_sc:
        QMessageBox.warning(parent, "Aviso", "Preencha os campos 'Num Orçamento', 'Versão' e 'Item'!")
        return

    tabela = ui.Tab_Sistemas_Correr_11
    num_rows = tabela.rowCount()
    if num_rows == 0: return # Nada para guardar

    # Lista de colunas no BD (ordem do INSERT)
    col_names_db = [
        'num_orc', 'ver_orc', 'id_sc', 'linha',
        'material', 'descricao', 'ref_le', 'descricao_no_orcamento',
        'ptab', 'pliq', 'desc1_plus', 'desc2_minus', 'und', 'desp',
        'corres_orla_0_4', 'corres_orla_1_0', 'tipo', 'familia',
        'comp_mp', 'larg_mp', 'esp_mp'
    ]

    # Mapeamento entre o nome do campo (usado no BD) e a coluna na tabela
    ui_to_db_mapping = {
        'num_orc': 3,
        'ver_orc': 4,
        'id_sc':   2,
        'material': 0,
        'descricao':       1,
        'ref_le':          5,
        'descricao_no_orcamento': 6,
        'ptab':            7,
        'pliq':            8,
        'desc1_plus':      9,
        'desc2_minus':     10,
        'und':             11,
        'desp':            12,
        'corres_orla_0_4': 13,
        'corres_orla_1_0': 14,
        'tipo':            15,
        'familia':         16,
        'comp_mp':         17,
        'larg_mp':         18,
        'esp_mp':          19
    }
    # Conjuntos para conversão de valores formatados

    campos_moeda = {"ptab", "pliq"}
    campos_percentual = {"desc1_plus", "desc2_minus", "desp"}

    # Coleta dos dados de cada linha da Tab_Sistemas_Correr_11
    dados_para_salvar = []
    for r in range(num_rows):
        dados_linha = {'num_orc': num_orc, 'ver_orc': ver_orc, 'id_sc': id_sc, 'linha': r}
        for key_db in col_names_db:
             if key_db in dados_linha: continue # Já definidos
             col_ui = ui_to_db_mapping.get(key_db)
             if col_ui is None: continue # Segurança: se a coluna não estiver mapeada

             cell = tabela.item(r, col_ui)
             valor_str = cell.text().strip() if cell else ""
             valor_final = None # Usar None para representar NULL na BD

             if key_db in campos_moeda:
                 try: valor_final = converter_texto_para_valor(valor_str, "moeda") if valor_str else None
                 except: valor_final = None # Ou 0.0? Preferível None para NULL
             elif key_db in campos_percentual:
                 try: valor_final = converter_texto_para_valor(valor_str, "percentual") if valor_str else None
                 except: valor_final = None # Ou 0.0?
             else: # Texto
                 valor_final = valor_str if valor_str else None
             dados_linha[key_db] = valor_final
        # Adiciona a tupla na ordem correta das colunas da BD
        dados_para_salvar.append(tuple(dados_linha.get(cn, None) for cn in col_names_db))

    # Interação com a BD
    try:
        linhas_afetadas_del = 0
        # Verifica se já existem dados e pergunta ao utilizador
        with obter_cursor() as cursor_check:
            cursor_check.execute(
                "SELECT COUNT(*) FROM dados_items_sistemas_correr WHERE num_orc=%s AND ver_orc=%s AND id_sc=%s",
                (num_orc, ver_orc, id_sc)
            )
            count = cursor_check.fetchone()[0]

        if count > 0:
            resposta = QMessageBox.question(parent, "Dados Existentes",
                                            "Já existem dados para este item (Sistemas Correr). Deseja substituí-los?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resposta == QMessageBox.No: return # Cancela
            else:
                # Se sim, apaga os dados antigos
                with obter_cursor() as cursor_del:
                    cursor_del.execute(
                        "DELETE FROM dados_items_sistemas_correr WHERE num_orc=%s AND ver_orc=%s AND id_sc=%s",
                        (num_orc, ver_orc, id_sc)
                    )
                    linhas_afetadas_del = cursor_del.rowcount
                    print(f"{linhas_afetadas_del} registos antigos de sistemas de correr eliminados.")
                # Commit é automático

        # Insere os novos dados
        linhas_inseridas = 0
        with obter_cursor() as cursor_insert:
            placeholders = ", ".join(["%s"] * len(col_names_db))
            query_insert = f"INSERT INTO dados_items_sistemas_correr ({', '.join(col_names_db)}) VALUES ({placeholders})"
            # Usar executemany para eficiência, se possível, ou loop
            for row_data in dados_para_salvar:
                try:
                    cursor_insert.execute(query_insert, row_data)
                    linhas_inseridas += 1
                except mysql.connector.Error as insert_err:
                     print(f"Erro MySQL ao inserir linha {row_data[3]} para item {id_sc}: {insert_err}")
                     # Poderia parar aqui ou apenas reportar? Vamos reportar e continuar.
                     QMessageBox.warning(parent, "Erro ao Inserir", f"Falha ao guardar linha {row_data[3]+1}: {insert_err}")
        # Commit automático

        if MOSTRAR_AVISOS:
            QMessageBox.information(parent, "Sucesso", f"{linhas_inseridas} linha(s) de Sistemas de Correr guardada(s).")
        print(f"{linhas_inseridas} linha(s) de Sistemas de Correr guardada(s).")

    except mysql.connector.Error as err:
        QMessageBox.critical(parent, "Erro Base de Dados", f"Erro ao guardar dados: {err}")
        print(f"Erro MySQL (guardar sistemas correr): {err}")
    except Exception as e:
        QMessageBox.critical(parent, "Erro Inesperado", f"Erro ao guardar dados: {e}")
        import traceback; traceback.print_exc()



# =======================================================================
# Função carregar_dados_items(parent) 
# =======================================================================
def carregar_dados_items_sistemas_correr(parent):
    """
    Carrega na Tab_Sistemas_Correr_11 os dados de sistemas de correr
    para (num_orc, ver_orc, id_sc). Se não encontrar em dados_items_sistemas_correr,
    tenta buscar em dados_gerais_sistemas_correr (ou outro local similar).
    Se não encontrar, apenas mantém as colunas fixas.
    """
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = ui.lineEdit_versao_orcamento.text().strip() # Não formatar aqui, usar como está
    id_sc = ui.lineEdit_item_orcamento.text().strip()
    MOSTRAR_AVISOS = False  # ATENÇÃO: Muda para True quando quiser ver as mensagens

    tabela = ui.Tab_Sistemas_Correr_11
    tabela.blockSignals(True)

    # Limpa colunas editáveis/preenchíveis
    clear_cols = [1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
    for row in range(tabela.rowCount()):
        for col in clear_cols:
            widget = tabela.cellWidget(row, col)
            if widget and isinstance(widget, QComboBox): widget.setCurrentIndex(-1) # Limpa ComboBox
            elif widget and hasattr(widget, 'clear'): widget.clear() # Limpa QLineEdit, etc.
            else:
                item = tabela.item(row, col);
                if item: item.setText("")
                else: tabela.setItem(row, col, QTableWidgetItem(""))
         # Preenche colunas fixas ID Item, Num Orc, Ver Orc
        tabela.setItem(row, 2, QTableWidgetItem(id_sc))
        tabela.setItem(row, 3, QTableWidgetItem(num_orc))
        tabela.setItem(row, 4, QTableWidgetItem(ver_orc))

    tipo_idx = next((i for i, c in enumerate(SISTEMAS_CORRER_COLUNAS) if c['nome'] == 'tipo'), None)
    familia_idx = next((i for i, c in enumerate(SISTEMAS_CORRER_COLUNAS) if c['nome'] == 'familia'), None)
    for r in range(tabela.rowCount()):
        if tipo_idx is not None:
            combo_t = tabela.cellWidget(r, tipo_idx)
            if isinstance(combo_t, QComboBox):
                idx = combo_t.findText('ROUPEIROS CORRER')
                if idx >= 0:
                    combo_t.setCurrentIndex(idx)
                else:
                    combo_t.setCurrentIndex(-1)
        if familia_idx is not None:
            combo_f = tabela.cellWidget(r, familia_idx)
            if isinstance(combo_f, QComboBox):
                idx = combo_f.findText('FERRAGENS')
                if idx >= 0:
                    combo_f.setCurrentIndex(idx)

    # Mapeamentos para os índices das colunas das tabelas do banco de dados:
    # Para a tabela dados_items_sistemas_correr (índices conforme definição)
    db_mapping_items = {
        'linha': 4,  # <--- ADICIONAR ESTA LINHA. Mapeia o campo 'linha' para o índice 4
        'material':  5, # Nota: O nome 'material' é usado aqui para consistência, mas refere-se ao 'sistemas_correr' da UI
        'descricao':        6,
        'id_sc':           3,
        'num_orc':         1,
        'ver_orc':         2,
        'ref_le':          7,
        'descricao_no_orcamento': 8,
        'ptab':            9,
        'pliq':            10,
        'desc1_plus':      11,
        'desc2_minus':     12,
        'und':             13,
        'desp':            14,
        'corres_orla_0_4': 15,
        'corres_orla_1_0': 16,
        'tipo':            17,
        'familia':         18,
        'comp_mp':         19,
        'larg_mp':         20,
        'esp_mp':          21
    }

    # Caso você tenha uma tabela "dados_gerais_sistemas_correr" ou
    # deseje reutilizar "dados_gerais_sistemas_correr", ajuste os índices.
    # Aqui, como no exemplo, reutilizamos "dados_gerais_sistemas_correr".
    db_mapping_gerais = {
        'descricao':        4,
        'id_sc':           5,  
        'num_orc':         6,
        'ver_orc':         7,
        'ref_le':          8,
        'descricao_no_orcamento': 9,
        'ptab':            10,
        'pliq':            11,
        'desc1_plus':      12,
        'desc2_minus':     13,
        'und':             14,
        'desp':            15,
        'corres_orla_0_4': 16,
        'corres_orla_1_0': 17,
        'tipo':            18,
        'familia':         19,
        'comp_mp':         20,
        'larg_mp':         21,
        'esp_mp':          22
    }
    # Mapeamento para a interface Tab_Sistemas_Correr_11: chave = nome do campo, valor = coluna
    tab_mapping = {
        'descricao':       1,
        'id_sc':          2,
        'num_orc':        3,
        'ver_orc':        4,
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

    registros_items = []
    try:
        # 1. Tenta carregar de dados_items_sistemas_correr
        with obter_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM dados_items_sistemas_correr
                WHERE num_orc=%s AND ver_orc=%s AND id_sc=%s
                ORDER BY linha -- Importante ordenar pela linha da UI
            """, (num_orc, ver_orc, id_sc))
            registros_items = cursor.fetchall()

        if registros_items:
            #print(f"Carregados {len(registros_items)} registos de dados_items_sistemas_correr.")
            for registro in registros_items:
                linha_idx = registro[db_mapping_items['linha']] # Obtém o índice da linha salvo no BD
                if 0 <= linha_idx < tabela.rowCount(): # Verifica se o índice é válido
                    for campo, col_tab_ui in tab_mapping.items():
                        # Ignora as chaves que já foram preenchidas
                        if campo in ['num_orc', 'ver_orc', 'id_sc']: continue

                        db_idx = db_mapping_items.get(campo)
                        if db_idx is None: continue

                        valor_bd = registro[db_idx]
                        texto_formatado = ""
                        # Formatação (mantida)
                        if valor_bd is not None:
                            if campo in ["ptab", "pliq"]: texto_formatado = formatar_valor_moeda(valor_bd)
                            elif campo in ["desc1_plus", "desc2_minus", "desp"]: texto_formatado = formatar_valor_percentual(valor_bd)
                            else: texto_formatado = str(valor_bd)

                        # Preenche ComboBox ou QTableWidgetItem
                        widget = tabela.cellWidget(linha_idx, col_tab_ui)
                        if isinstance(widget, QComboBox):
                            idx_combo = widget.findText(texto_formatado, Qt.MatchFixedString)
                            widget.setCurrentIndex(idx_combo if idx_combo >= 0 else -1)
                        else:
                            item = tabela.item(linha_idx, col_tab_ui)
                            if not item: item = QTableWidgetItem(); tabela.setItem(linha_idx, col_tab_ui, item)
                            item.setText(texto_formatado)
                else:
                     print(f"[AVISO] Índice de linha inválido ({linha_idx}) encontrado no registo de item.")

            if MOSTRAR_AVISOS: QMessageBox.information(parent, "Dados Carregados", "Dados do item (Sistemas Correr) carregados.")

        else:
            # 2. Se não encontrou nos itens, tenta carregar de dados_gerais_sistemas_correr (se existir)
            print("Nenhum dado de item encontrado, tentando carregar dados gerais...")
            registros_gerais = []
            try:
                with obter_cursor() as cursor_geral:
                    # Ajustar query se a tabela dados_gerais_sistemas_correr tiver estrutura diferente
                    # ou se precisar filtrar por outros campos (ex: nome do material/linha)
                    cursor_geral.execute("""
                        SELECT * FROM dados_gerais_sistemas_correr
                        WHERE num_orc = %s AND ver_orc = %s -- Exemplo de filtro, pode não ser o ideal
                        ORDER BY id
                    """, (num_orc, ver_orc)) # Usar o filtro apropriado aqui!
                    registros_gerais = cursor_geral.fetchall()
            except mysql.connector.Error as err_geral:
                 # Se a tabela geral não existir, ignora silenciosamente ou informa
                 if err_geral.errno == 1146: # Código de erro para "Table doesn't exist"
                      print("Tabela 'dados_gerais_sistemas_correr' não encontrada, carregamento de dados gerais ignorado.")
                 else: # Outro erro de BD
                      print(f"Erro MySQL ao buscar dados gerais de sistemas de correr: {err_geral}")
                      QMessageBox.warning(parent, "Erro BD", f"Erro ao buscar dados gerais: {err_geral}")

            if registros_gerais:
                print(f"Carregando {len(registros_gerais)} registos de dados_gerais_sistemas_correr.")
                for row_idx, registro in enumerate(registros_gerais):
                     if row_idx >= tabela.rowCount(): break # Evita erro se houver mais dados gerais que linhas na UI
                     for campo, col_tab_ui in tab_mapping.items():
                         if campo in ['num_orc', 'ver_orc', 'id_sc']: continue # Não sobrescrever chaves do item
                         db_idx = db_mapping_gerais.get(campo)
                         if db_idx is None: continue
                         # Verifica se o índice está dentro dos limites do registro geral
                         if db_idx < len(registro):
                              valor_bd = registro[db_idx]
                              texto_formatado = ""
                              # Formatação (mantida)
                              if valor_bd is not None:
                                    if campo in ["ptab", "pliq"]: texto_formatado = formatar_valor_moeda(valor_bd)
                                    elif campo in ["desc1_plus", "desc2_minus", "desp"]: texto_formatado = formatar_valor_percentual(valor_bd)
                                    else: texto_formatado = str(valor_bd)

                              widget = tabela.cellWidget(row_idx, col_tab_ui)
                              if isinstance(widget, QComboBox):
                                    idx_combo = widget.findText(texto_formatado, Qt.MatchFixedString)
                                    widget.setCurrentIndex(idx_combo if idx_combo >= 0 else -1)
                              else:
                                    item = tabela.item(row_idx, col_tab_ui)
                                    if not item: item = QTableWidgetItem(); tabela.setItem(row_idx, col_tab_ui, item)
                                    item.setText(texto_formatado)
                         else:
                              print(f"[AVISO] Índice DB {db_idx} fora dos limites para registo geral na linha UI {row_idx}.")

                if MOSTRAR_AVISOS: QMessageBox.information(parent, "Dados Carregados", "Dados gerais de Sistemas Correr importados.")
            else:
                 if MOSTRAR_AVISOS: QMessageBox.information(parent, "Dados Vazios", "Nenhum dado específico ou geral encontrado para este item (Sistemas Correr).")
                 print("Nenhum dado específico ou geral encontrado para Sistemas Correr.")

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao carregar dados de sistemas de correr: {err}")
        QMessageBox.critical(parent, "Erro Base de Dados", f"Erro ao carregar dados: {err}")
    except Exception as e:
        print(f"Erro inesperado ao carregar dados de sistemas de correr: {e}")
        QMessageBox.critical(parent, "Erro Inesperado", f"Erro ao carregar dados: {e}")
        import traceback; traceback.print_exc()
    finally:
        tabela.blockSignals(False) # Garante desbloqueio dos sinais

# --- Funções de Configuração e Inicialização (sem acesso direto à BD) ---
def configurar_dados_items_orcamento_sistemas_correr(parent):
    """
    Cria a tabela no BD (caso não exista), carrega dados de sistemas de correr
    para (num_orc, ver_orc, id_sc) e muda para a aba "orcamento_items".
    """
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = ui.lineEdit_versao_orcamento.text().strip()
    id_sc = ui.lineEdit_item_orcamento.text().strip()

    if ui.Tab_Sistemas_Correr_11.columnCount() == 0:  # tabela ainda não configurada
        configurar_tabela_sistemas_correr(parent)     # cria colunas, linhas, widgets
    
    if not num_orc or not ver_orc or not id_sc:
        QMessageBox.warning(parent, "Aviso", "Preencha os campos 'Num Orçamento', 'Versão' e 'Item'!")
        return

    criar_tabela_dados_items_sistemas_correr()
    carregar_dados_items_sistemas_correr(parent)

    # Alterna para a aba "orcamento_items"
    for i in range(ui.tabWidget_orcamento.count()):
        widget = ui.tabWidget_orcamento.widget(i)
        if widget.objectName() == "orcamento_items":
            ui.tabWidget_orcamento.setCurrentIndex(i)
            break

########################################
# Função para inicializar as configurações e conectar o botão de guardar
########################################
def inicializar_dados_items_sistemas_correr(parent):
    """
    Função principal para inicializar a Tabela Tab_Sistemas_Correr_11.
    Cria colunas/linhas, conecta botões "Guardar" e "Limpar Linha" e
    prepara tudo para manipular dados de sistemas de correr.
    """
    ui = parent.ui
    configurar_tabela_sistemas_correr(parent)

    # Conecta o botão de guardar (definido na interface como 'guardar_dados_item_orcamento_tab_sistemas_correr_3')
    ui.guardar_dados_item_orcamento_tab_sistemas_correr_3.clicked.connect(lambda: guardar_dados_item_orcamento_tab_sistemas_correr_3(parent))

    # Conecta o botão "limpar_linha_tab_sistemas_correr_2" a função limpar_linha_tab_sistemas_correr_2
    ui.limpar_linha_tab_sistemas_correr_2.clicked.connect(lambda: limpar_linha_tab_sistemas_correr_2(parent))

    # Botão para importar dados (ex.: a partir de modelos existentes)
    ui.importar_dados_item_tab_sistemas_correr_3.clicked.connect(lambda: importar_dados_item_tab_sistemas_correr_3(parent))
    adicionar_menu_limpar(ui.Tab_Sistemas_Correr_11, lambda: limpar_linha_tab_sistemas_correr_2(parent))

# =============================================================================
# Função para limpar as colunas da linha selecionada na Tab_Sistemas_Correr_11 com o botão "Limpar Linha Selecionada" 
# =============================================================================
def limpar_linha_tab_sistemas_correr_2(obj):
    """Limpa a linha selecionada na Tab_Sistemas_Correr_11.
    removendo valores (ref_le, ptab, pliq, descontos, etc.).
    """
    # (Código mantido como na resposta anterior - apenas manipula UI)
    if hasattr(obj, "ui"): ui = obj.ui; parent_widget = obj
    else: ui = obj; parent_widget = obj
    tabela = ui.Tab_Sistemas_Correr_11
    tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
    selection = tabela.selectionModel().selectedRows()
    if not selection: QMessageBox.warning(parent_widget, "Aviso", "Nenhuma linha selecionada!"); return
    row_index = selection[0].row()
    # Colunas que devem ser limpas (ref_le, descrição_no_orcamento, ptab, pliq, descontos, etc.)
    COLUNAS_LIMPAR_SISTEMAS_CORRER = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, 19]
    tabela.blockSignals(True)
    for col in COLUNAS_LIMPAR_SISTEMAS_CORRER:
        widget = tabela.cellWidget(row_index, col)
        if widget:
            if hasattr(widget, "setCurrentIndex"): widget.setCurrentIndex(-1) # Limpa ComboBox
            elif hasattr(widget, "clear"): widget.clear() # Limpa QLineEdit
        else:
            item = tabela.item(row_index, col)
            if item: item.setText("")
            else: tabela.setItem(row_index, col, QTableWidgetItem(""))
    tabela.blockSignals(False)
