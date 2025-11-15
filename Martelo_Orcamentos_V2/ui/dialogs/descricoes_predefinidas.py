from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services import descricoes_predefinidas as svc_descricoes


HELP_TEXT = (
    "<b>Descrição rápida</b><br>"
    "• Pesquise usando % como separador (ex.: \"gaveta%led\").<br>"
    "• Adicione, edite ou elimine descrições usando os botões inferiores.<br>"
    "• Use as setas ▲/▼ para reorganizar a ordem apresentada.<br>"
    "• Marque as caixas das linhas que pretende inserir no orçamento e clique em Inserir.<br>"
    "• Cada linha pode ser do tipo '-' (texto normal em itálico) ou '*' (destaque verde)."
)


@dataclass
class DescricaoTemplate:
    id: int
    texto: str
    tipo: str


class _DescricaoEditorDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, *, titulo: str, texto: str = "", tipo: str = "-"):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(420, 150)
        layout = QtWidgets.QVBoxLayout(self)

        self.edit_texto = QtWidgets.QLineEdit(self)
        self.edit_texto.setPlaceholderText("Descrição")
        self.edit_texto.setText(texto)

        self.combo_tipo = QtWidgets.QComboBox(self)
        self.combo_tipo.addItem("- Marcador", "-")
        self.combo_tipo.addItem("* Destaque verde", "*")
        if tipo.strip() == "*":
            self.combo_tipo.setCurrentIndex(1)

        layout.addWidget(QtWidgets.QLabel("Texto da descrição:", self))
        layout.addWidget(self.edit_texto)
        layout.addWidget(QtWidgets.QLabel("Tipo:", self))
        layout.addWidget(self.combo_tipo)

        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self
        )
        layout.addWidget(btn_box)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

    def text_value(self) -> str:
        return self.edit_texto.text().strip()

    def tipo_value(self) -> str:
        return self.combo_tipo.currentData() or "-"

    def accept(self) -> None:
        if not self.text_value():
            QtWidgets.QMessageBox.warning(self, "Descrições", "Informe o texto da descrição.")
            return
        super().accept()


class DescricoesPredefinidasDialog(QtWidgets.QDialog):
    def __init__(self, *, parent=None, user_id: Optional[int] = None):
        super().__init__(parent)
        self._session = SessionLocal()
        self._user_id = user_id
        self._rows: List[DescricaoTemplate] = []
        self._help_text = HELP_TEXT

        self.setWindowTitle("Descrições pré-definidas")
        self.resize(520, 520)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowContextHelpButtonHint)
        self.setToolTip("Gerir descrições pré-definidas do utilizador.")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.edit_search = QtWidgets.QLineEdit(self)
        self.edit_search.setPlaceholderText("Pesquisar (use % para separar palavras)")
        layout.addWidget(self.edit_search)

        self.list = QtWidgets.QListWidget(self)
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.list, 1)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Adicionar", self)
        self.btn_edit = QtWidgets.QPushButton("Editar", self)
        self.btn_remove = QtWidgets.QPushButton("Eliminar", self)
        self.btn_up = QtWidgets.QPushButton("▲", self)
        self.btn_down = QtWidgets.QPushButton("▼", self)
        for btn in (self.btn_add, self.btn_edit, self.btn_remove, self.btn_up, self.btn_down):
            btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_up)
        btn_row.addWidget(self.btn_down)
        layout.addLayout(btn_row)

        btn_row2 = QtWidgets.QHBoxLayout()
        self.btn_insert = QtWidgets.QPushButton("Inserir", self)
        self.btn_insert.setDefault(True)
        self.btn_cancel = QtWidgets.QPushButton("Cancelar", self)
        btn_row2.addWidget(self.btn_insert)
        btn_row2.addWidget(self.btn_cancel)
        layout.addLayout(btn_row2)

        self.edit_search.textChanged.connect(self._apply_filter)
        self.btn_add.clicked.connect(self._on_add)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_remove.clicked.connect(self._on_remove)
        self.btn_up.clicked.connect(lambda: self._move_selected("up"))
        self.btn_down.clicked.connect(lambda: self._move_selected("down"))
        self.btn_insert.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self._load_rows()

    def event(self, event: QtCore.QEvent) -> bool:  # type: ignore[override]
        if event.type() == QtCore.QEvent.Type.HelpRequest:
            QtWidgets.QMessageBox.information(self, "Ajuda - Descrições", HELP_TEXT)
            return True
        return super().event(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        try:
            self._session.close()
        finally:
            super().closeEvent(event)

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    def _load_rows(self) -> None:
        if not self._user_id:
            self._rows = []
            self.list.clear()
            return
        try:
            rows = svc_descricoes.list_descricoes(self._session, self._user_id)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Descrições", f"Falha ao carregar descrições: {exc}")
            rows = []
        self._rows = [DescricaoTemplate(id=row.id, texto=row.texto, tipo=row.tipo or "-") for row in rows]
        self._populate_list()
        self._apply_filter(self.edit_search.text())

    def _populate_list(self) -> None:
        self.list.clear()
        for row in self._rows:
            item = QtWidgets.QListWidgetItem(f"{row.tipo or '-'} {row.texto}")
            item.setFlags(
                item.flags()
                | QtCore.Qt.ItemIsUserCheckable
                | QtCore.Qt.ItemIsEnabled
                | QtCore.Qt.ItemIsSelectable
            )
            item.setCheckState(QtCore.Qt.Unchecked)
            if (row.tipo or "-") == "*":
                font = item.font()
                font.setItalic(True)
                item.setFont(font)
                item.setForeground(QtGui.QBrush(QtGui.QColor("#0a5c0a")))
            item.setData(QtCore.Qt.UserRole, row)
            self.list.addItem(item)

    def _apply_filter(self, text: str) -> None:
        termos = [t.strip().lower() for t in (text or "").split("%") if t.strip()]
        for i in range(self.list.count()):
            item = self.list.item(i)
            if not termos:
                item.setHidden(False)
                continue
            linha = (item.text() or "").lower()
            item.setHidden(not all(term in linha for term in termos))

    # ------------------------------------------------------------------
    # CRUD handlers
    # ------------------------------------------------------------------
    def _on_add(self) -> None:
        if not self._user_id:
            QtWidgets.QMessageBox.warning(self, "Descrições", "Utilizador não definido.")
            return
        dlg = _DescricaoEditorDialog(self, titulo="Adicionar descrição")
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        try:
            svc_descricoes.create_descricao(self._session, self._user_id, dlg.text_value(), dlg.tipo_value())
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            QtWidgets.QMessageBox.critical(self, "Descrições", f"Falha ao adicionar: {exc}")
            return
        self._load_rows()

    def _on_edit(self) -> None:
        row = self._current_row()
        if not row:
            return
        dlg = _DescricaoEditorDialog(self, titulo="Editar descrição", texto=row.texto, tipo=row.tipo)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        try:
            svc_descricoes.update_descricao(self._session, row.id, self._user_id, dlg.text_value(), dlg.tipo_value())
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            QtWidgets.QMessageBox.critical(self, "Descrições", f"Falha ao editar: {exc}")
            return
        self._load_rows()
        self._select_by_id(row.id)

    def _on_remove(self) -> None:
        selected = self.list.selectedItems()
        if not selected:
            return
        ids = [item.data(QtCore.Qt.UserRole).id for item in selected if item.data(QtCore.Qt.UserRole)]
        if not ids:
            return
        if QtWidgets.QMessageBox.question(
            self,
            "Descrições",
            "Eliminar descrições selecionadas?",
        ) != QtWidgets.QMessageBox.Yes:
            return
        try:
            svc_descricoes.delete_descricoes(self._session, self._user_id, ids)
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            QtWidgets.QMessageBox.critical(self, "Descrições", f"Falha ao eliminar: {exc}")
            return
        self._load_rows()

    def _move_selected(self, direction: str) -> None:
        row = self._current_row()
        if not row:
            return
        try:
            changed = svc_descricoes.move_descricao(self._session, row.id, self._user_id, direction)
            if changed:
                self._session.commit()
            else:
                self._session.rollback()
                return
        except Exception as exc:
            self._session.rollback()
            QtWidgets.QMessageBox.critical(self, "Descrições", f"Falha ao mover: {exc}")
            return
        self._load_rows()
        self._select_by_id(row.id)

    def _current_row(self) -> Optional[DescricaoTemplate]:
        item = self.list.currentItem()
        if not item:
            return None
        data = item.data(QtCore.Qt.UserRole)
        return data

    def _select_by_id(self, row_id: int) -> None:
        for i in range(self.list.count()):
            item = self.list.item(i)
            row = item.data(QtCore.Qt.UserRole)
            if row and row.id == row_id:
                self.list.setCurrentRow(i)
                break

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def checked_entries(self) -> List[DescricaoTemplate]:
        entries: List[DescricaoTemplate] = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.checkState() != QtCore.Qt.Checked:
                continue
            data = item.data(QtCore.Qt.UserRole)
            if data:
                entries.append(data)
        return entries

    def selected_entries(self) -> List[DescricaoTemplate]:
        """Compatibilidade: devolve as entradas marcadas."""
        return self.checked_entries()
