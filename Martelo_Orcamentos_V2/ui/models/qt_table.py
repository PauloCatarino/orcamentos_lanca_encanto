# ui/models/qt_table.py
from PySide6 import QtCore
from decimal import Decimal

class SimpleTableModel(QtCore.QAbstractTableModel):
    """
    Tabela simples para listas de objetos (ex.: ORM).
    columns: lista de tuplos (header, attr, formatter_opcional)
    - header: texto do cabeçalho (ex.: 'ID_MP', 'PRECO_TABELA')
    - attr: nome do atributo no objeto (ex.: 'id_mp', 'preco_tabela')
    - formatter: função que recebe o valor CRU e devolve string formatada
    """
    def __init__(self, rows=None, columns=None, parent=None):
        super().__init__(parent)
        self._rows = rows or []
        self._columns = columns or []

    # -------- API utilitária --------
    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def get_row(self, r):
        return self._rows[r]

    # -------- Qt Model API ----------
    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        row = self._rows[index.row()]
        col = self._columns[index.column()]

        # Desempacotar definição de coluna
        if isinstance(col, (tuple, list)):
            header = col[0]
            attr = col[1] if len(col) > 1 else None
            formatter = col[2] if len(col) > 2 else None
        elif isinstance(col, dict):
            header = col.get("header")
            attr = col.get("attr")
            formatter = col.get("formatter")
        else:
            header, attr, formatter = col, None, None

        # Obter valor CRU do objeto (para sort e alinhamento)
        try:
            val = getattr(row, attr) if attr else None
        except Exception:
            val = None

        # -------- Role para ORDENAR: devolver números quando possível --------
        if role == QtCore.Qt.UserRole:
            # Ordenação do ID_MP como inteiro (1,2,3,…,10,11…)
            if header == "ID_MP":
                try:
                    # aceita "0012" -> 12; strings vazias continuam como None
                    s = "" if val is None else str(val).strip()
                    return int(s) if s != "" else None
                except Exception:
                    return val  # se não der para converter, volta ao valor original

            # Para outros campos, se já for numérico, devolve tal e qual
            if isinstance(val, (int, float)) or str(type(val)).endswith("Decimal'>"):
                return val

            # Se for string e parecer número, tenta Decimal (para sort correto)
            if isinstance(val, str):
                s = val.strip().replace("€", "").replace("%", "").replace(",", ".")
                try:
                    return Decimal(s)
                except Exception:
                    return val

            return val

        # -------- Apresentação / edição --------
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            if formatter and val is not None:
                try:
                    return formatter(val)
                except Exception:
                    pass
            return "" if val is None else str(val)

        # -------- Alinhamento: números à direita --------
        if role == QtCore.Qt.TextAlignmentRole:
            if isinstance(val, (int, float)) or str(type(val)).endswith("Decimal'>"):
                return int(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return None
        if orientation == QtCore.Qt.Horizontal:
            if section >= len(self._columns):
                return ""
            col = self._columns[section]
            if isinstance(col, (tuple, list)):
                return col[0]
            if isinstance(col, dict):
                return col.get("header", "")
            return str(col)
        # Cabeçalho vertical = número de linha
        return str(section + 1)

    def sort(self, column: int, order: QtCore.Qt.SortOrder = QtCore.Qt.SortOrder.AscendingOrder):
        if not self._columns or column < 0 or column >= len(self._columns):
            return
        col = self._columns[column]
        if isinstance(col, (tuple, list)):
            attr = col[1] if len(col) > 1 else None
        elif isinstance(col, dict):
            attr = col.get("attr")
        else:
            attr = None
        reverse = order == QtCore.Qt.SortOrder.DescendingOrder

        def raw_value(row):
            if not attr:
                return row
            try:
                value = getattr(row, attr)
            except Exception:
                value = None
            return value

        def sort_key(row):
            value = raw_value(row)
            if value is None:
                return float('-inf') if reverse else float('inf')
            if isinstance(value, Decimal):
                return float(value)
            if isinstance(value, (int, float)):
                return value
            if isinstance(value, str):
                stripped = value.strip().replace('€', '').replace('%', '').replace(',', '.')
                try:
                    return float(stripped)
                except Exception:
                    return value
            return value

        self.layoutAboutToBeChanged.emit()
        try:
            self._rows.sort(key=sort_key, reverse=reverse)
        finally:
            self.layoutChanged.emit()
