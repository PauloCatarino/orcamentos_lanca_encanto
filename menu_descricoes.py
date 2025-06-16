# menu_descricoes.py
"""
Funções para gerir descrições pré-definidas usadas no separador 'Orcamento' e no campo
plainTextEdit_descricao_orcamento.

Este módulo fornece:
  - Carregamento e gravação de descrições num ficheiro JSON.
  - Um diálogo (DescricaoPredefinidaDialog) onde o utilizador pode
    filtrar, adicionar, editar e remover descrições.
  - Configuração de um menu de contexto no plainTextEdit que abre
    o diálogo e insere as linhas seleccionadas no texto do item.
"""

import json
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,QPushButton, QLineEdit, QDialogButtonBox, QMenu, QAction, QInputDialog, QMessageBox)
from PyQt5.QtCore import Qt

BASE_PATH = os.path.join("Base_Dados", "descricoes_orcamento.json")


def carregar_descricoes():
    """Lê o ficheiro JSON de descrições ou devolve lista vazia."""
    if not os.path.exists(BASE_PATH):
        return []
    try:
        with open(BASE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def guardar_descricoes(desc_list):
    """Guarda a lista de descrições no ficheiro JSON."""
    try:
        with open(BASE_PATH, "w", encoding="utf-8") as f:
            json.dump(desc_list, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[ERRO] Ao guardar descrições: {e}")


class DescricaoPredefinidaDialog(QDialog):
    """Diálogo para selecionar e gerir descrições pré-definidas."""

    def __init__(self, descricoes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Descrições Pré-definidas")
        self.descricoes = descricoes[:]  # copia
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Pesquisar... use % para separar")
        self.search_edit.textChanged.connect(self._filtrar_lista)
        layout.addWidget(self.search_edit)

        self.lista = QListWidget()
        self.lista.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(self.lista)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Adicionar")
        self.btn_edit = QPushButton("Editar")
        self.btn_del = QPushButton("Eliminar")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_del)
        layout.addLayout(btn_layout)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(bb)

        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        self.btn_add.clicked.connect(self._adicionar)
        self.btn_edit.clicked.connect(self._editar)
        self.btn_del.clicked.connect(self._eliminar)

        self._recarregar_lista()

    def _recarregar_lista(self):
        self.lista.clear()
        for texto in self.descricoes:
            item = QListWidgetItem(texto)
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Unchecked)
            self.lista.addItem(item)
        self._filtrar_lista(self.search_edit.text())

    def _filtrar_lista(self, texto):
        partes = [p.strip().lower() for p in texto.split('%') if p.strip()]
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            item_text = item.text().lower()
            item.setHidden(not all(p in item_text for p in partes))

    def _adicionar(self):
        text, ok = QInputDialog.getText(self, "Adicionar Descrição", "Texto:")
        if ok and text.strip():
            self.descricoes.append(text.strip())
            self._recarregar_lista()

    def _editar(self):
        items = self.lista.selectedItems()
        if not items:
            QMessageBox.warning(self, "Editar", "Selecione uma descrição para editar.")
            return
        item = items[0]
        text, ok = QInputDialog.getText(self, "Editar Descrição", "Texto:", text=item.text())
        if ok and text.strip():
            idx = self.lista.row(item)
            self.descricoes[idx] = text.strip()
            self._recarregar_lista()

    def _eliminar(self):
        items = self.lista.selectedItems()
        if not items:
            QMessageBox.warning(self, "Eliminar", "Selecione uma descrição para eliminar.")
            return
        for item in items:
            self.descricoes.pop(self.lista.row(item))
        self._recarregar_lista()

    def descricoes_selecionadas(self):
        return [self.lista.item(i).text() for i in range(self.lista.count()) if self.lista.item(i).checkState() == Qt.Checked]


def exibir_menu_descricoes(ui, pos):
    descricoes = carregar_descricoes()
    dlg = DescricaoPredefinidaDialog(descricoes, ui.plainTextEdit_descricao_orcamento)
    if dlg.exec_() == QDialog.Accepted:
        selecionadas = dlg.descricoes_selecionadas()
        if selecionadas:
            texto_atual = ui.plainTextEdit_descricao_orcamento.toPlainText().rstrip()
            for linha in selecionadas:
                texto_atual += "\n\t- " + linha
            ui.plainTextEdit_descricao_orcamento.setPlainText(texto_atual)
        guardar_descricoes(dlg.descricoes)


def configurar_menu_descricoes(ui):
    widget = ui.plainTextEdit_descricao_orcamento
    widget.setContextMenuPolicy(Qt.CustomContextMenu)
    widget.customContextMenuRequested.connect(lambda pos: exibir_menu_descricoes(ui, pos))