# dialogo_gerir_modulos.py
# -*- coding: utf-8 -*-

"""
Módulo: dialogo_gerir_modulos.py

Objetivo Principal:
-------------------
Fornecer uma interface gráfica (QDialog) centralizada para que o utilizador possa
visualizar, editar e eliminar os "Módulos Guardados" existentes na base de dados.

Principais Funcionalidades:
---------------------------
1.  **Listagem de Módulos:** Apresenta uma lista de todos os módulos guardados,
    mostrando nome e, opcionalmente, um ícone/thumbnail.
2.  **Visualização de Detalhes:** Ao selecionar um módulo na lista, exibe:
    - Nome completo do módulo.
    - Descrição detalhada.
    - Pré-visualização da imagem associada.
    - Uma tabela com todas as peças contidas no módulo selecionado e os seus dados principais
      (Ordem, Def_Peca, QT_und, Comp, Larg, Esp, Mat_Default, Tab_Default, etc.).
3.  **Edição de Módulo:**
    - Permite ao utilizador selecionar um módulo e clicar no botão "Editar Módulo".
    - Reutiliza o `DialogoGravarModulo`, pré-preenchendo-o com os dados do módulo
      selecionado (incluindo as suas peças). O utilizador pode então alterar nome,
      descrição, imagem e (implicitamente, ao regravar) a lista de peças.
4.  **Eliminação de Módulo:**
    - Permite ao utilizador selecionar um módulo e clicar no botão "Eliminar Módulo".
    - Pede confirmação antes de proceder com a eliminação.
    - Chama a função apropriada em `modulo_gestao_modulos_db.py` para remover o módulo
      e as suas peças associadas da base de dados.
    - Atualiza a lista de módulos após a eliminação.
5.  **Navegação e Interface Intuitiva:** Utiliza um `QSplitter` para permitir ao utilizador
    ajustar o espaço entre a lista de módulos e a área de detalhes.

Interação com Outros Módulos Chave:
-----------------------------------
-   Instanciado e chamado a partir do `main.py` (função `on_gerir_modulos_clicked`).
-   Utiliza extensivamente `modulo_gestao_modulos_db.py` para:
    - `obter_todos_modulos()`: Para popular a lista inicial de módulos.
    - `obter_pecas_de_modulo()`: Para exibir as peças do módulo selecionado.
    - `eliminar_modulo_por_id()`: Para a funcionalidade de eliminação.
-   Utiliza (instancia) o `DialogoGravarModulo` para a funcionalidade de edição,
    passando-lhe os dados do módulo a ser editado.
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
                             QListWidgetItem, QTextEdit, QPushButton, QSplitter,
                             QMessageBox, QAbstractItemView, QWidget, QHeaderView,
                             QTableWidget, QTableWidgetItem) # Adicionar QHeaderView
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon
import os
import modulo_gestao_modulos_db # Para buscar, editar e eliminar os módulos
from dialogo_gravar_modulo import DialogoGravarModulo # Para reutilizar para edição

class DialogoGerirModulos(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gerir Módulos Guardados")
        self.setMinimumSize(800, 600)

        self.selected_module_id = None
        self.lista_modulos_data = []

        # --- Layout Principal ---
        main_layout = QVBoxLayout(self)
        top_layout = QHBoxLayout() # Para lista de módulos e detalhes

        # --- Lado Esquerdo: Lista de Módulos ---
        lista_group = QWidget()
        lista_layout = QVBoxLayout(lista_group)
        self.lbl_lista_modulos = QLabel("Módulos Guardados:")
        self.lista_widget_modulos = QListWidget()
        self.lista_widget_modulos.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lista_widget_modulos.setIconSize(QSize(48, 48)) # Ícones um pouco menores aqui
        lista_layout.addWidget(self.lbl_lista_modulos)
        lista_layout.addWidget(self.lista_widget_modulos)
        
        top_layout.addWidget(lista_group, 1) # Proporção 1

        # --- Lado Direito: Detalhes do Módulo e Peças ---
        detalhes_group = QWidget()
        detalhes_layout = QVBoxLayout(detalhes_group)

        # Detalhes do Módulo (Nome, Imagem, Descrição)
        info_modulo_layout = QHBoxLayout()
        
        info_text_layout = QVBoxLayout()
        self.lbl_nome_modulo_detalhe = QLabel("Nome: (Nenhum módulo selecionado)")
        self.lbl_nome_modulo_detalhe.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.txt_descricao_modulo_detalhe = QTextEdit()
        self.txt_descricao_modulo_detalhe.setReadOnly(True)
        self.txt_descricao_modulo_detalhe.setFixedHeight(80)
        info_text_layout.addWidget(self.lbl_nome_modulo_detalhe)
        info_text_layout.addWidget(QLabel("Descrição:"))
        info_text_layout.addWidget(self.txt_descricao_modulo_detalhe)
        
        self.lbl_imagem_modulo_preview = QLabel()
        self.lbl_imagem_modulo_preview.setAlignment(Qt.AlignCenter)
        self.lbl_imagem_modulo_preview.setFixedSize(120, 120)
        self.lbl_imagem_modulo_preview.setStyleSheet("QLabel { border: 1px solid #ccc; background-color: #f0f0f0; }")
        
        info_modulo_layout.addLayout(info_text_layout, 2)
        info_modulo_layout.addWidget(self.lbl_imagem_modulo_preview, 1, Qt.AlignCenter)
        
        detalhes_layout.addLayout(info_modulo_layout)

        # Tabela de Peças do Módulo Selecionado
        self.lbl_pecas_modulo = QLabel("Peças do Módulo Selecionado:")
        self.tabela_pecas_modulo = QTableWidget()
        colunas_pecas = ["Ordem", "Def_Peca", "QT_und", "Comp", "Larg", "Esp", "Mat_Default", "Tab_Default", "Grupo", "UND"]
        self.tabela_pecas_modulo.setColumnCount(len(colunas_pecas))
        self.tabela_pecas_modulo.setHorizontalHeaderLabels(colunas_pecas)
        self.tabela_pecas_modulo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela_pecas_modulo.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela_pecas_modulo.verticalHeader().setVisible(False)
        self.tabela_pecas_modulo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabela_pecas_modulo.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch) # Def_Peca
        
        detalhes_layout.addWidget(self.lbl_pecas_modulo)
        detalhes_layout.addWidget(self.tabela_pecas_modulo)
        
        top_layout.addWidget(detalhes_group, 2) # Proporção 2 para detalhes

        main_layout.addLayout(top_layout)

        # --- Botões de Ação ---
        botoes_layout = QHBoxLayout()
        self.btn_editar_modulo = QPushButton("Editar Módulo")
        self.btn_eliminar_modulo = QPushButton("Eliminar Módulo")
        self.btn_fechar = QPushButton("Fechar")
        
        botoes_layout.addWidget(self.btn_editar_modulo)
        botoes_layout.addWidget(self.btn_eliminar_modulo)
        botoes_layout.addStretch()
        botoes_layout.addWidget(self.btn_fechar)
        main_layout.addLayout(botoes_layout)

        # --- Conexões ---
        self.lista_widget_modulos.currentItemChanged.connect(self.on_modulo_selecionado_changed)
        self.btn_editar_modulo.clicked.connect(self.editar_modulo_selecionado)
        self.btn_eliminar_modulo.clicked.connect(self.eliminar_modulo_selecionado)
        self.btn_fechar.clicked.connect(self.accept)

        self.btn_editar_modulo.setEnabled(False)
        self.btn_eliminar_modulo.setEnabled(False)

        # --- Carregar Módulos ---
        self.carregar_lista_modulos()

    def carregar_lista_modulos(self):
        self.lista_widget_modulos.clear()
        self.lista_modulos_data = modulo_gestao_modulos_db.obter_todos_modulos()

        if not self.lista_modulos_data:
            self.lista_widget_modulos.addItem("Nenhum módulo guardado encontrado.")
            self.btn_editar_modulo.setEnabled(False)
            self.btn_eliminar_modulo.setEnabled(False)
            return

        for modulo_data in self.lista_modulos_data:
            nome = modulo_data.get('nome_modulo', 'Nome Desconhecido')
            item = QListWidgetItem(nome)
            item.setData(Qt.UserRole, modulo_data.get('id_modulo'))
            caminho_img = modulo_data.get('caminho_imagem_modulo')
            if caminho_img and os.path.exists(caminho_img):
                icon = QIcon(QPixmap(caminho_img).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                item.setIcon(icon)
            self.lista_widget_modulos.addItem(item)
        
        if self.lista_widget_modulos.count() > 0:
            self.lista_widget_modulos.setCurrentRow(0)

    def on_modulo_selecionado_changed(self, current_item, previous_item):
        self.tabela_pecas_modulo.setRowCount(0) # Limpar tabela de peças
        if not current_item:
            self.lbl_nome_modulo_detalhe.setText("Nome: (Nenhum módulo selecionado)")
            self.txt_descricao_modulo_detalhe.clear()
            self.lbl_imagem_modulo_preview.clear()
            self.lbl_imagem_modulo_preview.setText("Sem imagem")
            self.btn_editar_modulo.setEnabled(False)
            self.btn_eliminar_modulo.setEnabled(False)
            self.selected_module_id = None
            return

        id_modulo_sel = current_item.data(Qt.UserRole)
        if id_modulo_sel is None: return

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
            
            self.btn_editar_modulo.setEnabled(True)
            self.btn_eliminar_modulo.setEnabled(True)
            
            # Carregar peças do módulo selecionado
            pecas_do_modulo = modulo_gestao_modulos_db.obter_pecas_de_modulo(self.selected_module_id)
            self.tabela_pecas_modulo.setRowCount(len(pecas_do_modulo))
            for i, peca in enumerate(pecas_do_modulo):
                self.tabela_pecas_modulo.setItem(i, 0, QTableWidgetItem(str(peca.get("ordem_peca", i))))
                self.tabela_pecas_modulo.setItem(i, 1, QTableWidgetItem(peca.get("def_peca_peca", "")))
                self.tabela_pecas_modulo.setItem(i, 2, QTableWidgetItem(peca.get("qt_und_peca", "")))
                self.tabela_pecas_modulo.setItem(i, 3, QTableWidgetItem(peca.get("comp_peca", "")))
                self.tabela_pecas_modulo.setItem(i, 4, QTableWidgetItem(peca.get("larg_peca", "")))
                self.tabela_pecas_modulo.setItem(i, 5, QTableWidgetItem(peca.get("esp_peca", "")))
                self.tabela_pecas_modulo.setItem(i, 6, QTableWidgetItem(peca.get("mat_default_peca", "")))
                self.tabela_pecas_modulo.setItem(i, 7, QTableWidgetItem(peca.get("tab_default_peca", "")))
                self.tabela_pecas_modulo.setItem(i, 8, QTableWidgetItem(peca.get("grupo_peca", "")))
                self.tabela_pecas_modulo.setItem(i, 9, QTableWidgetItem(peca.get("und_peca", "")))
            self.tabela_pecas_modulo.resizeColumnsToContents()
            if self.tabela_pecas_modulo.columnCount() > 1:
                self.tabela_pecas_modulo.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)


    def editar_modulo_selecionado(self):
        if self.selected_module_id is None:
            QMessageBox.warning(self, "Nenhum Módulo", "Selecione um módulo para editar.")
            return

        modulo_data_sel = next((m for m in self.lista_modulos_data if m.get('id_modulo') == self.selected_module_id), None)
        if not modulo_data_sel: return

        pecas_do_modulo = modulo_gestao_modulos_db.obter_pecas_de_modulo(self.selected_module_id)
        
        dialog_editar = DialogoGravarModulo(
            pecas_selecionadas=pecas_do_modulo, # As peças a serem editadas/re-salvas
            modulo_existente_id=self.selected_module_id,
            nome_mod_existente=modulo_data_sel.get('nome_modulo', ''),
            desc_mod_existente=modulo_data_sel.get('descricao_modulo', ''),
            img_path_existente=modulo_data_sel.get('caminho_imagem_modulo', ''),
            parent=self
        )
        dialog_editar.setWindowTitle(f"Editar Módulo: {modulo_data_sel.get('nome_modulo', '')}")
        if dialog_editar.exec_() == QDialog.Accepted:
            print(f"[INFO DialogoGerir] Módulo ID {self.selected_module_id} editado com sucesso.")
            self.carregar_lista_modulos() # Recarregar a lista para refletir mudanças
            # Tentar manter a seleção ou selecionar o item editado
            for i in range(self.lista_widget_modulos.count()):
                item = self.lista_widget_modulos.item(i)
                if item.data(Qt.UserRole) == self.selected_module_id:
                    self.lista_widget_modulos.setCurrentItem(item)
                    break
        else:
            print(f"[INFO DialogoGerir] Edição do módulo ID {self.selected_module_id} cancelada.")


    def eliminar_modulo_selecionado(self):
        if self.selected_module_id is None:
            QMessageBox.warning(self, "Nenhum Módulo", "Selecione um módulo para eliminar.")
            return

        modulo_data_sel = next((m for m in self.lista_modulos_data if m.get('nome_modulo') == self.lista_widget_modulos.currentItem().text()), None)
        if not modulo_data_sel: return

        nome_modulo = modulo_data_sel.get('nome_modulo', 'Desconhecido')
        resposta = QMessageBox.question(self, "Confirmar Eliminação",
                                        f"Tem a certeza que deseja eliminar o módulo '{nome_modulo}' e todas as suas peças?\nEsta ação não pode ser desfeita.",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resposta == QMessageBox.Yes:
            sucesso = modulo_gestao_modulos_db.eliminar_modulo_por_id(self.selected_module_id)
            if sucesso:
                QMessageBox.information(self, "Módulo Eliminado", f"O módulo '{nome_modulo}' foi eliminado com sucesso.")
                self.carregar_lista_modulos() # Recarrega a lista
                # Limpar detalhes se não houver mais módulos ou nenhum selecionado
                if self.lista_widget_modulos.count() == 0:
                    self.on_modulo_selecionado_changed(None, None)
                else:
                    self.lista_widget_modulos.setCurrentRow(0) # Seleciona o primeiro
            else:
                QMessageBox.critical(self, "Erro ao Eliminar", f"Não foi possível eliminar o módulo '{nome_modulo}'.")

# Para testar o diálogo de gestão isoladamente
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    # Garanta que as tabelas existem para o teste
    modulo_gestao_modulos_db.criar_tabelas_modulos() 

    dialog = DialogoGerirModulos()
    dialog.show()
    sys.exit(app.exec_())