from typing import Any, Dict, List, Optional, Sequence
from PySide6 import QtCore, QtGui
from PySide6.QtCore import Qt

class DadosTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: List[Dict[str, Any]] = []
        self.columns: List[Dict[str, str]] = []

    def rowCount(self, parent=None) -> int:
        return len(self.rows)

    def columnCount(self, parent=None) -> int:
        return len(self.columns)

    def data(self, index: QtCore.QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        if not (0 <= row < len(self.rows)):
            return None

        column = self.columns[col]
        field = column.get("field")
        if not field:
            return None

        value = self.rows[row].get(field)

        if column.get("type") == "bool":
            if role == Qt.CheckStateRole:
                return Qt.Checked if value else Qt.Unchecked
            return None

        if role == Qt.DisplayRole:
            if value is None:
                return ""
            return str(value)

        return None

    def setData(self, index: QtCore.QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not index.isValid():
            return False

        row = index.row()
        col = index.column()
        if not (0 <= row < len(self.rows)):
            return False

        column = self.columns[col]
        field = column.get("field")
        if not field:
            return False

        if column.get("type") == "bool" and role == Qt.CheckStateRole:
            new_value = bool(value == Qt.Checked)
            if self.rows[row].get(field) == new_value:
                return True
            self.rows[row][field] = new_value
            self.dataChanged.emit(index, index)
            return True

        if role == Qt.EditRole:
            self.rows[row][field] = value
            self.dataChanged.emit(index, index)
            return True

        return False

    def flags(self, index: QtCore.QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable

        column = self.columns[index.column()]
        if column.get("type") == "bool":
            flags |= Qt.ItemIsUserCheckable
        elif column.get("editable", False):
            flags |= Qt.ItemIsEditable

        return flags

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.columns[section].get("label", "")
        return None

    def set_columns(self, columns: List[Dict[str, str]]) -> None:
        self.beginResetModel()
        self.columns = columns
        self.endResetModel()

    def set_rows(self, rows: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()