"""
dialogo_descricoes.py
=====================
Diálogo simples para gerir e selecionar descrições pré-definidas
associadas ao campo ``plainTextEdit_descricao_orcamento``.
O utilizador pode pesquisar, adicionar, editar ou eliminar linhas
bem como selecionar múltiplas descrições para inserir no item atual.

Funções para gerir descrições pré-definidas usadas no separador 'Orcamento' e no campo
plainTextEdit_descricao_orcamento.

Este módulo fornece:
  - Carregamento e gravação de descrições num ficheiro JSON.
  - Um diálogo (DescricaoPredefinidaDialog) onde o utilizador pode
    filtrar, adicionar, editar e remover descrições.
  - Configuração de um menu de contexto no plainTextEdit que abre
    o diálogo e insere as linhas seleccionadas no texto do item.
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLineEdit, QAbstractItemView, QInputDialog, QWidgetAction, QMenu)
from PyQt5.QtCore import Qt
import os

FILE_PATH = os.path.join(os.path.dirname(__file__), "descricoes_predefinidas.txt")


def carregar_descricoes():
    """Lê o ficheiro de descrições e retorna uma lista de strings."""
    if not os.path.exists(FILE_PATH):
        return []
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        linhas = [l.strip() for l in f.readlines() if l.strip()]
    return linhas


def guardar_descricoes(descricoes):
    """Guarda a lista de descrições no ficheiro associado."""
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        for linha in descricoes:
            f.write(linha.strip() + "\n")


class DialogoDescricoes(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Descrições pré-definidas")
        self.resize(400, 500)
        # Adiciona botão de ajuda (?) e tooltip resumida
        self.setWindowFlags(self.windowFlags() | Qt.WindowContextHelpButtonHint)
        self.setToolTip(
            "Gerir descrições pré-definidas: pesquise, adicione, edite ou elimine "
            "linhas e selecione várias para inserir no orçamento."
        )
        layout = QVBoxLayout(self)
        self.edit_pesquisa = QLineEdit(self)
        self.edit_pesquisa.setPlaceholderText("Pesquisar (use % para separar palavras)")
        layout.addWidget(self.edit_pesquisa)

        self.lista = QListWidget(self)
        self.lista.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.lista)

        botoes = QHBoxLayout()
        self.btn_add = QPushButton("Adicionar", self)
        self.btn_edit = QPushButton("Editar", self)
        self.btn_del = QPushButton("Eliminar", self)
        botoes.addWidget(self.btn_add)
        botoes.addWidget(self.btn_edit)
        botoes.addWidget(self.btn_del)
        layout.addLayout(botoes)

        botoes2 = QHBoxLayout()
        self.btn_ok = QPushButton("Inserir", self)
        self.btn_cancel = QPushButton("Cancelar", self)
        botoes2.addWidget(self.btn_ok)
        botoes2.addWidget(self.btn_cancel)
        layout.addLayout(botoes2)

        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_add.clicked.connect(self.adicionar)
        self.btn_edit.clicked.connect(self.editar)
        self.btn_del.clicked.connect(self.eliminar)
        self.edit_pesquisa.textChanged.connect(self.aplicar_filtro)

        self.descricoes = carregar_descricoes()
        self._carregar_lista()

    def _carregar_lista(self):
        self.lista.clear()
        for texto in self.descricoes:
            item = QListWidgetItem(texto)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.lista.addItem(item)

    def aplicar_filtro(self, texto):
        termos = [t.lower() for t in texto.split('%') if t.strip()]
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            visivel = all(term in item.text().lower() for term in termos)
            item.setHidden(not visivel)

    def adicionar(self):
        dlg = QInputDialog(self)
        dlg.setWindowTitle("Adicionar descrição")
        dlg.setLabelText("Texto:")
        dlg.resize(500, 200)
        if dlg.exec_() == QDialog.Accepted:
            texto = dlg.textValue()
            if texto.strip():
                self.descricoes.append(texto.strip())
                guardar_descricoes(self.descricoes)
                self._carregar_lista()

    def editar(self):
        itens = self.lista.selectedItems()
        if not itens:
            return
        item = itens[0]
        dlg = QInputDialog(self)
        dlg.setWindowTitle("Editar descrição")
        dlg.setLabelText("Texto:")
        dlg.resize(500, 200)
        dlg.setTextValue(item.text())
        if dlg.exec_() == QDialog.Accepted:
            texto = dlg.textValue()
            if texto.strip():
                idx = self.lista.row(item)
                self.descricoes[idx] = texto.strip()
                guardar_descricoes(self.descricoes)
                self._carregar_lista()

    def eliminar(self):
        itens = self.lista.selectedItems()
        if not itens:
            return
        for item in itens:
            self.descricoes.remove(item.text())
        guardar_descricoes(self.descricoes)
        self._carregar_lista()

    def descricoes_selecionadas(self):
        selecionadas = []
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            if item.checkState() == Qt.Checked:
                selecionadas.append(item.text())
        return selecionadas


def exibir_menu_descricoes(widget, _pos=None):
    """Abre o diálogo de descrições e insere as linhas selecionadas."""
    dialog = DialogoDescricoes(widget)
    if dialog.exec_() == QDialog.Accepted:
        linhas = dialog.descricoes_selecionadas()
        if linhas:
            texto_atual = widget.toPlainText().rstrip()
            for linha in linhas:
                texto_atual += "\n\t- " + linha
            widget.setPlainText(texto_atual)


def configurar_menu_descricoes(widget):
    """Associa o menu de descrições pré-definidas ao widget dado."""
    widget.setContextMenuPolicy(Qt.CustomContextMenu)
    widget.customContextMenuRequested.connect(lambda pos: exibir_menu_descricoes(widget, pos))