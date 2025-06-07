"""
dialogs_modelos.py

Este script define diálogos em PyQt5 para o software de orçamentos de mobiliário.
Inclui:
- SelecaoModeloDialog: janela para o utilizador selecionar um único modelo de uma lista (com checkboxes).
- GerirNomesDialog: janela para visualizar, editar ou eliminar nomes/modelos guardados na base de dados.
As janelas são utilizadas para facilitar operações como importar acabamentos, selecionar referências, ou gerir listas de modelos/nomes.

Última alteração: [07-06-2025]
Autor: Paulo Catarino
"""

from PyQt5.QtWidgets import (QDialog,QVBoxLayout,QListWidget,QListWidgetItem, QDialogButtonBox, QLabel, QLineEdit, QHBoxLayout, QPushButton, QMessageBox, QInputDialog)
from PyQt5.QtCore import Qt

class SelecaoModeloDialog(QDialog):
    """Diálogo simples com checkboxes para escolher um único modelo."""
    def __init__(self, modelos, titulo="Selecionar Modelo", parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(400, 300)  # <-- ESTA LINHA AUMENTA A JANELA
        layout = QVBoxLayout(self)
        self.lista = QListWidget()
        self.lista.setMinimumWidth(350)  # Garante largura suficiente para os textos
        for nome in modelos:
            item = QListWidgetItem(nome)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.lista.addItem(item)
        self.lista.itemChanged.connect(self._apenas_um_checked)
        layout.addWidget(self.lista)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _apenas_um_checked(self, item):
        if item.checkState() == Qt.Checked:
            for i in range(self.lista.count()):
                it = self.lista.item(i)
                if it is not item:
                    it.setCheckState(Qt.Unchecked)

    def modelo_escolhido(self):
        for i in range(self.lista.count()):
            it = self.lista.item(i)
            if it.checkState() == Qt.Checked:
                return it.text()
        return None

class GerirNomesDialog(QDialog):
    """Permite visualizar, eliminar e escolher um nome para guardar."""
    def __init__(self, tabela, nomes, parent=None):
        super().__init__(parent)
        self.tabela = tabela
        self.setWindowTitle(f"Guardar Dados Gerais  -> {tabela.upper()}")
        self.resize(400, 300)  # <-- ESTA LINHA AUMENTA A JANELA
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Modelos existentes:"))
        self.lista = QListWidget()
        self.lista.addItems(nomes)
        lay.addWidget(self.lista)
        form = QHBoxLayout()
        form.addWidget(QLabel("Nome:"))
        self.edit = QLineEdit()
        form.addWidget(self.edit)
        lay.addLayout(form)
        btns = QHBoxLayout()
        self.btn_del = QPushButton("Eliminar Selecionado")
        self.btn_del.clicked.connect(self._eliminar)
        btns.addWidget(self.btn_del)
        self.btn_edit = QPushButton("Editar Nome")
        self.btn_edit.clicked.connect(self._editar)
        btns.addWidget(self.btn_edit)
        btns.addStretch()
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        btns.addWidget(self.buttons)
        lay.addLayout(btns)
        self.lista.itemClicked.connect(lambda it: self.edit.setText(it.text()))
        self.nome_eliminado = None
        self.nomes_editados = {}

    def _eliminar(self):
        item = self.lista.currentItem()
        if not item:
            QMessageBox.warning(self, "Aviso", "Selecione um nome para eliminar.")
            return
        self.nome_eliminado = item.text()
        row = self.lista.row(item)
        self.lista.takeItem(row)
        try:
            from dados_gerais_manager import apagar_registros_por_nome
            apagar_registros_por_nome(self.tabela, self.nome_eliminado)
        except Exception as e:
            print(f"Erro ao eliminar '{self.nome_eliminado}' da base de dados: {e}")

    def _editar(self):
        item = self.lista.currentItem()
        if not item:
            QMessageBox.warning(self, "Aviso", "Selecione um nome para editar.")
            return
        texto_atual = item.text()
        novo, ok = QInputDialog.getText(self, "Editar Nome", "Novo nome:", text=texto_atual)
        if ok and novo.strip():
            self.nomes_editados[texto_atual] = novo.strip()
            item.setText(novo.strip())

    def obter_nome(self):
        return self.edit.text().strip(), self.nome_eliminado, self.nomes_editados