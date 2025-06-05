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

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
                             QListWidgetItem, QTextEdit, QPushButton, QSplitter,
                             QMessageBox, QAbstractItemView, QWidget, QHeaderView, # Adicionado QHeaderView
                             QTableWidget, QTableWidgetItem) # Adicionado QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon
import os
import modulo_gestao_modulos_db # Para buscar os módulos

class DialogoImportarModulo(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Importar Módulo Guardado")
        self.setMinimumSize(800, 600)

        self.selected_module_id = None
        self.lista_modulos_data = [] # Para armazenar os dados completos dos módulos

        # --- Layout Principal (Vertical) ---
        main_layout = QVBoxLayout(self)

        # --- Splitter para dividir a lista e os detalhes ---
        splitter = QSplitter(Qt.Horizontal)

        # --- Lado Esquerdo: Lista de Módulos ---
        lista_group_widget = QWidget() # Usar QWidget como container para o layout da lista
        lista_layout = QVBoxLayout(lista_group_widget)
        self.lbl_lista_modulos = QLabel("Módulos Guardados:")
        self.lista_widget_modulos = QListWidget()
        self.lista_widget_modulos.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lista_widget_modulos.setIconSize(QSize(48, 48)) # Tamanho para ícones/thumbnails
        lista_layout.addWidget(self.lbl_lista_modulos)
        lista_layout.addWidget(self.lista_widget_modulos)
        splitter.addWidget(lista_group_widget)

        # --- Lado Direito: Detalhes do Módulo Selecionado ---
        detalhes_widget_container = QWidget()
        layout_detalhes = QVBoxLayout(detalhes_widget_container)
        
        # Layout para Nome e Imagem (Horizontal)
        nome_img_layout = QHBoxLayout()
        
        # Layout para Nome e Descrição (Vertical, à esquerda da imagem)
        nome_desc_layout = QVBoxLayout()
        self.lbl_nome_modulo_detalhe = QLabel("Nome: (Nenhum módulo selecionado)")
        self.lbl_nome_modulo_detalhe.setStyleSheet("font-weight: bold; font-size: 12pt;") # Aumentar um pouco
        nome_desc_layout.addWidget(self.lbl_nome_modulo_detalhe)
        
        self.lbl_descricao_titulo = QLabel("Descrição:")
        nome_desc_layout.addWidget(self.lbl_descricao_titulo)
        self.txt_descricao_modulo_detalhe = QTextEdit()
        self.txt_descricao_modulo_detalhe.setReadOnly(True)
        self.txt_descricao_modulo_detalhe.setMaximumHeight(80) # Limitar altura da descrição
        nome_desc_layout.addWidget(self.txt_descricao_modulo_detalhe)
        
        nome_img_layout.addLayout(nome_desc_layout, 2) # Dar mais espaço para nome/descrição

        # Imagem
        self.lbl_imagem_modulo_preview = QLabel()
        self.lbl_imagem_modulo_preview.setAlignment(Qt.AlignCenter)
        self.lbl_imagem_modulo_preview.setFixedSize(150, 150) # Ajustar tamanho se necessário
        self.lbl_imagem_modulo_preview.setStyleSheet("QLabel { border: 1px solid #ccc; background-color: #f0f0f0; }")
        nome_img_layout.addWidget(self.lbl_imagem_modulo_preview, 1, Qt.AlignCenter) # Menos espaço para imagem

        layout_detalhes.addLayout(nome_img_layout)

        # --- NOVA TABELA DE RESUMO DAS PEÇAS DO MÓDULO ---
        self.lbl_pecas_resumo_importar = QLabel("Peças Contidas no Módulo Selecionado:")
        layout_detalhes.addWidget(self.lbl_pecas_resumo_importar)
        
        self.tabela_resumo_pecas_importar = QTableWidget()
        # SUAS COLUNAS DESEJADAS:
        self.colunas_resumo_importar_definidas = ["Ordem", "Descricao_Livre" , "Def_Peca", "QT_und", "Comp", "Larg", "Esp", "Mat_Default", "Tab_Default"]
        self.tabela_resumo_pecas_importar.setColumnCount(len(self.colunas_resumo_importar_definidas))
        self.tabela_resumo_pecas_importar.setHorizontalHeaderLabels(self.colunas_resumo_importar_definidas)
        self.tabela_resumo_pecas_importar.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela_resumo_pecas_importar.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela_resumo_pecas_importar.setAlternatingRowColors(True)
        self.tabela_resumo_pecas_importar.verticalHeader().setVisible(False)
        # Ajuste inicial das colunas
        self.tabela_resumo_pecas_importar.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        if "Def_Peca" in self.colunas_resumo_importar_definidas:
            idx_def_peca = self.colunas_resumo_importar_definidas.index("Def_Peca")
            self.tabela_resumo_pecas_importar.horizontalHeader().setSectionResizeMode(idx_def_peca, QHeaderView.Stretch)
        if "Descricao_Livre" in self.colunas_resumo_importar_definidas:
            idx_desc_livre = self.colunas_resumo_importar_definidas.index("Descricao_Livre")
            self.tabela_resumo_pecas_importar.horizontalHeader().setSectionResizeMode(idx_desc_livre, QHeaderView.Stretch)

        layout_detalhes.addWidget(self.tabela_resumo_pecas_importar)
        # --- FIM DA NOVA TABELA ---
        
        splitter.addWidget(detalhes_widget_container)
        splitter.setSizes([250, 550]) # Ajustar proporções

        main_layout.addWidget(splitter)

        # --- Botões de Ação ---
        botoes_layout = QHBoxLayout()
        botoes_layout.addStretch()
        self.btn_importar = QPushButton("Importar Módulo")
        self.btn_importar.setEnabled(False)
        self.btn_cancelar = QPushButton("Cancelar")
        botoes_layout.addWidget(self.btn_importar)
        botoes_layout.addWidget(self.btn_cancelar)
        main_layout.addLayout(botoes_layout)

        # --- Conexões ---
        self.lista_widget_modulos.currentItemChanged.connect(self.on_modulo_selecionado_changed)
        self.btn_importar.clicked.connect(self.confirmar_importacao)
        self.btn_cancelar.clicked.connect(self.reject)

        # --- Carregar Módulos ---
        self.carregar_lista_modulos()

    def carregar_lista_modulos(self):
        self.lista_widget_modulos.clear()
        self.lista_modulos_data = modulo_gestao_modulos_db.obter_todos_modulos()

        if not self.lista_modulos_data:
            self.lista_widget_modulos.addItem("Nenhum módulo guardado encontrado.")
            self.btn_importar.setEnabled(False)
            return

        for modulo_data in self.lista_modulos_data:
            nome = modulo_data.get('nome_modulo', 'Nome Desconhecido')
            item = QListWidgetItem(nome)
            item.setData(Qt.UserRole, modulo_data.get('id_modulo')) # Armazena o ID do módulo no item
            
            # Adicionar thumbnail se existir imagem
            caminho_img = modulo_data.get('caminho_imagem_modulo')
            if caminho_img and os.path.exists(caminho_img):
                icon = QIcon(QPixmap(caminho_img).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                item.setIcon(icon)
            else: # Ícone placeholder se não houver imagem
                # Você pode criar um QPixmap simples ou usar um ícone padrão
                placeholder_icon = QPixmap(64,64)
                placeholder_icon.fill(Qt.lightGray)
                item.setIcon(QIcon(placeholder_icon))

            self.lista_widget_modulos.addItem(item)
        
        if self.lista_widget_modulos.count() > 0:
            self.lista_widget_modulos.setCurrentRow(0) # Selecionar o primeiro item por padrão

    def on_modulo_selecionado_changed(self, current_item, previous_item):
        if not current_item:
            self.lbl_nome_modulo_detalhe.setText("Nome: (Nenhum módulo selecionado)")
            self.txt_descricao_modulo_detalhe.clear()
            self.lbl_imagem_modulo_preview.clear()
            self.lbl_imagem_modulo_preview.setText("Sem imagem")
            self.btn_importar.setEnabled(False)
            self.selected_module_id = None
            return

        id_modulo_sel = current_item.data(Qt.UserRole)
        if id_modulo_sel is None: return

        # Encontrar os dados completos do módulo na nossa lista interna
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
            else:
                self.lbl_imagem_modulo_preview.clear()
                self.lbl_imagem_modulo_preview.setText("Sem imagem")
            
            self.btn_importar.setEnabled(True)

            # --- CARREGAR E PREENCHER A TABELA DE RESUMO DAS PEÇAS ---
            pecas_do_modulo_sel = modulo_gestao_modulos_db.obter_pecas_de_modulo(self.selected_module_id)
            self.tabela_resumo_pecas_importar.setRowCount(len(pecas_do_modulo_sel))
            # Mapeamento da chave do dicionário da peça para o índice da coluna na tabela de resumo
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
                # Adicione "und_peca" e "grupo_peca" aqui se também os adicionou a self.colunas_resumo_importar_definidas
            }

            for i, peca_data in enumerate(pecas_do_modulo_sel):
                for key_dado_peca, col_idx in map_key_to_col_idx.items():
                    # Verifica se o índice da coluna é válido para a tabela de resumo definida
                    if col_idx < self.tabela_resumo_pecas_importar.columnCount():
                        self.tabela_resumo_pecas_importar.setItem(i, col_idx, QTableWidgetItem(str(peca_data.get(key_dado_peca, ""))))
            
            self.tabela_resumo_pecas_importar.resizeColumnsToContents()
            if "Def_Peca" in self.colunas_resumo_importar_definidas:
                 idx_def_peca = self.colunas_resumo_importar_definidas.index("Def_Peca")
                 self.tabela_resumo_pecas_importar.horizontalHeader().setSectionResizeMode(idx_def_peca, QHeaderView.Stretch)
            if "Descricao_Livre" in self.colunas_resumo_importar_definidas:
                 idx_desc_livre = self.colunas_resumo_importar_definidas.index("Descricao_Livre")
                 self.tabela_resumo_pecas_importar.horizontalHeader().setSectionResizeMode(idx_desc_livre, QHeaderView.Stretch)
            # --- FIM DO PREENCHIMENTO DA TABELA DE RESUMO ---
        else:
            # Limpar se não encontrar os dados (improvável se a lista estiver correta)
            self.on_modulo_selecionado_changed(None, None)


    def confirmar_importacao(self):
        if self.selected_module_id is not None:
            print(f"[DialogoImportar] Módulo ID {self.selected_module_id} selecionado para importação.")
            self.accept() # Fecha o diálogo e sinaliza sucesso
        else:
            QMessageBox.warning(self, "Nenhum Módulo Selecionado", "Por favor, selecione um módulo da lista para importar.")
    
    def get_selected_module_id(self):
        return self.selected_module_id

# Para testar o diálogo isoladamente (opcional)
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    # Criar tabelas se não existirem (para teste)
    modulo_gestao_modulos_db.criar_tabelas_modulos() 
    
    # Adicionar alguns módulos de teste (opcional, se a BD estiver vazia)
    # modulo_gestao_modulos_db.salvar_novo_modulo_com_pecas("Modulo Teste 1", "Desc Teste 1", None, [{"def_peca_peca": "P1"}])
    # modulo_gestao_modulos_db.salvar_novo_modulo_com_pecas("Modulo Teste 2", "Desc Teste 2", None, [{"def_peca_peca": "P2"}])

    dialog = DialogoImportarModulo()
    if dialog.exec_() == QDialog.Accepted:
        print(f"ID do Módulo selecionado para importar: {dialog.get_selected_module_id()}")
    else:
        print("Importação cancelada.")
    sys.exit(app.exec_())