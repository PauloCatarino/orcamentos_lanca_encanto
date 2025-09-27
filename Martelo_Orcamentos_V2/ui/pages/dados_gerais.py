from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
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
        return f"{Decimal(value):.4f}"
    except Exception:
        return str(value)


def _money(value: Optional[Decimal]) -> str:
    if value in (None, ""):
        return ""
    try:
        amount = Decimal(value)
        return f"{amount:.2f}€"
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
    display = value * Decimal("100")
    return f"{display:.2f}%"


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
            ("ID", "id_mp"),
            ("Ref_LE", "ref_le"),
            ("Descrição", "descricao_orcamento"),
            ("Preço", "preco_tabela", _money),
            ("Tipo", "tipo"),
            ("Família", "familia"),
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

            toolbar.addWidget(btn_save_model)
            toolbar.addWidget(btn_import_model)
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
            table.setSortingEnabled(False)
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
        nome, ok = QtWidgets.QInputDialog.getText(self, "Guardar Modelo", "Nome do modelo:")
        if not ok or not nome.strip():
            return
        try:
            svc_dg.guardar_modelo(
                self.session,
                user_id=user_id,
                tipo_menu=key,
                nome_modelo=nome,
                linhas=linhas,
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
        modelos = svc_dg.listar_modelos(self.session, user_id=user_id, tipo_menu=key)
        if not modelos:
            QtWidgets.QMessageBox.information(self, "Info", "Sem modelos guardados para este submenu.")
            return
        nomes = [f"{m.id} - {m.nome_modelo}" for m in modelos]
        item, ok = QtWidgets.QInputDialog.getItem(self, "Importar Modelo", "Escolha o modelo:", nomes, 0, False)
        if not ok or not item:
            return
        modelo_id = int(item.split("-", 1)[0].strip())
        try:
            data = svc_dg.carregar_modelo(self.session, modelo_id)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar modelo: {exc}")
            return
        linhas = data.get("linhas", [])
        if not linhas:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Modelo sem linhas.")
            return
        substituir = QtWidgets.QMessageBox.question(
            self,
            "Importar Modelo",
            "Substituir as linhas atuais?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes,
        )
        model = self.models[key]
        if substituir == QtWidgets.QMessageBox.Yes:
            model.load_rows(linhas)
        else:
            existing = model.export_rows()
            combined = existing + [dict(linha) for linha in linhas]
            model.load_rows(combined)
        model._reindex()

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
        update_data = {
            "ref_le": materia.ref_le,
            "descricao_material": materia.descricao_orcamento,
            "preco_tab": materia.preco_tabela,
            "margem": materia.margem,
            "desconto": materia.desconto,
            "preco_liq": materia.pliq,
            "und": materia.und,
            "desp": materia.desp,
            "orl_0_4": materia.orl_0_4,
            "orl_1_0": materia.orl_1_0,
            "tipo": materia.tipo,
            "familia": materia.familia or current_row.get("familia"),
            "comp_mp": int(materia.comp_mp) if materia.comp_mp not in (None, "") else None,
            "larg_mp": int(materia.larg_mp) if materia.larg_mp not in (None, "") else None,
            "esp_mp": int(materia.esp_mp) if materia.esp_mp not in (None, "") else None,
            "id_mp": materia.id_mp,
            "nao_stock": bool(getattr(materia, 'nao_stock', False)),
        }
        model.update_row(idx.row(), update_data)
        model.recalculate(idx.row())

    # ------------------------------------------------------------------ Cleanup
    def closeEvent(self, event):
        try:
            self.session.close()
        finally:
            super().closeEvent(event)



