from typing import Any, Dict, List, Optional
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt

from ..models.dados_table_model import DadosTableModel

class DadosTableView(QtWidgets.QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = DadosTableModel(self)
        self.setModel(self.model)
        
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().hide()

    def setup_columns(self, columns: List[Dict[str, str]]) -> None:
        self.model.set_columns(columns)
        for i, col in enumerate(columns):
            if col.get("width"):
                self.setColumnWidth(i, col["width"])

    def load_data(self, rows: List[Dict[str, Any]]) -> None:
        self.model.set_rows(rows)

    def get_data(self) -> List[Dict[str, Any]]:
        return self.model.rows

    def clear(self) -> None:
        self.model.set_rows([])