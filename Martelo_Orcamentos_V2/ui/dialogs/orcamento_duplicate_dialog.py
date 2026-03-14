from __future__ import annotations

from PySide6 import QtWidgets
from PySide6.QtCore import Qt


def confirm_ref_cliente_duplicate(parent, *, ref_cliente: str, match_rows) -> bool:
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("Ref. Cliente duplicada")
    dialog.setModal(True)
    dialog.resize(760, 360)

    layout = QtWidgets.QVBoxLayout(dialog)
    info = QtWidgets.QLabel(
        f"Ja existem orcamentos com a Ref. Cliente '{ref_cliente}'. "
        "Verifique a lista e escolha se pretende criar mesmo assim."
    )
    info.setWordWrap(True)
    layout.addWidget(info)

    headers = ["ID", "Ano", "Num Orcamento", "Versao", "Cliente", "Ref. Cliente", "Data", "Estado", "Obra"]
    table = QtWidgets.QTableWidget(len(match_rows), len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setStretchLastSection(True)
    table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)

    for row_idx, row in enumerate(match_rows):
        values = [
            getattr(row, "id", ""),
            getattr(row, "ano", ""),
            getattr(row, "num_orcamento", ""),
            getattr(row, "versao", ""),
            getattr(row, "cliente", ""),
            getattr(row, "ref_cliente", ""),
            getattr(row, "data", ""),
            getattr(row, "estado", ""),
            getattr(row, "obra", ""),
        ]
        for col_idx, value in enumerate(values):
            item = QtWidgets.QTableWidgetItem(str(value or ""))
            item.setFlags(Qt.ItemIsEnabled)
            table.setItem(row_idx, col_idx, item)

    table.resizeColumnsToContents()
    layout.addWidget(table)

    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Yes | QtWidgets.QDialogButtonBox.No)
    buttons.button(QtWidgets.QDialogButtonBox.Yes).setText("Criar novo mesmo assim")
    buttons.button(QtWidgets.QDialogButtonBox.No).setText("Cancelar")
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    return dialog.exec() == QtWidgets.QDialog.Accepted
