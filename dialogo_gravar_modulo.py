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
        self.setMinimumSize(700, 550) # Tamanho mínimo inicial

        self.pecas_para_gravar = pecas_selecionadas
        self.modulo_id_para_atualizar = modulo_existente_id # Usado se estiver a editar um módulo
        self.caminho_imagem_selecionada = img_path_existente

        # --- Layout Principal ---
        main_layout = QVBoxLayout(self)

        # Abas de utilizadores
        self.utilizadores = ["Paulo", "Catia", "Andreia"]
        self.tab_utilizador = QTabWidget()
        for u in self.utilizadores:
            self.tab_utilizador.addTab(QWidget(), u)
        if utilizador_atual in self.utilizadores:
            self.tab_utilizador.setCurrentIndex(self.utilizadores.index(utilizador_atual))
        self.utilizador_selecionado = utilizador_atual
        self.tab_utilizador.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tab_utilizador)

        # --- Seção de Informações do Módulo ---
        info_layout = QHBoxLayout()

        # Layout para Nome, Descrição e Imagem
        form_layout = QVBoxLayout()
        
        # Nome do Módulo
        self.lbl_nome = QLabel("Nome do Módulo:")
        self.txt_nome_modulo = QLineEdit(nome_mod_existente)
        self.txt_nome_modulo.setPlaceholderText("Ex: Módulo Base Cozinha 700mm")
        form_layout.addWidget(self.lbl_nome)
        form_layout.addWidget(self.txt_nome_modulo)
        # Novo botão para escolher um módulo existente
        self.btn_selecionar_modulo = QPushButton("Selecionar Módulo Existente...")
        form_layout.addWidget(self.btn_selecionar_modulo)

        # Descrição do Módulo
        self.lbl_descricao = QLabel("Descrição (Opcional):")
        self.txt_descricao_modulo = QTextEdit(desc_mod_existente)
        self.txt_descricao_modulo.setFixedHeight(80)
        self.txt_descricao_modulo.setPlaceholderText("Detalhes sobre o módulo, utilização, etc.")
        form_layout.addWidget(self.lbl_descricao)
        form_layout.addWidget(self.txt_descricao_modulo)
        
        info_layout.addLayout(form_layout, 2) # Proporção 2 para o formulário

        # --- Seção da Imagem ---
        img_preview_layout = QVBoxLayout()
        img_preview_layout.setAlignment(Qt.AlignCenter)

        self.lbl_imagem_preview = QLabel("Sem imagem")
        self.lbl_imagem_preview.setAlignment(Qt.AlignCenter)
        self.lbl_imagem_preview.setFixedSize(150, 150) # Tamanho fixo para preview
        self.lbl_imagem_preview.setStyleSheet("QLabel { border: 1px solid gray; background-color: #f0f0f0; }")
        self.btn_escolher_imagem = QPushButton("Escolher Imagem...")
        self.btn_remover_imagem = QPushButton("Remover Imagem")
        
        img_preview_layout.addWidget(self.lbl_imagem_preview)
        img_preview_layout.addWidget(self.btn_escolher_imagem)
        img_preview_layout.addWidget(self.btn_remover_imagem)

        info_layout.addLayout(img_preview_layout, 1) # Proporção 1 para a imagem

        main_layout.addLayout(info_layout)

        # --- Tabela de Resumo das Peças (Opcional, mas informativo) ---
        self.lbl_pecas_resumo = QLabel(f"Resumo das {len(self.pecas_para_gravar)} Peças a Serem Gravadas:")
        main_layout.addWidget(self.lbl_pecas_resumo)
        
        self.tabela_resumo_pecas = QTableWidget()
        # Definir as colunas desejadas
        colunas_resumo = ["Ordem", "Descricao_Livre", "Def_Peca", "QT_und", "Comp", "Larg", "Mat_Default"]
        self.tabela_resumo_pecas.setColumnCount(len(colunas_resumo))
        self.tabela_resumo_pecas.setHorizontalHeaderLabels(colunas_resumo)
        self.tabela_resumo_pecas.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela_resumo_pecas.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela_resumo_pecas.verticalHeader().setVisible(False)
        
        self.preencher_tabela_resumo() # Chamada ao método atualizado
        main_layout.addWidget(self.tabela_resumo_pecas)

        # --- Botões de Ação ---
        botoes_layout = QHBoxLayout()
        self.btn_gravar = QPushButton("Gravar Módulo")
        self.btn_cancelar = QPushButton("Cancelar")
        botoes_layout.addStretch()
        botoes_layout.addWidget(self.btn_gravar)
        botoes_layout.addWidget(self.btn_cancelar)
        main_layout.addLayout(botoes_layout)

        # --- Conexões ---
        self.btn_escolher_imagem.clicked.connect(self.escolher_imagem)
        self.btn_remover_imagem.clicked.connect(self.remover_imagem)
        self.btn_selecionar_modulo.clicked.connect(self.selecionar_modulo_existente)
        self.btn_gravar.clicked.connect(self.confirmar_e_gravar_modulo)
        self.btn_cancelar.clicked.connect(self.reject)

        # Carregar imagem existente se houver
        if self.caminho_imagem_selecionada and os.path.exists(self.caminho_imagem_selecionada):
            self.carregar_preview_imagem(self.caminho_imagem_selecionada)
        else:
            self.caminho_imagem_selecionada = "" # Garantir que está vazio se o caminho for inválido

    def on_tab_changed(self, index):
        if 0 <= index < len(self.utilizadores):
            self.utilizador_selecionado = self.utilizadores[index]

    def preencher_tabela_resumo(self):
        self.tabela_resumo_pecas.setRowCount(len(self.pecas_para_gravar))
        for i, peca in enumerate(self.pecas_para_gravar):
            # Mapear os dados da peça para as colunas da tabela de resumo
            self.tabela_resumo_pecas.setItem(i, 0, QTableWidgetItem(str(peca.get("ordem_peca", i))))
            self.tabela_resumo_pecas.setItem(i, 1, QTableWidgetItem(peca.get("descricao_livre_peca", "")))
            self.tabela_resumo_pecas.setItem(i, 2, QTableWidgetItem(peca.get("def_peca_peca", "")))
            self.tabela_resumo_pecas.setItem(i, 3, QTableWidgetItem(peca.get("qt_und_peca", "")))
            self.tabela_resumo_pecas.setItem(i, 4, QTableWidgetItem(peca.get("comp_peca", "")))
            self.tabela_resumo_pecas.setItem(i, 5, QTableWidgetItem(peca.get("larg_peca", "")))
            self.tabela_resumo_pecas.setItem(i, 6, QTableWidgetItem(peca.get("mat_default_peca", "")))
            # Adicionar mais colunas aqui se necessário, lembrando de ajustar o setColumnCount
            
        self.tabela_resumo_pecas.resizeColumnsToContents()
        # Ajustar a largura da coluna Def_Peca para ocupar mais espaço se necessário
        if self.tabela_resumo_pecas.columnCount() > 2:
             self.tabela_resumo_pecas.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

    def escolher_imagem(self):
        ficheiro, _ = QFileDialog.getOpenFileName(self, "Escolher Imagem para o Módulo", "",
                                                  "Imagens (*.png *.jpg *.jpeg *.bmp)")
        if ficheiro:
            self.carregar_preview_imagem(ficheiro)

    def carregar_preview_imagem(self, caminho_ficheiro):
        pixmap = QPixmap(caminho_ficheiro)
        if pixmap.isNull():
            self.lbl_imagem_preview.setText("Erro Imagem")
            self.caminho_imagem_selecionada = ""
        else:
            self.lbl_imagem_preview.setPixmap(pixmap.scaled(self.lbl_imagem_preview.size(),
                                                            Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.caminho_imagem_selecionada = caminho_ficheiro

    def remover_imagem(self):
        self.lbl_imagem_preview.setText("Sem imagem")
        self.lbl_imagem_preview.setPixmap(QPixmap()) # Limpa o pixmap
        self.caminho_imagem_selecionada = ""

    def selecionar_modulo_existente(self):
        dialog = DialogoImportarModulo(
            utilizador_atual=self.utilizador_selecionado,
            parent=self,
        )
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
        nome_modulo = self.txt_nome_modulo.text().strip()
        descricao_modulo = self.txt_descricao_modulo.toPlainText().strip() # QTextEdit usa toPlainText()
        caminho_imagem = self.caminho_imagem_selecionada

        if not nome_modulo:
            QMessageBox.warning(self, "Nome Inválido", "Por favor, insira um nome para o módulo.")
            return

        # Verificar se o nome já existe (esta função será implementada em modulo_gestao_modulos_db.py)
        id_modulo_existente = modulo_gestao_modulos_db.verificar_nome_modulo_existe(nome_modulo, self.utilizador_selecionado)

        if id_modulo_existente is not None and (self.modulo_id_para_atualizar is None or self.modulo_id_para_atualizar != id_modulo_existente):
            resposta = QMessageBox.question(self, "Nome Existente",
                                            f"Já existe um módulo com o nome '{nome_modulo}'.\n"
                                            "Deseja substituí-lo?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resposta == QMessageBox.No:
                return
            else:
                # Se vai substituir, preparamos para atualizar
                self.modulo_id_para_atualizar = id_modulo_existente
        
        # Lógica de gravação/atualização (estas funções serão implementadas em modulo_gestao_modulos_db.py)
        sucesso = False
        if self.modulo_id_para_atualizar is not None:
            # Atualizar módulo existente
            print(f"Atualizando módulo ID: {self.modulo_id_para_atualizar}")
            sucesso = modulo_gestao_modulos_db.atualizar_modulo_existente_com_pecas(
                self.modulo_id_para_atualizar,
                nome_modulo,
                descricao_modulo,
                caminho_imagem,
                self.pecas_para_gravar,
                self.utilizador_selecionado,
            )
        else:
            # Salvar novo módulo
            print("Salvando novo módulo...")
            id_novo_modulo = modulo_gestao_modulos_db.salvar_novo_modulo_com_pecas(
                nome_modulo,
                descricao_modulo,
                caminho_imagem,
                self.pecas_para_gravar,
                self.utilizador_selecionado,
            )
            if id_novo_modulo is not None and id_novo_modulo > 0 : # Verifica se retornou um ID válido
                sucesso = True
            else:
                sucesso = False


        if sucesso:
            QMessageBox.information(self, "Sucesso", f"Módulo '{nome_modulo}' gravado com sucesso!")
            self.accept() # Fecha o diálogo com sucesso
        else:
            QMessageBox.critical(self, "Erro ao Gravar", f"Não foi possível gravar o módulo '{nome_modulo}'. Verifique o log para detalhes.")
            # Não fechar o diálogo em caso de erro, para o utilizador tentar novamente ou corrigir.

# Para testar o diálogo isoladamente (opcional)
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    # Simular peças selecionadas para teste
    pecas_teste = [
        {"ordem_peca": 0, "def_peca_peca": "LATERAL [2222]", "mat_default_peca": "Mat_Aglomerado_19", "tab_default_peca": "Tab_Material_11", "qt_und_peca": "2", "comp_peca": "H", "larg_peca": "P", "esp_peca": "19", "und_peca": "M2", "grupo_peca": "caixote"},
        {"ordem_peca": 1, "def_peca_peca": "PRATELEIRA [1111]", "mat_default_peca": "Mat_Aglomerado_19", "tab_default_peca": "Tab_Material_11", "qt_und_peca": "1", "comp_peca": "L-38", "larg_peca": "P-20", "esp_peca": "19", "und_peca": "M2", "grupo_peca": "caixote"}
    ]
    
    # Simular criação de tabelas de módulos antes de abrir o diálogo
    modulo_gestao_modulos_db.criar_tabelas_modulos()

    dialog = DialogoGravarModulo(pecas_teste)
    dialog.show()
    sys.exit(app.exec_())