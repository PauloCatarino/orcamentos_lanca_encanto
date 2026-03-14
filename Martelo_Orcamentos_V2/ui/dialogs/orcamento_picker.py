from __future__ import annotations

from typing import Optional

from PySide6 import QtWidgets
from PySide6.QtCore import Qt

from Martelo_Orcamentos_V2.app.services.orcamentos import list_orcamentos, search_orcamentos
from Martelo_Orcamentos_V2.app.utils.display import format_currency_pt
from Martelo_Orcamentos_V2.ui.models.qt_table import SimpleTableModel


def _format_currency(value) -> str:
    return format_currency_pt(value)


class OrcamentoPicker(QtWidgets.QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._selected_id: Optional[int] = None
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle("Selecionar Orcamento")
        self.resize(1150, 520)

        layout = QtWidgets.QVBoxLayout(self)
        search_row = QtWidgets.QHBoxLayout()
        self.ed_search = QtWidgets.QLineEdit()
        self.ed_search.setPlaceholderText("Pesquisar orcamentos (cliente, codigo, ref, obra...)")
        btn_search = QtWidgets.QPushButton("Pesquisar")
        btn_search.clicked.connect(self._reload)
        search_row.addWidget(self.ed_search, 1)
        search_row.addWidget(btn_search)
        layout.addLayout(search_row)

        self.table = QtWidgets.QTableView(self)
        self.model = SimpleTableModel(
            columns=[
                ("ID", "id"),
                ("Ano", "ano"),
                ("Num Orcamento", "num_orcamento"),
                ("Versao", "versao"),
                ("Enc PHC", "enc_phc"),
                ("Cliente", "cliente"),
                ("Ref Cliente", "ref_cliente"),
                ("Obra", "obra"),
                ("Preco", "preco", _format_currency),
                ("Estado", "estado"),
            ]
        )
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        width_map = {
            "ID": 55,
            "Ano": 60,
            "Num Orcamento": 100,
            "Versao": 60,
            "Enc PHC": 90,
            "Cliente": 160,
            "Ref Cliente": 100,
            "Obra": 220,
            "Preco": 90,
            "Estado": 120,
        }
        for idx, col in enumerate(self.model.columns):
            spec = self.model._col_spec(col)
            label = spec.get("header", "")
            header.setSectionResizeMode(idx, QtWidgets.QHeaderView.Interactive)
            if label in width_map:
                header.resizeSection(idx, width_map[label])
        self.table.doubleClicked.connect(self._accept_current)
        layout.addWidget(self.table, 1)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._reload()

    def _reload(self):
        text = self.ed_search.text().strip()
        if text:
            rows = search_orcamentos(self.session, text)
        else:
            rows = list_orcamentos(self.session)
        data = []
        for r in rows:
            data.append(
                {
                    "id": r.id,
                    "ano": r.ano,
                    "num_orcamento": r.num_orcamento,
                    "versao": r.versao,
                    "enc_phc": getattr(r, "enc_phc", None),
                    "cliente": getattr(r, "cliente", None)
                    or getattr(r, "cliente_nome", None)
                    or getattr(r, "cliente_simplex", None),
                    "ref_cliente": r.ref_cliente,
                    "obra": r.obra,
                    "preco": getattr(r, "preco_total", None) or getattr(r, "preco", None),
                    "estado": getattr(r, "status", None) or getattr(r, "estado", None),
                }
            )
        self.model.set_rows(data)
        if data:
            self.table.selectRow(0)

    def _capture_selection(self) -> bool:
        idxs = self.table.selectionModel().selectedRows()
        if not idxs:
            return False
        row = idxs[0].row()
        data = self.model.row(row)
        if data:
            self._selected_id = data.get("id")
            return True
        return False

    def accept(self):
        if not self._capture_selection():
            QtWidgets.QMessageBox.information(self, "Selecionar", "Escolha um orcamento na lista.")
            return
        super().accept()

    def _accept_current(self):
        if self._capture_selection():
            super().accept()

    def selected_id(self) -> Optional[int]:
        return self._selected_id
