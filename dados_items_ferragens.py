"""
Módulo: dados_items_ferragens.py
Descrição:
  Este módulo configura a tabela "Tab_Ferragens_11" destinada ao orçamento de ferragens (itens de hardware).
  Ele segue uma lógica similar ao módulo de materiais, mas adaptada especificamente para manipular
  dados de ferragens, como dobradiças, puxadores, suportes, etc.

  Principais funcionalidades:
    - Definição das colunas (FERRAGENS_COLUNAS) e linhas (FERRAGENS_LINHAS) para a tabela de ferragens.
    - Configuração dos widgets na tabela (ComboBox, botões e campos editáveis).
    - Cálculo automático do campo 'pliq' (preço líquido) baseado em ptab e descontos.
    - Funções para carregar, importar e guardar os dados referentes a ferragens no banco de dados.
    - Função para limpar o conteúdo de uma linha selecionada.
    - Função para selecionar ferragens (“Escolher”) abrindo um diálogo de seleção de materiais.

Autor: Paulo Catarino
Data: 19/03/2025 
"""

from PyQt5.QtWidgets import QTableWidgetItem, QComboBox, QPushButton, QMessageBox, QHeaderView, QAbstractItemView, QDialog
from PyQt5.QtCore import Qt
import mysql.connector # Adicionado para erros específicos de conexão com o banco de dados

# Importações de funções utilitárias para formatação e conversão de valores:
from utils import (formatar_valor_moeda, formatar_valor_percentual, converter_texto_para_valor,  get_distinct_values_with_filter, adicionar_menu_limpar)

# Diálogo de seleção de material/ferragem/ssitemascorrer/acabamentos
from dados_gerais_materiais_escolher import MaterialSelectionDialog

# Função de conexão com o banco de dados
from db_connection import obter_cursor

# Função para formatar a versão do orçamento
from configurar_guardar_dados_gerais_orcamento import formatar_versao

###############################################################
# Definição das colunas para Tab_Ferragens_11
###############################################################
# Esta lista define a estrutura das colunas que aparecerão na
# tabela dedicada às ferragens, com informações como tipo de dado,
# se a coluna é editável, se possui ComboBox, botão, etc.
###############################################################
FERRAGENS_COLUNAS = [
    {'nome': 'material',               'tipo': 'TEXT',    'visivel': True,  'editavel': False},
    {'nome': 'descricao',              'tipo': 'TEXT',    'visivel': True,  'editavel': True},
    {'nome': 'id_fer',                 'tipo': 'INTEGER', 'visivel': True,  'editavel': False},
    {'nome': 'num_orc',                'tipo': 'INTEGER', 'visivel': True,  'editavel': False},
    {'nome': 'ver_orc',                'tipo': 'INTEGER', 'visivel': True,  'editavel': False},
    {'nome': 'ref_le',                 'tipo': 'TEXT',    'visivel': True,  'editavel': False},
    {'nome': 'descricao_no_orcamento', 'tipo': 'TEXT',    'visivel': True,  'editavel': True},
    {'nome': 'ptab',                   'tipo': 'REAL',    'visivel': True,  'editavel': True},
    {'nome': 'pliq',                   'tipo': 'REAL',    'visivel': True,  'editavel': True},
    {'nome': 'desc1_plus',             'tipo': 'REAL',    'visivel': True,  'editavel': True},
    {'nome': 'desc2_minus',            'tipo': 'REAL',    'visivel': True,  'editavel': True},
    {'nome': 'und',                    'tipo': 'TEXT',    'visivel': True,  'editavel': True},
    {'nome': 'desp',                   'tipo': 'REAL',    'visivel': True,  'editavel': True},
    {'nome': 'corres_orla_0_4',        'tipo': 'TEXT',    'visivel': True,  'editavel': True},
    {'nome': 'corres_orla_1_0',        'tipo': 'TEXT',    'visivel': True,  'editavel': True},
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
# Definição das linhas para a tabela de Ferragens
###############################################################
# Cada linha representa um tipo de ferragem (dobradiça, puxador, etc.)
# que poderá ser orçado e exibido na Tab_Ferragens_11.
###############################################################
FERRAGENS_LINHAS = [
    'Fer_Dobradica', 'Fer_Suporte Prateleira', 'Fer_Suporte Varao', 'Fer_Varao_SPP',
    'Fer_Rodape_PVC', 'Fer_Pes_1', 'Fer_Pes_2', 'Fer_Grampas', 'Fer_Corredica_1',
    'Fer_Corredica_2', 'Fer_Corredica_3', 'Fer_Puxador', 'Fer_Puxador_SPP_1',
    'Fer_Puxador_SPP_2', 'Fer_Puxador_SPP_3', 'Fer_Sistema_Basculante_1',
    'Fer_Sistema_Basculante_2', 'Fer_Acessorio_1', 'Fer_Acessorio_2',
    'Fer_Acessorio_3', 'Fer_Acessorio_4', 'Fer_Acessorio_5', 'Fer_Acessorio_6',
    'Fer_Acessorio_7', 'Fer_Acessorio_8_SPP'
]

def escolher_ferragens_item(ui, linha_tab):
    """
    Abre um diálogo (MaterialSelectionDialog) para o usuário escolher uma ferragem.
    Ao escolher, o diálogo retorna os dados da ferragem e a função preenche
    as colunas correspondentes na linha específica da Tab_Ferragens_11.
    
    Parâmetros:
       ui: interface principal que contém a tabela Tab_Ferragens_11.
       linha_tab: inteiro representando a linha onde os dados serão preenchidos.

    Retorna:
       True se o usuário selecionou alguma ferragem,
       False se o usuário cancelou a operação.
    """
    tbl_item = ui.Tab_Ferragens_11
    tbl_item.blockSignals(True)
    
    # Índices das colunas na tabela, conforme definido no array FERRAGENS_COLUNAS:
    tipo_col_idx = 15
    familia_col_idx = 16
    
    pre_tipo = ""
    pre_familia = ""
    if tbl_item.cellWidget(linha_tab, tipo_col_idx):
        pre_tipo = tbl_item.cellWidget(linha_tab, tipo_col_idx).currentText()
    if tbl_item.cellWidget(linha_tab, familia_col_idx):
        pre_familia = tbl_item.cellWidget(linha_tab, familia_col_idx).currentText()
    
    # Abre o diálogo de seleção utilizando a tabela de matérias-primas (ui.tableWidget_materias_primas).
    # Podemos filtrar por tipo/família, se necessário.
    dialog = MaterialSelectionDialog(ui.tableWidget_materias_primas, pre_tipo, pre_familia)
    if dialog.exec_() == dialog.Accepted:
        row_idx = dialog.selected_row
        
        # Mapeamento para preencher a linha no Tab_Ferragens_11
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
        # Primeiro, limpamos as células que serão preenchidas
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
def on_item_changed_items_ferragens(item):
    """
    Callback que é acionado sempre que o usuário edita uma célula na
    Tab_Ferragens_11 (campo de ferragens). Ele recalcula o campo pliq
    baseado em ptab, desc1_plus e desc2_minus.

    Fórmula:
      pliq = (PRECO_TABELA*(1-DESC2_MINUS))*(1+DESC1_PLUS)

    Se o usuário editar a própria coluna pliq, o sistema apenas formata 
    o valor como moeda.
    """
    if not item:
        return
    tabela = item.tableWidget();
    if tabela.property("importando"):
        # Se estiver no modo de importação, ignoramos para não gerar loops.
        return
    
    row = item.row()
    col = item.column()

    # Colunas onde as edições impactam o cálculo do pliq:
    # ptab: col 7
    # desc1_plus: col 9
    # desc2_minus: col 10
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
    Função que é chamada ao clicar no botão "Escolher" (coluna MP).
    Aqui, chamamos a função escolher_ferragens_item, que abrirá o diálogo
    para selecionar a ferragem. Caso haja seleção, exibimos uma mensagem.
    """
    if escolher_ferragens_item(ui, row):
        QMessageBox.information(None, "Ferragem", f"Ferragem selecionada para a linha {row+1}.")


# Atribui a função do botão "Escolher" à respectiva coluna de MP
for col in FERRAGENS_COLUNAS:
    if col['nome'] == 'MP':
        col['funcao_botao'] = on_mp_button_clicked


########################################
# Função para definir larguras fixas para as colunas de Tab_Ferragens_11
########################################
def definir_larguras_tab_ferragens_item(ui):
    """
    Ajusta larguras fixas das colunas da Tab_Ferragens_11 para melhorar
    a aparência e usabilidade visual.
    """
    tabela = ui.Tab_Ferragens_11
    header = tabela.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.Fixed)
    header.setStretchLastSection(False)
    
    # Larguras definidas para cada coluna (ajuste conforme necessidade real)
    larguras = [200, 200, 50, 110, 50, 100, 400, 60, 60, 60, 60, 50,  50, 180, 110, 120, 120, 90, 90, 90, 100]
    num_cols = tabela.columnCount()
    if len(larguras) < num_cols:
        larguras += [100] * (num_cols - len(larguras))
    for idx in range(num_cols):
        tabela.setColumnWidth(idx, larguras[idx])


def importar_dados_item_orcamento_tab_ferragens(parent):
    """
    Função para importar dados de ferragens para a tabela Tab_Ferragens_11,
    reaproveitando a lógica de importação usada no módulo dados_gerais_manager.

    Passos:
       1. Redireciona temporariamente ui.Tab_Ferragens para ui.Tab_Ferragens_11.
       2. Chama a função de importação existente (importar_dados_gerais_com_opcao).
       3. Restaura o widget original.
    """
    ui = parent.ui

    # Mapeamento de colunas para a Tab_Ferragens_11 (colunas começam em 0, mas 0 é nome da linha)
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

    # Redireciona tabela "ferragens" para Tab_Ferragens_11
    original_tab = ui.Tab_Ferragens
    ui.Tab_Ferragens = ui.Tab_Ferragens_11

    try:
        # Importa usando a função genérica, passando "ferragens" como tipo e nosso mapeamento
        importar_dados_gerais_com_opcao(parent, "ferragens", mapeamento)
    finally:
        # Restaura para não atrapalhar outras partes do código
        ui.Tab_Ferragens = original_tab

########################################
# Função principal para configurar a Tab_Ferragens_11 (Dados do Item)
########################################
def configurar_tabela_ferragens(parent):
    """
    Configura a tabela Tab_Ferragens_11 para exibir dados de ferragens.
    Cria as colunas, define o cabeçalho, insere widgets (ComboBox, botões)
    e conecta o callback de edição on_item_changed_items_ferragens.

    Parâmetros:
        parent: Instância principal (janela) que contém o atributo ui.
    """
    ui = parent.ui
    tabela = ui.Tab_Ferragens_11
    tabela.clear()
    num_cols = len(FERRAGENS_COLUNAS)
    num_rows = len(FERRAGENS_LINHAS)
    tabela.setColumnCount(num_cols)
    tabela.setRowCount(num_rows)

    # Define o nome das colunas no cabeçalho
    headers = [col['nome'] for col in FERRAGENS_COLUNAS]
    tabela.setHorizontalHeaderLabels(headers)
    tabela.verticalHeader().setVisible(False)

    # Preenche a coluna 0 com o nome de cada linha (Fer_Dobradica, Fer_Puxador, etc.)
    for row_idx, nome_linha in enumerate(FERRAGENS_LINHAS):
        item = QTableWidgetItem(nome_linha)
        tabela.setItem(row_idx, 0, item)
    
    # Preenche as colunas restantes
    for col_idx, col_def in enumerate(FERRAGENS_COLUNAS):
        if col_idx == 0:
            continue  # A coluna 0 já foi preenchida com os nomes das linhas
        
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
                    return lambda: func(ui, r, "Tab_Ferragens_11")
                
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

    # Conecta o callback de edição
    tabela.itemChanged.connect(on_item_changed_items_ferragens)

    # Ajusta tamanho das colunas e linhas
    tabela.resizeColumnsToContents()
    tabela.resizeRowsToContents()

    # Define larguras personalizadas
    definir_larguras_tab_ferragens_item(ui)
    # Configura a tabela de Dados do Item na interface na coluna familia preenche com 'FERRAGENS' & coluna tipo com valores predefinidos exemplo: 'DOBRADICAS', 'SUPORTE_PRATELEIRA', etc.
    from utils import apply_row_selection_style
    tabela = ui.Tab_Ferragens_11
    familia_idx = next((i for i, c in enumerate(FERRAGENS_COLUNAS) if c['nome'] == 'familia'), None)
    tipo_idx = next((i for i, c in enumerate(FERRAGENS_COLUNAS) if c['nome'] == 'tipo'), None)
    tipo_padrao = {
        'Fer_Dobradica': 'DOBRADICAS',
        'Fer_Suporte Prateleira': 'SUPORTE PRATELEIRA',
        'Fer_Suporte Varao': 'SUPORTE VARAO',
        'Fer_Varao_SPP': 'SPP',
        'Fer_Rodape_PVC': 'RODAPE',
        'Fer_Pes_1': 'PES',
        'Fer_Pes_2': 'PES',
        'Fer_Corredica_1': 'CORREDICAS',
        'Fer_Corredica_2': 'CORREDICAS',
        'Fer_Corredica_3': 'CORREDICAS',
        'Fer_Puxador': 'PUXADOR',
        'Fer_Puxador_SPP_1': 'SPP',
        'Fer_Puxador_SPP_2': 'SPP',
        'Fer_Puxador_SPP_3': 'SPP'
    }
    for r, nome in enumerate(FERRAGENS_LINHAS):
        if familia_idx is not None:
            combo = tabela.cellWidget(r, familia_idx)
            if isinstance(combo, QComboBox):
                idx = combo.findText('FERRAGENS')
                if idx >= 0:
                    combo.setCurrentIndex(idx)
        if tipo_idx is not None:
            combo = tabela.cellWidget(r, tipo_idx)
            if isinstance(combo, QComboBox):
                padrao = tipo_padrao.get(nome, '')
                idx = combo.findText(padrao)
                if idx >= 0 and padrao:
                    combo.setCurrentIndex(idx)
                else:
                    combo.setCurrentIndex(-1)
    apply_row_selection_style(tabela)


# =============================================================================
# Função para limpar as colunas da linha selecionada na Tab_Ferragens_11 com o botão "Limpar Linha Selecionada" 
# =============================================================================

def limpar_linha_tab_ferragens(obj):
    """
    Limpa (apaga) o conteúdo de uma linha selecionada na Tab_Ferragens_11.
    Útil para descartar dados de ferragens que foram preenchidos incorretamente.

    Parâmetros:
       obj: pode ser o próprio parent ou ui, que contenha a Tabela Tab_Ferragens_11.
    """
    if hasattr(obj, "ui"):
        ui = obj.ui
        parent_widget = obj
    else:
        ui = obj
        parent_widget = obj

    tabela = ui.Tab_Ferragens_11

    # Define que a seleção será por linha
    tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
    selection = tabela.selectionModel().selectedRows()
    if not selection:
        QMessageBox.warning(parent_widget, "Aviso", "Nenhuma linha selecionada!")
        return

    row_index = selection[0].row()

    # Colunas que devem ser limpas (ref_le, descrição_no_orcamento, ptab, pliq, descontos, etc.)
    COLUNAS_LIMPAR_FERRAGENS = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, 19]

    tabela.blockSignals(True)

    # Iterar sobre cada coluna e limpar o conteúdo
    for col in COLUNAS_LIMPAR_FERRAGENS:
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


def criar_tabela_dados_items_ferragens():
    """
    Cria no banco de dados a tabela 'dados_items_ferragens' para armazenar
    os registros de ferragens por item/orçamento. Faz a verificação prévia
    para não criar se a tabela já existir.
    """
    #print("Verificando/Criando tabela 'dados_items_ferragens'...")
    try:
        with obter_cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'dados_items_ferragens'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE dados_items_ferragens (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        num_orc VARCHAR(50) NOT NULL,
                        ver_orc VARCHAR(10) NOT NULL,
                        id_fer VARCHAR(50) NOT NULL, -- Chave do item do orçamento
                        linha INT NOT NULL,         -- Índice da linha na UI (0 a N-1)
                        material TEXT NULL,         -- Nome da linha (ex: Fer_Dobradica)
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
                        UNIQUE KEY idx_item_fer_unico (num_orc, ver_orc, id_fer, linha),
                        INDEX idx_item_fer_lookup (num_orc, ver_orc, id_fer)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                print("Tabela 'dados_items_ferragens' criada.")
            else:
                 print("Tabela 'dados_items_ferragens' já existe.")   # Pretendo eliminar esta linha mas dá erro
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao criar/verificar 'dados_items_ferragens': {err}")
    except Exception as e:
        print(f"Erro inesperado ao criar/verificar 'dados_items_ferragens': {e}")

########################################
# FUNÇÃO: Guardar os dados dos itens do orçamento
########################################
def guardar_dados_item_orcamento_tab_ferragens(parent):
    """
    Percorre a Tab_Ferragens_11 e salva os dados no banco de dados (tabela dados_items_ferragens).
    Se já existir registro para o mesmo (num_orc, ver_orc, id_fer), o usuário será perguntado
    se deseja sobrescrever.

    Param:
       parent: instância principal, que contém a interface (ui).
    """
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = formatar_versao(ui.lineEdit_versao_orcamento.text())
    id_fer = ui.lineEdit_item_orcamento.text().strip()# ID do item do orçamento
    MOSTRAR_AVISOS = False  # Muda para True quando quiser ver as mensagens

        
    if not num_orc or not ver_orc or not id_fer:
        QMessageBox.warning(parent, "Aviso", "Preencha os campos 'Num Orçamento', 'Versão' e 'Item'!")
        return

    table_widget = ui.Tab_Ferragens_11
    tabela = table_widget 
    num_rows = table_widget.rowCount()
    if num_rows == 0: return

    # Lista de colunas no BD (ordem do INSERT)
    col_names_db = [
        'num_orc', 'ver_orc', 'id_fer','linha', 'material', 'descricao', 'ref_le',
        'descricao_no_orcamento', 'ptab', 'pliq', 'desc1_plus', 'desc2_minus',
        'und', 'desp', 'corres_orla_0_4', 'corres_orla_1_0', 'tipo', 'familia',
        'comp_mp', 'larg_mp', 'esp_mp'
    ]

    # Mapeamento entre o nome do campo (usado no BD) e a coluna na tabela
    ui_to_db_mapping = {
        'num_orc': 3,
        'ver_orc': 4,
        'id_fer': 2,
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

    # Coleta de dados da UI (mantida como antes)
    dados_para_salvar = []
    for r in range(num_rows):
        dados_linha = {'num_orc': num_orc, 'ver_orc': ver_orc, 'id_fer': id_fer, 'linha': r}
        for key_db in col_names_db:
            if key_db in dados_linha: continue
            col_ui = ui_to_db_mapping.get(key_db)
            if col_ui is None: continue
            # Obtemos o valor da célula correspondente na tabela
            cell = tabela.item(r, col_ui); valor_str = cell.text().strip() if cell else ""
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
                "SELECT COUNT(*) FROM dados_items_ferragens WHERE num_orc=%s AND ver_orc=%s AND id_fer=%s",
                (num_orc, ver_orc, id_fer)
            )
            count = cursor_check.fetchone()[0]

        if count > 0:
            resposta = QMessageBox.question(parent, "Dados Existentes",
                                            "Já existem dados para este item (Ferragens). Deseja substituí-los?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resposta == QMessageBox.No: return
            else:
                with obter_cursor() as cursor_del:
                    cursor_del.execute(
                        "DELETE FROM dados_items_ferragens WHERE num_orc=%s AND ver_orc=%s AND id_fer=%s",
                        (num_orc, ver_orc, id_fer)
                    )
                    print(f"{cursor_del.rowcount} registos antigos de ferragens eliminados.")

        linhas_inseridas = 0
        with obter_cursor() as cursor_insert:
            placeholders = ", ".join(["%s"] * len(col_names_db))
            query_insert = f"INSERT INTO dados_items_ferragens ({', '.join(col_names_db)}) VALUES ({placeholders})"
            for row_data in dados_para_salvar:
                try:
                    cursor_insert.execute(query_insert, row_data)
                    linhas_inseridas += 1
                except mysql.connector.Error as insert_err:
                     print(f"Erro MySQL ao inserir linha {row_data[3]} para item {id_fer}: {insert_err}")
                     QMessageBox.warning(parent, "Erro ao Inserir", f"Falha ao guardar linha {row_data[3]+1}: {insert_err}")

        if MOSTRAR_AVISOS: QMessageBox.information(parent, "Sucesso", f"{linhas_inseridas} linha(s) de Ferragens guardada(s).")
        print(f"{linhas_inseridas} linha(s) de Ferragens guardada(s).")

    except mysql.connector.Error as err:
        QMessageBox.critical(parent, "Erro Base de Dados", f"Erro ao guardar dados: {err}")
        print(f"Erro MySQL (guardar ferragens): {err}")
    except Exception as e:
        QMessageBox.critical(parent, "Erro Inesperado", f"Erro ao guardar dados: {e}")
        import traceback; traceback.print_exc()


# =============================================================================
# Função carregar_dados_items(parent) 
# =============================================================================
def carregar_dados_items(parent):
    """
    Carrega ou completa a Tabela de Ferragens (Tab_Ferragens_11) com dados
    salvos anteriormente no banco de dados, filtrando por (num_orc, ver_orc, id_fer).
    Se não houver dados específicos para o item, tenta importar dos dados gerais de ferragens.
    Se mesmo assim não encontrar, apenas mantém colunas fixas.

    Parâmetros:
       parent: instância principal que contém a interface (ui).
    """
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = ui.lineEdit_versao_orcamento.text().strip()
    id_fer = ui.lineEdit_item_orcamento.text().strip()
    MOSTRAR_AVISOS = False  # ATENÇÃO: Muda para True quando quiser ver as mensagens
    
    tabela = ui.Tab_Ferragens_11
    tabela.blockSignals(True)

    # Limpa colunas relevantes
    clear_cols = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,17,18,19]
    key_cols = {2: id_fer, 3: num_orc, 4: ver_orc}
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

    tipo_idx = next((i for i, c in enumerate(FERRAGENS_COLUNAS) if c['nome'] == 'tipo'), None)
    familia_idx = next((i for i, c in enumerate(FERRAGENS_COLUNAS) if c['nome'] == 'familia'), None)
    tipo_padrao = {
        'Fer_Dobradica': 'DOBRADICAS',
        'Fer_Suporte Prateleira': 'SUPORTE PRATELEIRA',
        'Fer_Suporte Varao': 'SUPORTE VARAO',
        'Fer_Varao_SPP': 'SPP',
        'Fer_Rodape_PVC': 'RODAPE',
        'Fer_Pes_1': 'PES',
        'Fer_Pes_2': 'PES',
        'Fer_Corredica_1': 'CORREDICAS',
        'Fer_Corredica_2': 'CORREDICAS',
        'Fer_Corredica_3': 'CORREDICAS',
        'Fer_Puxador': 'PUXADOR',
        'Fer_Puxador_SPP_1': 'SPP',
        'Fer_Puxador_SPP_2': 'SPP',
        'Fer_Puxador_SPP_3': 'SPP'
    }
    for r, nome in enumerate(FERRAGENS_LINHAS):
        if familia_idx is not None:
            combo_f = tabela.cellWidget(r, familia_idx)
            if isinstance(combo_f, QComboBox):
                idx = combo_f.findText('FERRAGENS')
                if idx >= 0:
                    combo_f.setCurrentIndex(idx)
        if tipo_idx is not None:
            combo_t = tabela.cellWidget(r, tipo_idx)
            if isinstance(combo_t, QComboBox):
                padrao = tipo_padrao.get(nome, '')
                idx = combo_t.findText(padrao)
                if idx >= 0 and padrao:
                    combo_t.setCurrentIndex(idx)
                else:
                    combo_t.setCurrentIndex(-1) 

    # Mapeamentos para os índices das colunas das tabelas do banco de dados:
    # Para a tabela dados_items_ferragens (índices conforme definição)
    db_mapping_items = {
        'linha': 4,  # <--- ADICIONAR ESTA LINHA. Mapeia o campo 'linha' para o índice 4
        'material': 5, 'descricao': 6, 'id_fer': 3, 'num_orc': 1, 'ver_orc': 2,
        'ref_le': 7, 'descricao_no_orcamento': 8, 'ptab': 9, 'pliq': 10,
        'desc1_plus': 11, 'desc2_minus': 12, 'und': 13, 'desp': 14,
        'corres_orla_0_4': 15, 'corres_orla_1_0': 16, 'tipo': 17,
        'familia': 18, 'comp_mp': 19, 'larg_mp': 20, 'esp_mp': 21
    }
    # Para a tabela dados_gerais_ferragens (índices conforme informado)
    db_mapping_gerais = {
        'descricao': 4, 'id_fer': 5, 'num_orc': 6, 'ver_orc': 7,
        'ref_le': 8, 'descricao_no_orcamento': 9, 'ptab': 10, 'pliq': 11,
        'desc1_plus': 12, 'desc2_minus': 13, 'und': 14, 'desp': 15,
        'corres_orla_0_4': 16, 'corres_orla_1_0': 17, 'tipo': 18,
        'familia': 19, 'comp_mp': 20, 'larg_mp': 21, 'esp_mp': 22
    }
    # Mapeamento para a interface Tab_Ferragens_11: chave = nome do campo, valor = coluna
    tab_mapping = {
        'descricao': 1, 'id_fer': 2, 'num_orc': 3, 'ver_orc': 4,
        'ref_le': 5, 'descricao_no_orcamento': 6, 'ptab': 7, 'pliq': 8,
        'desc1_plus': 9, 'desc2_minus': 10, 'und': 11, 'desp': 12,
        'corres_orla_0_4': 13, 'corres_orla_1_0': 14, 'tipo': 15,
        'familia': 16, 'comp_mp': 17, 'larg_mp': 18, 'esp_mp': 19
    }
    
    registros_items = []
    registros_gerais = []
    try:
        # 1. Tenta carregar de dados_items_ferragens
        with obter_cursor() as cursor_items:
            cursor_items.execute("""
                SELECT * FROM dados_items_ferragens
                WHERE num_orc = %s AND ver_orc = %s AND id_fer = %s
                ORDER BY linha
            """, (num_orc, ver_orc, id_fer))
            registros_items = cursor_items.fetchall()

        if registros_items:
            #print(f"Carregados {len(registros_items)} registos de dados_items_ferragens.")
            for registro in registros_items:
                linha_idx = registro[db_mapping_items['linha']]
                if 0 <= linha_idx < tabela.rowCount():
                    for campo, col_tab_ui in tab_mapping.items():
                        if campo in ['num_orc', 'ver_orc', 'id_fer']: continue
                        db_idx = db_mapping_items.get(campo);
                        if db_idx is None: continue
                        # Adiciona verificação de índice para evitar IndexError
                        if db_idx >= len(registro):
                             print(f"[AVISO] Índice DB {db_idx} inválido para registro de item na linha UI {linha_idx}.")
                             continue
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
            if MOSTRAR_AVISOS: QMessageBox.information(parent, "Dados Carregados", "Dados do item (Ferragens) carregados.")

        else:
            # 2. Se não houver dados de item, tenta carregar de dados_gerais_ferragens
            print("Nenhum dado de item encontrado, tentando carregar dados gerais...")
            try:
                with obter_cursor() as cursor_geral:
                    # Ajustar query se a tabela geral tiver estrutura diferente ou precisar de outro filtro
                    cursor_geral.execute("""
                        SELECT * FROM dados_gerais_ferragens
                        WHERE num_orc = %s AND ver_orc = %s -- Filtro exemplo, ajustar!
                        ORDER BY id -- Ou pela coluna 'material'/'ferragem' se existir?
                    """, (num_orc, ver_orc)) # Usar o filtro correto!
                    registros_gerais = cursor_geral.fetchall()
            except mysql.connector.Error as err_geral:
                 if err_geral.errno == 1146: print("Tabela 'dados_gerais_ferragens' não encontrada.")
                 else: print(f"Erro MySQL ao buscar dados gerais de ferragens: {err_geral}"); QMessageBox.warning(parent, "Erro BD", f"Erro ao buscar dados gerais: {err_geral}")

            if registros_gerais:
                print(f"Carregando {len(registros_gerais)} registos de dados_gerais_ferragens.")
                for row_idx, registro in enumerate(registros_gerais):
                     if row_idx >= tabela.rowCount(): break
                     # Precisa mapear o nome da ferragem da tabela geral para a linha correta na UI
                     material_geral = registro[db_mapping_gerais.get('material', 0)] # Ajustar índice se nome da coluna for diferente
                     linha_ui_destino = -1
                     for r_ui in range(tabela.rowCount()):
                          if tabela.item(r_ui, 0).text() == material_geral:
                               linha_ui_destino = r_ui; break
                     if linha_ui_destino == -1: continue # Pula se não encontrar a linha correspondente

                     for campo, col_tab_ui in tab_mapping.items():
                         if campo in ['num_orc', 'ver_orc', 'id_fer']: continue
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
                if MOSTRAR_AVISOS: QMessageBox.information(parent, "Dados Carregados", "Dados gerais de Ferragens importados.")
            else:
                 if MOSTRAR_AVISOS: QMessageBox.information(parent, "Dados Vazios", "Nenhum dado específico ou geral encontrado para este item (Ferragens).")
                 print("Nenhum dado específico ou geral encontrado para Ferragens.")

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao carregar dados de ferragens: {err}")
        QMessageBox.critical(parent, "Erro Base de Dados", f"Erro ao carregar dados: {err}")
    except Exception as e:
        print(f"Erro inesperado ao carregar dados de ferragens: {e}")
        QMessageBox.critical(parent, "Erro Inesperado", f"Erro ao carregar dados: {e}")
        import traceback; traceback.print_exc()
    finally:
        tabela.blockSignals(False) # Garante desbloqueio


def configurar_dados_items_orcamento_ferragens(parent):
    """
    Cria a tabela no BD (caso não exista), carrega os dados de ferragens
    correspondentes ao (num_orc, ver_orc, id_fer) e muda o TabWidget
    para o separador 'orcamento_items' para exibir os dados.

    Parâmetros:
        parent: instância principal que contém a interface (ui).
    """
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = ui.lineEdit_versao_orcamento.text().strip()
    id_fer = ui.lineEdit_item_orcamento.text().strip()

    if ui.Tab_Ferragens_11.columnCount() == 0:  # tabela ainda não configurada
        configurar_tabela_ferragens(parent)     # cria colunas, linhas, widgets

    if not num_orc or not ver_orc or not id_fer:
        QMessageBox.warning(parent, "Aviso", "Preencha os campos 'Num Orçamento', 'Versão' e 'Item'!")
        return

    criar_tabela_dados_items_ferragens()
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
def inicializar_dados_items_ferragens(parent):
    """
    Função principal para inicializar a tabela de Ferragens (Tab_Ferragens_11).
    Cria as colunas/linhas, conecta os botões "Guardar" e "Limpar Linha"
    e prepara tudo para receber e manipular os dados de ferragens.

    Parâmetros:
       parent: janela principal que possui o atributo ui.
    """
    ui = parent.ui
    configurar_tabela_ferragens(parent)

    # Conecta o botão de guardar (definido na interface como 'guardar_dados_item_orcamento_tab_ferragens_2')
    ui.guardar_dados_item_orcamento_tab_ferragens_2.clicked.connect(lambda: guardar_dados_item_orcamento_tab_ferragens(parent))

    # Conectar o botão 'limpar_linha_tab_ferragens' à função:
    ui.limpar_linha_tab_ferragens.clicked.connect(lambda: limpar_linha_tab_ferragens(parent))

    # Botão para importar dados do item (ex: reutilizar dados de outra tabela)
    ui.importar_dados_item_tab_ferragens_2.clicked.connect(lambda: importar_dados_item_orcamento_tab_ferragens(parent))
    ui.limpar_linha_tab_ferragens.clicked.connect(lambda: limpar_linha_tab_ferragens(parent))

    # Botão para importar dados do item (ex: reutilizar dados de outra tabela)
    ui.importar_dados_item_tab_ferragens_2.clicked.connect(lambda: importar_dados_item_orcamento_tab_ferragens(parent))
    adicionar_menu_limpar(ui.Tab_Ferragens_11, lambda: limpar_linha_tab_ferragens(parent))
