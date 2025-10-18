#--- START OF FILE custeio_items.py ---



from __future__ import annotations



from typing import Any, Dict, List, Mapping, Optional, Sequence, Set
import uuid



from PySide6 import QtCore, QtGui, QtWidgets



from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento, OrcamentoItem

from Martelo_Orcamentos_V2.app.services import custeio_items as svc_custeio

from Martelo_Orcamentos_V2.app.db import SessionLocal
from sqlalchemy import select
from .dados_gerais import MateriaPrimaPicker



# Compat: algumas versoes nao tem Qt.ItemIsTristate; usamos auto ou 0 como fallback.

TRISTATE_FLAG = getattr(QtCore.Qt, "ItemIsTristate", 0) or getattr(QtCore.Qt, "ItemIsAutoTristate", 0)

ITALIC_ON_BLK_KEYS = {
    "ref_le",
    "descricao_no_orcamento",
    "pliq",
    "und",
    "desp",
    "orl_0_4",
    "orl_1_0",
    "tipo",
    "familia",
    "comp_mp",
    "larg_mp",
    "esp_mp",
}

MANUAL_LOCK_KEYS = ITALIC_ON_BLK_KEYS

HEADER_TOOLTIPS = {
    "descricao_livre": "Texto livre editavel para identificar a linha no custeio.",
    "def_peca": "Codigo da peca selecionada na arvore de definicoes.",
    "descricao": "Descricao base importada do material associado.",
    "qt_mod": "Quantidade de modulos a produzir com esta linha.",
    "qt_und": "Quantidade de unidades por modulo.",
    "blk": "Quando ativo bloqueia atualizacoes vindas da tabela Dados Items.",
    "nst": "Indica que o material foi marcado como Nao-Stock nos Dados Items.",
    "mat_default": "Grupo de material usado como origem das informacoes desta linha.",
    "ref_le": "Referencia LE selecionada no material mapeado.",
    "descricao_no_orcamento": "Descricao utilizada na impressao do orcamento.",
    "pliq": "Preco liquido do material, conforme Dados Items.",
    "und": "Unidade de medida associada ao material.",
    "desp": "Percentual de desperdicio aplicado ao material.",
    "orl_0_4": "Codigo da orla de 0.4 mm configurada para o material.",
    "orl_1_0": "Codigo da orla de 1.0 mm configurada para o material.",
    "tipo": "Tipo de material selecionado.",
    "familia": "Familia principal do material selecionado.",
    "comp_mp": "Comprimento em mm da materia-prima.",
    "larg_mp": "Largura em mm da materia-prima.",
    "esp_mp": "Espessura em mm da materia-prima.",
}

CELL_TOOLTIP_KEYS = set(HEADER_TOOLTIPS.keys()) | {"descricao"}

COLUMN_WIDTH_DEFAULTS = {
    "id": 55,
    "descricao_livre": 170,
    "icon_hint": 36,
    "def_peca": 170,
    "descricao": 200,
    "qt_mod": 110,
    "qt_und": 90,
    "comp": 70,
    "larg": 70,
    "esp": 70,
    "mps": 55,
    "mo": 55,
    "orla": 55,
    "blk": 50,
    "nst": 55,
    "mat_default": 150,
    "acabamento": 150,
    "qt_total": 90,
    "comp_res": 80,
    "larg_res": 80,
    "esp_res": 80,
    "ref_le": 120,
    "descricao_no_orcamento": 200,
    "pliq": 90,
    "und": 70,
    "desp": 80,
    "orl_0_4": 130,
    "orl_1_0": 130,
    "tipo": 120,
    "familia": 120,
    "comp_mp": 90,
    "larg_mp": 90,
    "esp_mp": 90,
    "orl_c1": 70,
    "orl_c2": 70,
    "orl_l1": 70,
    "orl_l2": 70,
    "ml_orl_c1": 100,
    "ml_orl_c2": 100,
    "ml_orl_l1": 100,
    "ml_orl_l2": 100,
    "custo_orl_c1": 110,
    "custo_orl_c2": 110,
    "custo_orl_l1": 110,
    "custo_orl_l2": 110,
}


class CusteioTableView(QtWidgets.QTableView):
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            editor = self.focusWidget()
            # focusWidget() may return a child widget inside the actual editor
            # (for example the internal QLineEdit of a QComboBox). We must
            # find the top-level editor whose parent is the view's viewport
            # before calling commitData/closeEditor, otherwise Qt warns that
            # the editor does not belong to this view.
            top_editor = editor
            while top_editor is not None and top_editor.parent() is not self.viewport():
                # Stop climbing if we reached a top-level widget (no parent)
                parent = top_editor.parent()
                if parent is None:
                    break
                top_editor = parent

            if top_editor and top_editor.parent() is self.viewport():
                self.commitData(top_editor)
                self.closeEditor(top_editor, QtWidgets.QAbstractItemDelegate.SubmitModelCache)
            next_index = self.moveCursor(QtWidgets.QAbstractItemView.MoveRight, QtCore.Qt.NoModifier)
            if next_index.isValid():
                self.setCurrentIndex(next_index)
            event.accept()
            return
        super().keyPressEvent(event)


class NumericLineEditDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent: Optional[QtCore.QObject], spec: Mapping[str, Any]):
        super().__init__(parent)
        self._format = spec.get("format")

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        editor.setFrame(False)
        editor.setAlignment(QtCore.Qt.AlignRight)
        editor.setProperty("_custeio_editor", True)
        if self._format == "int":
            validator: QtGui.QValidator = QtGui.QIntValidator(editor)
        else:
            validator = QtGui.QDoubleValidator(editor)
            validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
            validator.setDecimals(6)
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor, index):
        value = index.data(QtCore.Qt.EditRole)
        if value in (None, ""):
            editor.setText("")
            return
        editor.setText(str(value))

    def setModelData(self, editor, model, index):
        text = editor.text().strip()
        model.setData(index, text, QtCore.Qt.EditRole)







class CusteioTreeFilterProxy(QtCore.QSortFilterProxyModel):

    """

    Proxy de filtro que:

      - casa texto no nÃ³ OU em qualquer descendente (expansÃ£o automÃ¡tica);

      - opcionalmente mostra sÃ³ itens marcados.

    """

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:

        super().__init__(parent)

        self._only_checked = False

        self.setRecursiveFilteringEnabled(False)  # mantemos False, pois filtramos manualmente descendentes

        self.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.setFilterKeyColumn(0)



    def set_only_checked(self, enabled: bool) -> None:

        if self._only_checked == enabled:

            return

        self._only_checked = enabled

        self.invalidateFilter()



    def only_checked(self) -> bool:

        return self._only_checked



    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:  # type: ignore[override]

        index = self.sourceModel().index(source_row, 0, source_parent)

        if not index.isValid():

            return False



        visible_by_text = self._matches_filter(index)

        visible_by_children = self._has_descendant_matching(index)

        if not (visible_by_text or visible_by_children):

            return False



        if not self._only_checked:

            return True



        if self._has_checked(index):

            return True



        return False



    # ----------------- helpers de filtro -----------------

    def _filter_pattern(self) -> Optional[QtCore.QRegularExpression]:

        pattern = self.filterRegularExpression()

        return pattern if pattern and pattern.pattern() else None



    def _matches_filter(self, index: QtCore.QModelIndex) -> bool:

        regex = self._filter_pattern()

        if regex is None:

            return True

        text = index.data(QtCore.Qt.DisplayRole) or ""

        return bool(regex.match(str(text)).hasMatch())



    def _has_descendant_matching(self, index: QtCore.QModelIndex) -> bool:

        model = self.sourceModel()

        row_count = model.rowCount(index)

        for row in range(row_count):

            child = model.index(row, 0, index)

            if not child.isValid():

                continue

            if self._matches_filter(child):

                return True

            if self._has_descendant_matching(child):

                return True

        return False



    def _has_checked(self, index: QtCore.QModelIndex) -> bool:

        item = self._item_from_index(index)

        if item is None:

            return False

        if item.checkState() == QtCore.Qt.Checked:

            return True

        row_count = item.rowCount()

        for row in range(row_count):

            child = item.child(row)

            if child is None:

                continue

            if self._has_checked(child.index()):

                return True

        return False



    def _item_from_index(self, index: QtCore.QModelIndex) -> Optional[QtGui.QStandardItem]:

        if not index.isValid():

            return None

        # JÃ¡ estamos a trabalhar sobre sourceModel(), por isso o index Ã© do modelo base

        if isinstance(self.sourceModel(), QtGui.QStandardItemModel):

            model: QtGui.QStandardItemModel = self.sourceModel()  # type: ignore[assignment]

            return model.itemFromIndex(index)

        return None





class CusteioTableModel(QtCore.QAbstractTableModel):

    def __init__(self, parent=None):

        super().__init__(parent)
        self._page = parent if parent is not None else None

        self.columns = svc_custeio.CUSTEIO_COLUMN_SPECS

        self.column_keys = [col["key"] for col in self.columns]

        self._column_index = {col["key"]: idx for idx, col in enumerate(self.columns)}

        self._blk_column = self._column_index.get("blk")

        self._italic_columns_idx = [self._column_index[key] for key in ITALIC_ON_BLK_KEYS if key in self._column_index]

        self._tooltip_columns_idx = [self._column_index[key] for key in CELL_TOOLTIP_KEYS if key in self._column_index]

        self._italic_font = QtGui.QFont()

        self._italic_font.setItalic(True)

        self._bold_font = QtGui.QFont()

        self._bold_font.setBold(True)

        self.rows: List[Dict[str, Any]] = []

    # --- Helpers ------------------------------------------------------

    @staticmethod
    def _normalize_def_peca(value: Optional[str]) -> str:
        return (value or "").strip().upper()

    def _is_division_row(self, row: Mapping[str, Any]) -> bool:
        return self._normalize_def_peca(row.get("def_peca")) == "DIVISAO INDEPENDENTE"

    @staticmethod
    def _format_factor(value: Optional[float]) -> Optional[str]:
        if value in (None, ""):
            return None
        try:
            num = float(value)
        except Exception:
            return None
        if abs(num) < 1e-9:
            return "0"
        if abs(num - round(num)) < 1e-9:
            return str(int(round(num)))
        return f"{num:.2f}".rstrip("0").rstrip(".")

    def _format_qt_mod_display(self, row_index: int) -> str:
        if not (0 <= row_index < len(self.rows)):
            return ""
        row = self.rows[row_index]
        row_type = row.get("_row_type") or "normal"
        if row_type == "separator":
            return ""
        if self._is_division_row(row):
            return self._format_factor(row.get("qt_mod")) or ""

        factors: List[str] = []
        divisor = self._format_factor(row.get("_qt_divisor"))
        if divisor and (divisor != "1" or row_type in ("child", "parent")):
            factors.append(divisor)

        parent_factor = self._format_factor(row.get("_qt_parent_factor"))
        factors.append(parent_factor or "1")

        child_factor = self._format_factor(row.get("_qt_child_factor"))
        if child_factor:
            factors.append(child_factor)
        elif row_type == "child":
            factors.append("1")

        return " x ".join(factors)



    # --- Qt API ---------------------------------------------------------

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:

        return 0 if parent.isValid() else len(self.rows)



    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:

        return 0 if parent.isValid() else len(self.columns)



    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.DisplayRole):

        if orientation == QtCore.Qt.Horizontal:

            if role == QtCore.Qt.DisplayRole:

                if 0 <= section < len(self.columns):

                    return self.columns[section]["label"]

            if role == QtCore.Qt.ToolTipRole:

                if 0 <= section < len(self.columns):

                    key = self.columns[section]["key"]

                    tooltip = HEADER_TOOLTIPS.get(key)

                    if tooltip:

                        return tooltip

                return None

        return super().headerData(section, orientation, role)



    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):

        if not index.isValid():

            return None

        row = index.row()

        col = index.column()

        if not (0 <= row < len(self.rows) and 0 <= col < len(self.columns)):

            return None



        row_data = self.rows[row]

        row_type = row_data.get("_row_type")

        spec = self.columns[col]

        key = spec["key"]

        value = row_data.get(key)

        if key == "icon_hint":

            if role == QtCore.Qt.DecorationRole:

                icon_value = row_data.get("icon_hint")

                if isinstance(icon_value, QtGui.QIcon):

                    return icon_value

                if isinstance(icon_value, str) and icon_value:

                    return QtGui.QIcon(icon_value)

            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):

                return ""

            return None

        if role == QtCore.Qt.BackgroundRole:

            if row_type == "division":

                return QtGui.QColor(210, 210, 210)

            if row_type == "separator":

                return QtGui.QColor(235, 235, 235)

        if role == QtCore.Qt.FontRole:

            if row_type == "division":

                return self._bold_font

            if row_data.get("blk") and key in ITALIC_ON_BLK_KEYS:

                return self._italic_font

            return None

        if role == QtCore.Qt.ToolTipRole:

            if key in CELL_TOOLTIP_KEYS:

                if spec["type"] == "bool":

                    return "Ativo" if bool(value) else "Inativo"

                display_value = self.data(index, QtCore.Qt.DisplayRole)

                if isinstance(display_value, str) and display_value:

                    return display_value

                if display_value not in (None, ""):

                    return str(display_value)

            return None



        if key == "qt_mod":

            if role == QtCore.Qt.DisplayRole:

                return self._format_qt_mod_display(row)

            if role == QtCore.Qt.ToolTipRole:

                formatted = self._format_qt_mod_display(row)

                return formatted or None

        if spec["type"] == "bool":

            if role == QtCore.Qt.CheckStateRole:

                return QtCore.Qt.Checked if value else QtCore.Qt.Unchecked

            if role == QtCore.Qt.DisplayRole:

                return ""

            if role == QtCore.Qt.EditRole:

                return bool(value)

            if role == QtCore.Qt.TextAlignmentRole:

                return QtCore.Qt.AlignCenter

            return None



        if role == QtCore.Qt.DisplayRole:

            if key == "id" and row_type == "division":

                collapsed = False

                page_ref = getattr(self, "_page", None)

                if page_ref is not None:

                    collapsed = row_data.get("_group_uid") in getattr(page_ref, "_collapsed_groups", set())

                symbol = "⊕" if collapsed else "⊖"

                base_value = value if value not in (None, "") else ""

                return (symbol + " " + str(base_value).strip()).strip()

            if value in (None, ""):

                return ""

            if spec["type"] == "numeric":

                fmt = spec.get("format")

                try:

                    num = float(value)

                except Exception:

                    return str(value)

                if fmt == "money":

                    return f"{num:.2f}€"

                if fmt == "percent":

                    display = num * 100 if abs(num) <= 1 else num

                    return f"{display:.2f}%"

                if fmt == "one":

                    return f"{num:.1f}"

                if fmt == "int":

                    return f"{int(round(num))}"

                if fmt == "two":

                    return f"{num:.2f}".rstrip("0").rstrip(".")

                return f"{num:.4f}".rstrip("0").rstrip(".")

            return str(value)



        if role == QtCore.Qt.EditRole:

            return value



        return None



    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:

        if not index.isValid():

            return QtCore.Qt.NoItemFlags



        spec = self.columns[index.column()]

        key = spec["key"]

        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

        if spec["type"] == "bool":

            flags |= QtCore.Qt.ItemIsUserCheckable

        elif spec.get("editable", False):

            row_data = self.rows[index.row()]

            if key == "qt_und" and self._is_division_row(row_data):

                return flags

            flags |= QtCore.Qt.ItemIsEditable

        return flags



    def setData(self, index: QtCore.QModelIndex, value: Any, role: int = QtCore.Qt.EditRole) -> bool:

        if not index.isValid():

            return False



        row = index.row()

        col = index.column()

        spec = self.columns[col]

        key = spec["key"]

        if spec["type"] == "icon":

            return False



        if spec["type"] == "bool" and role == QtCore.Qt.CheckStateRole:

            new_state = bool(value == QtCore.Qt.Checked)

            if self.rows[row].get(key) == new_state:

                return True

            self.rows[row][key] = new_state

            roles = [QtCore.Qt.DisplayRole, QtCore.Qt.CheckStateRole]

            if key == "blk":

                roles.append(QtCore.Qt.FontRole)

                self._emit_font_updates(row)

            self.dataChanged.emit(index, index, roles)

            return True



        if role != QtCore.Qt.EditRole or not spec.get("editable", False):

            return False



        manual_lock = spec["key"] in MANUAL_LOCK_KEYS



        requires_recalc = False

        if spec["type"] == "numeric":

            if key == "qt_mod" and self._is_division_row(self.rows[row]):

                if value in (None, ""):

                    numeric_value = 1

                else:

                    try:

                        numeric_raw = float(value)

                    except (TypeError, ValueError):

                        return False

                    if abs(numeric_raw - round(numeric_raw)) > 1e-9:

                        return False

                    numeric_value = int(round(numeric_raw))

                if numeric_value < 1 or numeric_value > 8:

                    return False

                self.rows[row][key] = float(numeric_value)

                requires_recalc = True

            else:

                if value in (None, ""):

                    self.rows[row][key] = None

                else:

                    try:

                        self.rows[row][key] = float(value)

                    except (TypeError, ValueError):

                        return False

                if key in {"qt_mod", "qt_und"}:

                    requires_recalc = True

        else:

            if key == "esp":

                self.rows[row][key] = self.rows[row].get("esp_mp")

            else:

                self.rows[row][key] = value

        if requires_recalc or key == "esp":

            self.recalculate_all()

        else:

            self.dataChanged.emit(index, index, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.FontRole, QtCore.Qt.ToolTipRole])



        if manual_lock:

            self.set_blk(row, True)

        else:

            if key in ITALIC_ON_BLK_KEYS:

                self._emit_font_updates(row)



        return True



    # --- API ------------------------------------------------------------

    def clear(self) -> None:

        self.beginResetModel()

        self.rows = []

        self.endResetModel()



    def load_rows(self, rows: Sequence[Mapping[str, Any]]) -> None:

        self.beginResetModel()

        self.rows = [self._coerce_row_impl(row) for row in rows]

        self.endResetModel()



    def append_rows(self, rows: Sequence[Mapping[str, Any]]) -> None:

        if not rows:

            return

        start = len(self.rows)

        end = start + len(rows) - 1

        self.beginInsertRows(QtCore.QModelIndex(), start, end)

        for row in rows:

            self.rows.append(self._coerce_row_impl(row))

        self.endInsertRows()


    def insert_rows(self, position: int, rows: Sequence[Mapping[str, Any]]) -> None:

        if not rows:

            return

        position = max(0, min(position, len(self.rows)))

        self.beginInsertRows(QtCore.QModelIndex(), position, position + len(rows) - 1)

        for offset, row in enumerate(rows):

            self.rows.insert(position + offset, self._coerce_row_impl(row))

        self.endInsertRows()


    def remove_rows(self, indices: Sequence[int]) -> None:

        if not indices:

            return

        for row in sorted(set(indices), reverse=True):

            if 0 <= row < len(self.rows):

                self.beginRemoveRows(QtCore.QModelIndex(), row, row)

                del self.rows[row]

                self.endRemoveRows()


    def _coerce_row_impl(self, row: Mapping[str, Any]) -> Dict[str, Any]:

        coerced: Dict[str, Any] = {}

        for spec in self.columns:

            key = spec["key"]

            value = row.get(key) if isinstance(row, Mapping) else None


            if spec["type"] == "bool":

                coerced[key] = bool(value)

            elif spec["type"] == "numeric":

                if value in (None, "", False):

                    coerced[key] = None

                else:

                    try:

                        coerced[key] = float(value)

                    except (TypeError, ValueError):

                        coerced[key] = None

            else:

                coerced[key] = value

        return coerced


    def _coerce_row(self, row: Mapping[str, Any]) -> Dict[str, Any]:

        return self._coerce_row_impl(row)



    def export_rows(self) -> List[Dict[str, Any]]:

        return [dict(row) for row in self.rows]



    def contains_def_peca(self, def_peca: str) -> bool:

        if not def_peca:

            return False

        return any((r.get("def_peca") or "").strip().lower() == def_peca.strip().lower() for r in self.rows)



    def recalculate_all(self) -> None:

        if not self.rows:

            return

        page_ref = getattr(self, "_page", None)

        session = getattr(page_ref, "session", None) if page_ref is not None else None

        context = getattr(page_ref, "context", None) if page_ref is not None else None

        if session is not None and context is not None:

            try:

                rules = svc_custeio.load_qt_rules(session, context)

            except Exception:

                rules = svc_custeio.DEFAULT_QT_RULES

        else:

            rules = svc_custeio.DEFAULT_QT_RULES

        divisor = 1.0

        current_group_uid = str(uuid.uuid4())

        current_parent_row: Optional[Dict[str, Any]] = None

        current_parent_uid: Optional[str] = None

        for row in self.rows:

            row["_uid"] = row.get("_uid") or str(uuid.uuid4())

            row["comp_res"] = row.get("comp")

            row["larg_res"] = row.get("larg")

            row["esp_res"] = row.get("esp")

            def_peca = row.get("def_peca") or ""

            if not def_peca.strip():

                row["_row_type"] = "separator"

                row["_group_uid"] = row.get("_group_uid") or current_group_uid

                row.pop("icon_hint", None)

                row["_qt_divisor"] = divisor

                row["_qt_parent_factor"] = None

                row["_qt_child_factor"] = None

                row["qt_total"] = None

                current_parent_row = None

                current_parent_uid = None

                continue

            if self._is_division_row(row):

                row["_row_type"] = "division"

                try:

                    divisor = float(row.get("qt_mod") or 1.0)

                except Exception:

                    divisor = 1.0

                divisor = max(divisor, 1.0)

                current_group_uid = row.get("_group_uid") or str(uuid.uuid4())

                row["_group_uid"] = current_group_uid

                row["_qt_divisor"] = divisor

                row["_qt_parent_factor"] = None

                row["_qt_child_factor"] = None

                row["qt_total"] = divisor

                if getattr(self, "_page", None):

                    row.setdefault("icon_hint", self._page._icon("division"))

                current_parent_row = None

                current_parent_uid = None

                continue

            if "+" in def_peca:

                row["_row_type"] = "parent"

                current_group_uid = row.get("_group_uid") or str(uuid.uuid4())

                row["_group_uid"] = current_group_uid

                current_parent_row = row

                current_parent_uid = row["_uid"]

                row["_regra_nome"] = None

            else:

                regra_nome = svc_custeio.identificar_regra(def_peca, rules)

                if regra_nome:

                    row["_row_type"] = "child"

                    row["_group_uid"] = row.get("_group_uid") or current_group_uid

                    row["_parent_uid"] = current_parent_uid

                    row["_regra_nome"] = regra_nome

                else:

                    row["_row_type"] = "normal"

                    row["_group_uid"] = row.get("_group_uid") or current_group_uid

                    current_parent_row = None

                    current_parent_uid = None

                    row["_regra_nome"] = None

            row["_qt_divisor"] = divisor

            row_type = row.get("_row_type")

            if row_type != "division":
                row.pop("icon_hint", None)

            if row_type == "child" and current_parent_row is not None:

                try:

                    parent_factor = float(current_parent_row.get("qt_und") or 1.0)

                except Exception:

                    parent_factor = 1.0

            else:

                try:

                    parent_factor = float(row.get("qt_mod") or 1.0)

                except Exception:

                    parent_factor = 1.0

                if row_type not in ("child", "separator") and row.get("qt_mod") in (None, ""):

                    row["qt_mod"] = parent_factor

            child_factor_value = row.get("qt_und")

            if row_type == "child" and current_parent_row is not None:

                regra_nome = row.get("_regra_nome") or row.get("_child_source")

                regra_nome = svc_custeio.identificar_regra(regra_nome or "", rules)

                try:

                    child_factor = svc_custeio.calcular_qt_filhos(regra_nome, current_parent_row, row, divisor, parent_factor, rules)

                except Exception:

                    try:

                        child_factor = float(child_factor_value or 1.0)

                    except Exception:

                        child_factor = 1.0

                row["qt_und"] = child_factor

            else:

                try:

                    child_factor = float(child_factor_value or 1.0)

                except Exception:

                    child_factor = 1.0

            row["_qt_parent_factor"] = parent_factor

            row["_qt_child_factor"] = child_factor

            try:

                total = float(divisor) * float(parent_factor) * float(child_factor)

            except Exception:

                total = 0.0

            row["qt_total"] = total if total else None

            if row.get("esp_mp") not in (None, ""):

                row["esp"] = row.get("esp_mp")

        left = self._column_index.get("qt_mod")

        right = self._column_index.get("qt_total")

        if left is None or right is None:

            return

        top_left = self.index(0, left)

        bottom_right = self.index(len(self.rows) - 1, right)

        self.dataChanged.emit(
            top_left,
            bottom_right,
            [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.ToolTipRole],
        )

        top_left_all = self.index(0, 0)

        bottom_right_all = self.index(len(self.rows) - 1, len(self.columns) - 1)

        self.dataChanged.emit(top_left_all, bottom_right_all, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole])

        if getattr(self, "_page", None):
            self._page._apply_collapse_state()


    def update_row_fields(self, row_index: int, updates: Mapping[str, Any], skip_keys: Optional[Sequence[str]] = None) -> None:

        if not (0 <= row_index < len(self.rows)):

            return

        skip = set(skip_keys or ())

        row = self.rows[row_index]

        for spec in self.columns:

            key = spec["key"]

            if key in skip or key == "id" or key not in updates:

                continue

            value = updates[key]

            if spec["type"] == "bool":

                row[key] = bool(value)

            elif spec["type"] == "numeric":

                if value in (None, "", False):

                    row[key] = None

                else:

                    try:

                        row[key] = float(value)

                    except (TypeError, ValueError):

                        row[key] = None

            else:

                row[key] = value

        if "esp_mp" in updates:

            row["esp"] = updates.get("esp_mp")

        elif row.get("esp_mp") not in (None, ""):

            row["esp"] = row.get("esp_mp")

        top_left = self.index(row_index, 0)

        bottom_right = self.index(row_index, len(self.columns) - 1)

        self.dataChanged.emit(top_left, bottom_right, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.CheckStateRole, QtCore.Qt.FontRole, QtCore.Qt.ToolTipRole])


    def _emit_font_updates(self, row_index: int) -> None:

        if not (0 <= row_index < len(self.rows)):

            return

        for col in self._italic_columns_idx:

            idx = self.index(row_index, col)

            self.dataChanged.emit(idx, idx, [QtCore.Qt.FontRole, QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole])


    def set_blk(self, row_index: int, value: bool) -> None:

        if not (0 <= row_index < len(self.rows)):

            return

        target = bool(value)

        current = bool(self.rows[row_index].get("blk"))

        if current == target:

            return

        self.rows[row_index]["blk"] = target

        if self._blk_column is not None:

            blk_index = self.index(row_index, self._blk_column)

            self.dataChanged.emit(blk_index, blk_index, [QtCore.Qt.DisplayRole, QtCore.Qt.CheckStateRole, QtCore.Qt.FontRole])

        self._emit_font_updates(row_index)



class MatDefaultDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, parent=None, page: Optional["CusteioItemsPage"] = None):

        super().__init__(parent)

        self._page = page


    def _options_for_index(self, index: QtCore.QModelIndex) -> List[str]:

        page = self._page

        if page is None or not getattr(page, "context", None):

            return svc_custeio.lista_mat_default()

        session = getattr(page, "session", None)

        context = page.context

        if not session or not context:

            return svc_custeio.lista_mat_default()

        familia: Optional[str] = None

        try:

            row = page.table_model.rows[index.row()]

            familia = row.get("familia") or row.get("mat_default")

        except Exception:

            familia = None

        options = svc_custeio.lista_mat_default(session, context, familia)

        return options or svc_custeio.lista_mat_default()


    def createEditor(self, parent, option, index):

        editor = QtWidgets.QComboBox(parent)

        editor.setEditable(False)

        editor.setInsertPolicy(QtWidgets.QComboBox.NoInsert)

        editor.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)

        seen = set()

        editor.addItem("")

        seen.add("")

        current_value = (index.data(QtCore.Qt.EditRole) or "").strip()

        if current_value and current_value not in seen:

            editor.addItem(current_value)

            seen.add(current_value)

        for option_text in self._options_for_index(index):

            text = (option_text or "").strip()

            if not text or text in seen:

                continue

            editor.addItem(text)

            seen.add(text)

        editor.setProperty("_custeio_editor", True)

        QtCore.QTimer.singleShot(0, editor.showPopup)

        return editor


    def setEditorData(self, editor, index):

        value = index.data(QtCore.Qt.EditRole) or ""

        pos = editor.findText(value)

        if pos >= 0:

            editor.setCurrentIndex(pos)


    def setModelData(self, editor, model, index):

        text = editor.currentText().strip()

        model.setData(index, text, QtCore.Qt.EditRole)

        if self._page is not None:

            self._page._apply_mat_default_selection(index.row(), text)



    # ------------------------------------------------------------------

    def _coerce_row_impl(self, row: Mapping[str, Any]) -> Dict[str, Any]:

        coerced: Dict[str, Any] = {}

        for spec in self.columns:

            key = spec["key"]

            value = row.get(key) if isinstance(row, Mapping) else None



            if spec["type"] == "bool":

                coerced[key] = bool(value)

            elif spec["type"] == "numeric":

                if value in (None, "", False):

                    coerced[key] = None

                else:

                    try:

                        coerced[key] = float(value)

                    except (TypeError, ValueError):

                        coerced[key] = None

            else:

                coerced[key] = value

        return coerced


class AcabamentoDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate para coluna 'acabamento' que preenche um QComboBox com as
    opções de acabamentos disponíveis para o item em contexto."""

    def __init__(self, parent: Optional[QtCore.QObject] = None, page: Optional["CusteioItemsPage"] = None):
        super().__init__(parent)
        self._page = page

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        editor.setEditable(False)
        editor.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        editor.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)

        # Preencher opções: tenta obter via serviço com session+context, senão usa defaults
        options: List[str] = []
        if self._page is not None:
            session = getattr(self._page, "session", None)
            ctx = getattr(self._page, "context", None)
            try:
                options = svc_custeio.lista_acabamento(session, ctx)
            except Exception:
                options = []

        # Sempre incluir uma opção vazia
        seen = set()
        editor.addItem("")
        seen.add("")

        current_value = (index.data(QtCore.Qt.EditRole) or "").strip()
        if current_value and current_value not in seen:
            editor.addItem(current_value)
            seen.add(current_value)

        for opt in options:
            text = (opt or "").strip()
            if not text or text in seen:
                continue
            editor.addItem(text)
            seen.add(text)

        editor.setProperty("_custeio_editor", True)
        QtCore.QTimer.singleShot(0, editor.showPopup)
        return editor

    def setEditorData(self, editor, index):
        value = index.data(QtCore.Qt.EditRole) or ""
        pos = editor.findText(value)
        if pos >= 0:
            editor.setCurrentIndex(pos)

    def setModelData(self, editor, model, index):
        text = editor.currentText().strip()
        model.setData(index, text, QtCore.Qt.EditRole)





class CusteioItemsPage(QtWidgets.QWidget):

    CATEGORY_ROLE = QtCore.Qt.UserRole + 1


    ICON_MAP = {
        "insert_above": QtWidgets.QStyle.SP_ArrowUp,
        "insert_below": QtWidgets.QStyle.SP_ArrowDown,
        "delete": QtWidgets.QStyle.SP_TrashIcon,
        "copy": QtWidgets.QStyle.SP_FileDialogDetailedView,
        "paste": QtWidgets.QStyle.SP_DialogOpenButton,
        "select_mp": QtWidgets.QStyle.SP_DirOpenIcon,
        "refresh": QtWidgets.QStyle.SP_BrowserReload,
        "save": QtWidgets.QStyle.SP_DialogSaveButton,
        "division": QtWidgets.QStyle.SP_FileDialogNewFolder,
    }



    def __init__(self, parent=None, current_user=None):

        super().__init__(parent)

        self.current_user = current_user

        self.session = SessionLocal()

        self.context = None

        self.current_orcamento_id: Optional[int] = None

        self.current_item_id: Optional[int] = None



        self._updating_checks = False  # guarda contra reentrÃ¢ncia ao propagar check

        self._clipboard_rows: List[Dict[str, Any]] = []

        self.table_model = CusteioTableModel(self)

        self.table_model._page = self

        self._collapsed_groups: Set[str] = set()

        self._setup_ui()

        self._populate_tree()

        self._update_summary()



    # ------------------------------------------------------------------ UI setup

    def _setup_ui(self) -> None:

        root = QtWidgets.QVBoxLayout(self)

        root.setContentsMargins(8, 8, 8, 8)

        root.setSpacing(8)



        # Header ---------------------------------------------------------

        header_layout = QtWidgets.QVBoxLayout()

        header_layout.setContentsMargins(0, 0, 0, 0)

        header_layout.setSpacing(6)



        self._base_title_text = "Custeio dos Items"

        self.lbl_title = QtWidgets.QLabel(f"{self._base_title_text} - Item: -")

        title_font = self.lbl_title.font()

        title_font.setBold(True)

        title_font.setPointSize(title_font.pointSize() + 2)

        self.lbl_title.setFont(title_font)

        header_layout.addWidget(self.lbl_title)



        self.lbl_descr = QtWidgets.QLabel("-")

        self.lbl_descr.setWordWrap(True)

        self.lbl_descr.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        header_layout.addWidget(self.lbl_descr)



        self.lbl_cliente = QtWidgets.QLabel("-")

        self.lbl_utilizador = QtWidgets.QLabel("-")

        self.lbl_ano = QtWidgets.QLabel("-")

        self.lbl_num = QtWidgets.QLabel("-")

        self.lbl_ver = QtWidgets.QLabel("-")

        self.lbl_altura = QtWidgets.QLabel("-")

        self.lbl_largura = QtWidgets.QLabel("-")

        self.lbl_profundidade = QtWidgets.QLabel("-")



        dims_layout = QtWidgets.QHBoxLayout()

        dims_layout.setSpacing(16)

        dims_layout.addWidget(QtWidgets.QLabel("Comp:"))

        dims_layout.addWidget(self.lbl_altura)

        dims_layout.addSpacing(16)

        dims_layout.addWidget(QtWidgets.QLabel("Largura:"))

        dims_layout.addWidget(self.lbl_largura)

        dims_layout.addSpacing(16)

        dims_layout.addWidget(QtWidgets.QLabel("Profundidade:"))

        dims_layout.addWidget(self.lbl_profundidade)

        dims_layout.addStretch(1)

        header_layout.addLayout(dims_layout)



        info_layout = QtWidgets.QHBoxLayout()

        info_layout.setSpacing(16)

        for caption, widget in [

            ("Cliente:", self.lbl_cliente),

            ("Utilizador:", self.lbl_utilizador),

            ("Ano:", self.lbl_ano),

            ("Num. Orcamento:", self.lbl_num),

            ("Versao:", self.lbl_ver),

        ]:

            label = QtWidgets.QLabel(caption)

            info_layout.addWidget(label)

            info_layout.addWidget(widget)

            info_layout.addSpacing(8)

        info_layout.addStretch(1)

        header_layout.addLayout(info_layout)



        root.addLayout(header_layout)




        # Splitter -------------------------------------------------------

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)

        splitter.setChildrenCollapsible(False)

        root.addWidget(splitter, 1)



        # Left panel -----------------------------------------------------

        panel_left = QtWidgets.QWidget(splitter)

        panel_layout = QtWidgets.QVBoxLayout(panel_left)

        panel_layout.setContentsMargins(0, 0, 0, 0)

        panel_layout.setSpacing(6)



        search_layout = QtWidgets.QHBoxLayout()

        search_layout.setContentsMargins(0, 0, 0, 0)

        search_layout.setSpacing(4)



        self.edit_search = QtWidgets.QLineEdit()

        self.edit_search.setPlaceholderText("Buscar... (Ctrl+F)")

        self.edit_search.textChanged.connect(self._on_search_changed)

        search_layout.addWidget(self.edit_search, 1)



        self.btn_clear_search = QtWidgets.QToolButton()

        self.btn_clear_search.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogResetButton))

        self.btn_clear_search.setToolTip("Limpar pesquisa e selecao")

        self.btn_clear_search.clicked.connect(self._on_clear_filters)

        search_layout.addWidget(self.btn_clear_search)



        panel_layout.addLayout(search_layout)



        controls_layout = QtWidgets.QHBoxLayout()

        controls_layout.setSpacing(6)



        self.btn_expand = QtWidgets.QToolButton()

        self.btn_expand.setText("Expandir")

        self.btn_expand.clicked.connect(self._on_expand_all)

        controls_layout.addWidget(self.btn_expand)



        self.btn_collapse = QtWidgets.QToolButton()

        self.btn_collapse.setText("Colapsar")

        self.btn_collapse.clicked.connect(self._on_collapse_all)

        controls_layout.addWidget(self.btn_collapse)



        self.chk_selected_only = QtWidgets.QCheckBox("So selecionados")

        self.chk_selected_only.toggled.connect(self._on_selected_only_toggled)

        controls_layout.addWidget(self.chk_selected_only)



        controls_layout.addStretch(1)

        panel_layout.addLayout(controls_layout)



        # Modelo/Proxy da Ãrvore

        self.tree_model = QtGui.QStandardItemModel()

        self.tree_model.setHorizontalHeaderLabels(["Pecas"])

        self.tree_model.itemChanged.connect(self._on_tree_item_changed)



        self.proxy_model = CusteioTreeFilterProxy(self)

        self.proxy_model.setSourceModel(self.tree_model)



        self.tree = QtWidgets.QTreeView()

        self.tree.setModel(self.proxy_model)

        self.tree.setUniformRowHeights(True)

        self.tree.setHeaderHidden(False)

        self.tree.setAnimated(True)

        self.tree.setAlternatingRowColors(True)

        self.tree.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)



        panel_layout.addWidget(self.tree, 1)



        footer_layout = QtWidgets.QHBoxLayout()

        footer_layout.setSpacing(12)



        self.lbl_summary = QtWidgets.QLabel("Selecionados: 0")

        footer_layout.addWidget(self.lbl_summary)

        footer_layout.addStretch(1)



        panel_layout.addLayout(footer_layout)



        self.btn_add = QtWidgets.QPushButton("Adicionar Selecoes")

        self.btn_add.setDefault(True)

        self.btn_add.clicked.connect(self._on_add_selected)

        panel_layout.addWidget(self.btn_add)



        splitter.addWidget(panel_left)



        # Right panel ----------------------------------------------------

        panel_right = QtWidgets.QWidget(splitter)

        right_layout = QtWidgets.QVBoxLayout(panel_right)

        right_layout.setContentsMargins(12, 12, 12, 12)

        right_layout.setSpacing(8)



        actions_layout = QtWidgets.QHBoxLayout()

        actions_layout.setSpacing(8)

        self.btn_refresh = QtWidgets.QPushButton("Atualizar")

        self.btn_save = QtWidgets.QPushButton("Guardar Dados Custeio")

        actions_layout.addWidget(self.btn_refresh)

        actions_layout.addWidget(self.btn_save)

        actions_layout.addStretch(1)

        right_layout.addLayout(actions_layout)



        self.table_view = CusteioTableView()

        self.table_view.setModel(self.table_model)

        self.table_view.setAlternatingRowColors(True)

        self.table_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.table_view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.table_view.setEditTriggers(
            QtWidgets.QAbstractItemView.SelectedClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )

        self.table_view.setStyleSheet(
            "QTableView::item:selected { background-color: #d9d9d9; color: #000000; }\n"
            "QTableView::item:selected:!active { background-color: #d9d9d9; color: #000000; }"
        )

        self.table_view.setMouseTracking(True)

        self.table_view.horizontalHeader().setStretchLastSection(False)

        self.table_view.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.table_view.horizontalHeader().setDefaultSectionSize(96)

        self._apply_initial_column_widths()

        for col_index, spec in enumerate(self.table_model.columns):
            if spec["type"] == "numeric":
                self.table_view.setItemDelegateForColumn(col_index, NumericLineEditDelegate(self.table_view, spec))

        try:

            mat_col = self.table_model.column_keys.index("mat_default")

            self.table_view.setItemDelegateForColumn(mat_col, MatDefaultDelegate(self.table_view, self))

        except ValueError:

            pass

        # Registar delegate para a coluna 'acabamento' (drop-down de acabamentos)
        try:
            acb_col = self.table_model.column_keys.index("acabamento")
            self.table_view.setItemDelegateForColumn(acb_col, AcabamentoDelegate(self.table_view, self))
        except ValueError:
            pass

        self.table_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        self.table_view.customContextMenuRequested.connect(self._on_table_context_menu)

        self.table_view.clicked.connect(self._on_table_clicked)

        right_layout.addWidget(self.table_view, 1)



        self.lbl_placeholder = QtWidgets.QLabel(

            "Area de trabalho do custeio (tab_custeio_items).\n"

            "Selecione pecas e utilize o painel para adicionar linhas."

        )

        self.lbl_placeholder.setAlignment(QtCore.Qt.AlignCenter)

        self.lbl_placeholder.setStyleSheet("color: #777777; font-style: italic;")

        right_layout.addWidget(self.lbl_placeholder)



        splitter.addWidget(panel_right)

        splitter.setStretchFactor(0, 0)

        splitter.setStretchFactor(1, 1)



        self.btn_refresh.clicked.connect(self._on_refresh_custeio)

        self.btn_save.clicked.connect(self._on_save_custeio)

        self._update_table_placeholder_visibility()



        # Shortcuts ------------------------------------------------------

        shortcut_find = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F"), self)

        shortcut_find.activated.connect(self.edit_search.setFocus)



    def _apply_initial_column_widths(self) -> None:

        header = self.table_view.horizontalHeader()
        header.setMinimumSectionSize(40)
        defaults = COLUMN_WIDTH_DEFAULTS
        for index, spec in enumerate(self.table_model.columns):
            width = defaults.get(spec['key'])
            if width:
                self.table_view.setColumnWidth(index, width)



    # ------------------------------------------------------------------ Tree creation

    def _populate_tree(self) -> None:

        """ConstrÃ³i a Ã¡rvore a partir do dicionÃ¡rio retornado pelo serviÃ§o."""

        self.tree_model.blockSignals(True)

        self.tree_model.removeRows(0, self.tree_model.rowCount())

        self.tree_model.setColumnCount(1)



        definition = svc_custeio.obter_arvore()

        for node in definition:

            item = self._create_item(node, parent_path=())

            if item is not None:

                self.tree_model.appendRow(item)



        self.tree_model.blockSignals(False)

        self.proxy_model.invalidate()

        self.tree.expandToDepth(0)



    def _create_item(self, node: Dict[str, Any], parent_path: Sequence[str]) -> Optional[QtGui.QStandardItem]:

        """

        Cria um QStandardItem:

          - pais: checkable + flags de tri-state; Ã­cone de pasta;

          - folhas: checkable; Ã­cone de ficheiro.

        """

        label = str(node.get("label", "")).strip()

        if not label:

            return None



        item = QtGui.QStandardItem(label)

        item.setEditable(False)

        item.setCheckable(True)

        item.setToolTip(label)

        item.setCheckState(QtCore.Qt.Unchecked)



        # guarda caminho amigÃ¡vel (usado na recolha de seleÃ§Ã£o)

        path = tuple(parent_path) + (label,)

        item.setData(" > ".join(path), self.CATEGORY_ROLE)



        children = node.get("children") or []

        if children:

            # Pais: checkable + (se existir) tri-state

            flags = item.flags() | QtCore.Qt.ItemIsUserCheckable

            if TRISTATE_FLAG:

                flags |= TRISTATE_FLAG

            item.setFlags(flags)



            icon = self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon)

            item.setIcon(icon)

            for child in children:

                child_item = self._create_item(child, parent_path=path)

                if child_item is not None:

                    item.appendRow(child_item)

        else:

            icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)

            item.setIcon(icon)



        return item



    # ------------------------------------------------------------------ Header helpers

    def _reset_header(self) -> None:

        base_title = getattr(self, "_base_title_text", "Custeio dos Items")
        self.lbl_title.setText(f"{base_title} - Item: -")

        self.lbl_descr.setText("-")

        self.lbl_cliente.setText("-")

        self.lbl_utilizador.setText("-")

        self.lbl_ano.setText("-")

        self.lbl_num.setText("-")

        self.lbl_ver.setText("-")

        self.lbl_altura.setText("-")

        self.lbl_largura.setText("-")

        self.lbl_profundidade.setText("-")



    def _apply_orcamento_header(self, orcamento: Optional[Orcamento]) -> None:

        if not orcamento:

            self.lbl_cliente.setText("-")

            self.lbl_utilizador.setText("-")

            self.lbl_ano.setText("-")

            self.lbl_num.setText("-")

            self.lbl_ver.setText("-")

            return



        self.lbl_cliente.setText(

            svc_custeio.obter_cliente_nome(self.session, getattr(orcamento, "client_id", None))

        )

        user_name = svc_custeio.obter_user_nome(

            self.session,

            getattr(orcamento, "updated_by", None) or getattr(orcamento, "created_by", None),

        )

        self.lbl_utilizador.setText(user_name)

        self.lbl_ano.setText(str(getattr(orcamento, "ano", "-") or "-"))

        self.lbl_num.setText(str(getattr(orcamento, "num_orcamento", "-") or "-"))

        self.lbl_ver.setText(str(getattr(orcamento, "versao", "-") or "-"))



    def _apply_item_header(self, item: Optional[OrcamentoItem]) -> None:

        base_title = getattr(self, "_base_title_text", "Custeio dos Items")

        if not item:

            self.lbl_title.setText(f"{base_title} - Item: -")

            self.lbl_descr.setText("-")

            self.lbl_altura.setText("-")

            self.lbl_largura.setText("-")

            self.lbl_profundidade.setText("-")

            return



        numero = getattr(item, "item_ord", None) or getattr(item, "item", None) or getattr(item, "id_item", None)

        self.lbl_title.setText(f"{base_title} - Item: {numero}")

        descricao = (item.descricao or "").strip()

        self.lbl_descr.setText(descricao or "-")



        self.lbl_altura.setText(self._format_dim(getattr(item, "altura", None)))

        self.lbl_largura.setText(self._format_dim(getattr(item, "largura", None)))

        self.lbl_profundidade.setText(self._format_dim(getattr(item, "profundidade", None)))



    def _format_dim(self, value: Any) -> str:

        try:

            if value in (None, ""):

                return "-"

            return f"{float(value):.1f} mm"

        except Exception:

            return str(value)



    # ------------------------------------------------------------------ Slots

    def _on_expand_all(self) -> None:

        self.tree.expandAll()



    def _on_collapse_all(self) -> None:

        self.tree.collapseAll()

        self.tree.expandToDepth(0)



    def _on_selected_only_toggled(self, checked: bool) -> None:

        self.proxy_model.set_only_checked(checked)

        self.tree.expandAll()

        if not checked:

            self.tree.expandToDepth(0)



    def _on_search_changed(self, text: str) -> None:

        expression = QtCore.QRegularExpression(

            QtCore.QRegularExpression.escape(text),

            QtCore.QRegularExpression.CaseInsensitiveOption

        )

        self.proxy_model.setFilterRegularExpression(expression)

        self.tree.expandAll()

        if not text:

            self.tree.expandToDepth(0)



    def _on_clear_filters(self) -> None:

        """Limpa busca + seleÃ§Ã£o (todas as folhas e pais)."""

        self.edit_search.clear()

        self.chk_selected_only.setChecked(False)

        self._clear_all_checks()   # agora limpa recursivamente

        self.tree.expandToDepth(0)



    def _clear_all_checks(self) -> None:

        """Desmarca tudo recursivamente (raiz -> folhas)."""

        self._updating_checks = True

        try:

            for row in range(self.tree_model.rowCount()):

                item = self.tree_model.item(row, 0)

                if item is not None:

                    self._propagate_to_children(item, QtCore.Qt.Unchecked)  # ***

                    item.setCheckState(QtCore.Qt.Unchecked)                 # mantÃ©m pai coerente

        finally:

            self._updating_checks = False

        self._update_summary()



    def _on_tree_item_changed(self, item: QtGui.QStandardItem) -> None:

        """Propaga estado aos filhos e recalcula estado dos pais (tri-state)."""

        if self._updating_checks:

            return



        self._updating_checks = True

        try:

            if item.hasChildren():

                self._propagate_to_children(item, item.checkState())

            self._update_parent_state(item)

        finally:

            self._updating_checks = False

        self._update_summary()



    def _propagate_to_children(self, item: QtGui.QStandardItem, state: QtCore.Qt.CheckState) -> None:

        for row in range(item.rowCount()):

            child = item.child(row)

            if child is None:

                continue

            child.setCheckState(state)

            if child.hasChildren():

                self._propagate_to_children(child, state)



    def _update_parent_state(self, item: QtGui.QStandardItem) -> None:

        parent = item.parent()

        if parent is None:

            return



        checked = 0

        partial = False

        total = parent.rowCount()

        for row in range(total):

            child = parent.child(row)

            if child is None:

                continue

            state = child.checkState()

            if state == QtCore.Qt.PartiallyChecked:

                partial = True

            elif state == QtCore.Qt.Checked:

                checked += 1



        if partial or (0 < checked < total):

            parent.setCheckState(QtCore.Qt.PartiallyChecked)

        elif checked == total:

            parent.setCheckState(QtCore.Qt.Checked)

        else:

            parent.setCheckState(QtCore.Qt.Unchecked)



        # garante flags corretas nos pais (tri-state + checkable)

        parent.setCheckable(True)

        flags = parent.flags() | QtCore.Qt.ItemIsUserCheckable

        if TRISTATE_FLAG:

            flags |= TRISTATE_FLAG

        parent.setFlags(flags)



        # sobe na arvore

        self._update_parent_state(parent)



    def _on_add_selected(self) -> None:

        if not self.context:

            QtWidgets.QMessageBox.information(self, "Informacao", "Nenhum item selecionado.")

            return



        selections = self._gather_checked_items()

        if not selections:

            QtWidgets.QMessageBox.information(self, "Informacao", "Nenhuma peca selecionada.")

            return



        novas_linhas = svc_custeio.gerar_linhas_para_selecoes(self.session, self.context, selections)

        if not novas_linhas:

            QtWidgets.QMessageBox.warning(self, "Aviso", "Nao foi possivel gerar dados para as selecoes.")

            return
        self.table_model.append_rows(novas_linhas)

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()

        self._clear_all_checks()



    def _on_refresh_custeio(self) -> None:
        if not self.context:
            QtWidgets.QMessageBox.information(self, "Informacao", "Nenhum item selecionado.")
            return
        if hasattr(self.session, "expire_all"):
            self.session.expire_all()
        self._apply_updates_from_items()
        self.table_model.recalculate_all()
        self._update_table_placeholder_visibility()


    def _on_save_custeio(self) -> None:

        if not self.context:

            QtWidgets.QMessageBox.information(self, "Informacao", "Nenhum item selecionado.")

            return

        linhas = self.table_model.export_rows()

        try:

            svc_custeio.salvar_custeio_items(self.session, self.context, linhas)

        except Exception as exc:

            self.session.rollback()

            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao guardar Dados Custeio: {exc}")

            return

        QtWidgets.QMessageBox.information(self, "Sucesso", "Dados de custeio guardados.")

        self._reload_custeio_rows()

        self._apply_updates_from_items()

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()



    def _reload_custeio_rows(self) -> None:

        if not self.context:

            self.table_model.clear()

            self._update_table_placeholder_visibility()

            return

        linhas = svc_custeio.listar_custeio_items(self.session, self.context.orcamento_id, self.context.item_id)

        self.table_model.load_rows(linhas)

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()



    def _update_table_placeholder_visibility(self) -> None:
        has_rows = self.table_model.rowCount() > 0
        if has_rows:
            self.lbl_placeholder.hide()
        else:
            if self.context is None:
                self.lbl_placeholder.setText(
                    "Selecione um item do orcamento e utilize o painel a esquerda para adicionar pecas."
                )
            else:
                self.lbl_placeholder.setText(
                    "Selecione pecas no painel a esquerda e utilize o botao Adicionar Selecoes."
                )
            self.lbl_placeholder.show()
        self.btn_save.setEnabled(self.context is not None and has_rows)
        self.btn_refresh.setEnabled(has_rows)



    def _apply_collapse_state(self) -> None:

        if not hasattr(self, "table_view"):
            return

        collapsed = getattr(self, "_collapsed_groups", set())
        current_group = None
        row_count = self.table_model.rowCount()

        for idx in range(row_count):
            row = self.table_model.rows[idx]
            row_type = row.get("_row_type")
            group_uid = row.get("_group_uid") or current_group

            if row_type == "division":
                current_group = group_uid
                self.table_view.setRowHidden(idx, False)
                continue

            hide = bool(group_uid in collapsed) if group_uid else False
            self.table_view.setRowHidden(idx, hide)

        self.table_view.viewport().update()


    def _icon(self, key: str) -> QtGui.QIcon:

        style = self.style() or QtWidgets.QApplication.style()

        return style.standardIcon(self.ICON_MAP.get(key, QtWidgets.QStyle.SP_FileIcon))


    def _selected_table_rows(self) -> List[int]:

        selection = self.table_view.selectionModel()

        if not selection:

            return []

        return sorted({index.row() for index in selection.selectedRows()})


    def _on_table_clicked(self, index: QtCore.QModelIndex) -> None:

        if not index.isValid():

            return

        spec = self.table_model.columns[index.column()]

        row_data = self.table_model.rows[index.row()]

        if spec["key"] == "id" and row_data.get("_row_type") == "division":

            group_uid = row_data.get("_group_uid")

            if group_uid:

                if group_uid in self._collapsed_groups:

                    self._collapsed_groups.remove(group_uid)

                else:

                    self._collapsed_groups.add(group_uid)

                self._apply_collapse_state()

                self.table_model.dataChanged.emit(index, index, [QtCore.Qt.DisplayRole])

            return

        if spec["type"] == "bool":

            current = bool(row_data.get(spec["key"]))

            new_state = QtCore.Qt.Unchecked if current else QtCore.Qt.Checked

            self.table_model.setData(index, new_state, QtCore.Qt.CheckStateRole)


    def _on_table_context_menu(self, pos: QtCore.QPoint) -> None:

        index = self.table_view.indexAt(pos)

        selection = self.table_view.selectionModel()

        if index.isValid() and selection and not selection.isRowSelected(index.row()):

            selection.select(index, QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.Rows)

        selected_rows = self._selected_table_rows()

        menu = QtWidgets.QMenu(self.table_view)

        action_insert_above = menu.addAction(self._icon("insert_above"), "Inserir linha vazia acima")

        action_insert_below = menu.addAction(self._icon("insert_below"), "Inserir linha vazia abaixo")

        action_delete = menu.addAction(self._icon("delete"), "Eliminar linha(s)")

        menu.addSeparator()

        action_copy = menu.addAction(self._icon("copy"), "Copiar linha(s)")

        action_paste = menu.addAction(self._icon("paste"), "Colar linha(s)")

        menu.addSeparator()

        action_divisao = menu.addAction(self._icon("division"), "Inserir Linha 'DIVISAO INDEPENDENTE'")

        action_select_mp = menu.addAction(self._icon("select_mp"), "Selecionar Materia-Prima")

        if not selected_rows:

            action_insert_above.setEnabled(False)

            action_insert_below.setEnabled(False)

            action_delete.setEnabled(False)

            action_copy.setEnabled(False)

            action_select_mp.setEnabled(False)

            action_divisao.setEnabled(False)

        action_paste.setEnabled(bool(self._clipboard_rows))

        if len(selected_rows) != 1:

            action_select_mp.setEnabled(False)

        if not selected_rows:

            action_divisao.setEnabled(False)

        chosen = menu.exec(self.table_view.viewport().mapToGlobal(pos))

        if chosen is None:

            return

        if chosen == action_insert_above:

            self._insert_blank_rows(selected_rows, before=True)

            return

        if chosen == action_insert_below:

            self._insert_blank_rows(selected_rows, before=False)

            return

        if chosen == action_delete:

            self._delete_rows(selected_rows)

            return

        if chosen == action_copy:

            self._copy_rows(selected_rows)

            return

        if chosen == action_paste:

            self._paste_rows(selected_rows)

            return

        if chosen == action_divisao and selected_rows:

            self._insert_divisao_independente(selected_rows[-1])

            return

        if chosen == action_select_mp and selected_rows:

            self._on_select_materia_prima(selected_rows[0])


    def _insert_blank_rows(self, rows: Sequence[int], *, before: bool) -> None:

        if not rows:

            return

        for offset, row_index in enumerate(sorted(rows)):

            position = row_index + offset if before else row_index + 1 + offset

            linha = svc_custeio.linha_vazia()

            self.table_model.insert_rows(position, [linha])

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()


    def _insert_divisao_independente(self, anchor_row: int) -> None:

        position = anchor_row + 1 if anchor_row >= 0 else self.table_model.rowCount()

        linha = svc_custeio.linha_vazia()

        linha["def_peca"] = "DIVISAO INDEPENDENTE"

        linha["descricao"] = ""

        linha["descricao_livre"] = ""

        linha["qt_mod"] = 1.0

        linha["qt_und"] = 1.0

        linha["qt_total"] = 1.0

        linha["icon_hint"] = self._icon("division")

        self.table_model.insert_rows(position, [linha])

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()

        self.table_view.selectRow(position)



    def _delete_rows(self, rows: Sequence[int]) -> None:

        if not rows:

            return

        self.table_model.remove_rows(rows)

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()


    def _copy_rows(self, rows: Sequence[int]) -> None:

        if not rows:

            self._clipboard_rows = []

            return

        column_keys = tuple(self.table_model.column_keys)

        collected: List[Dict[str, Any]] = []

        for idx in rows:

            if 0 <= idx < self.table_model.rowCount():

                source_row = self.table_model.rows[idx]

                filtered = {key: source_row.get(key) for key in column_keys}

                collected.append(filtered)

        self._clipboard_rows = collected


    def _paste_rows(self, target_rows: Sequence[int]) -> None:

        if not self._clipboard_rows:

            QtWidgets.QMessageBox.information(self, "Informacao", "Nenhum dado copiado.")

            return

        if not target_rows:

            QtWidgets.QMessageBox.information(self, "Informacao", "Selecione linhas para colar.")

            return

        column_keys = tuple(self.table_model.column_keys)

        rows_to_insert: List[Dict[str, Any]] = []

        for source in self._clipboard_rows:

            filtered = {key: source.get(key) for key in column_keys}

            filtered["id"] = None

            rows_to_insert.append(filtered)

        insert_at = (max(target_rows) + 1) if target_rows else self.table_model.rowCount()

        self.table_model.insert_rows(insert_at, rows_to_insert)

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()


    def _on_select_materia_prima(self, row_index: int) -> None:

        if not (0 <= row_index < self.table_model.rowCount()):

            return

        row = self.table_model.rows[row_index]

        picker = MateriaPrimaPicker(

            self.session,

            parent=self,

            tipo=row.get("tipo"),

            familia=row.get("familia") or "PLACAS",

        )

        if picker.exec() != QtWidgets.QDialog.Accepted:

            return

        materia = picker.selected()

        if not materia:

            return

        updates = svc_custeio.dados_material(materia)

        self.table_model.update_row_fields(row_index, updates, skip_keys=("def_peca", "descricao_livre", "qt_mod", "qt_und", "comp", "larg", "esp"))

        orla_updates = svc_custeio.calcular_espessuras_orla(self.session, row)
        self.table_model.update_row_fields(row_index, orla_updates)

        self.table_model.set_blk(row_index, True)

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()


    def _apply_mat_default_selection(self, row_index: int, selection: str) -> None:

        if not self.context:

            return

        try:

            self.session.expire_all()

        except Exception:

            pass

        if not (0 <= row_index < self.table_model.rowCount()):

            return

        selection = (selection or "").strip()

        if not selection:

            return

        row = self.table_model.rows[row_index]

        familia = row.get("familia") or row.get("mat_default")

        material = svc_custeio.obter_material_por_familia(self.session, self.context, familia, selection)

        if not material:

            QtWidgets.QMessageBox.warning(self, "Aviso", f"Nao foi possivel localizar dados para '{selection}'.")

            return

        updates = svc_custeio.dados_material(material)

        self.table_model.update_row_fields(row_index, updates, skip_keys=("def_peca", "descricao_livre", "qt_mod", "qt_und", "comp", "larg", "esp"))

        orla_updates = svc_custeio.calcular_espessuras_orla(self.session, row)
        self.table_model.update_row_fields(row_index, orla_updates)

        row["mat_default"] = selection

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()



    def _apply_updates_from_items(self) -> None:

        if not self.context:

            return

        try:

            self.session.expire_all()

        except Exception:

            pass

        cache: Dict[str, Any] = {}
        orla_lookup = svc_custeio.obter_mapa_orlas(self.session)

        for idx, row in enumerate(self.table_model.rows):

            if row.get("blk"):

                continue

            familia_hint = row.get("familia")
            mat_default = (row.get("mat_default") or "").strip()

            if mat_default:

                grupo = mat_default

            else:

                def_peca = (row.get("def_peca") or "").strip()

                grupo = svc_custeio.grupo_por_def_peca(def_peca)

            if not grupo:

                continue

            cache_key = (grupo, familia_hint)

            if cache_key not in cache:

                cache[cache_key] = svc_custeio.obter_material_por_grupo(

                    self.session,

                    self.context,

                    grupo,

                    familia_hint,

                )

            material = cache[cache_key]

            if not material:

                continue

            updates = svc_custeio.dados_material(material)

            self.table_model.update_row_fields(

                idx,

                updates,

                skip_keys=("def_peca", "descricao_livre", "qt_mod", "qt_und", "comp", "larg", "esp", "mps", "mo", "orla", "blk", "mat_default", "nst"),

            )

            novo_default = updates.get("mat_default")

            if novo_default:

                atual_default = (row.get("mat_default") or "").strip().casefold()

                familia_atual = (row.get("familia") or "").strip().casefold()

                if not atual_default or atual_default == familia_atual:

                    row["mat_default"] = novo_default

            orla_updates = svc_custeio.aplicar_espessuras_orla(row, orla_lookup)
            self.table_model.update_row_fields(idx, orla_updates)

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()

    # ------------------------------------------------------------------ Helpers

    def _gather_checked_items(self) -> List[str]:

        collected: List[str] = []

        for row in range(self.tree_model.rowCount()):

            item = self.tree_model.item(row, 0)

            if item:

                collected.extend(self._collect_from_item(item))

        return collected



    def _collect_from_item(self, item: QtGui.QStandardItem) -> List[str]:

        if item.rowCount() == 0:

            if item.checkState() == QtCore.Qt.Checked:

                value = item.data(self.CATEGORY_ROLE)

                return [str(value)]

            return []



        results: List[str] = []

        for row in range(item.rowCount()):

            child = item.child(row)

            if child:

                results.extend(self._collect_from_item(child))

        return results



    def _update_summary(self) -> None:

        count = len(self._gather_checked_items())

        self.lbl_summary.setText(f"Selecionados: {count}")



    # ------------------------------------------------------------------ Public API

    def load_item(self, orcamento_id: int, item_id: Optional[int]) -> None:

        self.current_orcamento_id = orcamento_id

        normalized_item_id = item_id

        try:
            self.session.rollback()
        except Exception:
            pass

        if item_id is not None:
            try:
                normalized_item_id = int(item_id)
            except (TypeError, ValueError):
                normalized_item_id = item_id
            try:
                self.session.flush()
            except Exception:
                pass
            try:
                self.session.expire_all()
            except Exception:
                pass

        self.current_item_id = normalized_item_id

        self._collapsed_groups.clear()

        print(f"[Custeio.load_item] orcamento_id={orcamento_id} item_id={item_id}")
        if not orcamento_id:

            self.context = None

            self._reset_header()

            self.table_model.clear()

            self._update_table_placeholder_visibility()

            return



        orcamento = svc_custeio.carregar_orcamento(self.session, orcamento_id)

        if not orcamento:

            QtWidgets.QMessageBox.critical(self, "Erro", "Orcamento nao encontrado.")

            self.context = None

            self._reset_header()

            return



        self._reset_header()

        self._apply_orcamento_header(orcamento)



        item_obj: Optional[OrcamentoItem] = None

        if normalized_item_id:

            item_obj = svc_custeio.carregar_item(self.session, normalized_item_id)
            print(f"[Custeio.load_item] fetched item_obj id={getattr(item_obj, 'id_item', None) if item_obj else None}")
            if item_obj is None:

                QtWidgets.QMessageBox.warning(self, "Aviso", "Item nao encontrado para o orcamento selecionado.")
                ids = self.session.execute(select(OrcamentoItem.id_item).where(OrcamentoItem.id_orcamento == orcamento_id)).scalars().all()
                print(f'[Custeio.load_item] available ids={ids}')



        self._apply_item_header(item_obj)



        if item_obj is not None:

            try:

                self.context = svc_custeio.carregar_contexto(

                    self.session, orcamento_id, item_id=getattr(item_obj, "id_item", normalized_item_id)

                )

            except Exception:

                self.context = None

        else:

            self.context = None



        self._reload_custeio_rows()

        self._apply_updates_from_items()

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()



    def clear_context(self) -> None:

        self.context = None

        self.current_orcamento_id = None

        self.current_item_id = None

        self._collapsed_groups.clear()

        self._reset_header()

        self._clear_all_checks()

        self.table_model.clear()

        self._update_table_placeholder_visibility()
