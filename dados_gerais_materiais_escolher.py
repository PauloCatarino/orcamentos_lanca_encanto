"""
dados_gerais_materiais_escolher.py
==================================
Módulo que exibe um diálogo para seleção de material a partir de uma tabela de matérias-primas.
Funcionalidades:
  - Exibe uma cópia da tabela original de matérias-primas (obtida via QTableWidget).
  - Permite que o usuário filtre os dados utilizando um campo de pesquisa.
  - Apresenta botões para "Selecionar", "Cancelar" e "Limpar Filtros".
  - Aplica pré-filtros para as colunas TIPO e FAMILIA, se definidos.
  - Permite que o usuário selecione uma linha e retorne a linha selecionada para posterior processamento.
  
Observação:
  Este módulo utiliza MySQL para as operações de banco de dados, por meio da função
  get_connection() importada do módulo "db_connection.py". Certifique-se de que este
  módulo esteja devidamente configurado para conectar ao seu servidor MySQL.
"""
import mysql.connector # Para capturar erros específicos
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QMessageBox, QLineEdit, QHeaderView
from PyQt5.QtCore import Qt
# Importa a função de conexão MySQL do módulo db_connection.py
from db_connection import obter_cursor

class MaterialSelectionDialog(QDialog):
    def __init__(self, materiais_table, pre_filtro_tipo="", pre_filtro_familia=""):
        """
        Inicializa o diálogo de seleção de material.
        
        Parâmetros:
          - materiais_table: QTableWidget que contém os dados originais de matérias-primas.
          - pre_filtro_tipo: String para pré-filtrar a coluna TIPO.
          - pre_filtro_familia: String para pré-filtrar a coluna FAMILIA.
          
        O diálogo inclui:
          - Um campo de pesquisa que filtra os dados conforme o usuário digita.
          - Botões "Selecionar", "Cancelar" e "Limpar Filtros".
          - Uma tabela que exibe uma cópia dos dados originais, com os pré-filtros aplicados, se definidos.
        """
        super().__init__()
        # Permite que o diálogo tenha botões padrão de janela (minimizar, maximizar)
        self.setWindowFlags(Qt.Window)
        self.setWindowTitle("Selecionar Material")
        self.setMinimumSize(2500, 900)
        
        main_layout = QVBoxLayout(self)
        
        # Campo de pesquisa para filtragem dos dados
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Pesquisar (use % para separar termos)...")
        self.search_edit.textChanged.connect(self.aplicar_filtro)
        main_layout.addWidget(self.search_edit)
        
        # Layout com os botões: Selecionar, Cancelar e Limpar Filtros
        btn_layout = QHBoxLayout()
        self.btn_select = QPushButton("Selecionar", self)
        self.btn_cancel = QPushButton("Cancelar", self)
        self.btn_limpar = QPushButton("Limpar Filtros", self)
        btn_layout.addWidget(self.btn_select)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_limpar)
        main_layout.addLayout(btn_layout)
        
        # Conecta os botões aos seus respectivos métodos
        self.btn_select.clicked.connect(self.on_select)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_limpar.clicked.connect(self.limpar_filtros)
        
        # Cria a tabela que exibirá os dados (cópia da tabela original)
        self.table = QTableWidget(self)
        main_layout.addWidget(self.table)
        self.orig_table = materiais_table
        self.carregar_dados()
        
        # Armazena os valores de pré-filtro para as colunas TIPO e FAMILIA
        self.pre_filtro_tipo = pre_filtro_tipo.strip()
        self.pre_filtro_familia = pre_filtro_familia.strip()
        # Se houver pré-filtro e o campo de pesquisa estiver vazio, aplica o pré-filtro
        if (self.pre_filtro_tipo or self.pre_filtro_familia) and (self.search_edit.text().strip() == ""):
            self.aplicar_pre_filtro()
        
        # Define larguras fixas para as colunas da tabela (exemplo)
        col_widths = [50, 90, 90, 65, 300, 350, 80, 80, 80, 50, 50, 50, 50, 100, 100, 90, 90, 90, 90, 60, 60, 90, 90, 90, 90, 50, 50, 50, 50]
        for i, w in enumerate(col_widths):
             # Adicionar verificação para evitar IndexError se col_widths for menor que col_count
            if i < self.table.columnCount():
                self.table.setColumnWidth(i, w)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)

    def carregar_dados(self):
        """
        Copia os dados da tabela original (materiais_table) para a tabela deste diálogo.
        """
        col_count = self.orig_table.columnCount()
        row_count = self.orig_table.rowCount()
        self.table.setColumnCount(col_count)
        headers = []
        for i in range(col_count):
            header_item = self.orig_table.horizontalHeaderItem(i)
            headers.append(header_item.text() if header_item else f"Col{i}")
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(row_count)
        for r in range(row_count):
            for c in range(col_count):
                orig_item = self.orig_table.item(r, c)
                texto = orig_item.text() if orig_item else ""
                self.table.setItem(r, c, QTableWidgetItem(texto))
          
    def aplicar_pre_filtro(self):
        """
        Aplica um pré-filtro na tabela com base nos valores de self.pre_filtro_tipo e self.pre_filtro_familia.
        Assume que a coluna TIPO está no índice 13 e a coluna FAMILIA no índice 14.
        """
        row_count = self.table.rowCount()
        for r in range(row_count):
            tipo = self.table.item(r, 13).text() if self.table.item(r, 13) else ""
            familia = self.table.item(r, 14).text() if self.table.item(r, 14) else ""
            
            if not self.pre_filtro_tipo and not self.pre_filtro_familia:
                self.table.setRowHidden(r, False)
            elif self.pre_filtro_tipo and not self.pre_filtro_familia:
                self.table.setRowHidden(r, self.pre_filtro_tipo.lower() not in tipo.lower())
            elif not self.pre_filtro_tipo and self.pre_filtro_familia:
                self.table.setRowHidden(r, self.pre_filtro_familia.lower() not in familia.lower())
            else:
                if (self.pre_filtro_tipo.lower() in tipo.lower()) and (self.pre_filtro_familia.lower() in familia.lower()):
                    self.table.setRowHidden(r, False)
                else:
                    self.table.setRowHidden(r, True)
    
    def aplicar_filtro(self):
        """
        Aplica um filtro na tabela com base no texto digitado no campo de pesquisa.
        Se o campo estiver vazio, aplica os pré-filtros; caso contrário, filtra as linhas que contenham
        todos os termos (separados por '%') em qualquer coluna.
        """
        search_text = self.search_edit.text().strip()
        if search_text == "":
            self.aplicar_pre_filtro()
        else:
            termos = [t.strip().lower() for t in search_text.split('%') if t.strip()]
            row_count = self.table.rowCount()
            for r in range(row_count):
                row_text = ""
                # Concatena texto de colunas visíveis para pesquisa
                for c in range(self.table.columnCount()):
                     if not self.table.isColumnHidden(c): # Pesquisa apenas em colunas visíveis
                          item = self.table.item(r, c)
                          if item:
                               row_text += item.text().lower() + " "
                # Verifica se todos os termos estão presentes
                if all(term in row_text for term in termos):
                    self.table.setRowHidden(r, False)
                else:
                    self.table.setRowHidden(r, True)

    def limpar_filtros(self):
        """
        Limpa os filtros: esvazia o campo de pesquisa e remove os pré-filtros,
        exibindo todas as linhas da tabela.
        """
        self.search_edit.clear()
        self.pre_filtro_tipo = ""
        self.pre_filtro_familia = ""
        for r in range(self.table.rowCount()):
            self.table.setRowHidden(r, False)
    
    def keyPressEvent(self, event):
        """
        Ao pressionar a tecla ENTER, confirma a seleção se houver uma linha selecionada.
        """
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.table.selectedItems():
                self.on_select()
                return
        super().keyPressEvent(event)
    
    def on_select(self):
        """
        Define a linha selecionada e fecha o diálogo com sucesso.
        """
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Erro", "Nenhuma linha selecionada.")
            return
        self.selected_row = selected_items[0].row()
        self.accept()

def get_distinct_values(col_name):
    """
    Retorna os valores distintos da coluna 'col_name' da tabela de matérias-primas.
    """
    values = []
    # Validação básica do nome da coluna
    allowed_cols = {"tipo", "familia", "ref_le", "descricao", "material", "und"} # Adicionar outras se necessário
    col_name_safe = col_name.strip('`').lower()
    if col_name_safe not in allowed_cols:
        print(f"[ERRO] Tentativa de usar coluna não permitida em get_distinct_values: {col_name}")
        return values

    # Query SQL usando backticks e placeholders
    query = f"""
        SELECT DISTINCT `{col_name_safe}`
        FROM materias_primas
        WHERE `{col_name_safe}` IS NOT NULL AND `{col_name_safe}` <> ''
        ORDER BY `{col_name_safe}`
    """
    try:
        # Usa o gestor de contexto
        with obter_cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            # Extrai o primeiro elemento de cada tupla (o valor distinto)
            values = [row[0] for row in results]
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao obter valores distintos para '{col_name}': {err}")
        # Não mostrar QMessageBox aqui, pode ser chamado muitas vezes
    except Exception as e:
        print(f"Erro inesperado ao obter valores distintos para '{col_name}': {e}")
        import traceback
        traceback.print_exc()
    return values
