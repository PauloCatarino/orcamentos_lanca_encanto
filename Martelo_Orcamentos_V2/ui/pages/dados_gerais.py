from __future__ import annotations



from dataclasses import dataclass

from decimal import Decimal

from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence



from PySide6 import QtCore, QtWidgets

from PySide6.QtCore import Qt

from PySide6.QtWidgets import (

    QAbstractItemView,

    QCheckBox,

    QComboBox,

    QDialog,

    QDialogButtonBox,

    QFormLayout,

    QGridLayout,

    QGroupBox,

    QHBoxLayout,

    QInputDialog,

    QLabel,

    QLineEdit,

    QListWidget,

    QListWidgetItem,

    QPushButton,

    QRadioButton,

    QTableView,

    QTableWidget,

    QTableWidgetItem,

    QTabWidget,

    QVBoxLayout,

)



from Martelo_Orcamentos_V2.app.db import SessionLocal

from Martelo_Orcamentos_V2.app.models import Orcamento, Client, User

from Martelo_Orcamentos_V2.app.services import dados_gerais as svc_dg

from Martelo_Orcamentos_V2.app.services import materias_primas as svc_mp

from ..models.qt_table import SimpleTableModel





@dataclass

class ColumnSpec:

    header: str

    field: str

    kind: str = "text"  # text | decimal | money | percent | integer | choice | bool

    width: Optional[int] = None

    readonly: bool = False

    options: Optional[Callable[[], Sequence[str]]] = None

    visible: bool = True





def _decimal(value: Optional[Decimal]) -> str:

    if value in (None, ""):

        return ""

    try:

        dec = Decimal(str(value))

        return str(dec.quantize(Decimal('0.0001'))).replace('.', ',')

    except Exception:

        return str(value)





def _money(value: Optional[Decimal]) -> str:

    if value in (None, ""):

        return ""

    try:

        amount = Decimal(str(value)).quantize(Decimal('0.01'))

        return f"{str(amount).replace('.', ',')} €"

    except Exception:

        return str(value)





def _int_value(value) -> str:

    if value in (None, ""):

        return ""

    try:

        return str(int(Decimal(str(value))))

    except Exception:

        return str(value)





def _percent(value: Optional[Decimal]) -> str:

    if value in (None, ""):

        return ""

    if not isinstance(value, Decimal):

        try:

            value = Decimal(str(value))

        except Exception:

            return str(value)

    display = (value * Decimal('100')).quantize(Decimal('0.01'))

    return f"{str(display).replace('.', ',')} %"





class ChoiceDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, options_cb: Callable[[], Sequence[str]], parent=None):

        super().__init__(parent)

        self._options_cb = options_cb



    def paint(self, painter, option, index):

        combo_opt = QtWidgets.QStyleOptionComboBox()

        combo_opt.rect = option.rect

        combo_opt.state = option.state

        combo_opt.currentText = index.data(Qt.DisplayRole) or ""

        combo_opt.editable = False

        style = QtWidgets.QApplication.style()

        painter.save()

        style.drawComplexControl(QtWidgets.QStyle.ComplexControl.CC_ComboBox, combo_opt, painter)

        style.drawControl(QtWidgets.QStyle.ControlElement.CE_ComboBoxLabel, combo_opt, painter)

        painter.restore()



    def createEditor(self, parent, option, index):

        editor = QtWidgets.QComboBox(parent)

        editor.setEditable(False)

        self._refresh(editor, index.data(Qt.DisplayRole))

        return editor



    def setEditorData(self, editor, index):

        value = index.model().data(index, Qt.EditRole) or ""

        self._refresh(editor, value)

        pos = editor.findText(str(value))

        if pos < 0:

            editor.setCurrentIndex(-1)

        else:

            editor.setCurrentIndex(pos)



    def setModelData(self, editor, model, index):

        value = editor.currentText()

        model.setData(index, value, Qt.EditRole)



    def updateEditorGeometry(self, editor, option, index):

        editor.setGeometry(option.rect)



    def _refresh(self, editor: QtWidgets.QComboBox, current_value: Optional[str]) -> None:

        options = list(dict.fromkeys(self._options_cb() or []))

        current = (current_value or "").strip()

        if current and current not in options:

            options.insert(0, current)

        editor.blockSignals(True)

        editor.clear()

        editor.addItems(options)

        idx = editor.findText(current) if current else -1

        if idx >= 0:

            editor.setCurrentIndex(idx)

        editor.blockSignals(False)





class DadosGeraisTableModel(QtCore.QAbstractTableModel):

    def __init__(self, columns: Sequence[ColumnSpec], rows: Optional[List[Dict]] = None, parent=None):

        super().__init__(parent)

        self.columns = list(columns)

        self._rows: List[Dict] = rows or []

        self._field_index = {spec.field: idx for idx, spec in enumerate(self.columns)}



    # --- Qt API ---

    def rowCount(self, parent=QtCore.QModelIndex()):

        return 0 if parent.isValid() else len(self._rows)



    def columnCount(self, parent=QtCore.QModelIndex()):

        return 0 if parent.isValid() else len(self.columns)



    def data(self, index, role=Qt.DisplayRole):

        if not index.isValid():

            return None

        row = self._rows[index.row()]

        spec = self.columns[index.column()]

        value = row.get(spec.field)



        if role == Qt.DisplayRole:

            if spec.kind == "money":

                return _money(value)

            if spec.kind == "decimal":

                return _decimal(value)

            if spec.kind == "percent":

                return _percent(value)

            if spec.kind == "bool":

                return ""

            return "" if value is None else str(value)



        if role == Qt.EditRole:

            if spec.kind in {"money", "decimal"}:

                return _decimal(value)

            if spec.kind == "percent":

                if value in (None, ""):

                    return ""

                try:

                    dec = Decimal(str(value))

                    return f"{(dec * Decimal('100')):.4f}"

                except Exception:

                    return str(value)

            if spec.kind == "bool":

                return bool(value)

            return "" if value is None else str(value)



        if role == Qt.CheckStateRole and spec.kind == "bool":

            return Qt.Checked if bool(value) else Qt.Unchecked



        if role == Qt.TextAlignmentRole:

            if spec.kind in {"money", "decimal", "percent", "integer"}:

                if spec.field in {"comp_mp", "larg_mp", "esp_mp"}:

                    return int(Qt.AlignCenter | Qt.AlignVCenter)

                return int(Qt.AlignRight | Qt.AlignVCenter)

            if spec.kind == "bool":

                return int(Qt.AlignCenter | Qt.AlignVCenter)



        return None



    def headerData(self, section, orientation, role=Qt.DisplayRole):

        if role != Qt.DisplayRole:

            return None

        if orientation == Qt.Horizontal and 0 <= section < len(self.columns):

            return self.columns[section].header

        if orientation == Qt.Vertical:

            return section + 1

        return None



    def flags(self, index):

        if not index.isValid():

            return Qt.NoItemFlags

        spec = self.columns[index.column()]

        base = Qt.ItemIsSelectable | Qt.ItemIsEnabled

        if spec.kind == "bool":

            base |= Qt.ItemIsUserCheckable

        if not spec.readonly and spec.kind != "bool":

            base |= Qt.ItemIsEditable

        return base



    def setData(self, index, value, role=Qt.EditRole):

        if not index.isValid():

            return False

        spec = self.columns[index.column()]

        row = self._rows[index.row()]



        if spec.kind == "bool" and role == Qt.CheckStateRole:

            row[spec.field] = bool(value == Qt.Checked)

            self.dataChanged.emit(index, index, [Qt.CheckStateRole, Qt.DisplayRole])

            return True



        if role not in (Qt.EditRole, Qt.DisplayRole):

            return False



        if spec.kind in {"money", "decimal"}:

            row[spec.field] = self._parse_decimal(value)

        elif spec.kind == "percent":

            row[spec.field] = self._parse_percent(value)

        elif spec.kind == "integer":

            row[spec.field] = self._parse_int(value)

        else:

            text = str(value).strip() if value is not None else ""

            row[spec.field] = text or None

        self._rows[index.row()] = row

        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])

        self._after_set(index.row(), spec.field)

        return True



    # --- helpers ---

    def _after_set(self, row_index: int, field: str) -> None:

        pass



    def _raw_value(self, row: Dict[str, Any], spec: ColumnSpec):

        value = row.get(spec.field)

        if spec.kind in {"money", "decimal", "percent"}:

            if value is None:

                return 0.0

            if isinstance(value, Decimal):

                return float(value)

            try:

                return float(str(value).replace(',', '.'))

            except Exception:

                return 0.0

        if spec.kind == "integer":

            if value in (None, ""):

                return 0

            try:

                return int(Decimal(str(value)))

            except Exception:

                return 0

        if spec.kind == "bool":

            return 1 if value else 0

        return value if value is not None else ""



    def _parse_decimal(self, value) -> Optional[Decimal]:

        if value in (None, ""):

            return None

        try:

            text = str(value).strip()

            text = text.replace('€', '')

            text = text.replace('EUR', '')

            text = text.replace(' ', '')

            text = text.replace(',', '.')

            return Decimal(text)

        except Exception:

            return None







    def _parse_percent(self, value) -> Optional[Decimal]:

        if value in (None, ""):

            return None

        try:

            text = str(value).strip().replace("%", "").replace(",", ".")

            dec = Decimal(text)

            if dec > 1:

                dec = dec / Decimal("100")

            return dec

        except Exception:

            return None



    def _parse_int(self, value) -> Optional[int]:

        if value in (None, ""):

            return None

        try:

            return int(str(value).strip())

        except Exception:

            return None



    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder):

        if column < 0 or column >= len(self.columns):

            return

        spec = self.columns[column]

        reverse = order == Qt.DescendingOrder



        def sort_key(row: Dict[str, Any]):

            value = self._raw_value(row, spec)

            if isinstance(value, str):

                return value.lower()

            return value



        self.layoutAboutToBeChanged.emit()

        try:

            self._rows.sort(key=sort_key, reverse=reverse)

        finally:

            self.layoutChanged.emit()



    # --- API ---

    def load_rows(self, rows: Iterable[Dict]) -> None:

        self.beginResetModel()

        self._rows = [dict(row) for row in rows]

        self.endResetModel()



    def export_rows(self) -> List[Dict]:

        return [dict(row) for row in self._rows]



    def append_row(self, defaults: Optional[Dict] = None) -> int:

        new_row = dict(defaults or {})

        new_row.setdefault("ordem", len(self._rows))

        pos = len(self._rows)

        self.beginInsertRows(QtCore.QModelIndex(), pos, pos)

        self._rows.append(new_row)

        self.endInsertRows()

        return pos



    def remove_rows(self, indices: Sequence[int]) -> None:

        for row in sorted(indices, reverse=True):

            if 0 <= row < len(self._rows):

                self.beginRemoveRows(QtCore.QModelIndex(), row, row)

                self._rows.pop(row)

                self.endRemoveRows()

        self._reindex()



    def _reindex(self):

        for idx, row in enumerate(self._rows):

            row["ordem"] = idx



    def row_at(self, row_index: int) -> Dict:

        return self._rows[row_index]



    def update_row(self, row_index: int, data: Dict) -> None:

        if not (0 <= row_index < len(self._rows)):

            return

        row = self._rows[row_index]

        row.update(data)

        self._rows[row_index] = row

        top_left = self.index(row_index, 0)

        bottom_right = self.index(row_index, self.columnCount() - 1)

        self.dataChanged.emit(top_left, bottom_right)





class MateriaisTableModel(DadosGeraisTableModel):

    MARGIN_FIELDS = {"preco_tab", "margem", "desconto"}



    def __init__(self, columns: Sequence[ColumnSpec], parent=None):

        super().__init__(columns=columns, rows=None, parent=parent)

        self._field_index = {spec.field: idx for idx, spec in enumerate(self.columns)}



    def _after_set(self, row_index: int, field: str) -> None:

        if field in self.MARGIN_FIELDS:

            self.recalculate(row_index)



    def recalculate(self, row_index: int) -> None:

        row = self.row_at(row_index)

        preco_tab = row.get("preco_tab")

        margem = row.get("margem")

        desconto = row.get("desconto")

        pliq = svc_dg.calcular_preco_liq(preco_tab, margem, desconto)

        row["preco_liq"] = pliq

        self._rows[row_index] = row

        idx = self._field_index.get("preco_liq")

        if idx is not None:

            model_index = self.index(row_index, idx)

            self.dataChanged.emit(model_index, model_index, [Qt.DisplayRole])





class MateriaPrimaPicker(QDialog):

    def __init__(self, session, parent=None, *, tipo: Optional[str] = None, familia: Optional[str] = None):

        super().__init__(parent)

        self.session = session

        self.filter_tipo = (tipo or "").strip() or None

        self.filter_familia = (familia or "").strip() or None

        self.setWindowTitle("Selecionar Matéria-Prima")

        self.resize(1200, 700)



        layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()

        self.ed_search = QLineEdit()

        self.ed_search.setPlaceholderText("Pesquisar... use % para vários termos")

        btn_search = QPushButton("Pesquisar")

        btn_search.clicked.connect(self.refresh)

        btn_clear = QPushButton("Limpar Filtro")

        btn_clear.clicked.connect(self.on_clear_filters)



        search_layout.addWidget(self.ed_search, 1)

        search_layout.addWidget(btn_search)

        search_layout.addWidget(btn_clear)



        self.lbl_filters = QLabel()

        self.lbl_filters.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._update_filter_label()



        self._search_timer = QtCore.QTimer(self)

        self._search_timer.setSingleShot(True)

        self._search_timer.timeout.connect(self.refresh)

        self.ed_search.textChanged.connect(self._on_search_text_changed)



        self.table = QTableView(self)

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.table.setSelectionMode(QAbstractItemView.SingleSelection)

        self.table.setSortingEnabled(True)

        self.table.doubleClicked.connect(self.accept)



        columns = [

            ("Ref_LE", "ref_le"),

            ("Descrição", "descricao_orcamento"),

            ("Preço Tabela", "preco_tabela", _money),

            ("Margem", "margem", _percent),

            ("Desconto", "desconto", _percent),

            ("Preço Líq", "pliq", _money),

            ("Und", "und"),

            ("Desp", "desp", _percent),

            ("Comp MP", "comp_mp", _int_value),

            ("Larg MP", "larg_mp", _int_value),

            ("Esp MP", "esp_mp", _int_value),

            ("Tipo", "tipo"),

            ("Família", "familia"),

            ("ORL 0.4", "orl_0_4"),

            ("ORL 1.0", "orl_1_0"),

            ("Stock", "stock", lambda v: "1" if bool(v) else "0"),

        ]

        self.model = SimpleTableModel(columns=columns)

        self.table.setModel(self.model)



        layout.addLayout(search_layout)

        layout.addWidget(self.lbl_filters)

        layout.addWidget(self.table, 1)



        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        btn_box.accepted.connect(self.accept)

        btn_box.rejected.connect(self.reject)

        layout.addWidget(btn_box)



        self.refresh()



    def _on_search_text_changed(self, _text: str) -> None:

        self._search_timer.start(250)



    def _update_filter_label(self) -> None:

        tipo = self.filter_tipo or "(todos os tipos)"

        familia = self.filter_familia or "(todas as famílias)"

        self.lbl_filters.setText(f"Filtro atual: Tipo {tipo} | Família {familia}")



    def on_clear_filters(self) -> None:

        self.filter_tipo = None

        self.filter_familia = None

        self._update_filter_label()

        self.refresh()



    def refresh(self):

        rows = svc_mp.list_materias_primas(

            self.session,

            self.ed_search.text(),

            tipo=self.filter_tipo,

            familia=self.filter_familia,

        )

        self.model.set_rows(rows)

        if rows:

            self.table.selectRow(0)

        self._update_filter_label()



    def selected(self):

        idx = self.table.currentIndex()

        if idx.isValid():

            return self.model.get_row(idx.row())

        return None



    def accept(self):

        if not self.selected():

            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione uma matéria-prima")

            return

        super().accept()









class DadosGeraisPage(QtWidgets.QWidget):

    TAB_ORDER = [

        svc_dg.MENU_MATERIAIS,

        svc_dg.MENU_FERRAGENS,

        svc_dg.MENU_SIS_CORRER,

        svc_dg.MENU_ACABAMENTOS,

    ]



    def __init__(self, parent=None, current_user=None):

        super().__init__(parent)

        self.current_user = current_user

        self.session = SessionLocal()

        self.context: Optional[svc_dg.DadosGeraisContext] = None

        self._tipos_cache: List[str] = []

        self._familias_cache: List[str] = []



        self._setup_ui()



    # ------------------------------------------------------------------ UI

    def _setup_ui(self) -> None:

        root = QVBoxLayout(self)

        root.setContentsMargins(8, 8, 8, 8)

        root.setSpacing(8)



        header = QtWidgets.QWidget(self)

        grid = QGridLayout(header)

        grid.setContentsMargins(0, 0, 0, 0)

        grid.setHorizontalSpacing(12)

        grid.setVerticalSpacing(4)



        self.lbl_cliente = QLabel("-")

        self.lbl_utilizador = QLabel("-")

        self.lbl_ano = QLabel("-")

        self.lbl_num = QLabel("-")

        self.lbl_ver = QLabel("-")



        grid.addWidget(QLabel("Cliente:"), 0, 0)

        grid.addWidget(self.lbl_cliente, 0, 1)

        grid.addWidget(QLabel("Utilizador:"), 0, 2)

        grid.addWidget(self.lbl_utilizador, 0, 3)

        grid.addWidget(QLabel("Ano:"), 1, 0)

        grid.addWidget(self.lbl_ano, 1, 1)

        grid.addWidget(QLabel("Nº Orçamento:"), 1, 2)

        grid.addWidget(self.lbl_num, 1, 3)

        grid.addWidget(QLabel("Versão:"), 1, 4)

        grid.addWidget(self.lbl_ver, 1, 5)



        self.btn_guardar = QPushButton("Guardar")

        self.btn_guardar.clicked.connect(self.on_guardar)

        grid.addWidget(self.btn_guardar, 0, 5)



        root.addWidget(header)



        self.tabs = QTabWidget(self)

        root.addWidget(self.tabs, 1)



        self.models: Dict[str, DadosGeraisTableModel] = {}

        self.tables: Dict[str, QTableView] = {}



        for key in self.TAB_ORDER:

            widget = QtWidgets.QWidget()

            layout = QVBoxLayout(widget)

            layout.setContentsMargins(0, 0, 0, 0)

            layout.setSpacing(4)



            toolbar = QHBoxLayout()

            toolbar.setSpacing(6)

            btn_save_model = QPushButton("Guardar Modelo")

            btn_save_model.clicked.connect(lambda _, k=key: self.on_guardar_modelo(k))

            btn_import_model = QPushButton("Importar Modelo")

            btn_import_model.clicked.connect(lambda _, k=key: self.on_importar_modelo(k))

            btn_import_multi = QPushButton("Importar Multi Modelos")

            btn_import_multi.clicked.connect(self.on_importar_multi_modelos)



            toolbar.addWidget(btn_save_model)

            toolbar.addWidget(btn_import_model)

            toolbar.addWidget(btn_import_multi)

            toolbar.addStretch(1)



            if key == svc_dg.MENU_MATERIAIS:

                btn_mp = QPushButton("Selecionar Matéria-Prima")

                btn_mp.clicked.connect(self.on_selecionar_mp)

                toolbar.addWidget(btn_mp)



            layout.addLayout(toolbar)



            table = QTableView(self)

            table.setSelectionBehavior(QAbstractItemView.SelectRows)

            table.setSelectionMode(QAbstractItemView.SingleSelection)

            table.horizontalHeader().setStretchLastSection(False)

            table.setSortingEnabled(True)

            layout.addWidget(table, 1)



            self.tabs.addTab(widget, self._tab_title(key))



            model = self._create_model(key)

            self.models[key] = model

            self.tables[key] = table

            table.setModel(model)



            self._configure_delegates(key)



    def _tab_title(self, key: str) -> str:

        mapping = {

            svc_dg.MENU_MATERIAIS: "Materiais",

            svc_dg.MENU_FERRAGENS: "Ferragens",

            svc_dg.MENU_SIS_CORRER: "Sistemas Correr",

            svc_dg.MENU_ACABAMENTOS: "Acabamentos",

        }

        return mapping.get(key, key.title())



    def _create_model(self, key: str) -> DadosGeraisTableModel:

        if key == svc_dg.MENU_MATERIAIS:

            columns = [

                ColumnSpec("Materiais", "grupo_material", width=200, readonly=True),

                ColumnSpec("Descrição", "descricao", width=240),

                ColumnSpec("Ref_LE", "ref_le", width=110, readonly=True),

                ColumnSpec("Descrição Material", "descricao_material", width=260),

                ColumnSpec("Preço Tab", "preco_tab", "money", width=110),

                ColumnSpec("Preço Liq", "preco_liq", "money", width=110, readonly=True),

                ColumnSpec("Margem", "margem", "percent", width=90),

                ColumnSpec("Desconto", "desconto", "percent", width=90),

                ColumnSpec("Und", "und", width=60),

                ColumnSpec("Desp", "percent", width=90),

                ColumnSpec("ORL 0.4", "orl_0_4", width=110),

                ColumnSpec("ORL 1.0", "orl_1_0", width=110),

                ColumnSpec("Tipo", "tipo", "choice", width=140, options=self._tipos_options),

                ColumnSpec("Família", "familia", "choice", width=120, options=self._familias_options),

                ColumnSpec("Comp MP", "comp_mp", "integer", width=95),

                ColumnSpec("Larg MP", "larg_mp", "integer", width=95),

                ColumnSpec("Esp MP", "esp_mp", "integer", width=95),

                ColumnSpec("ID MP", "id_mp", width=110, readonly=True),

                ColumnSpec("Não Stock", "nao_stock", "bool", width=70),

                ColumnSpec("Reserva 1", "reserva_1", visible=False),

                ColumnSpec("Reserva 2", "reserva_2", visible=False),

                ColumnSpec("Reserva 3", "reserva_3", visible=False),

            ]

            return MateriaisTableModel(columns=columns, parent=self)



        columns = [

            ColumnSpec("Categoria", "categoria", width=160),

            ColumnSpec("Descrição", "descricao", width=220),

            ColumnSpec("Referência", "referencia", width=120),

            ColumnSpec("Fornecedor", "fornecedor", width=160),

            ColumnSpec("Preço Tab", "preco_tab", "money", width=100),

            ColumnSpec("Preço Liq", "preco_liq", "money", width=100, readonly=True),

            ColumnSpec("Margem", "margem", "percent", width=90),

            ColumnSpec("Desconto", "desconto", "percent", width=90),

            ColumnSpec("Und", "und", width=60),

            ColumnSpec("Qt", "qt", "decimal", width=80),

            ColumnSpec("Não Stock", "nao_stock", "bool", width=80),

            ColumnSpec("Reserva 1", "reserva_1", width=140),

            ColumnSpec("Reserva 2", "reserva_2", width=140),

            ColumnSpec("Reserva 3", "reserva_3", width=140),

        ]

        return DadosGeraisTableModel(columns=columns, parent=self)



    def _configure_delegates(self, key: str) -> None:

        table = self.tables[key]

        model = self.models[key]

        for idx, spec in enumerate(model.columns):

            if not spec.visible:

                table.setColumnHidden(idx, True)

                continue

            if spec.options:

                delegate = ChoiceDelegate(spec.options, parent=table)

                table.setItemDelegateForColumn(idx, delegate)

            if spec.kind == "money":

                table.horizontalHeader().setSectionResizeMode(idx, QtWidgets.QHeaderView.ResizeToContents)

            elif spec.kind == "bool":

                table.horizontalHeader().setSectionResizeMode(idx, QtWidgets.QHeaderView.ResizeToContents)

            elif spec.width:

                table.setColumnWidth(idx, spec.width)



    def _tipos_options(self) -> Sequence[str]:

        return self._tipos_cache or []



    def _familias_options(self) -> Sequence[str]:

        return self._familias_cache or ["PLACAS"]



    # ------------------------------------------------------------------ Data flow

    def load_orcamento(self, orcamento_id: int) -> None:

        try:

            ctx = svc_dg.carregar_contexto(self.session, orcamento_id)

        except Exception as exc:

            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar contexto: {exc}")

            return

        self.context = ctx

        self._carregar_topo(orcamento_id)

        self._carregar_tipos_familias()

        try:

            data = svc_dg.carregar_dados_gerais(self.session, ctx)

        except Exception as exc:

            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar dados: {exc}")

            data = {key: [] for key in self.TAB_ORDER}

        for key, model in self.models.items():

            rows = data.get(key, [])

            model.load_rows(rows)

            model._reindex()



    def _carregar_topo(self, orcamento_id: int) -> None:

        orc: Orcamento = self.session.get(Orcamento, orcamento_id)

        if not orc:

            return

        cliente: Optional[Client] = self.session.get(Client, orc.client_id) if orc.client_id else None

        user: Optional[User] = self.session.get(User, orc.created_by) if orc.created_by else None

        self.lbl_cliente.setText(getattr(cliente, "nome", "-") or "-")

        self.lbl_ano.setText(str(getattr(orc, "ano", "") or "-"))

        self.lbl_num.setText(str(getattr(orc, "num_orcamento", "") or "-"))

        versao = getattr(orc, "versao", "")

        try:

            versao = f"{int(versao):02d}"

        except Exception:

            versao = str(versao or "")

        self.lbl_ver.setText(versao or "-")

        username = getattr(user, "username", None) or getattr(self.current_user, "username", None) or "-"

        self.lbl_utilizador.setText(username)



    def _carregar_tipos_familias(self) -> None:

        try:

            self._tipos_cache = svc_mp.listar_tipos(self.session)

        except Exception:

            self._tipos_cache = []

        try:

            familias = svc_mp.listar_familias(self.session)

        except Exception:

            familias = []

        self._familias_cache = ["PLACAS"]

        if familias:

            if "PLACAS" in familias:

                self._familias_cache = ["PLACAS"]

            else:

                self._familias_cache = ["PLACAS"]



    # ------------------------------------------------------------------ Actions

    def on_guardar(self):

        if not self.context:

            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum orçamento carregado.")

            return

        payload = {key: model.export_rows() for key, model in self.models.items()}

        try:

            svc_dg.guardar_dados_gerais(self.session, self.context, payload)

            self.session.commit()

            QtWidgets.QMessageBox.information(self, "Sucesso", "Dados gerais guardados.")

        except Exception as exc:

            self.session.rollback()

            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao guardar: {exc}")



    def on_add_row(self, key: str):

        model = self.models[key]

        defaults = {"ordem": model.rowCount()}

        if key == svc_dg.MENU_MATERIAIS:

            defaults["grupo_material"] = next(iter(svc_dg.MATERIAIS_GRUPOS), None)

        row_index = model.append_row(defaults)

        table = self.tables[key]

        table.selectRow(row_index)



    def on_del_row(self, key: str):

        table = self.tables[key]

        model = self.models[key]

        indexes = table.selectionModel().selectedRows()

        if not indexes:

            return

        rows = [idx.row() for idx in indexes]

        model.remove_rows(rows)



    def on_guardar_modelo(self, key: str):

        if not self.context:

            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum orçamento carregado.")

            return

        user_id = getattr(self.current_user, "id", None)

        if not user_id:

            QtWidgets.QMessageBox.warning(self, "Aviso", "Utilizador sem ID válido.")

            return

        linhas = self.models[key].export_rows()

        if not linhas:

            QtWidgets.QMessageBox.warning(self, "Aviso", "Não há linhas para guardar.")

            return

        dialog = GuardarModeloDialog(self.session, user_id=user_id, tipo_menu=key, linhas=linhas, parent=self)

        if dialog.exec() != QDialog.Accepted:

            return

        try:

            svc_dg.guardar_modelo(

                self.session,

                user_id=user_id,

                tipo_menu=key,

                nome_modelo=dialog.model_name,

                linhas=linhas,

                replace_id=dialog.replace_model_id,

            )

            self.session.commit()

            QtWidgets.QMessageBox.information(self, "Sucesso", "Modelo guardado.")

        except Exception as exc:

            self.session.rollback()

            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao guardar modelo: {exc}")





    def on_importar_modelo(self, key: str):

        user_id = getattr(self.current_user, "id", None)

        if not user_id:

            QtWidgets.QMessageBox.warning(self, "Aviso", "Utilizador sem ID válido.")

            return

        modelos_existentes = svc_dg.listar_modelos(self.session, user_id=user_id, tipo_menu=key)

        if not modelos_existentes:

            QtWidgets.QMessageBox.information(self, "Info", "Sem modelos guardados para este submenu.")

            return

        dialog = ImportarModeloDialog(self.session, user_id=user_id, tipo_menu=key, parent=self)

        if dialog.exec() != QDialog.Accepted:

            return

        if not dialog.selected_lines:

            return

        self._apply_imported_rows(key, dialog.selected_lines, replace=dialog.replace_existing)





    def _apply_imported_rows(self, key: str, rows: Sequence[Mapping[str, Any]], *, replace: bool) -> None:

        model = self.models[key]

        if replace:

            model.load_rows(rows)

        else:

            combined = model.export_rows() + [dict(r) for r in rows]

            model.load_rows(combined)

        model._reindex()

        if key == svc_dg.MENU_MATERIAIS:

            if isinstance(model, MateriaisTableModel):

                for idx in range(model.rowCount()):

                    model.recalculate(idx)

        else:

            self._recalculate_menu_rows(key)



    def _recalculate_menu_rows(self, key: str) -> None:

        model = self.models[key]

        for idx in range(model.rowCount()):

            try:

                row = model.row_at(idx)

            except Exception:

                row = None

            if not row:

                continue

            preco_liq = svc_dg.calcular_preco_liq(row.get("preco_tab"), row.get("margem"), row.get("desconto"))

            if preco_liq is not None:

                updated = dict(row)

                updated["preco_liq"] = preco_liq

                model.update_row(idx, updated)



    def on_importar_multi_modelos(self):

        user_id = getattr(self.current_user, "id", None)

        if not user_id:

            QtWidgets.QMessageBox.warning(self, "Aviso", "Utilizador sem ID válido.")

            return

        dialog = ImportarMultiModelosDialog(self.session, user_id=user_id, parent=self)

        if dialog.exec() != QDialog.Accepted:

            return

        if not dialog.selections:

            return

        for menu, info in dialog.selections.items():

            modelo_id = info.get("modelo_id")

            if not modelo_id:

                continue

            try:

                data = svc_dg.carregar_modelo(self.session, modelo_id, user_id=user_id)

            except Exception as exc:

                QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar modelo: {exc}")

                continue

            linhas = data.get("linhas", [])

            if not linhas:

                continue

            self._apply_imported_rows(menu, linhas, replace=info.get("replace", True))



    def on_selecionar_mp(self):

        key = svc_dg.MENU_MATERIAIS

        table = self.tables[key]

        model: MateriaisTableModel = self.models[key]  # type: ignore[assignment]

        idx = table.currentIndex()

        if not idx.isValid():

            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione uma linha.")

            return

        current_row = model.row_at(idx.row())

        picker = MateriaPrimaPicker(

            self.session,

            parent=self,

            tipo=current_row.get("tipo"),

            familia=current_row.get("familia") or "PLACAS",

        )

        if picker.exec() != QDialog.Accepted:

            return

        materia = picker.selected()

        if not materia:

            return

        def _as_fraction(raw):
            if raw in (None, ""):
                return None
            try:
                dec = Decimal(str(raw))
            except Exception:
                return None
            if dec > 1:
                dec = dec / Decimal("100")
            return dec

        margem = _as_fraction(materia.margem)
        desconto = _as_fraction(materia.desconto)
        desp = _as_fraction(getattr(materia, "desp", None))
        preco_liq = materia.pliq
        if preco_liq in (None, ""):
            preco_liq = svc_dg.calcular_preco_liq(materia.preco_tabela, margem, desconto)

        update_data = {

            "ref_le": materia.ref_le,

            "descricao_material": materia.descricao_orcamento,

            "preco_tab": materia.preco_tabela,

            "margem": margem,

            "desconto": desconto,

            "preco_liq": preco_liq,

            "und": materia.und,

            "desp": desp,

            "orl_0_4": materia.orl_0_4,

            "orl_1_0": materia.orl_1_0,

            "tipo": materia.tipo,

            "familia": materia.familia or current_row.get("familia"),

            "comp_mp": int(materia.comp_mp) if materia.comp_mp not in (None, "") else None,

            "larg_mp": int(materia.larg_mp) if materia.larg_mp not in (None, "") else None,

            "esp_mp": int(materia.esp_mp) if materia.esp_mp not in (None, "") else None,

            "id_mp": materia.id_mp,

            "nao_stock": bool(getattr(materia, 'stock', 0)),

        }

        model.update_row(idx.row(), update_data)

        model.recalculate(idx.row())



    # ------------------------------------------------------------------ Cleanup

    def closeEvent(self, event):

        try:

            self.session.close()

        finally:

            super().closeEvent(event)















PREVIEW_COLUMNS = {

    svc_dg.MENU_MATERIAIS: [

        ("Materiais", "grupo_material", "text"),

        ("Ref_LE", "ref_le", "text"),

        ("Descrição", "descricao_material", "text"),

        ("Preço Tab", "preco_tab", "money"),

        ("Preço Liq", "preco_liq", "money"),

        ("Margem", "margem", "percent"),

        ("Desconto", "desconto", "percent"),

        ("Und", "und", "text"),

    ],

    svc_dg.MENU_FERRAGENS: [

        ("Categoria", "categoria", "text"),

        ("Descrição", "descricao", "text"),

        ("Referência", "referencia", "text"),

        ("Preço Tab", "preco_tab", "money"),

        ("Preço Liq", "preco_liq", "money"),

        ("Margem", "margem", "percent"),

        ("Desconto", "desconto", "percent"),

        ("Qt", "qt", "decimal"),

    ],

    svc_dg.MENU_SIS_CORRER: [

        ("Categoria", "categoria", "text"),

        ("Descrição", "descricao", "text"),

        ("Referência", "referencia", "text"),

        ("Preço Tab", "preco_tab", "money"),

        ("Preço Liq", "preco_liq", "money"),

        ("Margem", "margem", "percent"),

        ("Desconto", "desconto", "percent"),

        ("Qt", "qt", "decimal"),

    ],

    svc_dg.MENU_ACABAMENTOS: [

        ("Categoria", "categoria", "text"),

        ("Descrição", "descricao", "text"),

        ("Referência", "referencia", "text"),

        ("Preço Tab", "preco_tab", "money"),

        ("Preço Liq", "preco_liq", "money"),

        ("Margem", "margem", "percent"),

        ("Desconto", "desconto", "percent"),

        ("Qt", "qt", "decimal"),

    ],

}





def _format_preview_value(kind: str, value: Any) -> str:

    if kind == "money":

        return _money(value)

    if kind == "percent":

        return _percent(value)

    if kind == "decimal":

        return _decimal(value)

    if kind == "int":

        if value in (None, ""):

            return ""

        try:

            return str(int(Decimal(str(value))))

        except Exception:

            return str(value)

    return "" if value is None else str(value)





class GuardarModeloDialog(QDialog):

    def __init__(self, session, user_id: int, tipo_menu: str, linhas: Sequence[Mapping[str, Any]], parent=None):

        super().__init__(parent)

        self.session = session

        self.user_id = user_id

        self.tipo_menu = tipo_menu

        self.linhas = [dict(row) for row in linhas]

        self.models = svc_dg.listar_modelos(self.session, user_id=user_id, tipo_menu=tipo_menu)

        self.replace_model_id: Optional[int] = None

        self.model_name: str = ""



        self.setWindowTitle("Guardar Modelo")

        self.resize(900, 600)



        layout = QVBoxLayout(self)

        split = QHBoxLayout()



        self.models_list = QListWidget()

        self.models_list.itemSelectionChanged.connect(self._on_model_selected)

        split.addWidget(self.models_list, 1)



        self.preview_table = QTableWidget()

        self.preview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.preview_table.setSelectionMode(QAbstractItemView.NoSelection)

        split.addWidget(self.preview_table, 2)



        layout.addLayout(split)



        form = QFormLayout()

        self.name_edit = QLineEdit()

        form.addRow("Nome do modelo:", self.name_edit)

        layout.addLayout(form)



        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)

        self.button_box.accepted.connect(self.accept)

        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)



        self._populate_models()

        self._populate_preview()

        if self.models_list.count() > 0:

            self.models_list.setCurrentRow(0)



    def _filtered_lines(self) -> List[Dict[str, Any]]:

        fields = svc_dg.MENU_FIELDS.get(self.tipo_menu, ())

        filtered: List[Dict[str, Any]] = []

        for row in self.linhas:

            if any((row.get(field) not in (None, "", 0, 0.0)) for field in fields if field not in ("grupo_material",)):

                filtered.append(dict(row))

        return filtered



    def _populate_models(self) -> None:

        self.models_list.clear()

        for model in self.models:

            display = model.nome_modelo

            created = getattr(model, "created_at", None)

            if created:

                try:

                    display += f" ({created})"

                except Exception:

                    display += f" ({str(created)})"

            item = QListWidgetItem(display)

            item.setData(Qt.UserRole, model.id)

            self.models_list.addItem(item)



    def _populate_preview(self) -> None:

        columns = PREVIEW_COLUMNS.get(self.tipo_menu, PREVIEW_COLUMNS[svc_dg.MENU_FERRAGENS])

        rows = self._filtered_lines()

        limit = min(len(rows), 12)

        self.preview_table.setColumnCount(len(columns))

        self.preview_table.setRowCount(limit)

        self.preview_table.setHorizontalHeaderLabels([col[0] for col in columns])

        for row_idx in range(limit):

            row_data = rows[row_idx]

            for col_idx, (_, key, kind) in enumerate(columns):

                text = _format_preview_value(kind, row_data.get(key))

                item = QTableWidgetItem(text)

                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

                self.preview_table.setItem(row_idx, col_idx, item)

        self.preview_table.resizeColumnsToContents()



    def _on_model_selected(self) -> None:

        item = self.models_list.currentItem()

        if not item:

            return

        self.name_edit.setText(item.text().split(" (")[0])



    def accept(self) -> None:

        name = self.name_edit.text().strip()

        if not name:

            QtWidgets.QMessageBox.warning(self, "Aviso", "Indique um nome para o modelo.")

            return

        replace_id: Optional[int] = None

        for model in self.models:

            if model.nome_modelo.strip().lower() == name.lower():

                answer = QtWidgets.QMessageBox.question(

                    self,

                    "Substituir",

                    f"Já existe um modelo chamado '{name}'. Deseja substituir?",

                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,

                    QtWidgets.QMessageBox.No,

                )

                if answer != QtWidgets.QMessageBox.Yes:

                    return

                replace_id = model.id

                break

        self.model_name = name

        self.replace_model_id = replace_id

        super().accept()





class ImportarModeloDialog(QDialog):

    def __init__(self, session, user_id: int, tipo_menu: str, parent=None):

        super().__init__(parent)

        self.session = session

        self.user_id = user_id

        self.tipo_menu = tipo_menu

        self.models = svc_dg.listar_modelos(self.session, user_id=user_id, tipo_menu=tipo_menu)

        self.current_model = None

        self.current_lines: List[Dict[str, Any]] = []

        self.display_lines: List[Dict[str, Any]] = []

        self.selected_lines: List[Dict[str, Any]] = []

        self.replace_existing: bool = True



        self.setWindowTitle("Importar Modelo")

        self.resize(1100, 650)



        layout = QVBoxLayout(self)

        split = QHBoxLayout()



        left_layout = QVBoxLayout()

        self.models_list = QListWidget()

        self.models_list.itemSelectionChanged.connect(self._on_model_selected)

        left_layout.addWidget(self.models_list)



        actions_layout = QHBoxLayout()

        self.btn_rename = QPushButton("Renomear")

        self.btn_delete = QPushButton("Eliminar")

        self.btn_rename.clicked.connect(self._on_rename_model)

        self.btn_delete.clicked.connect(self._on_delete_model)

        actions_layout.addWidget(self.btn_rename)

        actions_layout.addWidget(self.btn_delete)

        left_layout.addLayout(actions_layout)



        split.addLayout(left_layout, 1)



        self.lines_table = QTableWidget()

        self.lines_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.lines_table.setSelectionMode(QAbstractItemView.NoSelection)

        split.addWidget(self.lines_table, 2)



        layout.addLayout(split)



        select_layout = QHBoxLayout()

        self.btn_select_all = QPushButton("Selecionar Tudo")

        self.btn_clear_selection = QPushButton("Limpar Seleção")

        self.btn_select_all.clicked.connect(lambda: self._set_all_checks(Qt.Checked))

        self.btn_clear_selection.clicked.connect(lambda: self._set_all_checks(Qt.Unchecked))

        select_layout.addWidget(self.btn_select_all)

        select_layout.addWidget(self.btn_clear_selection)

        select_layout.addStretch()

        layout.addLayout(select_layout)



        options_layout = QHBoxLayout()

        self.radio_replace = QRadioButton("Substituir linhas atuais")

        self.radio_replace.setChecked(True)

        self.radio_append = QRadioButton("Adicionar / mesclar")

        options_layout.addWidget(self.radio_replace)

        options_layout.addWidget(self.radio_append)

        options_layout.addStretch()

        layout.addLayout(options_layout)



        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        self.button_box.accepted.connect(self.accept)

        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)



        self._populate_models()

        if self.models_list.count() > 0:

            self.models_list.setCurrentRow(0)

        else:

            self.btn_delete.setEnabled(False)

            self.btn_rename.setEnabled(False)



    def _filtered_lines(self, rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:

        fields = svc_dg.MENU_FIELDS.get(self.tipo_menu, ())

        filtered: List[Dict[str, Any]] = []

        for row in rows:

            if any((row.get(field) not in (None, "", 0, 0.0)) for field in fields if field not in ("grupo_material",)):

                filtered.append(dict(row))

        return filtered



    def _set_all_checks(self, state: Qt.CheckState) -> None:

        for row_idx in range(self.lines_table.rowCount()):

            item = self.lines_table.item(row_idx, 0)

            if item:

                item.setCheckState(state)



    def _populate_models(self) -> None:

        self.models_list.clear()

        for model in self.models:

            display = model.nome_modelo

            created = getattr(model, "created_at", None)

            if created:

                try:

                    display += f" ({created})"

                except Exception:

                    display += f" ({str(created)})"

            item = QListWidgetItem(display)

            item.setData(Qt.UserRole, model.id)

            self.models_list.addItem(item)



    def _on_model_selected(self) -> None:

        item = self.models_list.currentItem()

        if not item:

            self.current_model = None

            self.current_lines = []

            self.display_lines = []

            self.lines_table.clear()

            self.lines_table.setRowCount(0)

            self.lines_table.setColumnCount(0)

            return

        model_id = item.data(Qt.UserRole)

        try:

            data = svc_dg.carregar_modelo(self.session, model_id, user_id=self.user_id)

        except Exception as exc:

            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar modelo: {exc}")

            return

        self.current_model = data.get("modelo")

        self.current_lines = [dict(row) for row in data.get("linhas", [])]

        self.display_lines = self._filtered_lines(self.current_lines)

        self._populate_lines_table()



    def _populate_lines_table(self) -> None:

        columns = PREVIEW_COLUMNS.get(self.tipo_menu, PREVIEW_COLUMNS[svc_dg.MENU_FERRAGENS])

        self.lines_table.setColumnCount(len(columns) + 1)

        headers = ["Importar"] + [col[0] for col in columns]

        self.lines_table.setHorizontalHeaderLabels(headers)

        self.lines_table.setRowCount(len(self.display_lines))

        for row_idx, row_data in enumerate(self.display_lines):

            check_item = QTableWidgetItem()

            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)

            check_item.setCheckState(Qt.Checked)

            self.lines_table.setItem(row_idx, 0, check_item)

            for col_idx, (_, key, kind) in enumerate(columns, start=1):

                text = _format_preview_value(kind, row_data.get(key))

                item = QTableWidgetItem(text)

                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

                self.lines_table.setItem(row_idx, col_idx, item)

        self.lines_table.resizeColumnsToContents()



    def _on_delete_model(self) -> None:

        item = self.models_list.currentItem()

        if not item:

            return

        model_id = item.data(Qt.UserRole)

        confirm = QtWidgets.QMessageBox.question(

            self,

            "Eliminar",

            "Eliminar este modelo?",

            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,

            QtWidgets.QMessageBox.No,

        )

        if confirm != QtWidgets.QMessageBox.Yes:

            return

        try:

            svc_dg.eliminar_modelo(self.session, modelo_id=model_id, user_id=self.user_id)

            self.session.commit()

        except Exception as exc:

            self.session.rollback()

            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar: {exc}")

            return

        self.models = [m for m in self.models if m.id != model_id]

        self._populate_models()

        self.models_list.setCurrentRow(0 if self.models else -1)



    def _on_rename_model(self) -> None:

        item = self.models_list.currentItem()

        if not item:

            return

        model_id = item.data(Qt.UserRole)

        model_name = item.text().split(" (")[0]

        new_name, ok = QtWidgets.QInputDialog.getText(self, "Renomear Modelo", "Novo nome:", text=model_name)

        if not ok or not new_name.strip():

            return

        try:

            svc_dg.renomear_modelo(self.session, modelo_id=model_id, user_id=self.user_id, novo_nome=new_name.strip())

            self.session.commit()

        except Exception as exc:

            self.session.rollback()

            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao renomear: {exc}")

            return

        self.models = svc_dg.listar_modelos(self.session, user_id=self.user_id, tipo_menu=self.tipo_menu)

        self._populate_models()

        for idx in range(self.models_list.count()):

            if self.models_list.item(idx).data(Qt.UserRole) == model_id:

                self.models_list.setCurrentRow(idx)

                break



    def accept(self) -> None:

        if not self.display_lines:

            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um modelo.")

            return

        selected: List[Dict[str, Any]] = []

        for row_idx in range(self.lines_table.rowCount()):

            item = self.lines_table.item(row_idx, 0)

            if item and item.checkState() == Qt.Checked:

                selected.append(dict(self.display_lines[row_idx]))

        if not selected:

            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione pelo menos uma linha para importar.")

            return

        self.selected_lines = selected

        self.replace_existing = self.radio_replace.isChecked()

        super().accept()





class ImportarMultiModelosDialog(QDialog):

    def __init__(self, session, user_id: int, parent=None):

        super().__init__(parent)

        self.session = session

        self.user_id = user_id

        self.selections: Dict[str, Dict[str, Any]] = {}



        self.setWindowTitle("Importar Multi Modelos")

        self.resize(600, 420)



        layout = QVBoxLayout(self)

        self.sections: Dict[str, Dict[str, Any]] = {}

        for menu, titulo in (

            (svc_dg.MENU_MATERIAIS, "Materiais"),

            (svc_dg.MENU_FERRAGENS, "Ferragens"),

            (svc_dg.MENU_SIS_CORRER, "Sistemas Correr"),

            (svc_dg.MENU_ACABAMENTOS, "Acabamentos"),

        ):

            box = QGroupBox(titulo)

            box_layout = QVBoxLayout(box)

            combo = QComboBox()

            combo.addItem("(nenhum)", None)

            modelos = svc_dg.listar_modelos(self.session, user_id=self.user_id, tipo_menu=menu)

            for modelo in modelos:

                display = modelo.nome_modelo

                created = getattr(modelo, "created_at", None)

                if created:

                    try:

                        display += f" ({created})"

                    except Exception:

                        display += f" ({str(created)})"

                combo.addItem(display, modelo.id)

            replace_check = QCheckBox("Substituir linhas atuais")

            replace_check.setChecked(True)

            box_layout.addWidget(combo)

            box_layout.addWidget(replace_check)

            layout.addWidget(box)

            self.sections[menu] = {"combo": combo, "replace": replace_check}



        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        self.button_box.accepted.connect(self._on_accept)

        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)



    def _on_accept(self) -> None:

        selections: Dict[str, Dict[str, Any]] = {}

        for menu, widgets in self.sections.items():

            combo: QComboBox = widgets["combo"]

            modelo_id = combo.currentData()

            if modelo_id:

                selections[menu] = {

                    "modelo_id": modelo_id,

                    "replace": widgets["replace"].isChecked(),

                }

        if not selections:

            QtWidgets.QMessageBox.information(self, "Informação", "Selecione pelo menos um modelo.")

            return

        self.selections = selections

        super().accept()







