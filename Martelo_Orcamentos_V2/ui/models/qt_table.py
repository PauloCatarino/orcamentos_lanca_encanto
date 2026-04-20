from decimal import Decimal
from typing import Any, Dict, Iterable, Optional

from Martelo_Orcamentos_V2.app.utils.bool_converter import bool_to_int, int_to_bool
from Martelo_Orcamentos_V2.app.utils.display import repair_mojibake

from PySide6 import QtCore


class SimpleTableModel(QtCore.QAbstractTableModel):
    """
    Model Qt simples para listas de objetos (ORM, dataclasses) ou dicionarios.
    columns aceita tuplos, dicionarios ou objetos com atributos (ex.: ColumnSpec).
    Linhas podem ser objetos com atributos ou dicionarios.
    """

    _NUMERIC_TYPES = {"int", "integer", "number", "float", "decimal"}
    _INTEGER_TYPES = {"int", "integer"}

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

    # compat alias for older code paths
    def row(self, row_index: int) -> Any:
        return self.get_row(row_index)

    def _col_spec(self, col: Any) -> Dict[str, Any]:
        """
        Normaliza a definicao de coluna num dicionario:
        {header, attr, formatter, type, editable}
        """
        if isinstance(col, (tuple, list)):
            header = col[0] if len(col) > 0 else ""
            attr = col[1] if len(col) > 1 else None
            formatter = col[2] if len(col) > 2 else None
            tooltip = col[3] if len(col) > 3 else None
            return {
                "header": header,
                "attr": attr,
                "formatter": formatter,
                "type": None,
                "editable": True,
                "tooltip": tooltip,
            }

        if isinstance(col, dict):
            header = col.get("header") or col.get("label") or ""
            attr = col.get("attr") or col.get("field")
            formatter = col.get("formatter")
            col_type = col.get("type") or col.get("kind")
            if isinstance(col_type, str):
                col_type = col_type.lower()
            editable = col.get("editable")
            if editable is None:
                editable = not col.get("readonly", False)
            tooltip = col.get("tooltip") or col.get("help")
            return {
                "header": header,
                "attr": attr,
                "formatter": formatter,
                "type": col_type,
                "editable": editable,
                "tooltip": tooltip,
            }

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
        tooltip = getattr(col, "tooltip", getattr(col, "help_text", None))
        return {
            "header": header,
            "attr": attr,
            "formatter": formatter,
            "type": col_type,
            "editable": editable_attr,
            "tooltip": tooltip,
        }

    def _coerce_numeric_value(self, value: Any, col_type: Optional[str]) -> Optional[Any]:
        if value is None:
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return value
        if isinstance(value, Decimal):
            try:
                return int(value) if col_type in self._INTEGER_TYPES else float(value)
            except Exception:
                return None
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                return int(text) if col_type in self._INTEGER_TYPES else float(text)
            except Exception:
                return None
        return None

    def _sort_key(self, value: Any, col_type: Optional[str]) -> tuple[int, Any]:
        if value is None:
            return (2, "")
        if col_type in self._NUMERIC_TYPES:
            numeric_value = self._coerce_numeric_value(value, col_type)
            if numeric_value is not None:
                return (0, numeric_value)
        if isinstance(value, str):
            return (1, repair_mojibake(value).casefold())
        if isinstance(value, Decimal):
            try:
                return (0, float(value))
            except Exception:
                return (1, str(value).casefold())
        return (0, value)

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
                return QtCore.Qt.Checked if int_to_bool(val) else QtCore.Qt.Unchecked
            if role == QtCore.Qt.DisplayRole:
                return ""
            if role == QtCore.Qt.EditRole:
                return int_to_bool(val)

        if role == QtCore.Qt.ToolTipRole:
            tooltip = spec.get("tooltip")
            if not tooltip:
                if col_type == "bool":
                    return None
                if val in (None, ""):
                    return None
                formatted = None
                if formatter:
                    try:
                        formatted = formatter(val)
                    except Exception:
                        formatted = None
                if formatted is None:
                    formatted = str(val)
                return repair_mojibake(formatted)
            if callable(tooltip):
                try:
                    return tooltip(row_obj, val, spec)
                except Exception:
                    return None
            if val in (None, ""):
                return repair_mojibake(tooltip)
            formatted = None
            if formatter:
                try:
                    formatted = formatter(val)
                except Exception:
                    formatted = None
            if formatted is None:
                formatted = str(val)
            return repair_mojibake(f"{tooltip}\nValor atual: {formatted}")

        # display / edit role
        if role == QtCore.Qt.DisplayRole:
            if formatter and val is not None:
                try:
                    return repair_mojibake(formatter(val))
                except Exception:
                    pass
            return "" if val is None else repair_mojibake(str(val))

        if role == QtCore.Qt.EditRole:
            if formatter and val is not None:
                try:
                    return formatter(val)
                except Exception:
                    pass
            return "" if val is None else str(val)

        # alinhamento: numeros a direita
        if role == QtCore.Qt.TextAlignmentRole:
            if (
                isinstance(val, (int, float))
                or str(type(val)).endswith("Decimal'>")
                or (col_type in self._NUMERIC_TYPES and self._coerce_numeric_value(val, col_type) is not None)
            ):
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
        if col_type == "bool" and role in (QtCore.Qt.CheckStateRole, QtCore.Qt.EditRole):
            if role == QtCore.Qt.CheckStateRole:
                new_bool = bool(value)
            else:
                if isinstance(value, (int, float)):
                    new_bool = bool(value)
                elif isinstance(value, str):
                    new_bool = value.strip().lower() in {"1", "true", "sim", "yes", "on"}
                else:
                    new_bool = bool(value)

            if isinstance(row_obj, dict):
                if int_to_bool(row_obj.get(attr)) == new_bool:
                    return True
                row_obj[attr] = new_bool
            else:
                stored_value = getattr(row_obj, attr, None)
                if int_to_bool(stored_value) == new_bool:
                    return True
                try:
                    setattr(row_obj, attr, new_bool)
                except Exception:
                    try:
                        setattr(row_obj, attr, bool_to_int(new_bool))
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
        if orientation == QtCore.Qt.Horizontal:
            if section >= len(self._columns):
                return "" if role == QtCore.Qt.DisplayRole else None
            col = self._columns[section]
            spec = self._col_spec(col)
            if role == QtCore.Qt.DisplayRole:
                return repair_mojibake(spec.get("header", ""))
            if role == QtCore.Qt.ToolTipRole:
                tooltip = spec.get("tooltip")
                return repair_mojibake(tooltip) if isinstance(tooltip, str) else tooltip
            return None
        if role == QtCore.Qt.DisplayRole:
            return str(section + 1)
        return None

    # ---------- utilitarios ----------
    def sort(self, column: int, order: QtCore.Qt.SortOrder = QtCore.Qt.SortOrder.AscendingOrder) -> None:
        if not self._columns or column < 0 or column >= len(self._columns):
            return
        col = self._columns[column]
        spec = self._col_spec(col)
        attr = spec["attr"]
        col_type = spec.get("type")
        reverse = order == QtCore.Qt.SortOrder.DescendingOrder

        def raw_value(row_obj: Any):
            try:
                if isinstance(row_obj, dict):
                    return row_obj.get(attr)
                return getattr(row_obj, attr)
            except Exception:
                return None

        old_rows = list(self._rows)
        new_rows = sorted(old_rows, key=lambda row_obj: self._sort_key(raw_value(row_obj), col_type), reverse=reverse)
        if new_rows == old_rows:
            return

        self.layoutAboutToBeChanged.emit()
        try:
            # Atualiza indexes persistentes (ex.: selecao/cursor) para manter a linha correta após ordenacao.
            old_persistent = self.persistentIndexList()
            if old_persistent:
                old_by_objid: dict[int, list[int]] = {}
                for old_index, row_obj in enumerate(old_rows):
                    old_by_objid.setdefault(id(row_obj), []).append(old_index)

                old_to_new: dict[int, int] = {}
                for new_index, row_obj in enumerate(new_rows):
                    old_index = old_by_objid[id(row_obj)].pop(0)
                    old_to_new[old_index] = new_index

                new_persistent = [self.index(old_to_new.get(idx.row(), idx.row()), idx.column()) for idx in old_persistent]
                self.changePersistentIndexList(old_persistent, new_persistent)

            self._rows = new_rows
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
