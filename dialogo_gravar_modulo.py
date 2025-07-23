# dialogo_gravar_modulo.py
# -*- coding: utf-8 -*-

"""
Módulo: dialogo_gravar_modulo.py

Objetivo Principal:
-------------------
Fornecer uma interface gráfica (QDialog) para o utilizador gravar um conjunto de
peças selecionadas da 'tab_def_pecas' como um novo "Módulo Guardado" ou para
atualizar um módulo existente.

Principais Funcionalidades:
---------------------------
1.  Apresenta campos para o utilizador definir/editar:
    - Nome do Módulo (obrigatório e único).
    - Descrição do Módulo (opcional).
    - Imagem associada ao Módulo (opcional, com preview).
2.  Mostra uma tabela de resumo com as peças que serão incluídas no módulo.
3.  Ao gravar:
    - Valida o nome do módulo.
    - Verifica se um módulo com o mesmo nome já existe e pergunta ao utilizador se deseja
      substituí-lo.
    - Chama as funções apropriadas em `modulo_gestao_modulos_db.py` para:
        - `salvar_novo_modulo_com_pecas` (se for um novo módulo).
        - `atualizar_modulo_existente_com_pecas` (se for para substituir/editar).
4.  Permite ao utilizador selecionar um ficheiro de imagem do sistema.
5.  Oferece a opção de remover uma imagem associada.

Interação com Outros Módulos Chave:
-----------------------------------
-   Instanciado e chamado a partir do `main.py` (função `on_guardar_modulo_clicked` ou
    `on_editar_modulo_selecionado` do `DialogoGerirModulos`).
-   Recebe a lista de peças a serem gravadas do módulo chamador.
-   Utiliza `modulo_gestao_modulos_db.py` para verificar nomes e persistir os dados do módulo.
-   Pode ser reutilizado pelo `DialogoGerirModulos` para a funcionalidade de edição.
"""

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QSizePolicy,
    QHeaderView,
    QTabWidget,
    QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
import os
from configuracoes import obter_caminho_base_dados # Para obter o caminho_base_dados
import modulo_gestao_modulos_db # Importar as funções de BD do módulo de gestão de módulos
from dialogo_importar_modulo import DialogoImportarModulo

class DialogoGravarModulo(QDialog):
    def __init__(self, pecas_selecionadas, modulo_existente_id=None, nome_mod_existente="", desc_mod_existente="", img_path_existente="", utilizador_atual="Paulo", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gravar Módulo de Peças")
        self.setMinimumSize(1100, 700)
        self.pecas_para_gravar = pecas_selecionadas
        self.modulo_id_para_atualizar = modulo_existente_id
        self.caminho_imagem_selecionada = img_path_existente

        # --- Layout principal: sem margem e sem spacing ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)

        # --- Abas coladas ao topo ---
        self.utilizadores = ["Paulo", "Catia", "Andreia"]
        self.tab_utilizador = QTabWidget()
        self.tab_utilizador.setStyleSheet("""
            QTabBar::tab { min-width: 100px; height: 34px; font-size: 12pt; }
            QTabWidget::pane { border: 0px; margin-top: 0px; }
        """)
        for u in self.utilizadores:
            self.tab_utilizador.addTab(QWidget(), u)
        if utilizador_atual in self.utilizadores:
            self.tab_utilizador.setCurrentIndex(self.utilizadores.index(utilizador_atual))
        self.utilizador_selecionado = utilizador_atual
        self.tab_utilizador.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tab_utilizador, 0)  # stretch=0 para não "empurrar" nada para baixo

        # --- Conteúdo imediatamente abaixo das abas ---
        conteudo_widget = QWidget()
        conteudo_layout = QVBoxLayout(conteudo_widget)
        conteudo_layout.setContentsMargins(0, 0, 0, 0)  # Margem mínima no topo
        conteudo_layout.setSpacing(0)  # SEM espaçamento extra entre abas e info

        # --- Área de informações do módulo ---
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(14)

        # [restante código igual, sem alterações a partir daqui]

        # --- Formulário: Nome e Descrição ---
        form_layout = QVBoxLayout()
        form_layout.setSpacing(6)
        self.lbl_nome = QLabel("Nome do Módulo:")
        self.lbl_nome.setStyleSheet("margin-bottom:2px;")
        self.txt_nome_modulo = QLineEdit(nome_mod_existente)
        self.txt_nome_modulo.setPlaceholderText("Ex: Módulo Base Cozinha 700mm")
        form_layout.addWidget(self.lbl_nome)
        form_layout.addWidget(self.txt_nome_modulo)

        self.btn_selecionar_modulo = QPushButton("Selecionar Módulo Existente...")
        form_layout.addWidget(self.btn_selecionar_modulo)

        self.lbl_descricao = QLabel("Descrição (Opcional):")
        form_layout.addWidget(self.lbl_descricao)
        self.txt_descricao_modulo = QTextEdit(desc_mod_existente)
        self.txt_descricao_modulo.setFixedHeight(140)
        self.txt_descricao_modulo.setPlaceholderText("Detalhes sobre o módulo, utilização, etc.")
        self.txt_descricao_modulo.setStyleSheet("background: #fafaff; border-radius: 6px;")
        form_layout.addWidget(self.txt_descricao_modulo)

        form_layout.addStretch(1)
        info_layout.addLayout(form_layout, 3)

        img_layout = QVBoxLayout()
        img_layout.setContentsMargins(0, 0, 0, 0)
        img_layout.setAlignment(Qt.AlignTop)
        self.lbl_imagem_preview = QLabel("Sem imagem")
        self.lbl_imagem_preview.setAlignment(Qt.AlignCenter)
        self.lbl_imagem_preview.setFixedSize(400, 300)
        self.lbl_imagem_preview.setStyleSheet("""
            QLabel {
                border: 1px solid #888; border-radius: 8px;
                background-color: #f9f9f9;
                font-size: 11pt; color: #888;
            }
        """)
        img_layout.addWidget(self.lbl_imagem_preview)

        btn_img_layout = QHBoxLayout()
        self.btn_escolher_imagem = QPushButton("Escolher Imagem...")
        self.btn_remover_imagem = QPushButton("Remover Imagem")
        btn_img_layout.addWidget(self.btn_escolher_imagem)
        btn_img_layout.addWidget(self.btn_remover_imagem)
        img_layout.addLayout(btn_img_layout)
        info_layout.addLayout(img_layout, 2)

        conteudo_layout.addLayout(info_layout)

        # --- Tabela de resumo das peças ---
        self.lbl_pecas_resumo = QLabel(f"Resumo das {len(self.pecas_para_gravar)} Peças a Serem Gravadas:")
        self.lbl_pecas_resumo.setStyleSheet("font-weight: bold; margin-top: 8px; margin-bottom: 3px;")
        conteudo_layout.addWidget(self.lbl_pecas_resumo)

        self.colunas_resumo = ["Ordem", "Descricao_Livre", "Def_Peca", "QT_und", "Comp", "Larg", "Esp", "Mat_Default", "Tab_Default"]
        self.tabela_resumo_pecas = QTableWidget()
        self.tabela_resumo_pecas.setColumnCount(len(self.colunas_resumo))
        self.tabela_resumo_pecas.setHorizontalHeaderLabels(self.colunas_resumo)
        self.tabela_resumo_pecas.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela_resumo_pecas.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela_resumo_pecas.verticalHeader().setVisible(False)
        self.tabela_resumo_pecas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabela_resumo_pecas.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.preencher_tabela_resumo()
        conteudo_layout.addWidget(self.tabela_resumo_pecas)

        # --- Botões de ação ---
        botoes_layout = QHBoxLayout()
        botoes_layout.setContentsMargins(0, 6, 0, 0)
        self.btn_gravar = QPushButton("Gravar Módulo")
        self.btn_cancelar = QPushButton("Cancelar")
        botoes_layout.addStretch()
        botoes_layout.addWidget(self.btn_gravar)
        botoes_layout.addWidget(self.btn_cancelar)
        conteudo_layout.addLayout(botoes_layout)

        # --- Adiciona o widget de conteúdo principal ao main_layout (depois das abas) ---
        main_layout.addWidget(conteudo_widget, 1)  # stretch=1 para ocupar o resto da janela

        # --- Ligações e resto do código: mantém igual! ---

        self.btn_escolher_imagem.clicked.connect(self.escolher_imagem)
        self.btn_remover_imagem.clicked.connect(self.remover_imagem)
        self.btn_selecionar_modulo.clicked.connect(self.selecionar_modulo_existente)
        self.btn_gravar.clicked.connect(self.confirmar_e_gravar_modulo)
        self.btn_cancelar.clicked.connect(self.reject)

        if self.caminho_imagem_selecionada and os.path.exists(self.caminho_imagem_selecionada):
            self.carregar_preview_imagem(self.caminho_imagem_selecionada)
        else:
            self.caminho_imagem_selecionada = ""

    def on_tab_changed(self, index):
        if 0 <= index < len(self.utilizadores):
            self.utilizador_selecionado = self.utilizadores[index]

    def preencher_tabela_resumo(self):
        """Preenche a tabela de peças do módulo."""
        self.tabela_resumo_pecas.setRowCount(len(self.pecas_para_gravar))
        # Mapear as chaves dos dicionários das peças para as colunas certas
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
        for i, peca in enumerate(self.pecas_para_gravar):
            for key_dado_peca, col_idx in map_key_to_col_idx.items():
                if col_idx < self.tabela_resumo_pecas.columnCount():
                    self.tabela_resumo_pecas.setItem(i, col_idx, QTableWidgetItem(str(peca.get(key_dado_peca, ""))))
        self.tabela_resumo_pecas.resizeColumnsToContents()
        if self.tabela_resumo_pecas.columnCount() > 2:
            self.tabela_resumo_pecas.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

    def escolher_imagem(self):
        ficheiro, _ = QFileDialog.getOpenFileName(self, "Escolher Imagem para o Módulo", "",
                                                  "Imagens (*.png *.jpg *.jpeg *.bmp)")
        if ficheiro:
            self.carregar_preview_imagem(ficheiro)

    def carregar_preview_imagem(self, caminho_ficheiro):
        """Mostra o preview da imagem escolhida."""
        pixmap = QPixmap(caminho_ficheiro)
        if pixmap.isNull():
            self.lbl_imagem_preview.setText("Erro Imagem")
            self.caminho_imagem_selecionada = ""
        else:
            self.lbl_imagem_preview.setPixmap(
                pixmap.scaled(self.lbl_imagem_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.lbl_imagem_preview.setText("")
            self.caminho_imagem_selecionada = caminho_ficheiro

    def remover_imagem(self):
        """Remove a imagem do preview e do módulo."""
        self.lbl_imagem_preview.setText("Sem imagem")
        self.lbl_imagem_preview.setPixmap(QPixmap())
        self.caminho_imagem_selecionada = ""

    def selecionar_modulo_existente(self):
        """Abre o diálogo para escolher um módulo já existente."""
        dialog = DialogoImportarModulo(utilizador_atual=self.utilizador_selecionado, parent=self)
        dialog.setWindowTitle("Selecionar Módulo Existente")
        dialog.btn_importar.setText("Selecionar")
        if dialog.exec_() == QDialog.Accepted:
            mod_id = dialog.get_selected_module_id()
            dados = modulo_gestao_modulos_db.obter_modulo_por_id(mod_id)
            if dados:
                self.modulo_id_para_atualizar = mod_id
                self.txt_nome_modulo.setText(dados.get('nome_modulo', ''))
                self.txt_descricao_modulo.setPlainText(dados.get('descricao_modulo', ''))
                caminho_img = dados.get('caminho_imagem_modulo', '')
                if caminho_img and os.path.exists(caminho_img):
                    self.carregar_preview_imagem(caminho_img)
                else:
                    self.remover_imagem()

    def confirmar_e_gravar_modulo(self):
        """Valida e grava o módulo na base de dados."""
        nome_modulo = self.txt_nome_modulo.text().strip()
        descricao_modulo = self.txt_descricao_modulo.toPlainText().strip()
        caminho_imagem = self.caminho_imagem_selecionada

        if not nome_modulo:
            QMessageBox.warning(self, "Nome Inválido", "Por favor, insira um nome para o módulo.")
            return

        # Verifica duplicidade do nome
        id_modulo_existente = modulo_gestao_modulos_db.verificar_nome_modulo_existe(nome_modulo, self.utilizador_selecionado)
        if id_modulo_existente is not None and (self.modulo_id_para_atualizar is None or self.modulo_id_para_atualizar != id_modulo_existente):
            resposta = QMessageBox.question(self, "Nome Existente",
                                            f"Já existe um módulo com o nome '{nome_modulo}'.\nDeseja substituí-lo?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resposta == QMessageBox.No:
                return
            else:
                self.modulo_id_para_atualizar = id_modulo_existente

        # Grava ou atualiza o módulo
        sucesso = False
        if self.modulo_id_para_atualizar is not None:
            sucesso = modulo_gestao_modulos_db.atualizar_modulo_existente_com_pecas(
                self.modulo_id_para_atualizar, nome_modulo, descricao_modulo,
                caminho_imagem, self.pecas_para_gravar, self.utilizador_selecionado
            )
        else:
            id_novo_modulo = modulo_gestao_modulos_db.salvar_novo_modulo_com_pecas(
                nome_modulo, descricao_modulo, caminho_imagem,
                self.pecas_para_gravar, self.utilizador_selecionado
            )
            sucesso = id_novo_modulo is not None and id_novo_modulo > 0

        if sucesso:
            QMessageBox.information(self, "Sucesso", f"Módulo '{nome_modulo}' gravado com sucesso!")
            self.accept()
        else:
            QMessageBox.critical(self, "Erro ao Gravar", f"Não foi possível gravar o módulo '{nome_modulo}'. Verifique o log para detalhes.")

# Teste do diálogo isolado
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)

    pecas_teste = [
        {"ordem_peca": 0, "descricao_livre_peca": "Lateral esquerda", "def_peca_peca": "LATERAL [2222]", "qt_und_peca": "2", "comp_peca": "H", "larg_peca": "P", "esp_peca": "19", "mat_default_peca": "Mat_Aglomerado_19", "tab_default_peca": "Tab_Material_11"},
        {"ordem_peca": 1, "descricao_livre_peca": "Prateleira interna", "def_peca_peca": "PRATELEIRA [1111]", "qt_und_peca": "1", "comp_peca": "L-38", "larg_peca": "P-20", "esp_peca": "19", "mat_default_peca": "Mat_Aglomerado_19", "tab_default_peca": "Tab_Material_11"}
    ]
    modulo_gestao_modulos_db.criar_tabelas_modulos()

    dialog = DialogoGravarModulo(pecas_teste)
    dialog.show()
    sys.exit(app.exec_())