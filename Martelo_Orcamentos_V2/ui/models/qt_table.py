from decimal import Decimal
from typing import Any, Dict, Iterable, Optional

from PySide6 import QtCore


class SimpleTableModel(QtCore.QAbstractTableModel):
    """
    Model Qt simples para listas de objetos (ORM, dataclasses) ou dicionarios.
    columns aceita tuplos, dicionarios ou objetos com atributos (ex.: ColumnSpec).
    Linhas podem ser objetos com atributos ou dicionarios.
    """

    def __init__(self, rows: Optional[Iterable[Any]] = None, columns: Optional[Iterable[Any]] = None, parent=None):
        super().__init__(parent)
        self._rows = list(rows) if rows is not None else []
        self._columns = list(columns) if columns is not None else []
        # manter compatibilidade com codigo existente que acede a model.columns
        self.columns = self._columns

    # -------- API utilitaria --------
    def set_rows(self, rows: Optional[Iterable[Any]]) -> None:
        self.beginResetModel()
        self._rows = list(rows) if rows is not None else []
        self.endResetModel()

    def set_columns(self, columns: Optional[Iterable[Any]]) -> None:
        self.beginResetModel()
        self._columns = list(columns) if columns is not None else []
        self.columns = self._columns
        self.endResetModel()

    def get_row(self, row_index: int) -> Any:
        return self._rows[row_index]

    def _col_spec(self, col: Any) -> Dict[str, Any]:
        """
        Normaliza a definicao de coluna num dicionario:
        {header, attr, formatter, type, editable}
        """
        if isinstance(col, (tuple, list)):
            header = col[0] if len(col) > 0 else ""
            attr = col[1] if len(col) > 1 else None
            formatter = col[2] if len(col) > 2 else None
            return {"header": header, "attr": attr, "formatter": formatter, "type": None, "editable": True}

        if isinstance(col, dict):
            header = col.get("header") or col.get("label") or ""
            attr = col.get("attr") or col.get("field")
            formatter = col.get("formatter")
            col_type = col.get("type") or col.get("kind")
            editable = col.get("editable")
            if editable is None:
                editable = not col.get("readonly", False)
            return {"header": header, "attr": attr, "formatter": formatter, "type": col_type, "editable": editable}

        # Objetos (ex.: dataclasses)
        header = getattr(col, "header", getattr(col, "label", str(col)))
        attr = getattr(col, "attr", getattr(col, "field", None))
        formatter = getattr(col, "formatter", None)
        col_type = getattr(col, "type", getattr(col, "kind", None))
        if isinstance(col_type, str):
            col_type = col_type.lower()
        editable_attr = getattr(col, "editable", None)
        if editable_attr is None:
            editable_attr = not getattr(col, "readonly", False)
        return {"header": header, "attr": attr, "formatter": formatter, "type": col_type, "editable": editable_attr}

    # -------- Qt Model API ----------
    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        row_obj = self._rows[index.row()]
        col = self._columns[index.column()]
        spec = self._col_spec(col)
        attr = spec["attr"]
        formatter = spec["formatter"]
        col_type = spec.get("type")

        # obter valor bruto
        try:
            if isinstance(row_obj, dict):
                val = row_obj.get(attr) if attr else None
            else:
                val = getattr(row_obj, attr) if attr else None
        except Exception:
            val = None

        # ---- coluna booleana -> checkbox ----
        if col_type == "bool":
            if role == QtCore.Qt.CheckStateRole:
                return QtCore.Qt.Checked if bool(val) else QtCore.Qt.Unchecked
            if role == QtCore.Qt.DisplayRole:
                return ""

        # display / edit role
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            if formatter and val is not None:
                try:
                    return formatter(val)
                except Exception:
                    pass
            return "" if val is None else str(val)

        # alinhamento: numeros a direita
        if role == QtCore.Qt.TextAlignmentRole:
            if isinstance(val, (int, float)) or str(type(val)).endswith("Decimal'>"):
                return int(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        if role == QtCore.Qt.UserRole:
            return val

        return None

    def setData(self, index: QtCore.QModelIndex, value: Any, role: int = QtCore.Qt.EditRole) -> bool:
        if not index.isValid():
            return False

        row_obj = self._rows[index.row()]
        col = self._columns[index.column()]
        spec = self._col_spec(col)
        attr = spec["attr"]
        col_type = spec.get("type")

        if not attr:
            return False

        # checkbox -> role CheckStateRole
        if col_type == "bool" and role == QtCore.Qt.CheckStateRole:
            new_value = value == QtCore.Qt.Checked
            if isinstance(row_obj, dict):
                if row_obj.get(attr) == new_value:
                    return True
                row_obj[attr] = new_value
            else:
                if getattr(row_obj, attr, None) == new_value:
                    return True
                try:
                    setattr(row_obj, attr, new_value)
                except Exception:
                    return False
            self.dataChanged.emit(index, index, [QtCore.Qt.CheckStateRole, QtCore.Qt.DisplayRole])
            return True

        if role == QtCore.Qt.EditRole:
            if isinstance(row_obj, dict):
                row_obj[attr] = value
            else:
                try:
                    setattr(row_obj, attr, value)
                except Exception:
                    return False
            self.dataChanged.emit(index, index, [QtCore.Qt.EditRole, QtCore.Qt.DisplayRole])
            return True

        return False

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        col = self._columns[index.column()]
        spec = self._col_spec(col)
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

        if spec.get("type") == "bool":
            flags |= QtCore.Qt.ItemIsUserCheckable
        elif spec.get("editable", True):
            flags |= QtCore.Qt.ItemIsEditable

        return flags

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return None
        if orientation == QtCore.Qt.Horizontal:
            if section >= len(self._columns):
                return ""
            col = self._columns[section]
            spec = self._col_spec(col)
            return spec.get("header", "")
        return str(section + 1)

    # ---------- utilitarios ----------
    def sort(self, column: int, order: QtCore.Qt.SortOrder = QtCore.Qt.SortOrder.AscendingOrder) -> None:
        if not self._columns or column < 0 or column >= len(self._columns):
            return
        col = self._columns[column]
        spec = self._col_spec(col)
        attr = spec["attr"]
        reverse = order == QtCore.Qt.SortOrder.DescendingOrder

        def raw_value(row_obj: Any):
            try:
                if isinstance(row_obj, dict):
                    return row_obj.get(attr)
                return getattr(row_obj, attr)
            except Exception:
                return None

        self.layoutAboutToBeChanged.emit()
        try:
            self._rows.sort(key=lambda row_obj: (raw_value(row_obj) is None, raw_value(row_obj)), reverse=reverse)
        finally:
            self.layoutChanged.emit()

    def _coerce_for_export(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, Decimal):
            try:
                return float(value)
            except Exception:
                return str(value)
        return value

    def export_rows(self):
        """
        Devolve lista de dicionarios com os dados atuais do modelo.
        """
        exported = []
        for row_obj in self._rows:
            row_dict: Dict[str, Any] = {}
            for col in self._columns:
                spec = self._col_spec(col)
                attr = spec["attr"]
                if not attr:
                    continue
                try:
                    if isinstance(row_obj, dict):
                        val = row_obj.get(attr)
                    else:
                        val = getattr(row_obj, attr)
                except Exception:
                    val = None
                row_dict[attr] = self._coerce_for_export(val)
            exported.append(row_dict)
        return exported
