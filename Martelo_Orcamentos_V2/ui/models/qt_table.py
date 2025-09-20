from PySide6 import QtCore


class SimpleTableModel(QtCore.QAbstractTableModel):
    """Tabela simples para listas de objetos SQLAlchemy.

    columns: list of (header, attr)
    """

    def __init__(self, rows=None, columns=None, parent=None):
        super().__init__(parent)
        self._rows = rows or []
        self._columns = columns or []

    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    # Qt Model API
    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        header, attr = self._columns[index.column()]
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            try:
                val = getattr(row, attr)
            except Exception:
                val = None
            return "" if val is None else str(val)
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return None
        if orientation == QtCore.Qt.Horizontal:
            return self._columns[section][0] if section < len(self._columns) else ""
        return str(section + 1)

    def get_row(self, r):
        return self._rows[r]

