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

from PyQt5.QtWidgets import (QDialog,QVBoxLayout,QListWidget,QListWidgetItem, QDialogButtonBox, QLabel, QLineEdit, QHBoxLayout, QPushButton, QMessageBox, QInputDialog, QTextEdit)
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
        self.descricoes = {}
        for nome, desc in (modelos.items() if isinstance(modelos, dict) else [(m, "") for m in modelos]):
            item = QListWidgetItem(nome)
            item.setData(Qt.UserRole, nome)
            self.descricoes[nome] = desc
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.lista.addItem(item)
        self.lista.itemChanged.connect(self._apenas_um_checked)
        self.lista.currentItemChanged.connect(self._mostrar_descricao)
        layout.addWidget(self.lista)
        self.desc_label = QLabel("")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)
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

    def _mostrar_descricao(self, item):
            """Atualiza a descrição exibida conforme o item selecionado."""
            if not item:
                self.desc_label.setText("")
                return
            nome = item.data(Qt.UserRole)
            self.desc_label.setText(self.descricoes.get(nome, ""))

    def modelo_escolhido(self):
        for i in range(self.lista.count()):
            it = self.lista.item(i)
            if it.checkState() == Qt.Checked:
                return it.data(Qt.UserRole)
        return None

class GerirNomesDialog(QDialog):
    """Permite visualizar, eliminar e escolher um nome para guardar."""
    def __init__(self, tabela, nomes_desc, parent=None):
        super().__init__(parent)
        self.tabela = tabela
        self.setWindowTitle(f"Guardar Dados Gerais  -> {tabela.upper()}")
        self.resize(400, 300)  # <-- ESTA LINHA AUMENTA A JANELA
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Modelos existentes:"))
        self.lista = QListWidget()
        self.nomes_desc = nomes_desc
        for nome, desc in nomes_desc.items():
            item = QListWidgetItem(f"{nome} - {desc}")
            item.setData(Qt.UserRole, nome)
            self.lista.addItem(item)
        lay.addWidget(self.lista)
        form = QHBoxLayout()
        form.addWidget(QLabel("Nome:"))
        self.edit = QLineEdit()
        form.addWidget(self.edit)
        lay.addLayout(form)
        lay_desc = QVBoxLayout()
        lay_desc.addWidget(QLabel("Descrição:"))
        self.edit_desc = QTextEdit()
        self.edit_desc.setFixedHeight(60)
        lay_desc.addWidget(self.edit_desc)
        lay.addLayout(lay_desc)
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
        self.lista.itemClicked.connect(self._preencher_campos)
        self.nome_eliminado = None
        # Dicionários para rastrear alterações feitas pelo utilizador.
        # A inicialização aqui garante que existam mesmo se métodos forem
        # chamados de forma inesperada.
        self.nomes_editados = {}
        self.descricoes_editadas = {}

    def _preencher_campos(self, item):
        nome = item.data(Qt.UserRole)
        self.edit.setText(nome)
        self.edit_desc.setPlainText(self.nomes_desc.get(nome, ""))

    def _eliminar(self):
        item = self.lista.currentItem()
        if not item:
            QMessageBox.warning(self, "Aviso", "Selecione um nome para eliminar.")
            return
        self.nome_eliminado = item.data(Qt.UserRole)
        row = self.lista.row(item)
        self.lista.takeItem(row)
        try:
            from dados_gerais_manager import apagar_registros_por_nome
            apagar_registros_por_nome(self.tabela, self.nome_eliminado)
        except Exception as e:
            print(f"Erro ao eliminar '{self.nome_eliminado}' da base de dados: {e}")
        self.nomes_desc.pop(self.nome_eliminado, None)

    def _editar(self):
        item = self.lista.currentItem()
        if not item:
            QMessageBox.warning(self, "Aviso", "Selecione um nome para editar.")
            return
        texto_atual = item.data(Qt.UserRole)
        novo, ok = QInputDialog.getText(self, "Editar Nome", "Novo nome:", text=texto_atual)
        if ok and novo.strip():
            self.nomes_editados[texto_atual] = novo.strip()
            desc = self.nomes_desc.pop(texto_atual, "")
            self.nomes_desc[novo.strip()] = desc
            item.setText(f"{novo.strip()} - {desc}")
            item.setData(Qt.UserRole, novo.strip())

    def obter_nome(self):
        nome = self.edit.text().strip()
        desc = self.edit_desc.toPlainText().strip()

        # Garante que dicionários de estado existam mesmo se a instância
        # tiver sido criada com uma versão antiga da classe
        if not hasattr(self, "nomes_editados"):
            self.nomes_editados = {}
        if not hasattr(self, "descricoes_editadas"):
            self.descricoes_editadas = {}

        if nome:
            if self.nomes_desc.get(nome, "") != desc:
                self.descricoes_editadas[nome] = desc
            self.nomes_desc[nome] = desc
        return (
            nome,
            desc,
            getattr(self, "nome_eliminado", None),
            self.nomes_editados,
            self.descricoes_editadas,
        )