#--- START OF FILE custeio_items.py ---



from __future__ import annotations



from typing import Any, Dict, List, Mapping, Optional, Sequence



from PySide6 import QtCore, QtGui, QtWidgets



from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento, OrcamentoItem

from Martelo_Orcamentos_V2.app.services import custeio_items as svc_custeio

from Martelo_Orcamentos_V2.app.db import SessionLocal
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

MANUAL_LOCK_KEYS = ITALIC_ON_BLK_KEYS | {"mat_default"}

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

        self.columns = svc_custeio.CUSTEIO_COLUMN_SPECS

        self.column_keys = [col["key"] for col in self.columns]

        self._column_index = {col["key"]: idx for idx, col in enumerate(self.columns)}

        self._blk_column = self._column_index.get("blk")

        self._italic_columns_idx = [self._column_index[key] for key in ITALIC_ON_BLK_KEYS if key in self._column_index]

        self._tooltip_columns_idx = [self._column_index[key] for key in CELL_TOOLTIP_KEYS if key in self._column_index]

        self._italic_font = QtGui.QFont()

        self._italic_font.setItalic(True)

        self.rows: List[Dict[str, Any]] = []



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



        spec = self.columns[col]

        key = spec["key"]

        value = self.rows[row].get(key)

        if role == QtCore.Qt.FontRole:

            if self.rows[row].get("blk") and key in ITALIC_ON_BLK_KEYS:

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

            flags |= QtCore.Qt.ItemIsEditable

        return flags



    def setData(self, index: QtCore.QModelIndex, value: Any, role: int = QtCore.Qt.EditRole) -> bool:

        if not index.isValid():

            return False



        row = index.row()

        col = index.column()

        spec = self.columns[col]

        key = spec["key"]



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



        if spec["type"] == "numeric":

            if value in (None, ""):

                self.rows[row][key] = None

            else:

                try:

                    self.rows[row][key] = float(value)

                except (TypeError, ValueError):

                    return False

        else:

            self.rows[row][key] = value



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

        for row in self.rows:

            qt_mod = row.get("qt_mod") or 0

            qt_und = row.get("qt_und") or 0

            try:

                total = float(qt_mod) * float(qt_und)

            except Exception:

                total = 0.0

            row["qt_total"] = total if total else None

            row["comp_res"] = row.get("comp")

            row["larg_res"] = row.get("larg")

            row["esp_res"] = row.get("esp")



        top_left = self.index(0, 0)

        bottom_right = self.index(len(self.rows) - 1, len(self.columns) - 1)

        self.dataChanged.emit(top_left, bottom_right, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole])


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



        self._setup_ui()

        self._populate_tree()

        self._update_summary()



    # ------------------------------------------------------------------ UI setup

    def _setup_ui(self) -> None:

        root = QtWidgets.QVBoxLayout(self)

        root.setContentsMargins(8, 8, 8, 8)

        root.setSpacing(8)



        # Header ---------------------------------------------------------

        header_layout = QtWidgets.QHBoxLayout()

        header_layout.setContentsMargins(0, 0, 0, 0)

        header_layout.setSpacing(20)



        self.lbl_title = QtWidgets.QLabel("Custeio dos Items")

        title_font = self.lbl_title.font()

        title_font.setBold(True)

        title_font.setPointSize(title_font.pointSize() + 2)

        self.lbl_title.setFont(title_font)



        title_box = QtWidgets.QVBoxLayout()

        title_box.setContentsMargins(0, 0, 0, 0)

        title_box.setSpacing(6)

        title_box.addWidget(self.lbl_title)



        item_box = QtWidgets.QVBoxLayout()

        item_box.setContentsMargins(0, 0, 0, 0)

        item_box.setSpacing(2)



        lbl_item_caption = QtWidgets.QLabel("Item")

        lbl_item_caption.setStyleSheet("color: #666666;")

        item_box.addWidget(lbl_item_caption)



        self.lbl_item = QtWidgets.QLabel("-")

        self.lbl_item.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        item_font = self.lbl_item.font()

        item_font.setBold(True)

        self.lbl_item.setFont(item_font)

        item_box.addWidget(self.lbl_item)



        lbl_descr_caption = QtWidgets.QLabel("Descricao")

        lbl_descr_caption.setStyleSheet("color: #666666;")

        item_box.addWidget(lbl_descr_caption)



        self.lbl_descr = QtWidgets.QLabel("-")

        self.lbl_descr.setWordWrap(True)

        self.lbl_descr.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        item_box.addWidget(self.lbl_descr)



        title_box.addLayout(item_box)



        header_layout.addLayout(title_box, 1)



        meta_box = QtWidgets.QVBoxLayout()

        meta_box.setContentsMargins(0, 0, 0, 0)

        meta_box.setSpacing(6)



        self.lbl_cliente = QtWidgets.QLabel("-")

        self.lbl_utilizador = QtWidgets.QLabel("-")

        self.lbl_ano = QtWidgets.QLabel("-")

        self.lbl_num = QtWidgets.QLabel("-")

        self.lbl_ver = QtWidgets.QLabel("-")

        self.lbl_altura = QtWidgets.QLabel("-")

        self.lbl_largura = QtWidgets.QLabel("-")

        self.lbl_profundidade = QtWidgets.QLabel("-")



        captions = [

            ("Cliente:", self.lbl_cliente),

            ("Utilizador:", self.lbl_utilizador),

            ("Ano:", self.lbl_ano),

            ("N.º Orçamento:", self.lbl_num),

            ("VersÃ£o:", self.lbl_ver),

        ]



        meta_row = QtWidgets.QHBoxLayout()

        meta_row.setSpacing(16)

        for caption, widget in captions:

            label = QtWidgets.QLabel(caption)

            meta_row.addWidget(label)

            meta_row.addWidget(widget)

            meta_row.addSpacing(8)

        meta_row.addStretch(1)



        meta_box.addLayout(meta_row)



        dims_layout = QtWidgets.QHBoxLayout()

        dims_layout.setSpacing(12)

        dims_layout.addWidget(QtWidgets.QLabel("Altura:"))

        dims_layout.addWidget(self.lbl_altura)

        dims_layout.addSpacing(16)

        dims_layout.addWidget(QtWidgets.QLabel("Largura:"))

        dims_layout.addWidget(self.lbl_largura)

        dims_layout.addSpacing(16)

        dims_layout.addWidget(QtWidgets.QLabel("Profundidade:"))

        dims_layout.addWidget(self.lbl_profundidade)

        dims_layout.addStretch(1)



        meta_box.addLayout(dims_layout)



        header_layout.addLayout(meta_box, 2)

        header_layout.addStretch(1)



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



        self.table_view = QtWidgets.QTableView()

        self.table_view.setModel(self.table_model)

        self.table_view.setAlternatingRowColors(True)

        self.table_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.table_view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.table_view.setStyleSheet(
            "QTableView::item:selected { background-color: #d9d9d9; color: #000000; }\n"
            "QTableView::item:selected:!active { background-color: #d9d9d9; color: #000000; }"
        )

        self.table_view.setMouseTracking(True)

        self.table_view.horizontalHeader().setStretchLastSection(False)

        self.table_view.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        try:

            mat_col = self.table_model.column_keys.index("mat_default")

            self.table_view.setItemDelegateForColumn(mat_col, MatDefaultDelegate(self.table_view, self))

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

        self.lbl_item.setText("-")

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

        if not item:

            self.lbl_item.setText("-")

            self.lbl_descr.setText("-")

            self.lbl_altura.setText("-")

            self.lbl_largura.setText("-")

            self.lbl_profundidade.setText("-")

            return



        numero = getattr(item, "item_ord", None) or getattr(item, "item", None) or getattr(item, "id_item", None)

        self.lbl_item.setText(str(numero))

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

        if spec["type"] == "bool":

            current = bool(self.table_model.rows[index.row()].get(spec["key"]))

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

        action_select_mp = menu.addAction(self._icon("select_mp"), "Selecionar Materia-Prima")

        if not selected_rows:

            action_insert_above.setEnabled(False)

            action_insert_below.setEnabled(False)

            action_delete.setEnabled(False)

            action_copy.setEnabled(False)

            action_select_mp.setEnabled(False)

        action_paste.setEnabled(bool(self._clipboard_rows))

        if len(selected_rows) != 1:

            action_select_mp.setEnabled(False)

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

        if chosen == action_select_mp and selected_rows:

            self._on_select_materia_prima(selected_rows[0])


    def _insert_blank_rows(self, rows: Sequence[int], *, before: bool) -> None:

        if not rows:

            return

        for offset, row_index in enumerate(sorted(rows)):

            position = row_index + offset if before else row_index + 1 + offset

            self.table_model.insert_rows(position, [svc_custeio.linha_vazia()])

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()


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

        self._clipboard_rows = [dict(self.table_model.rows[idx]) for idx in rows if 0 <= idx < self.table_model.rowCount()]


    def _paste_rows(self, target_rows: Sequence[int]) -> None:

        if not self._clipboard_rows:

            QtWidgets.QMessageBox.information(self, "Informacao", "Nenhum dado copiado.")

            return

        if not target_rows:

            QtWidgets.QMessageBox.information(self, "Informacao", "Selecione linhas para colar.")

            return

        for offset, row_index in enumerate(target_rows):

            source = self._clipboard_rows[offset % len(self._clipboard_rows)]

            updates = {k: v for k, v in source.items() if k != "id"}

            self.table_model.update_row_fields(row_index, updates)

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

        self.table_model.set_blk(row_index, True)

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()


    def _apply_mat_default_selection(self, row_index: int, selection: str) -> None:

        if not self.context:

            return

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

        self.table_model.set_blk(row_index, True)

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()



    def _apply_updates_from_items(self) -> None:

        if not self.context:

            return

        cache: Dict[str, Any] = {}

        for idx, row in enumerate(self.table_model.rows):

            if row.get("blk"):

                continue

            def_peca = (row.get("def_peca") or "").strip()

            grupo = svc_custeio.grupo_por_def_peca(def_peca)

            if not grupo:

                continue

            if grupo not in cache:

                cache[grupo] = svc_custeio.obter_material_por_grupo(

                    self.session,

                    self.context,

                    grupo,

                    row.get("familia"),

                )

            material = cache[grupo]

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

        self.current_item_id = item_id



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

        if item_id:

            item_obj = svc_custeio.carregar_item(self.session, item_id)

            if item_obj is None:

                QtWidgets.QMessageBox.warning(self, "Aviso", "Item nao encontrado para o orcamento selecionado.")



        self._apply_item_header(item_obj)



        if item_obj is not None:

            try:

                self.context = svc_custeio.carregar_contexto(

                    self.session, orcamento_id, item_id=getattr(item_obj, "id_item", item_id)

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

        self._reset_header()

        self._clear_all_checks()

        self.table_model.clear()

        self._update_table_placeholder_visibility()
