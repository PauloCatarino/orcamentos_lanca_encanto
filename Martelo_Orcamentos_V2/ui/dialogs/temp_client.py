from __future__ import annotations

from typing import Optional

from PySide6 import QtWidgets
from PySide6.QtCore import Qt

from Martelo_Orcamentos_V2.app.services.clientes_temporarios import (
    get_cliente_temporario_por_nome,
    list_clientes_temporarios,
    search_clientes_temporarios,
    upsert_cliente_temporario,
)
from Martelo_Orcamentos_V2.ui.models.qt_table import SimpleTableModel


class TempClientDialog(QtWidgets.QDialog):
    def __init__(self, *, parent=None, db):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle("Clientes Temporarios")
        self.resize(1300, 760)

        self._db = db
        self._current_id: Optional[int] = None
        self._result: Optional[dict] = None
        self._dup_match_id: Optional[int] = None

        layout = QtWidgets.QVBoxLayout(self)

        search_row = QtWidgets.QHBoxLayout()
        search_row.addWidget(QtWidgets.QLabel("Pesquisar:"), 0)
        self.ed_search = QtWidgets.QLineEdit()
        self.ed_search.setPlaceholderText("Pesquisar clientes temporarios (use % para multi-termos)")
        self.ed_search.textChanged.connect(self._on_search)
        btn_clear = QtWidgets.QToolButton()
        btn_clear.setText("X")
        btn_clear.clicked.connect(lambda: self.ed_search.setText(""))
        search_row.addWidget(self.ed_search, 1)
        search_row.addWidget(btn_clear)
        layout.addLayout(search_row)

        self.table = QtWidgets.QTableView(self)
        self.model = SimpleTableModel(
            rows=[],
            columns=[
                ("ID", "id"),
                ("Nome", "nome"),
                ("Simplex", "nome_simplex"),
                ("Morada", "morada"),
                ("Email", "email"),
                ("WEB", "web_page"),
                ("Telefone", "telefone"),
                ("Telemovel", "telemovel"),
                ("Num_PHC", "num_cliente_phc"),
                ("Info 1", "info_1"),
                ("Info 2", "info_2"),
            ],
        )
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        width_map = {
            "ID": 40,
            "Nome": 280,
            "Simplex": 280,
            "Morada": 220,
            "Email": 180,
            "WEB": 140,
            "Telefone": 120,
            "Telemovel": 120,
            "Num_PHC": 90,
            "Info 1": 140,
            "Info 2": 140,
        }
        for idx, col in enumerate(self.model.columns):
            spec = self.model._col_spec(col)
            label = spec.get("header", "")
            if label in width_map:
                header.resizeSection(idx, width_map[label])
        self.table.selectionModel().selectionChanged.connect(lambda *_: self._load_selected())
        self.table.doubleClicked.connect(lambda *_: self._use_selected())
        layout.addWidget(self.table, 1)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        self.ed_nome = QtWidgets.QLineEdit()
        self.ed_simplex = QtWidgets.QLineEdit()
        self.ed_morada = QtWidgets.QTextEdit()
        self.ed_morada.setFixedHeight(60)
        self.ed_email = QtWidgets.QLineEdit()
        self.ed_web = QtWidgets.QLineEdit()
        self.ed_tel = QtWidgets.QLineEdit()
        self.ed_tm = QtWidgets.QLineEdit()
        self.ed_phc = QtWidgets.QLineEdit()
        self.ed_info1 = QtWidgets.QTextEdit()
        self.ed_info1.setFixedHeight(60)
        self.ed_info2 = QtWidgets.QTextEdit()
        self.ed_info2.setFixedHeight(60)
        self.ed_notas = QtWidgets.QTextEdit()
        self.ed_notas.setFixedHeight(60)

        for w in (self.ed_nome, self.ed_simplex, self.ed_email, self.ed_web, self.ed_tel, self.ed_tm, self.ed_phc):
            w.setReadOnly(True)
        for w in (self.ed_morada, self.ed_info1, self.ed_info2, self.ed_notas):
            w.setReadOnly(True)

        form.addRow("Nome Cliente:", self.ed_nome)
        form.addRow("Nome Cliente Simplex:", self.ed_simplex)
        form.addRow("Num Cliente PHC:", self.ed_phc)
        form.addRow("Telefone:", self.ed_tel)
        form.addRow("Telemovel:", self.ed_tm)
        form.addRow("E-Mail:", self.ed_email)
        form.addRow("Pagina WEB:", self.ed_web)
        form.addRow("Morada:", self.ed_morada)
        layout.addLayout(form)

        self.lbl_dup = QtWidgets.QLabel("")
        self.lbl_dup.setStyleSheet("color:#b00020;")
        self.lbl_dup.setWordWrap(True)
        self.lbl_dup.setVisible(False)
        layout.addWidget(self.lbl_dup)

        actions = QtWidgets.QHBoxLayout()
        actions.addStretch(1)
        self.btn_use = QtWidgets.QPushButton("Selecionar Cliente")
        self.btn_cancel = QtWidgets.QPushButton("Cancelar")
        self.btn_use.clicked.connect(self._use_selected)
        self.btn_cancel.clicked.connect(self.reject)
        actions.addWidget(self.btn_use)
        actions.addWidget(self.btn_cancel)
        layout.addLayout(actions)

        self._refresh_table()

    def _on_search(self, text: str) -> None:
        self._refresh_table(text or "")

    def _refresh_table(self, query: str = "") -> None:
        try:
            rows = search_clientes_temporarios(self._db, query) if query else list_clientes_temporarios(self._db)
        except Exception:
            rows = []
        self.model.set_rows(rows)
        if rows:
            try:
                self.table.selectRow(0)
            except Exception:
                pass

    def _on_new(self) -> None:
        self._current_id = None
        for w in (self.ed_nome, self.ed_simplex, self.ed_email, self.ed_web, self.ed_tel, self.ed_tm, self.ed_phc):
            w.clear()
        self.ed_morada.clear()
        self.ed_info1.clear()
        self.ed_info2.clear()
        self.ed_notas.clear()
        self.ed_nome.setFocus()
        self._check_duplicate()

    def _selected_row(self):
        sel_model = self.table.selectionModel()
        if sel_model is not None:
            selected = sel_model.selectedRows()
            if selected:
                try:
                    return self.model.get_row(selected[0].row())
                except Exception:
                    return None
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        return self.model.get_row(idx.row())

    def _load_selected(self) -> None:
        row = self._selected_row()
        if not row:
            return
        self._current_id = row.id
        self.ed_nome.setText(row.nome or "")
        self.ed_simplex.setText(row.nome_simplex or "")
        self.ed_morada.setPlainText(row.morada or "")
        self.ed_email.setText(row.email or "")
        self.ed_web.setText(row.web_page or "")
        self.ed_tel.setText(row.telefone or "")
        self.ed_tm.setText(row.telemovel or "")
        self.ed_phc.setText(row.num_cliente_phc or "")
        self.ed_info1.setPlainText(row.info_1 or "")
        self.ed_info2.setPlainText(row.info_2 or "")
        self.ed_notas.setPlainText(getattr(row, "notas", "") or "")

    def _select_row_by_id(self, cid: int) -> bool:
        if cid is None:
            return False
        try:
            idx = next((i for i, r in enumerate(self.model._rows) if getattr(r, "id", None) == cid), None)
        except Exception:
            idx = None
        if idx is None:
            return False
        try:
            self.table.selectRow(idx)
            self.table.scrollTo(self.model.index(idx, 0))
        except Exception:
            return False
        return True

    def _check_duplicate(self) -> None:
        nome = (self.ed_nome.text() or "").strip()
        self._dup_match_id = None
        if not nome:
            self.lbl_dup.setText("")
            return
        existing = get_cliente_temporario_por_nome(self._db, nome)
        if existing and getattr(existing, "id", None) != self._current_id:
            self._dup_match_id = getattr(existing, "id", None)
            self.lbl_dup.setText(
                f"Ja existe um cliente temporario com este nome (ID {self._dup_match_id}). "
                "Use o botao 'Usar Cliente' para selecionar o registo existente."
            )
            return
        self.lbl_dup.setText("")

    def _use_selected(self) -> None:
        row = self._selected_row()
        if not row and self._dup_match_id:
            if self._select_row_by_id(self._dup_match_id):
                row = self._selected_row()
        if not row:
            QtWidgets.QMessageBox.information(self, "Cliente", "Selecione um cliente temporario.")
            return
        nome_simplex = (getattr(row, "nome_simplex", None) or row.nome or "").strip()
        self._result = {"temp_id": row.id, "nome": nome_simplex}
        self.accept()

    def _on_save(self) -> None:
        nome = (self.ed_nome.text() or "").strip()
        if not nome:
            QtWidgets.QMessageBox.warning(self, "Cliente", "Indique o nome do cliente temporario.")
            return
        if self._dup_match_id and self._current_id is None:
            msg = "Ja existe um cliente temporario com este nome.\n\nDeseja usar o cliente existente?"
            resp = QtWidgets.QMessageBox.question(
                self,
                "Cliente existente",
                msg,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Yes,
            )
            if resp == QtWidgets.QMessageBox.Yes:
                self._select_row_by_id(self._dup_match_id)
                self._use_selected()
                return
            if resp == QtWidgets.QMessageBox.Cancel:
                return

        try:
            temp = upsert_cliente_temporario(
                self._db,
                id=self._current_id,
                nome=nome,
                nome_simplex=self.ed_simplex.text(),
                morada=self.ed_morada.toPlainText(),
                email=self.ed_email.text(),
                web_page=self.ed_web.text(),
                telefone=self.ed_tel.text(),
                telemovel=self.ed_tm.text(),
                num_cliente_phc=self.ed_phc.text(),
                info_1=self.ed_info1.toPlainText(),
                info_2=self.ed_info2.toPlainText(),
                notas=self.ed_notas.toPlainText(),
            )
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar cliente temporario: {exc}")
            return

        self._result = {"temp_id": temp.id, "nome": temp.nome or nome}
        self.accept()

    def result_data(self) -> Optional[dict]:
        return self._result
