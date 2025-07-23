# dialogo_importar_modulo.py
# -*- coding: utf-8 -*-

"""
Módulo: dialogo_importar_modulo.py

Objetivo Principal:
-------------------
Fornecer uma interface gráfica (QDialog) para o utilizador visualizar os "Módulos Guardados"
existentes na base de dados, selecionar um e iniciar o processo de importação das suas
peças para a tabela principal de definição de peças (`tab_def_pecas`).

Principais Funcionalidades:
---------------------------
1.  Apresenta uma lista dos módulos disponíveis, mostrando o nome e, opcionalmente,
    um ícone/thumbnail da imagem do módulo.
2.  Ao selecionar um módulo na lista, exibe:
    - O nome completo do módulo.
    - A descrição do módulo.
    - Uma pré-visualização da imagem do módulo (se existir).
    - Uma tabela de resumo com as peças contidas no módulo selecionado.
3.  Permite ao utilizador confirmar a importação do módulo selecionado.
4.  Retorna o ID do módulo selecionado para a função chamadora (em `main.py`)
    para que esta possa buscar e inserir as peças.

Interação com Outros Módulos Chave:
-----------------------------------
-   Instanciado e chamado a partir do `main.py` (função `on_importar_modulo_clicked`).
-   Utiliza `modulo_gestao_modulos_db.py` para:
    - `obter_todos_modulos()`: Para popular a lista de módulos disponíveis.
    - `obter_pecas_de_modulo()`: Para buscar e exibir as peças do módulo selecionado na tabela de resumo.
"""

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QSplitter,
    QMessageBox,
    QAbstractItemView,
    QWidget,
    QHeaderView,  # Adicionado QHeaderView
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
)
import unicodedata
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon
import os
import modulo_gestao_modulos_db # Para buscar os módulos

class DialogoImportarModulo(QDialog):
    def __init__(self, utilizador_atual="Paulo", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Importar Módulo Guardado")
        self.setMinimumSize(1100, 700)

        self.selected_module_id = None
        self.lista_modulos_data = []
        self.utilizadores = ["Paulo", "Catia", "Andreia"]
        self.utilizador_selecionado = utilizador_atual if utilizador_atual in self.utilizadores else self.utilizadores[0]

        # --- Layout principal, margens mínimas ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(4)

        # --- Abas dos utilizadores, coladas ao topo ---
        self.tabs_utilizador = QTabWidget()
        self.tabs_utilizador.setStyleSheet("""
            QTabBar::tab { min-width: 100px; height: 34px; font-size: 12pt; }
            QTabWidget::pane { border: 0px; margin-top: 0px; }
        """)
        for u in self.utilizadores:
            self.tabs_utilizador.addTab(QWidget(), u)
        self.tabs_utilizador.setCurrentIndex(self.utilizadores.index(self.utilizador_selecionado))
        self.tabs_utilizador.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tabs_utilizador)

        # --- Layout horizontal para lista de módulos + detalhes do módulo ---
        conteudo_layout = QHBoxLayout()
        conteudo_layout.setContentsMargins(0, 0, 0, 0)
        conteudo_layout.setSpacing(16)

        # ----- Lado Esquerdo: Lista de módulos e campo de pesquisa -----
        lista_layout = QVBoxLayout()
        lista_layout.setContentsMargins(0, 0, 0, 0)
        lista_layout.setSpacing(8)
        self.lbl_lista_modulos = QLabel("Módulos Guardados:")
        lista_layout.addWidget(self.lbl_lista_modulos)
        # Campo de pesquisa
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Pesquisar módulos (use % para separar palavras)...")
        lista_layout.addWidget(self.search_edit)
        # Lista de módulos
        self.lista_widget_modulos = QListWidget()
        self.lista_widget_modulos.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lista_widget_modulos.setIconSize(QSize(96, 96))
        lista_layout.addWidget(self.lista_widget_modulos, 1)

        # Widget container só para aplicar proporção
        lista_container = QWidget()
        lista_container.setLayout(lista_layout)
        conteudo_layout.addWidget(lista_container, 2)

        # ----- Lado Direito: Detalhes do módulo -----
        detalhes_layout = QVBoxLayout()
        detalhes_layout.setContentsMargins(0, 0, 0, 0)
        detalhes_layout.setSpacing(7)

        # Nome, descrição e imagem, numa linha (nome+desc à esquerda, imagem à direita)
        info_layout = QHBoxLayout()
        info_layout.setSpacing(14)

        # --- Esquerda: Nome e descrição ---
        nome_desc_layout = QVBoxLayout()
        nome_desc_layout.setSpacing(5)
        self.lbl_nome_modulo_detalhe = QLabel("Nome: (Nenhum módulo selecionado)")
        self.lbl_nome_modulo_detalhe.setStyleSheet("font-weight: bold; font-size: 13pt;")
        nome_desc_layout.addWidget(self.lbl_nome_modulo_detalhe)
        # Descrição do módulo, bem maior
        self.lbl_descricao_titulo = QLabel("Descrição:")
        nome_desc_layout.addWidget(self.lbl_descricao_titulo)
        self.txt_descricao_modulo_detalhe = QTextEdit()
        self.txt_descricao_modulo_detalhe.setReadOnly(True)
        self.txt_descricao_modulo_detalhe.setMinimumHeight(120)
        self.txt_descricao_modulo_detalhe.setMaximumHeight(200)
        self.txt_descricao_modulo_detalhe.setStyleSheet("background: #fafaff; border-radius: 6px;")
        nome_desc_layout.addWidget(self.txt_descricao_modulo_detalhe)

        nome_desc_layout.addStretch(1)
        info_layout.addLayout(nome_desc_layout, 3)

        # --- Direita: Imagem do módulo ---
        self.lbl_imagem_modulo_preview = QLabel("Sem imagem")
        self.lbl_imagem_modulo_preview.setAlignment(Qt.AlignCenter)
        self.lbl_imagem_modulo_preview.setFixedSize(400, 300)
        self.lbl_imagem_modulo_preview.setStyleSheet("""
            QLabel {
                border: 1px solid #888; border-radius: 8px;
                background-color: #f9f9f9;
                font-size: 11pt; color: #888;
            }
        """)
        info_layout.addWidget(self.lbl_imagem_modulo_preview, 2, Qt.AlignTop)
        detalhes_layout.addLayout(info_layout)

        # --- Tabela de peças do módulo ---
        self.lbl_pecas_resumo = QLabel("Peças do Módulo Selecionado:")
        self.lbl_pecas_resumo.setStyleSheet("font-weight: bold; margin-top: 8px; margin-bottom: 3px;")
        detalhes_layout.addWidget(self.lbl_pecas_resumo)

        self.tabela_resumo_pecas = QTableWidget()
        self.colunas_resumo = ["Ordem", "Descricao_Livre", "Def_Peca", "QT_und", "Comp", "Larg", "Esp", "Mat_Default", "Tab_Default"]
        self.tabela_resumo_pecas.setColumnCount(len(self.colunas_resumo))
        self.tabela_resumo_pecas.setHorizontalHeaderLabels(self.colunas_resumo)
        self.tabela_resumo_pecas.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela_resumo_pecas.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela_resumo_pecas.verticalHeader().setVisible(False)
        self.tabela_resumo_pecas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabela_resumo_pecas.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        detalhes_layout.addWidget(self.tabela_resumo_pecas, 4)

        detalhes_container = QWidget()
        detalhes_container.setLayout(detalhes_layout)
        conteudo_layout.addWidget(detalhes_container, 5)

        main_layout.addLayout(conteudo_layout, 8)

        # ----- Botões de ação -----
        botoes_layout = QHBoxLayout()
        botoes_layout.setContentsMargins(0, 6, 0, 0)
        self.btn_importar = QPushButton("Importar Módulo")
        self.btn_importar.setEnabled(False)
        self.btn_cancelar = QPushButton("Cancelar")
        botoes_layout.addStretch()
        botoes_layout.addWidget(self.btn_importar)
        botoes_layout.addWidget(self.btn_cancelar)
        main_layout.addLayout(botoes_layout)

        # --- Ligações (signals) ---
        self.search_edit.textChanged.connect(self.aplicar_filtro_lista_modulos)
        self.lista_widget_modulos.currentItemChanged.connect(self.on_modulo_selecionado_changed)
        self.btn_importar.clicked.connect(self.confirmar_importacao)
        self.btn_cancelar.clicked.connect(self.reject)

        # --- Carrega os módulos para o utilizador ---
        self.carregar_lista_modulos()

    def _normalize(self, texto):
        """Remove acentos e baixa o texto para normalizar pesquisa."""
        texto = texto or ""
        texto = unicodedata.normalize('NFKD', texto)
        texto = ''.join(c for c in texto if not unicodedata.combining(c))
        return texto.lower()

    def aplicar_filtro_lista_modulos(self):
        """Filtra a lista de módulos conforme o texto da pesquisa."""
        self.lista_widget_modulos.clear()
        termos = [self._normalize(t) for t in self.search_edit.text().split('%') if t.strip()]
        if not self.lista_modulos_data:
            self.lista_widget_modulos.addItem("Nenhum módulo guardado encontrado.")
            self.btn_importar.setEnabled(False)
            return
        for modulo_data in self.lista_modulos_data:
            nome = modulo_data.get('nome_modulo', '')
            desc = modulo_data.get('descricao_modulo', '')
            texto_mod = f"{self._normalize(nome)} {self._normalize(desc)}"
            if all(term in texto_mod for term in termos):
                item = QListWidgetItem(nome or 'Nome Desconhecido')
                item.setData(Qt.UserRole, modulo_data.get('id_modulo'))
                caminho_img = modulo_data.get('caminho_imagem_modulo')
                if caminho_img and os.path.exists(caminho_img):
                    icon = QIcon(QPixmap(caminho_img).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    item.setIcon(icon)
                else:
                    placeholder_icon = QPixmap(64, 64)
                    placeholder_icon.fill(Qt.lightGray)
                    item.setIcon(QIcon(placeholder_icon))
                self.lista_widget_modulos.addItem(item)
        if self.lista_widget_modulos.count() > 0:
            self.lista_widget_modulos.setCurrentRow(0)

    def carregar_lista_modulos(self):
        """Carrega todos os módulos do utilizador selecionado."""
        self.lista_widget_modulos.clear()
        self.lista_modulos_data = modulo_gestao_modulos_db.obter_todos_modulos(self.utilizador_selecionado)
        self.aplicar_filtro_lista_modulos()

    def on_tab_changed(self, index):
        """Muda o utilizador das abas."""
        if 0 <= index < len(self.utilizadores):
            self.utilizador_selecionado = self.utilizadores[index]
            self.carregar_lista_modulos()

    def on_modulo_selecionado_changed(self, current_item, previous_item):
        """Atualiza detalhes quando seleciona módulo."""
        if not current_item:
            self.lbl_nome_modulo_detalhe.setText("Nome: (Nenhum módulo selecionado)")
            self.txt_descricao_modulo_detalhe.clear()
            self.lbl_imagem_modulo_preview.clear()
            self.lbl_imagem_modulo_preview.setText("Sem imagem")
            self.btn_importar.setEnabled(False)
            self.selected_module_id = None
            self.tabela_resumo_pecas.setRowCount(0)
            return
        id_modulo_sel = current_item.data(Qt.UserRole)
        if id_modulo_sel is None:
            self.btn_importar.setEnabled(False)
            return
        modulo_data_sel = next((m for m in self.lista_modulos_data if m.get('id_modulo') == id_modulo_sel), None)
        if modulo_data_sel:
            self.selected_module_id = id_modulo_sel
            self.lbl_nome_modulo_detalhe.setText(f"Nome: {modulo_data_sel.get('nome_modulo', '')}")
            self.txt_descricao_modulo_detalhe.setText(modulo_data_sel.get('descricao_modulo', ''))
            caminho_img = modulo_data_sel.get('caminho_imagem_modulo')
            if caminho_img and os.path.exists(caminho_img):
                pixmap = QPixmap(caminho_img)
                self.lbl_imagem_modulo_preview.setPixmap(
                    pixmap.scaled(self.lbl_imagem_modulo_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.lbl_imagem_modulo_preview.setText("")
            else:
                self.lbl_imagem_modulo_preview.setPixmap(QPixmap())
                self.lbl_imagem_modulo_preview.setText("Sem imagem")
            self.btn_importar.setEnabled(True)
            # Carrega peças do módulo
            pecas_do_modulo_sel = modulo_gestao_modulos_db.obter_pecas_de_modulo(self.selected_module_id)
            self.tabela_resumo_pecas.setRowCount(len(pecas_do_modulo_sel))
            map_key_to_col_idx = {
                "ordem_peca": 0,
                "descricao_livre_peca": 1,
                "def_peca_peca": 2,
                "qt_und_peca": 3,
                "comp_peca": 4,
                "larg_peca": 5,
                "esp_peca": 6,
                "mat_default_peca": 7,
                "tab_default_peca": 8
            }
            for i, peca in enumerate(pecas_do_modulo_sel):
                for key_dado_peca, col_idx in map_key_to_col_idx.items():
                    if col_idx < self.tabela_resumo_pecas.columnCount():
                        self.tabela_resumo_pecas.setItem(i, col_idx, QTableWidgetItem(str(peca.get(key_dado_peca, ""))))
            self.tabela_resumo_pecas.resizeColumnsToContents()
            if self.tabela_resumo_pecas.columnCount() > 2:
                self.tabela_resumo_pecas.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        else:
            self.on_modulo_selecionado_changed(None, None)

    def confirmar_importacao(self):
        """Confirma a importação do módulo selecionado."""
        if self.selected_module_id is not None:
            self.accept()
        else:
            QMessageBox.warning(self, "Nenhum Módulo Selecionado", "Por favor, selecione um módulo da lista para importar.")

    def get_selected_module_id(self):
        """Retorna o id do módulo selecionado para a função chamadora."""
        return self.selected_module_id

# Para testar isoladamente
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    modulo_gestao_modulos_db.criar_tabelas_modulos()
    dialog = DialogoImportarModulo()
    if dialog.exec_() == QDialog.Accepted:
        print(f"ID do Módulo selecionado para importar: {dialog.get_selected_module_id()}")
    else:
        print("Importação cancelada.")
    sys.exit(app.exec_())