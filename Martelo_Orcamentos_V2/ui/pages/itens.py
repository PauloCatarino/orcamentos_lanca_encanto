# Martelo_Orcamentos_V2/ui/pages/itens.py
# -----------------------------------------------------------------------------
# P?gina de Itens (V2) ? carrega layout do Qt Designer (.ui) com QUiLoader
# - O .ui fica em: Martelo_Orcamentos_V2/ui/forms/itens_form.ui
# - Mant?m toda a l?gica de BD, valida??o e opera??es
# -----------------------------------------------------------------------------

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple, Mapping
from pathlib import Path
import sys
import logging

# PySide6
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtUiTools import QUiLoader           # ? para carregar .ui em runtime
from PySide6.QtCore import QFile, Qt, QItemSelectionModel, Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QHeaderView, QMessageBox, QButtonGroup

# SQLAlchemy
from sqlalchemy import select, func

# Projeto
from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.orcamentos import (
    list_items,
    create_item,
    update_item,
    delete_item,
    move_item,
)
from Martelo_Orcamentos_V2.app.models import Orcamento, Client, User
from Martelo_Orcamentos_V2.app.models.orcamento import OrcamentoItem
from Martelo_Orcamentos_V2.app.services import custeio_items as svc_custeio
from Martelo_Orcamentos_V2.app.services import dados_items as svc_dados_items
from Martelo_Orcamentos_V2.app.services import producao as svc_producao
from Martelo_Orcamentos_V2.app.services import margens as svc_margens
from Martelo_Orcamentos_V2.ui.dialogs.descricoes_predefinidas import DescricoesPredefinidasDialog
from ..models.qt_table import SimpleTableModel
from ..utils.header import apply_highlight_text, init_highlight_label
from ..workers.custeio_batch import CusteioBatchWorker

logger = logging.getLogger(__name__)


DIMENSION_KEY_ORDER: Tuple[str, ...] = tuple(svc_custeio.DIMENSION_KEY_ORDER)
PRIMARY_DIMENSION_KEYS = ("H", "L", "P")
DIMENSION_GROUPS = [
    ("H", "L", "P"),
    ("H1", "L1", "P1"),
    ("H2", "L2", "P2"),
    ("H3", "L3", "P3"),
    ("H4", "L4", "P4"),
]
DIMENSION_GROUP_COLORS: List[QtGui.QColor] = [
    QtGui.QColor("#FFF2CC"),  # amarelo claro
    QtGui.QColor("#CCE5FF"),  # azul claro
    QtGui.QColor("#D4EDDA"),  # verde claro
    QtGui.QColor("#F8D7DA"),  # vermelho claro
    QtGui.QColor("#E2D9FF"),  # lilas claro
]
DIMENSION_COLOR_MAP: Dict[str, QtGui.QColor] = {}
for color, group in zip(DIMENSION_GROUP_COLORS, DIMENSION_GROUPS):
    for key in group:
        DIMENSION_COLOR_MAP[key] = color


class DescricaoHighlighter(QtGui.QSyntaxHighlighter):
    """Aplica estilo nas linhas de descrição com prefixos especiais."""

    def __init__(self, document: QtGui.QTextDocument):
        super().__init__(document)
        self._dash_format = QtGui.QTextCharFormat()
        self._dash_format.setFontItalic(True)

        self._star_format = QtGui.QTextCharFormat(self._dash_format)
        self._star_format.setBackground(QtGui.QColor("#d8f5d2"))
        self._star_format.setFontItalic(True)

    def highlightBlock(self, text: str) -> None:  # type: ignore[override]
        if not text:
            return
        stripped = text.lstrip()
        if not stripped:
            return
        marker = stripped[0]
        if marker not in "-*":
            return
        prefix_length = len(text) - len(stripped)
        start = prefix_length + 1
        while start < len(text) and text[start] in {" ", "\t"}:
            start += 1
        length = len(text) - start
        if length <= 0:
            return
        fmt = self._dash_format if marker == "-" else self._star_format
        self.setFormat(start, length, fmt)


# ---------- helper para carregar .ui e expor widgets por objectName ----------
def _load_ui_into(widget: QtWidgets.QWidget, ui_path: str) -> QtWidgets.QWidget:
    """
    Carrega um .ui para dentro de 'widget' usando QUiLoader e
    exp?e todos os filhos (por objectName) como atributos de 'widget'.
    Ex.: no .ui existe QLineEdit com objectName 'edit_codigo' ? podes usar self.edit_codigo.
    """
    loader = QUiLoader()
    ui_candidates = [Path(ui_path)]
    mei_base = getattr(sys, "_MEIPASS", None)
    if mei_base:
        mei_base = Path(mei_base)
        ui_candidates.append(mei_base / Path(ui_path).name)
        ui_candidates.append(mei_base / "Martelo_Orcamentos_V2" / "ui" / "forms" / Path(ui_path).name)
    ui_file = next((p for p in ui_candidates if p.exists()), None)
    if ui_file is None:
        raise FileNotFoundError(f"Não consegui abrir UI: {ui_path}")
    f = QFile(str(ui_file))
    if not f.open(QFile.ReadOnly):
        raise FileNotFoundError(f"Não consegui abrir UI: {ui_file}")
    try:
        loaded = loader.load(f, widget)
    finally:
        f.close()

    if loaded is None:
        raise RuntimeError(f"Falha a carregar UI: {ui_path}")

    # Mete o widget carregado dentro deste QWidget
    lay = QtWidgets.QVBoxLayout(widget)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(loaded)

    # Exp?e os filhos por objectName em 'self'
    for child in loaded.findChildren(QtCore.QObject):
        name = child.objectName()
        if name:
            setattr(widget, name, child)

    return loaded


# ---------- util tabela: formata??o inteira (sem casas decimais) ----------
DIMENSION_LIMITS = {
    'altura': (Decimal('50'), Decimal('2800')),
    'largura': (Decimal('50'), Decimal('4000')),
    'profundidade': (Decimal('50'), Decimal('1000')),
}


def _fmt_int(value):
    if value in (None, ""):
        return ""
    try:
        return str(int(Decimal(str(value))))
    except Exception:
        return str(value)


def _fmt_two_decimals(value):
    if value in (None, ""):
        return ""
    try:
        num = Decimal(str(value))
        return f"{num.quantize(Decimal('0.01')):.2f}"
    except Exception:
        try:
            return f"{float(value):.2f}"
        except Exception:
            return str(value)


def _fmt_percent(value):
    text = _fmt_two_decimals(value)
    return f"{text}%" if text else ""


def _fmt_currency(value):
    text = _fmt_two_decimals(value)
    return f"{text}€" if text else ""


class ItensTableModel(SimpleTableModel):
    MARGEM_TOOLTIP_MAP = {
        "margem_lucro_perc": ("margem_lucro_perc", "valor_margem", "Margem de Lucro"),
        "valor_margem": ("margem_lucro_perc", "valor_margem", "Margem de Lucro"),
        "custos_admin_perc": ("custos_admin_perc", "valor_custos_admin", "Custos Administrativos"),
        "valor_custos_admin": ("custos_admin_perc", "valor_custos_admin", "Custos Administrativos"),
        "margem_acabamentos_perc": ("margem_acabamentos_perc", "valor_acabamentos", "Margem Acabamentos"),
        "valor_acabamentos": ("margem_acabamentos_perc", "valor_acabamentos", "Margem Acabamentos"),
        "margem_mp_orlas_perc": ("margem_mp_orlas_perc", "valor_mp_orlas", "Margem MP/Orlas"),
        "valor_mp_orlas": ("margem_mp_orlas_perc", "valor_mp_orlas", "Margem MP/Orlas"),
        "margem_mao_obra_perc": ("margem_mao_obra_perc", "valor_mao_obra", "Margem Mão de Obra"),
        "valor_mao_obra": ("margem_mao_obra_perc", "valor_mao_obra", "Margem Mão de Obra"),
    }

    def __init__(self, columns):
        super().__init__(columns=columns)

    def _extract_value(self, row_obj, attr: str):
        try:
            if isinstance(row_obj, dict):
                return row_obj.get(attr)
            return getattr(row_obj, attr, None)
        except Exception:
            return None

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        col = self._columns[index.column()]
        spec = self._col_spec(col)
        attr = spec.get("attr")

        if role == QtCore.Qt.ToolTipRole and attr == "custo_produzido":
            row_obj = self._rows[index.row()]
            parts = [
                ("Custo Total Orlas", "custo_total_orlas"),
                ("Custo Total Mão de Obra", "custo_total_mao_obra"),
                ("Custo Total Matéria Prima", "custo_total_materia_prima"),
                ("Custo Total Acabamentos", "custo_total_acabamentos"),
                ("Custo Colagem", "custo_colagem"),
            ]
            lines = ["Custo Produzido = soma dos componentes:"]
            subtotal = 0.0
            for label, key in parts:
                value = self._extract_value(row_obj, key)
                try:
                    num = float(value)
                except (TypeError, ValueError):
                    num = 0.0
                subtotal += num
                lines.append(f" - {label}: {_fmt_currency(num)}")
            total_val = self._extract_value(row_obj, "custo_produzido")
            try:
                total_num = float(total_val)
            except (TypeError, ValueError):
                total_num = subtotal
            lines.append(f"Total: {_fmt_currency(total_num)}")
            return "\n".join(lines)

        if role == QtCore.Qt.ToolTipRole and attr == "preco_unitario":
            row_obj = self._rows[index.row()]
            components = [
                ("Custo Produzido", "custo_produzido"),
                ("Margem Lucro (€)", "valor_margem"),
                ("Custos Administrativos (€)", "valor_custos_admin"),
                ("Margem Acabamentos (€)", "valor_acabamentos"),
                ("Margem MP/Orlas (€)", "valor_mp_orlas"),
                ("Margem Mão de Obra (€)", "valor_mao_obra"),
                ("Ajuste (€)", "ajuste"),
            ]
            lines = ["Preço Unitário (€) = soma dos componentes:"]
            total_dec = Decimal("0.00")
            for label, key in components:
                value = self._extract_value(row_obj, key) or 0
                try:
                    dec = Decimal(str(value))
                except Exception:
                    dec = Decimal("0.00")
                total_dec += dec
                lines.append(f" - {label}: {_fmt_currency(dec)}")
            unit_val = self._extract_value(row_obj, "preco_unitario")
            try:
                unit_dec = Decimal(str(unit_val))
            except Exception:
                unit_dec = total_dec
            lines.append(f"Total: {_fmt_currency(unit_dec)}")
            lines.append("Fórmula: Custo + Margens (€) + Ajuste (€)")
            return "\n".join(lines)

        if role == QtCore.Qt.ToolTipRole and attr == "preco_total":
            row_obj = self._rows[index.row()]
            qt_val = self._extract_value(row_obj, "qt") or 0
            unit_val = self._extract_value(row_obj, "preco_unitario") or 0
            total_val = self._extract_value(row_obj, "preco_total") or 0
            qt_txt = _fmt_int(qt_val) or str(qt_val)
            unit_txt = _fmt_currency(unit_val) or "0,00 €"
            total_txt = _fmt_currency(total_val) or "0,00 €"
            lines = [
                f"Preço Total (€) = Qt ({qt_txt}) x Preço Unitário ({unit_txt})",
                f"Resultado: {total_txt}",
            ]
            return "\n".join(lines)

        if role == QtCore.Qt.ToolTipRole and attr in self.MARGEM_TOOLTIP_MAP:
            row_obj = self._rows[index.row()]
            perc_attr, value_attr, label = self.MARGEM_TOOLTIP_MAP.get(attr)
            tooltip = self._build_margin_tooltip(row_obj, perc_attr, value_attr, label)
            if tooltip:
                return tooltip

        return super().data(index, role)

    def _build_margin_tooltip(self, row_obj, perc_attr: Optional[str], value_attr: Optional[str], label: str) -> Optional[str]:
        if perc_attr is None or value_attr is None:
            return None
        base_val = self._extract_value(row_obj, "custo_produzido") or 0
        perc_val = self._extract_value(row_obj, perc_attr) or 0
        valor = self._extract_value(row_obj, value_attr) or 0
        try:
            base_dec = Decimal(str(base_val))
            perc_dec = Decimal(str(perc_val))
            valor_dec = Decimal(str(valor))
        except Exception:
            return None
        return (
            f"{label}: {base_dec:.2f} € x ({perc_dec:.2f}%) = {valor_dec:.2f} €"
        )


class ItensPage(QtWidgets.QWidget):
    item_selected = Signal(object)
    production_mode_changed = Signal(str)
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.db = SessionLocal()
        self._orc_id: Optional[int] = None
        self._edit_item_id: Optional[int] = None
        self._custeio_thread: Optional[QtCore.QThread] = None
        self._custeio_worker: Optional[CusteioBatchWorker] = None

        # ------------------------------------------------------------------
        # 1) Carregar o .ui (QUiLoader em vez de uic.loadUi)
        # ------------------------------------------------------------------
        ui_path = Path(__file__).resolve().parents[1] / "forms" / "itens_form.ui"
        _load_ui_into(self, str(ui_path))

        # ------------------------------------------------------------------
        # 2) Preparar widgets do formul?rio
        # ------------------------------------------------------------------
        self._mode_button_group = QButtonGroup(self)
        self._mode_button_group.setExclusive(True)
        self._mode_button_group.addButton(self.btn_mode_std)
        self._mode_button_group.addButton(self.btn_mode_serie)
        self._style = self.style() or QtWidgets.QApplication.style()
        style = self._style
        for btn in (self.btn_mode_std, self.btn_mode_serie):
            btn.setIcon(QtGui.QIcon())
            btn.setText(btn.text().upper())
            font = btn.font()
            font.setBold(True)
            btn.setFont(font)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            btn.setMinimumWidth(90)
        self.btn_mode_std.setToolTip("Usar dados STD (standard) no custeio.")
        self.btn_mode_serie.setToolTip("Usar dados em série no custeio.")
        self.btn_mode_std.clicked.connect(lambda: self._on_mode_clicked("STD"))
        self.btn_mode_serie.clicked.connect(lambda: self._on_mode_clicked("SERIE"))
        self.btn_mode_std.setProperty("modeToggle", True)
        self.btn_mode_serie.setProperty("modeToggle", True)
        self.btn_mode_std.setProperty("modePosition", "left")
        self.btn_mode_serie.setProperty("modePosition", "right")
        self._production_mode = "STD"

        self.btn_update_costs = QtWidgets.QPushButton("Atualizar Custos")
        self.btn_update_costs.setObjectName("btnUpdateCostsPrimary")
        self.btn_update_costs.setToolTip("Soma os custos do Custeio dos Items e atualiza esta tabela.")
        self.btn_update_costs.setEnabled(False)
        self.btn_update_costs.clicked.connect(self._on_update_item_costs_clicked)
        self.btn_update_costs.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_update_costs.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        cost_font = self.btn_update_costs.font()
        cost_font.setBold(True)
        cost_font.setPointSize(cost_font.pointSize() + 1)
        self.btn_update_costs.setFont(cost_font)
        self._costs_dirty = False
        self._base_update_costs_text = self.btn_update_costs.text()

        self.lbl_custeio_status = QtWidgets.QLabel("", self)
        self.lbl_custeio_status.setObjectName("lbl_custeio_status")
        self.lbl_custeio_status.setStyleSheet("color: #666; font-size: 11px;")
        self.lbl_custeio_status.setWordWrap(True)
        self.lbl_custeio_status.hide()

        self._margens_dirty = False
        self._margem_inputs: Dict[str, QtWidgets.QDoubleSpinBox] = {}
        self._current_margem_config: Dict[str, Decimal] = {
            "percent": svc_margens.load_margens(self.db),
            "objetivo": Decimal("0.00"),
            "soma": Decimal("0.00"),
        }
        self._margens_loading = False

        # Campo de descrição com formatação automática e menu personalizado
        self._descricao_update_block = False
        if hasattr(self, "edit_descricao"):
            self._descricao_highlighter = DescricaoHighlighter(self.edit_descricao.document())
            self.edit_descricao.textChanged.connect(self._on_descricao_text_changed)
            icon = QtGui.QIcon.fromTheme(
                "view-list-text",
                self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView),
            )
            self._descricao_menu_action = QtGui.QAction(icon, "Descrições Pré-Definidas", self)
            self._descricao_menu_action.triggered.connect(self._open_descricoes_predef_dialog)
            self.edit_descricao.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.edit_descricao.customContextMenuRequested.connect(self._on_descricao_context_menu)

        self._margem_panel = QtWidgets.QGroupBox("Margens e Ajustes", self)
        self._margem_panel.setMinimumWidth(360)
        self._margem_panel.setMaximumWidth(520)
        margem_layout = QtWidgets.QGridLayout(self._margem_panel)
        margem_layout.setContentsMargins(10, 10, 10, 10)
        margem_layout.setHorizontalSpacing(12)
        margem_layout.setVerticalSpacing(6)

        for idx, spec in enumerate(svc_margens.MARGEM_FIELDS):
            key = str(spec["key"])
            label_widget = QtWidgets.QLabel(str(spec["label"]))
            spin = QtWidgets.QDoubleSpinBox(self._margem_panel)
            spin.setDecimals(2)
            spin.setRange(0.0, 500.0)
            spin.setSingleStep(0.25)
            spin.setSuffix(" %")
            spin.setAlignment(QtCore.Qt.AlignRight)
            spin.valueChanged.connect(lambda _=0.0, k=key: self._on_margem_spin_changed(k))
            col = idx % 2
            row = idx // 2
            margem_layout.addWidget(label_widget, row, col * 2)
            margem_layout.addWidget(spin, row, col * 2 + 1)
            self._margem_inputs[key] = spin

        objetivo_label = QtWidgets.QLabel("Atingir Objetivo Preço Final (€)")
        self.spin_objetivo = QtWidgets.QDoubleSpinBox(self._margem_panel)
        self.spin_objetivo.setDecimals(2)
        self.spin_objetivo.setRange(0.0, 1_000_000_000.0)
        self.spin_objetivo.setSingleStep(50.0)
        self.spin_objetivo.setSuffix(" €")
        self.spin_objetivo.setAlignment(QtCore.Qt.AlignRight)
        self.spin_objetivo.valueChanged.connect(lambda: self._on_margem_spin_changed("_objetivo"))
        objetivo_row = (len(svc_margens.MARGEM_FIELDS) + 1) // 2
        margem_layout.addWidget(objetivo_label, objetivo_row, 0)
        margem_layout.addWidget(self.spin_objetivo, objetivo_row, 1)

        soma_label = QtWidgets.QLabel("Soma Preço Final Orçamento (€)")
        self.lbl_soma_preco = QtWidgets.QLabel("0,00 €")
        font = self.lbl_soma_preco.font()
        font.setBold(True)
        self.lbl_soma_preco.setFont(font)
        self.lbl_soma_preco.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        margem_layout.addWidget(soma_label, objetivo_row, 2)
        margem_layout.addWidget(self.lbl_soma_preco, objetivo_row, 3)

        update_row = objetivo_row + 1
        margem_layout.addWidget(self.btn_update_costs, update_row, 0, 1, 4)
        margem_layout.addWidget(self.lbl_custeio_status, update_row + 1, 0, 1, 4)

        self.btn_objetivo_apply = QtWidgets.QPushButton("Ajustar Margens (Objetivo)", self._margem_panel)
        self.btn_objetivo_apply.setToolTip(
            "Ajusta as margens (Lucro, Custos Adm., MP/Orlas e Mão de Obra) até atingir o objetivo definido "
            "com tolerância de ±0,50 €."
        )
        self.btn_objetivo_apply.clicked.connect(self._on_apply_objetivo_clicked)
        objetivo_actions = QtWidgets.QHBoxLayout()
        objetivo_actions.setContentsMargins(0, 4, 0, 0)
        objetivo_actions.addStretch(1)
        margem_layout.addLayout(objetivo_actions, update_row + 2, 0, 1, 4)

        button_row = QtWidgets.QHBoxLayout()
        button_row.setContentsMargins(0, 4, 0, 0)
        self.btn_margens_save = QtWidgets.QPushButton("Guardar Margens", self._margem_panel)
        self.btn_margens_save.clicked.connect(self._on_save_margens_clicked)
        self.btn_margens_save.setEnabled(False)
        self.btn_margens_reset = QtWidgets.QPushButton("Repor Valores Padrão", self._margem_panel)
        self.btn_margens_reset.clicked.connect(self._on_reset_margens_clicked)
        button_row.addWidget(self.btn_objetivo_apply)
        button_row.addWidget(self.btn_margens_save)
        button_row.addWidget(self.btn_margens_reset)
        button_row.addStretch(1)
        margem_layout.addLayout(button_row, update_row + 3, 0, 1, 4)

        self._top_right_panel = self._margem_panel
        placeholder_layout = getattr(self, "margens_placeholder_layout", None)
        if placeholder_layout is None:
            placeholder_widget = getattr(self, "margens_placeholder", None)
            if isinstance(placeholder_widget, QtWidgets.QWidget):
                placeholder_widget.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
                placeholder_layout = placeholder_widget.layout()
        added_margem_panel = False
        if isinstance(placeholder_layout, QtWidgets.QLayout):
            placeholder_layout.addWidget(self._top_right_panel)
            added_margem_panel = True

        grid_layout = getattr(self, "gridLayout", None)
        if not added_margem_panel and isinstance(grid_layout, QtWidgets.QGridLayout):
            grid_layout.addWidget(self._top_right_panel, 1, 12, 1, 4)
        if isinstance(grid_layout, QtWidgets.QGridLayout):
            grid_layout.setColumnStretch(2, 4)
            grid_layout.setColumnStretch(3, 1)
            grid_layout.setColumnStretch(9, 1)
            grid_layout.setColumnStretch(10, 1)
            grid_layout.setColumnStretch(11, 1)
        self._set_margens_panel_enabled(False)
        main_layout = getattr(self, "verticalLayoutMain", None)
        if isinstance(main_layout, QtWidgets.QVBoxLayout):
            main_layout.setStretch(0, 0)
            main_layout.setStretch(1, 0)
            main_layout.setStretch(2, 0)
            main_layout.setStretch(3, 0)
            main_layout.setStretch(4, 1)
        dims_actions_layout = getattr(self, "layout_dims_actions", None)
        if isinstance(dims_actions_layout, QtWidgets.QHBoxLayout):
            dims_actions_layout.setStretch(0, 2)
            dims_actions_layout.setStretch(1, 3)
        self.refresh_margem_defaults()
        self._rebuild_form_layout()

        self._update_mode_buttons()
        self.btn_add.setIcon(style.standardIcon(QtWidgets.QStyle.SP_FileDialogNewFolder))
        self.btn_add.setToolTip("Inserir um novo item no orçamento.")
        self.btn_save.setIcon(style.standardIcon(QtWidgets.QStyle.SP_DialogSaveButton))
        self.btn_save.setToolTip("Gravar alterações do item selecionado.")
        self.btn_del.setIcon(style.standardIcon(QtWidgets.QStyle.SP_TrashIcon))
        self.btn_del.setToolTip("Eliminar o item selecionado.")
        self.btn_up.setIcon(style.standardIcon(QtWidgets.QStyle.SP_ArrowUp))
        self.btn_up.setToolTip("Mover o item selecionado para cima.")
        self.btn_dn.setIcon(style.standardIcon(QtWidgets.QStyle.SP_ArrowDown))
        self.btn_dn.setToolTip("Mover o item selecionado para baixo.")
        if hasattr(self, "btn_toggle_rows"):
            self.btn_toggle_rows.setIcon(style.standardIcon(QtWidgets.QStyle.SP_ArrowDown))
            self.btn_toggle_rows.setToolTip("Expandir descrições longas na tabela.")

        action_buttons = [
            getattr(self, "btn_add", None),
            getattr(self, "btn_save", None),
            getattr(self, "btn_del", None),
            getattr(self, "btn_toggle_rows", None),
            getattr(self, "btn_up", None),
            getattr(self, "btn_dn", None),
            getattr(self, "btn_objetivo_apply", None),
            getattr(self, "btn_margens_save", None),
            getattr(self, "btn_margens_reset", None),
        ]
        for btn in action_buttons:
            if btn is None:
                continue
            btn.setProperty("actionButton", True)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        button_stylesheet = """
        QPushButton[actionButton="true"] {
            background-color: #f8f8f8;
            border: 1px solid #d5d5d5;
            padding: 6px 14px;
            border-radius: 4px;
            font-weight: 600;
        }
        QPushButton[actionButton="true"]:hover {
            background-color: #ffffff;
            border-color: #b5b5b5;
        }
        QPushButton[actionButton="true"]:pressed {
            background-color: #e0e0e0;
        }
        QPushButton[actionButton="true"]:disabled {
            color: #9a9a9a;
            border-color: #e0e0e0;
            background-color: #f3f3f3;
        }
        QPushButton[modeToggle="true"] {
            border: 1px solid #4c6ef5;
            padding: 6px 18px;
            border-radius: 3px;
            background-color: #ffffff;
            color: #4c6ef5;
            font-weight: 700;
        }
        QPushButton[modeToggle="true"]:checked {
            background-color: #4c6ef5;
            color: #ffffff;
        }
        QPushButton[modeToggle="true"]:disabled {
            color: #a7a7a7;
            border-color: #d0d0d0;
            background-color: #f6f6f6;
        }
        QPushButton#btnUpdateCostsPrimary {
            background-color: #1e80ff;
            color: #ffffff;
            border: none;
            padding: 10px 18px;
            border-radius: 6px;
        }
        QPushButton#btnUpdateCostsPrimary:hover {
            background-color: #166ad1;
        }
        QPushButton#btnUpdateCostsPrimary:disabled {
            background-color: #8fb7ff;
            color: #f0f0f0;
        }
        """
        existing_stylesheet = self.styleSheet()
        if existing_stylesheet:
            self.setStyleSheet(f"{existing_stylesheet}\n{button_stylesheet}")
        else:
            self.setStyleSheet(button_stylesheet)
        if hasattr(self, "lbl_highlight"):
            init_highlight_label(self.lbl_highlight)
        info_labels = [
            getattr(self, name, None)
            for name in ("lbl_cliente_val", "lbl_num_val", "lbl_ver_val")
        ]
        info_labels = [lbl for lbl in info_labels if lbl is not None]
        if info_labels:
            value_font = info_labels[0].font()
            value_font.setBold(True)
            value_font.setPointSize(value_font.pointSize() + 2)
            for lbl in info_labels:
                lbl.setFont(value_font)
        v = QDoubleValidator(0.0, 9_999_999.0, 3, self)
        v.setNotation(QDoubleValidator.StandardNotation)
        v.setLocale(QtCore.QLocale.system())

        # Validadores + alinhamento à esquerda nos campos numéricos
        for w in (self.edit_altura, self.edit_largura, self.edit_profundidade, self.edit_qt):
            w.setValidator(v)
            w.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.edit_und.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # C?digo em mai?sculas (mant?m cursor)
        self.edit_codigo.textEdited.connect(
            lambda t: self._force_uppercase(self.edit_codigo, t)
        )

        # Enter avan?a o foco pelos campos
        self._input_sequence = [
            self.edit_codigo,
            self.edit_altura,
            self.edit_largura,
            self.edit_profundidade,
            self.edit_qt,
            self.edit_und,
        ]
        for i, w in enumerate(self._input_sequence):
            w.returnPressed.connect(lambda _=False, idx=i: self._focus_next_field(idx))

        # Campo "Item" ? sempre autom?tico
        self.edit_item.setReadOnly(True)
        if not self.edit_und.text().strip():
            self.edit_und.setText("und")

        # ------------------------------------------------------------------
        # 3) Model da tabela
        # ------------------------------------------------------------------
        def _col(header: str, attr: str, formatter=None, tooltip: Optional[str] = None, *, editable: bool = False):
            return {
                "header": header,
                "attr": attr,
                "formatter": formatter,
                "tooltip": tooltip or header,
                "editable": editable,
            }

        table_columns = [
            _col("ID", "id_item", tooltip="Identificador interno do item no orçamento."),
            _col("Item", "item_nome", tooltip="Referência sequencial apresentada ao utilizador."),
            _col("Código", "codigo", tooltip="Código do catálogo/dados do item."),
            _col("Descrição", "descricao", tooltip="Descrição resumida do item."),
            _col("Altura (mm)", "altura", _fmt_int, "Altura principal em milímetros."),
            _col("Largura (mm)", "largura", _fmt_int, "Largura principal em milímetros."),
            _col("Profundidade (mm)", "profundidade", _fmt_int, "Profundidade principal em milímetros."),
            _col("Unidade", "und", tooltip="Unidade de medida (ex.: und, par, m²)."),
            _col("Qt", "qt", _fmt_int, "Quantidade a produzir para este item."),
            _col(
                "Preço Unitário (€)",
                "preco_unitario",
                _fmt_currency,
                "Cálculo: Custo Produzido + margens em € + Ajuste (por unidade).",
            ),
            _col(
                "Preço Total (€)",
                "preco_total",
                _fmt_currency,
                "Resultado final da linha (Qt x Preço Unitário).",
            ),
            _col(
                "Custo Produzido (€)",
                "custo_produzido",
                _fmt_currency,
                "Custo Total Orlas + Custo Total Mão de Obra + Custo Total Matéria Prima + "
                "Custo Total Acabamentos + Custo Colagem (importado do Custeio dos Items).",
            ),
            _col(
                "Ajuste (€)",
                "ajuste",
                _fmt_currency,
                "Correção manual em € aplicada apenas a este item.",
                editable=True,
            ),
            _col(
                "Custo Total Orlas (€)",
                "custo_total_orlas",
                _fmt_currency,
                "Somatório de CUSTEIO_ITEMS.CUSTO_TOTAL_ORLA para o item/versão selecionado no Custeio dos Items.",
            ),
            _col(
                "Custo Total Mão de Obra (€)",
                "custo_total_mao_obra",
                _fmt_currency,
                "Somatório de CUSTEIO_ITEMS.SOMA_CUSTO_UND do item em Custeio dos Items.",
            ),
            _col(
                "Custo Total Matéria Prima (€)",
                "custo_total_materia_prima",
                _fmt_currency,
                "Somatório de CUSTEIO_ITEMS.CUSTO_MP_TOTAL do item em Custeio dos Items.",
            ),
            _col(
                "Custo Total Acabamentos (€)",
                "custo_total_acabamentos",
                _fmt_currency,
                "Somatório de CUSTEIO_ITEMS.SOMA_CUSTO_ACB do item em Custeio dos Items.",
            ),
            _col(
                "Margem de Lucro (%)",
                "margem_lucro_perc",
                _fmt_percent,
                "Percentual de margem de lucro aplicado sobre o custo produzido.",
            ),
            _col(
                "Valor da Margem (€)",
                "valor_margem",
                _fmt_currency,
                "Valor em € correspondente à Margem de Lucro (%).",
            ),
            _col(
                "Custos Administrativos (%)",
                "custos_admin_perc",
                _fmt_percent,
                "Percentual destinado aos custos administrativos.",
            ),
            _col(
                "Valor Custos Administrativos (€)",
                "valor_custos_admin",
                _fmt_currency,
                "Valor em € calculado a partir dos Custos Administrativos (%).",
            ),
            _col(
                "Margem Acabamentos (%)",
                "margem_acabamentos_perc",
                _fmt_percent,
                "Percentual aplicado às margens de acabamentos.",
            ),
            _col(
                "Valor Margem Acabamentos (€)",
                "valor_acabamentos",
                _fmt_currency,
                "Valor em € correspondente à margem de acabamentos.",
            ),
            _col(
                "Margem MP/Orlas (%)",
                "margem_mp_orlas_perc",
                _fmt_percent,
                "Percentual aplicado para matérias-primas e orlas.",
            ),
            _col(
                "Valor Margem MP/Orlas (€)",
                "valor_mp_orlas",
                _fmt_currency,
                "Valor em € correspondente à Margem MP/Orlas (%).",
            ),
            _col(
                "Margem Mão de Obra (%)",
                "margem_mao_obra_perc",
                _fmt_percent,
                "Percentual aplicado à mão de obra.",
            ),
            _col(
                "Valor Margem Mão de Obra (€)",
                "valor_mao_obra",
                _fmt_currency,
                "Valor em € correspondente à Margem de Mão de Obra (%).",
            ),
            _col(
                "Custo Colagem (€)",
                "custo_colagem",
                _fmt_currency,
                "Somatório de CUSTEIO_ITEMS.CP09_COLAGEM_UND para o item/versão em Custeio dos Items.",
            ),
        ]

        self.model = ItensTableModel(columns=table_columns)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.setMouseTracking(True)
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.SelectedClicked | QtWidgets.QAbstractItemView.EditKeyPressed
        )
        self.table.setStyleSheet(
            """
            QTableView::item:selected {
                background-color: #d0d0d0;
                color: #202020;
            }
            QTableView::item:hover {
                background-color: #c3c3c3;
            }
            """
        )
        self.table.clicked.connect(self._on_table_clicked)
        self.model.dataChanged.connect(lambda *_, **__: self._set_costs_dirty(True))

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        f = header.font()
        f.setBold(True)
        header.setFont(f)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._suppress_selection_signal = False

        # Larguras iniciais (podes ajustar no runtime/UI)
        column_widths = {
            "id_item": 55,
            "item_nome": 70,
            "codigo": 110,
            "descricao": 360,
            "altura": 80,
            "largura": 80,
            "profundidade": 90,
            "und": 70,
            "qt": 60,
            "preco_unitario": 140,
            "preco_total": 150,
            "custo_produzido": 140,
            "ajuste": 110,
            "custo_total_orlas": 150,
            "custo_total_mao_obra": 170,
            "custo_total_materia_prima": 180,
            "custo_total_acabamentos": 170,
            "margem_lucro_perc": 140,
            "valor_margem": 140,
            "custos_admin_perc": 150,
            "valor_custos_admin": 150,
            "margem_acabamentos_perc": 150,
            "valor_acabamentos": 150,
            "margem_mp_orlas_perc": 150,
            "valor_mp_orlas": 150,
            "margem_mao_obra_perc": 150,
            "valor_mao_obra": 150,
            "custo_colagem": 120,
        }

        for i, col_def in enumerate(table_columns):
            attr = col_def.get("attr")
            width = column_widths.get(attr or "")
            if width:
                header.resizeSection(i, width)

        self._init_dimensions_ui()

        self.edit_altura.textEdited.connect(lambda text: self._on_primary_dimension_text_edited("H", text))
        self.edit_largura.textEdited.connect(lambda text: self._on_primary_dimension_text_edited("L", text))
        self.edit_profundidade.textEdited.connect(lambda text: self._on_primary_dimension_text_edited("P", text))

        # Altura das linhas (como combin?mos: 26px colapsado)
        self._row_height_collapsed = 26
        self._row_height_expanded = 70
        self._rows_expanded = False
        vh = self.table.verticalHeader()
        vh.setDefaultSectionSize(self._row_height_collapsed)
        vh.setSectionResizeMode(QHeaderView.Fixed)

        # Sele??o -> preencher formul?rio
        if self.table.selectionModel():
            self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self._apply_row_height()

        # ------------------------------------------------------------------
        # 4) Ligar bot?es aos handlers existentes
        # ------------------------------------------------------------------
        self.btn_add.clicked.connect(self.on_new_item)
        self.btn_save.clicked.connect(self.on_save_item)
        self.btn_del.clicked.connect(self.on_del)
        if hasattr(self, "btn_toggle_rows"):
            self.btn_toggle_rows.toggled.connect(self.on_toggle_rows)
        self.btn_up.clicked.connect(lambda: self.on_move(-1))
        self.btn_dn.clicked.connect(lambda: self.on_move(1))

        # Estado inicial
        self._clear_form()
        self.destroyed.connect(lambda: self._stop_custeio_worker())

    # ==========================================================================
    # Carregamento do or?amento + refresh
    # ==========================================================================
    def load_orcamento(self, orc_id: int):
        """Carrega dados do or?amento e preenche cabe?alho."""
        def _txt(v) -> str:
            return "" if v is None else str(v)

        def _fmt_ver(v) -> str:
            if v in (None, ""):
                return ""
            try:
                return f"{int(v):02d}"
            except (TypeError, ValueError):
                return _txt(v)

        self._orc_id = orc_id
        self._update_cost_button_state()
        cliente_nome = ""
        ano_txt = ""
        num_txt = ""
        ver_txt = ""
        username = ""
        o = self.db.get(Orcamento, orc_id)
        if o:
            cliente = self.db.get(Client, o.client_id)
            user = self.db.get(User, o.created_by) if o.created_by else None
            if not user and getattr(self.current_user, "id", None):
                user = self.db.get(User, getattr(self.current_user, "id", None))
            username = getattr(user, "username", "") or getattr(self.current_user, "username", "") or ""

            cliente_nome = _txt(getattr(cliente, "nome", ""))
            ano_txt = _txt(getattr(o, "ano", ""))
            num_txt = _txt(getattr(o, "num_orcamento", ""))
            ver_txt = _fmt_ver(getattr(o, "versao", ""))

            self.lbl_cliente_val.setText(cliente_nome)
            self.lbl_ano_val.setText(ano_txt)
            self.lbl_num_val.setText(num_txt)
            self.lbl_ver_val.setText(ver_txt)
            self.lbl_user_val.setText(_txt(username))
        else:
            self.lbl_cliente_val.setText("")
            self.lbl_ano_val.setText("")
            self.lbl_num_val.setText("")
            self.lbl_ver_val.setText("")
            self.lbl_user_val.setText("")
        if hasattr(self, "lbl_highlight"):
            apply_highlight_text(
                self.lbl_highlight,
                cliente=cliente_nome or "",
                numero=num_txt or "",
                versao=ver_txt or "",
                ano=ano_txt or "",
                utilizador=username or "",
            )

        self._load_production_mode()
        self._load_orcamento_margem_config(self._orc_id)
        self.refresh()

    def refresh(
        self,
        select_row: Optional[int] = None,
        select_last: bool = False,
        select_id: Optional[int] = None,
    ):
        """Atualiza a tabela; se vazia, prepara pr?ximo item."""
        self._update_cost_button_state()
        if not self._orc_id:
            self.model.set_rows([])
            self._clear_form()
            self._set_costs_dirty(False)
            return

        versao_filtro = (self.lbl_ver_val.text() or '').strip() or None
        if versao_filtro:
            try:
                versao_filtro = f"{int(versao_filtro):02d}"
            except Exception:
                pass
        rows = list_items(self.db, self._orc_id, versao=versao_filtro)
        self.model.set_rows(rows)
        self._apply_row_height()
        self._set_costs_dirty(False)

        if rows:
            row_to_select: Optional[int] = None
            if select_id is not None:
                for idx, row in enumerate(rows):
                    rid = getattr(row, "id_item", None)
                    if rid == select_id:
                        row_to_select = idx
                        break
            if row_to_select is None:
                if select_row is not None:
                    row_to_select = max(0, min(select_row, len(rows) - 1))
                elif select_last:
                    row_to_select = len(rows) - 1
                else:
                    row_to_select = 0
            if row_to_select is not None:
                logger.debug("Itens.refresh selecting row %s for select_id=%s", row_to_select, select_id)
                self._select_table_row(row_to_select)
                self._apply_selection_to_form()
        else:
            self._prepare_next_item(focus_codigo=False)

    # ==========================================================================
    # Helpers de sele??o / user / parsing
    # ==========================================================================
    def selected_id(self) -> Optional[int]:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        row = self.model.get_row(idx.row())
        return getattr(row, "id_item", None)

    def focus_item(self, item_id: Optional[int]) -> None:
        if not getattr(self, "table", None) or not getattr(self, "model", None):
            return
        if item_id in (None, ""):
            selection_model = self.table.selectionModel()
            if selection_model is None:
                return
            self._suppress_selection_signal = True
            try:
                selection_model.clearSelection()
            finally:
                self._suppress_selection_signal = False
            return
        row_count = self.model.rowCount()
        if row_count <= 0:
            return
        try:
            target_id = int(item_id)
        except (TypeError, ValueError):
            target_id = item_id
        row_to_select: Optional[int] = None
        for row_idx in range(row_count):
            try:
                row = self.model.get_row(row_idx)
            except Exception:
                continue
            row_id = getattr(row, "id_item", None) or getattr(row, "id_item_fk", None)
            if row_id == target_id:
                row_to_select = row_idx
                break
        if row_to_select is None or row_to_select < 0:
            return
        self._select_table_row(row_to_select)
        self._apply_selection_to_form()

    def _current_user_id(self) -> Optional[int]:
        return getattr(self.current_user, "id", None)

    def _production_context(self) -> Optional[svc_producao.ProducaoContext]:
        if not self._orc_id:
            return None
        user_id = self._current_user_id()
        if not user_id:
            return None
        versao_text = (self.lbl_ver_val.text() or "").strip() or None
        try:
            return svc_producao.build_context(self.db, self._orc_id, user_id, versao=versao_text)
        except Exception as exc:
            logger.exception("Itens._production_context failed: %s", exc)
            return None

    def _update_mode_buttons(self) -> None:
        mode = (self._production_mode or "STD").upper()
        self.btn_mode_std.blockSignals(True)
        self.btn_mode_serie.blockSignals(True)
        self.btn_mode_std.setChecked(mode == "STD")
        self.btn_mode_serie.setChecked(mode == "SERIE")
        self.btn_mode_std.blockSignals(False)
        self.btn_mode_serie.blockSignals(False)
        self._update_cost_button_state()

    def _update_cost_button_state(self) -> None:
        if hasattr(self, "btn_update_costs"):
            self.btn_update_costs.setEnabled(bool(self._orc_id))
            self._apply_costs_button_text()

    def _apply_costs_button_text(self) -> None:
        if not hasattr(self, "btn_update_costs"):
            return
        base = getattr(self, "_base_update_costs_text", "Atualizar Custos")
        text = f"{base}*" if getattr(self, "_costs_dirty", False) else base
        self.btn_update_costs.setText(text)

    def _set_costs_dirty(self, dirty: bool) -> None:
        dirty = bool(dirty)
        if getattr(self, "_costs_dirty", False) == dirty:
            return
        self._costs_dirty = dirty
        self._apply_costs_button_text()

    def _clear_layout_items(self, layout: Optional[QtWidgets.QLayout]) -> None:
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.setParent(None)
            if child_layout is not None:
                self._clear_layout_items(child_layout)

    def _rebuild_form_layout(self) -> None:
        frame = getattr(self, "form_frame", None)
        if not isinstance(frame, QtWidgets.QFrame):
            return
        base_layout = frame.layout()
        if not isinstance(base_layout, QtWidgets.QGridLayout):
            return
        self._clear_layout_items(base_layout)
        base_layout.setContentsMargins(8, 6, 8, 6)
        base_layout.setHorizontalSpacing(0)
        base_layout.setVerticalSpacing(0)

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(4, 2, 4, 2)

        left_group = QtWidgets.QGroupBox("Item do Orçamento", frame)
        left_group.setFlat(False)
        left_group_layout = QtWidgets.QVBoxLayout(left_group)
        left_group_layout.setContentsMargins(10, 8, 10, 20) # left, top, right, bottom
        left_group_layout.setSpacing(8)

        def _field(label_text: str, widget: QtWidgets.QWidget, width: Optional[int] = None) -> QtWidgets.QWidget:
            container = QtWidgets.QWidget(frame)
            lay = QtWidgets.QHBoxLayout(container)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(4)
            lbl = QtWidgets.QLabel(label_text, container)
            lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
            lay.addWidget(lbl)
            widget.setParent(container)
            if width:
                widget.setFixedWidth(width)
            lay.addWidget(widget)
            return container

        fields_row = QtWidgets.QHBoxLayout()
        fields_row.setSpacing(12)
        fields_row.addWidget(_field("Item", self.edit_item, 70))
        fields_row.addWidget(_field("Código", self.edit_codigo, 200))
        fields_row.addWidget(_field("Altura", self.edit_altura, 100))
        fields_row.addWidget(_field("Largura", self.edit_largura, 100))
        fields_row.addWidget(_field("Profundidade", self.edit_profundidade, 100))
        fields_row.addWidget(_field("Qt", self.edit_qt, 70))
        fields_row.addWidget(_field("Und", self.edit_und, 80))
        fields_row.addStretch(1)
        left_group_layout.addLayout(fields_row)

        desc_row = QtWidgets.QHBoxLayout()
        desc_row.setContentsMargins(0, 0, 0, 0) # 3 px de “folga” por baixo
        desc_row.setSpacing(6)
        desc_label = QtWidgets.QLabel("Descrição", frame)
        desc_label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        desc_row.addWidget(desc_label)
        self.edit_descricao.setParent(frame)
        self.edit_descricao.setMinimumHeight(180)
        desc_row.addWidget(self.edit_descricao, 1)
        left_group_layout.addLayout(desc_row)

        main_layout.addWidget(left_group, 3)

        if hasattr(self, "_top_right_panel") and isinstance(self._top_right_panel, QtWidgets.QWidget):
            self._top_right_panel.setParent(frame)
            self._top_right_panel.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
            main_layout.addWidget(self._top_right_panel, 0, QtCore.Qt.AlignTop)

        base_layout.addLayout(main_layout, 0, 0, 1, 1)

    def _set_custeio_status(self, text: Optional[str], *, busy: bool = False) -> None:
        label = getattr(self, "lbl_custeio_status", None)
        if label is None:
            return
        if not text:
            label.hide()
            label.setText("")
            return
        prefix = "..." if busy else ""
        label.setText(f"{prefix}{text}")
        label.show()

    def _set_margens_panel_enabled(self, enabled: bool) -> None:
        for widget in list(self._margem_inputs.values()) + [getattr(self, "spin_objetivo", None)]:
            if widget is not None:
                widget.setEnabled(enabled)
        if hasattr(self, "btn_margens_reset"):
            self.btn_margens_reset.setEnabled(enabled)
        if hasattr(self, "btn_margens_save"):
            self.btn_margens_save.setEnabled(enabled and self._margens_dirty)
        if hasattr(self, "btn_objetivo_apply"):
            self.btn_objetivo_apply.setEnabled(enabled)

    def _set_margem_inputs(self, valores: Mapping[str, Decimal]) -> None:
        self._margens_loading = True
        for key, spin in self._margem_inputs.items():
            valor = valores.get(key, Decimal("0"))
            try:
                flt = float(Decimal(str(valor)))
            except Exception:
                flt = 0.0
            spin.blockSignals(True)
            spin.setValue(flt)
            spin.blockSignals(False)
        self._margens_loading = False

    def _collect_margem_inputs(self) -> Dict[str, Decimal]:
        valores: Dict[str, Decimal] = {}
        for key, spin in self._margem_inputs.items():
            valores[key] = Decimal(f"{spin.value():.2f}")
        return valores

    def _on_margem_spin_changed(self, _key: str) -> None:
        if getattr(self, "_margens_loading", False):
            return
        self._margens_dirty = True
        if hasattr(self, "btn_margens_save"):
            self.btn_margens_save.setEnabled(bool(self._orc_id))

    def _load_orcamento_margem_config(self, orc_id: Optional[int]) -> None:
        if not hasattr(self, "_margem_inputs"):
            return
        config = svc_margens.load_orcamento_config(self.db, orc_id)
        self._current_margem_config = config
        self._set_margem_inputs(config["percent"])
        objetivo = config.get("objetivo", Decimal("0.00"))
        if hasattr(self, "spin_objetivo"):
            self.spin_objetivo.blockSignals(True)
            self.spin_objetivo.setValue(float(objetivo))
            self.spin_objetivo.blockSignals(False)
        soma = config.get("soma") or (svc_margens.somar_preco_total(self.db, orc_id) if orc_id else Decimal("0.00"))
        self._current_margem_config["soma"] = soma
        self._update_sum_preco_label(soma)
        self._margens_dirty = False
        if hasattr(self, "btn_margens_save"):
            self.btn_margens_save.setEnabled(False)
        self._set_margens_panel_enabled(bool(orc_id))

    def _update_sum_preco_label(self, total: Optional[Decimal]) -> None:
        if not hasattr(self, "lbl_soma_preco"):
            return
        if total is None:
            self.lbl_soma_preco.setText("0,00 €")
            return
        try:
            text = f"{Decimal(str(total)).quantize(Decimal('0.01')):,.2f} €"
        except Exception:
            text = "0,00 €"
        self.lbl_soma_preco.setText(text.replace(",", "X").replace(".", ",").replace("X", "."))

    def refresh_margem_defaults(self) -> None:
        if self._orc_id:
            self._load_orcamento_margem_config(self._orc_id)
        else:
            valores = svc_margens.load_margens(self.db)
            self._set_margem_inputs(valores)
            self._update_sum_preco_label(Decimal("0.00"))
            self._set_margens_panel_enabled(False)

    def _persist_margens_config(self, *, auto: bool, commit: bool) -> Optional[Dict[str, Decimal]]:
        if not self._orc_id:
            return None
        valores = self._collect_margem_inputs()
        objetivo = Decimal(f"{self.spin_objetivo.value():.2f}")
        try:
            soma_atual = self._current_margem_config.get("soma")
            svc_margens.save_orcamento_config(self.db, self._orc_id, valores, objetivo, soma=soma_atual)
            if commit:
                self.db.commit()
            else:
                self.db.flush()
        except Exception as exc:
            self.db.rollback()
            if auto:
                logger.exception("ItensPage: falha ao guardar margens: %s", exc)
            else:
                QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao guardar margens: {exc}")
            return None
        self._current_margem_config["percent"] = valores
        self._current_margem_config["objetivo"] = objetivo
        self._margens_dirty = False
        if hasattr(self, "btn_margens_save"):
            self.btn_margens_save.setEnabled(False)
        return self._current_margem_config

    def _on_save_margens_clicked(self) -> None:
        if not self._orc_id:
            QtWidgets.QMessageBox.information(self, "Margens", "Selecione um orçamento antes de guardar.")
            return
        if self._persist_margens_config(auto=False, commit=True):
            QtWidgets.QMessageBox.information(self, "Margens", "Margens guardadas.")

    def _on_reset_margens_clicked(self) -> None:
        valores = svc_margens.load_margens(self.db)
        self._set_margem_inputs(valores)
        if hasattr(self, "spin_objetivo"):
            self.spin_objetivo.blockSignals(True)
            self.spin_objetivo.setValue(0.0)
            self.spin_objetivo.blockSignals(False)
        self._margens_dirty = True
        if hasattr(self, "btn_margens_save"):
            self.btn_margens_save.setEnabled(bool(self._orc_id))

    def _on_apply_objetivo_clicked(self) -> None:
        if not self._orc_id:
            QtWidgets.QMessageBox.information(self, "Margens & Ajustes", "Selecione um orçamento antes de ajustar as margens.")
            return
        objetivo = Decimal(f"{self.spin_objetivo.value():.2f}")
        if objetivo <= Decimal("0.00"):
            QtWidgets.QMessageBox.information(
                self,
                "Margens & Ajustes",
                "Defina um valor positivo em 'Atingir Objetivo Preço Final (€)'.",
            )
            return

        button = getattr(self, "btn_objetivo_apply", None)
        if button is not None:
            button.setDisabled(True)
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        total_calculado: Optional[Decimal] = None
        atingiu = False
        try:
            percentuais = self._collect_margem_inputs()
            novos_percentuais, estimativa, atingiu = svc_margens.ajustar_percentuais_para_objetivo(
                self.db, self._orc_id, percentuais, objetivo
            )
            self._set_margem_inputs(novos_percentuais)
            self._margens_dirty = True
            if self._persist_margens_config(auto=True, commit=False) is None:
                raise RuntimeError("Não foi possível guardar as margens.")
            total_calculado = self._apply_margens_to_items()
            self.db.commit()
        except ValueError as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.information(self, "Margens & Ajustes", str(exc))
            return
        except Exception as exc:
            self.db.rollback()
            logger.exception("ItensPage: falha ao ajustar margens para objetivo: %s", exc)
            QtWidgets.QMessageBox.critical(
                self,
                "Margens & Ajustes",
                f"Não foi possível ajustar as margens:\n{exc}",
            )
            return
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            if button is not None:
                button.setEnabled(True)

        if total_calculado is not None:
            self._update_sum_preco_label(total_calculado)
        else:
            self._update_sum_preco_label(None)

        self.refresh(select_id=self.selected_id())
        self._apply_selection_to_form()
        if hasattr(self, "btn_margens_save"):
            self.btn_margens_save.setEnabled(False)

        toast_target = button or self._margem_panel
        if atingiu:
            message = "Objetivo alcançado dentro da tolerância (±0,50 €)."
        else:
            message = "Margens ajustadas. Objetivo fora da tolerância (±0,50 €)."
        self._show_toast(toast_target, message)

    def _apply_margens_to_items(self) -> Optional[Decimal]:
        if not self._orc_id:
            return None
        valores = self._collect_margem_inputs()
        total = svc_margens.aplicar_margens_orcamento(self.db, self._orc_id, valores)
        svc_margens.update_sum_preco_final(self.db, self._orc_id, total)
        self._current_margem_config["percent"] = valores
        self._current_margem_config["soma"] = total
        return total

    def _start_custeio_batch_update(self, mode: str) -> None:
        if not self._orc_id:
            return
        if self._custeio_thread and self._custeio_thread.isRunning():
            self._set_custeio_status("Atualização em andamento...", busy=True)
            return
        worker = CusteioBatchWorker(
            orcamento_id=self._orc_id,
            versao=(self.lbl_ver_val.text() or "").strip() or "01",
            production_mode=mode,
            user_id=self._current_user_id(),
        )
        thread = QtCore.QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_custeio_batch_progress)
        worker.finished.connect(self._on_custeio_batch_finished)
        self._custeio_worker = worker
        self._custeio_thread = thread
        self._set_custeio_status("A atualizar custeio dos items...", busy=True)
        thread.start()

    @QtCore.Slot(int, int)
    def _on_custeio_batch_progress(self, done: int, total: int) -> None:
        if total <= 0:
            self._set_custeio_status("A atualizar custeio...", busy=True)
            return
        self._set_custeio_status(f"A atualizar custeio ({done}/{total})...", busy=True)

    @QtCore.Slot(bool, str)
    def _on_custeio_batch_finished(self, success: bool, message: str) -> None:
        worker = self._custeio_worker
        thread = self._custeio_thread
        self._custeio_worker = None
        self._custeio_thread = None
        if worker is not None:
            worker.deleteLater()
        if thread is not None:
            thread.quit()
            thread.wait()
            thread.deleteLater()
        if success:
            self._set_custeio_status("Custeio atualizado.")
            QtCore.QTimer.singleShot(3000, lambda: self._set_custeio_status(None))
        else:
            self._set_custeio_status(None)
            if message and message != "cancelled":
                QtWidgets.QMessageBox.warning(
                    self,
                    "Custeio",
                    f"Falha ao atualizar custeio: {message}",
                )

    def _stop_custeio_worker(self) -> None:
        if self._custeio_worker:
            self._custeio_worker.request_cancel()
        if self._custeio_thread:
            self._custeio_thread.quit()
            self._custeio_thread.wait()
            self._custeio_thread.deleteLater()
            self._custeio_thread = None
        if self._custeio_worker:
            self._custeio_worker.deleteLater()
            self._custeio_worker = None

    def _show_toast(self, widget: Optional[QtWidgets.QWidget], text: str, timeout_ms: int = 2500) -> None:
        if not widget or not text:
            return
        try:
            rect = widget.rect()
            center = rect.center()
            global_pos = widget.mapToGlobal(center)
            QtWidgets.QToolTip.showText(global_pos, text, widget, rect, timeout_ms)
        except Exception:
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), text)

    def _load_production_mode(self) -> None:
        ctx = self._production_context()
        has_ctx = ctx is not None
        self.btn_mode_std.setEnabled(has_ctx)
        self.btn_mode_serie.setEnabled(has_ctx)
        mode = "STD"
        if ctx is not None:
            try:
                mode = svc_producao.get_mode(self.db, ctx)
            except Exception as exc:
                logger.exception("Itens._load_production_mode failed: %s", exc)
                mode = "STD"
        if mode not in {"STD", "SERIE"}:
            mode = "STD"
        self._production_mode = mode
        self._update_mode_buttons()
        self.production_mode_changed.emit(mode)

    def _on_update_item_costs_clicked(self) -> None:
        if not self._orc_id:
            QtWidgets.QMessageBox.information(self, "Atualizar Custos", "Nenhum orçamento carregado.")
            return

        button = getattr(self, "btn_update_costs", None)
        if button:
            button.setDisabled(True)

        selected_item_id = self.selected_id()
        try:
            self.db.flush()
        except Exception:
            pass
        try:
            self.db.expire_all()
        except Exception:
            pass

        current_index = self.table.currentIndex()
        current_row = current_index.row() if current_index.isValid() else None

        total_preco = None
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            if self._persist_margens_config(auto=True, commit=False) is None:
                QtWidgets.QApplication.restoreOverrideCursor()
                if button:
                    button.setEnabled(True)
                return
            atualizados = svc_custeio.atualizar_resumo_custos_orcamento(self.db, self._orc_id)
            total_preco = self._apply_margens_to_items()
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QApplication.restoreOverrideCursor()
            logger.exception("Itens._on_update_item_costs_clicked failed: %s", exc)
            QtWidgets.QMessageBox.critical(
                self,
                "Atualizar Custos",
                f"Não foi possível atualizar os custos a partir do Custeio dos Items:\n{exc}",
            )
            if button:
                button.setEnabled(True)
            return
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        try:
            self.db.expire_all()
        except Exception:
            pass

        self.refresh(select_row=current_row, select_id=selected_item_id)
        self._apply_selection_to_form()
        if total_preco is not None:
            self._update_sum_preco_label(total_preco)

        if button:
            button.setEnabled(True)
        self._set_costs_dirty(False)

        if atualizados:
            self._show_toast(button or self.table, f"Custos atualizados para {atualizados} item(s).")
        else:
            self._show_toast(
                button or self.table,
                "Custeio dos Items sem dados para este orçamento/versão.",
            )

    def _on_mode_clicked(self, mode: str) -> None:
        mode_norm = (mode or "").upper()
        if mode_norm not in {"STD", "SERIE"}:
            self._update_mode_buttons()
            return
        ctx = self._production_context()
        if ctx is None:
            QMessageBox.information(self, "Aviso", "Selecione um orcamento antes de alterar o modo produtivo.")
            self._update_mode_buttons()
            return
        if mode_norm == (self._production_mode or "").upper():
            self._update_mode_buttons()
            return
        try:
            svc_producao.set_mode(self.db, ctx, mode_norm)
            self.db.commit()
            self._production_mode = mode_norm
            self.production_mode_changed.emit(mode_norm)
            self._start_custeio_batch_update(mode_norm)
        except Exception as exc:
            self.db.rollback()
            QMessageBox.critical(self, "Erro", f"Falha ao definir modo de producao: {exc}")
        finally:
            self._update_mode_buttons()

    def _parse_decimal(self, text: Optional[str], *, default: Optional[Decimal] = None) -> Optional[Decimal]:
        if text is None:
            return default
        t = text.strip()
        if not t:
            return default
        t = t.replace(",", ".")
        try:
            return Decimal(t)
        except (InvalidOperation, ValueError):
            raise ValueError

    def _force_uppercase(self, widget: QtWidgets.QLineEdit, text: str):
        cursor = widget.cursorPosition()
        widget.blockSignals(True)
        widget.setText(text.upper())
        widget.setCursorPosition(cursor)
        widget.blockSignals(False)

    def _focus_next_field(self, index: int):
        if not getattr(self, "_input_sequence", None):
            return
        next_idx = (index + 1) % len(self._input_sequence)
        w = self._input_sequence[next_idx]
        w.setFocus()
        if isinstance(w, QtWidgets.QLineEdit):
            w.selectAll()

    def _decimal_from_input(self, widget: QtWidgets.QLineEdit, label: str, *, default: Optional[Decimal] = None) -> Optional[Decimal]:
        try:
            return self._parse_decimal(widget.text(), default=default)
        except ValueError:
            raise ValueError(f"Valor inv?lido para {label}.")
        
    def _validate_dimensions(self, data: dict) -> None:
        labels = {"altura": "Altura", "largura": "Comprimento", "profundidade": "Profundidade"}
        warnings: List[str] = []
        for field, (min_v, max_v) in DIMENSION_LIMITS.items():
            value = data.get(field)
            if value is None:
                continue
            if value <= 0:
                warnings.append(f"{labels[field]} deve ser superior a 0.")
                continue
            if value < min_v or value > max_v:
                warnings.append(
                    f"{labels[field]} {value} mm está fora do intervalo recomendado ({min_v} - {max_v} mm)."
                )
        if not warnings:
            return
        message = "\n".join(warnings + ["Pretende manter estes valores?"])
        resp = QMessageBox.question(
            self,
            "Confirmar dimensões",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            raise ValueError("Valores de dimensão fora dos limites padrão.")

    # ==========================================================================
    # Formulário: ler/preencher/limpar
    # ==========================================================================
    def _collect_form_data(self) -> dict:
        data = {
            "item": self.edit_item.text().strip() or None,
            "codigo": (self.edit_codigo.text().strip().upper() or None),
            "descricao": (self.edit_descricao.toPlainText().strip() or None),
            "altura": self._decimal_from_input(self.edit_altura, "Altura"),
            "largura": self._decimal_from_input(self.edit_largura, "Largura"),
            "profundidade": self._decimal_from_input(self.edit_profundidade, "Profundidade"),
            "und": self.edit_und.text().strip() or None,
            "qt": self._decimal_from_input(self.edit_qt, "QT", default=Decimal("1")),
        }
        self._validate_dimensions(data)
        return data

    def _format_decimal(self, value) -> str:
        if value in (None, ""):
            return ""
        try:
            dec = Decimal(str(value))
        except Exception:
            return str(value)
        text = format(dec, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    # ==========================================================================
    # Tabela de vari?veis dimensionais (H, L, P, H1...)
    # ==========================================================================
    def _init_dimensions_ui(self) -> None:
        self._dimension_values: Dict[str, Optional[float]] = {key: None for key in DIMENSION_KEY_ORDER}
        self._dimension_col_map: Dict[str, int] = {key: idx for idx, key in enumerate(DIMENSION_KEY_ORDER)}
        self._dimensions_dirty = False

        self.dimensions_table = QtWidgets.QTableWidget(2, len(DIMENSION_KEY_ORDER), self)
        self.dimensions_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.dimensions_table.setFixedHeight(72)
        self.dimensions_table.verticalHeader().setVisible(False)
        self.dimensions_table.horizontalHeader().setVisible(False)
        self.dimensions_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.dimensions_table.setFocusPolicy(Qt.StrongFocus)
        self.dimensions_table.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        self.dimensions_table.setAlternatingRowColors(True)
        self.dimensions_table.setStyleSheet(
            "QTableWidget { gridline-color: #d0d0d0; }"
        )

        for row in range(2):
            self.dimensions_table.setRowHeight(row, 28 if row else 24)

        for col, key in enumerate(DIMENSION_KEY_ORDER):
            header_item = QtWidgets.QTableWidgetItem(key)
            header_item.setFlags(QtCore.Qt.ItemIsEnabled)
            header_item.setTextAlignment(QtCore.Qt.AlignCenter)
            header_font = header_item.font()
            header_font.setBold(True)
            header_item.setFont(header_font)
            self.dimensions_table.setItem(0, col, header_item)

            value_item = QtWidgets.QTableWidgetItem("")
            value_item.setTextAlignment(QtCore.Qt.AlignCenter)
            if key in PRIMARY_DIMENSION_KEYS:
                value_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            else:
                value_item.setFlags(
                    QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled
                )
            self.dimensions_table.setItem(1, col, value_item)
            self.dimensions_table.setColumnWidth(col, 60)

        self.dimensions_table.itemChanged.connect(self._on_dimension_item_changed)

        # Inserir no layout principal antes da tabela de itens
        self.dimensions_frame = QtWidgets.QFrame(self)
        frame_layout = QtWidgets.QVBoxLayout(self.dimensions_frame)
        frame_layout.setContentsMargins(0, 4, 0, 4)
        frame_layout.setSpacing(0)
        frame_layout.addWidget(self.dimensions_table)

        added = False
        if hasattr(self, "dimensions_placeholder_layout"):
            placeholder = self.dimensions_placeholder_layout
            if isinstance(placeholder, QtWidgets.QLayout):
                placeholder.addWidget(self.dimensions_frame)
                added = True
        if not added and hasattr(self, "verticalLayoutMain"):
            layout: QtWidgets.QVBoxLayout = self.verticalLayoutMain
            table_index = layout.indexOf(self.table)
            if table_index == -1:
                layout.addWidget(self.dimensions_frame)
            else:
                layout.insertWidget(table_index, self.dimensions_frame)
            added = True

        if added:
            self._configure_main_layout_stretch()

        self._set_dimensions_enabled(False)
        self._update_dimension_table()

    def _configure_main_layout_stretch(self) -> None:
        if not hasattr(self, "verticalLayoutMain"):
            return
        layout: QtWidgets.QVBoxLayout = self.verticalLayoutMain
        count = layout.count()
        for idx in range(count):
            layout.setStretch(idx, 0)

        table_index = layout.indexOf(self.table)
        if table_index != -1:
            layout.setStretch(table_index, 1)

    def _format_dimension_value(self, value: Optional[float]) -> str:
        if value is None:
            return ""
        if abs(value - int(round(value))) < 1e-6:
            return str(int(round(value)))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def _coerce_dimension_value(self, text: Any) -> Optional[float]:
        if text in (None, ""):
            return None
        stripped = str(text).strip()
        if not stripped:
            return None
        stripped = stripped.replace(",", ".")
        try:
            return float(stripped)
        except ValueError:
            return None

    def _style_dimension_cell(self, item: Optional[QtWidgets.QTableWidgetItem], key: str) -> None:
        if item is None:
            return
        text = (item.text() or "").strip()
        has_value = bool(text)
        color = DIMENSION_COLOR_MAP.get(key)
        if has_value and color is not None:
            item.setBackground(QtGui.QBrush(color))
        else:
            item.setBackground(QtGui.QBrush(QtCore.Qt.transparent))
        font = item.font()
        font.setBold(has_value)
        item.setFont(font)

    def _set_dimension_value(
        self,
        key: str,
        value: Optional[float],
        *,
        mark_dirty: bool = False,
        source_item: Optional[QtWidgets.QTableWidgetItem] = None,
    ) -> None:
        if key not in self._dimension_values:
            return
        current = self._dimension_values.get(key)
        if current == value:
            target_item = source_item or self.dimensions_table.item(1, self._dimension_col_map.get(key, -1))
            self._style_dimension_cell(target_item, key)
            if mark_dirty and current != value:
                self._dimensions_dirty = True
            return

        self._dimension_values[key] = value
        target_item = source_item
        if target_item is None and hasattr(self, "dimensions_table"):
            col = self._dimension_col_map.get(key)
            if col is not None and col >= 0:
                target_item = self.dimensions_table.item(1, col)
        if target_item is not None:
            self.dimensions_table.blockSignals(True)
            target_item.setText(self._format_dimension_value(value))
            self.dimensions_table.blockSignals(False)
            self._style_dimension_cell(target_item, key)
        if mark_dirty:
            self._dimensions_dirty = True

    def _update_dimension_table(self) -> None:
        if not hasattr(self, "dimensions_table"):
            return
        self.dimensions_table.blockSignals(True)
        for key, col in self._dimension_col_map.items():
            item = self.dimensions_table.item(1, col)
            if item is None:
                item = QtWidgets.QTableWidgetItem("")
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.dimensions_table.setItem(1, col, item)
            item.setText(self._format_dimension_value(self._dimension_values.get(key)))
            self._style_dimension_cell(item, key)
        self.dimensions_table.blockSignals(False)

    def _set_dimensions_enabled(self, enabled: bool) -> None:
        if hasattr(self, "dimensions_table"):
            self.dimensions_table.setEnabled(enabled)

    def _clear_dimension_values(self, *, enable: bool = False) -> None:
        self._dimension_values = {key: None for key in DIMENSION_KEY_ORDER}
        self._dimensions_dirty = False
        self._set_dimensions_enabled(enable)
        self._update_dimension_table()

    def _collect_dimension_payload(self) -> Dict[str, Optional[float]]:
        return {key: self._dimension_values.get(key) for key in DIMENSION_KEY_ORDER}

    def _on_primary_dimension_text_edited(self, key: str, text: str) -> None:
        value = self._coerce_dimension_value(text)
        self._set_dimension_value(key, value, mark_dirty=True)

    def _apply_primary_dimensions_to_table(self, *, mark_dirty: bool) -> None:
        values = {
            "H": self._coerce_dimension_value(self.edit_altura.text()),
            "L": self._coerce_dimension_value(self.edit_largura.text()),
            "P": self._coerce_dimension_value(self.edit_profundidade.text()),
        }
        updated = False
        for key, new_value in values.items():
            if self._dimension_values.get(key) != new_value:
                self._set_dimension_value(key, new_value, mark_dirty=mark_dirty)
                updated = True
            else:
                col = self._dimension_col_map.get(key)
                item = self.dimensions_table.item(1, col) if col is not None else None
                self._style_dimension_cell(item, key)
        if mark_dirty and updated:
            self._dimensions_dirty = True

    def _load_dimension_values_for_item(self, item: Optional[OrcamentoItem]) -> None:
        item_id = getattr(item, "id_item", None)
        if not item_id or not self._orc_id:
            self._clear_dimension_values(enable=bool(self._orc_id))
            self._apply_primary_dimensions_to_table(mark_dirty=False)
            return
        try:
            ctx = svc_dados_items.carregar_contexto(self.db, self._orc_id, item_id)
        except Exception as exc:  # pragma: no cover - apenas log
            logger.exception("ItensPage falha ao carregar contexto de dimensoes: %s", exc)
            self._clear_dimension_values(enable=True)
            self._apply_primary_dimensions_to_table(mark_dirty=False)
            return
        try:
            armazenados, tem_registro = svc_custeio.carregar_dimensoes(self.db, ctx)
        except Exception as exc:  # pragma: no cover - apenas log
            logger.exception("ItensPage falha ao carregar dimensoes armazenadas: %s", exc)
            armazenados, tem_registro = {}, False

        defaults = svc_custeio.dimensoes_default_por_item(item)
        for key in DIMENSION_KEY_ORDER:
            valor = armazenados.get(key)
            if valor is None and not tem_registro:
                valor = defaults.get(key)
            self._dimension_values[key] = valor
        self._dimensions_dirty = False
        self._set_dimensions_enabled(True)
        self._update_dimension_table()
        self._apply_primary_dimensions_to_table(mark_dirty=False)

    def _persist_dimensions(self, item_id: Optional[int], *, force: bool = False) -> None:
        if not item_id or not self._orc_id:
            return
        if not force and not self._dimensions_dirty:
            return
        try:
            ctx = svc_dados_items.carregar_contexto(self.db, self._orc_id, item_id)
        except Exception as exc:
            raise RuntimeError(f"Falha ao preparar contexto de dimensoes: {exc}") from exc
        payload = self._collect_dimension_payload()
        try:
            svc_custeio.guardar_dimensoes(self.db, ctx, payload)
        except Exception as exc:
            raise RuntimeError(f"Falha ao guardar dimensoes do item: {exc}") from exc

    def _on_dimension_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if item.row() != 1:
            return
        key = DIMENSION_KEY_ORDER[item.column()]
        novo_valor = self._coerce_dimension_value(item.text())
        if item.text().strip() and novo_valor is None:
            self.dimensions_table.blockSignals(True)
            item.setText(self._format_dimension_value(self._dimension_values.get(key)))
            self.dimensions_table.blockSignals(False)
            self._style_dimension_cell(item, key)
            return
        self._set_dimension_value(key, novo_valor, mark_dirty=True, source_item=item)

    def _populate_form(self, item):
        self.edit_item.setText(getattr(item, "item_nome", "") or "")
        self.edit_codigo.setText((getattr(item, "codigo", "") or "").upper())
        self.edit_descricao.setPlainText(getattr(item, "descricao", "") or "")
        self.edit_altura.setText(self._format_decimal(getattr(item, "altura", None)))
        self.edit_largura.setText(self._format_decimal(getattr(item, "largura", None)))
        self.edit_profundidade.setText(self._format_decimal(getattr(item, "profundidade", None)))
        self.edit_und.setText(getattr(item, "und", "") or "und")
        qt_txt = self._format_decimal(getattr(item, "qt", None))
        self.edit_qt.setText(qt_txt or "1")
        self.edit_item.setReadOnly(True)
        self._edit_item_id = getattr(item, "id_item", None)
        self._load_dimension_values_for_item(item)

    def _clear_form(self):
        self.edit_item.clear()
        self.edit_codigo.clear()
        self.edit_descricao.clear()
        self.edit_altura.clear()
        self.edit_largura.clear()
        self.edit_profundidade.clear()
        self.edit_und.setText("und")
        self.edit_qt.setText("1")
        self.edit_item.setReadOnly(True)
        self._edit_item_id = None
        self._clear_dimension_values(enable=bool(self._orc_id))

    # ======================================================================
    # Descrição - regras de formatação e menu auxiliar
    # ======================================================================
    def _apply_descricao_header_rule(self) -> None:
        if getattr(self, "_descricao_update_block", False):
            return
        self._descricao_update_block = True
        try:
            self._ensure_descricao_header_capitalized()
        finally:
            self._descricao_update_block = False

    def _on_descricao_text_changed(self) -> None:
        self._apply_descricao_header_rule()

    def _ensure_descricao_header_capitalized(self) -> None:
        if not hasattr(self, "edit_descricao"):
            return
        doc = self.edit_descricao.document()
        block = doc.firstBlock()
        if not block.isValid():
            return
        text = block.text()
        idx = None
        for pos, ch in enumerate(text):
            if ch.strip():
                idx = pos
                break
        if idx is None:
            return
        char = text[idx]
        if not char.isalpha():
            return
        upper = char.upper()
        if char == upper:
            return
        user_cursor = self.edit_descricao.textCursor()
        user_anchor = user_cursor.anchor()
        user_pos = user_cursor.position()
        cursor = QtGui.QTextCursor(doc)
        cursor.beginEditBlock()
        cursor.setPosition(block.position() + idx)
        cursor.movePosition(QtGui.QTextCursor.NextCharacter, QtGui.QTextCursor.KeepAnchor)
        cursor.insertText(upper)
        cursor.endEditBlock()
        restore = QtGui.QTextCursor(doc)
        restore.setPosition(user_anchor)
        restore.setPosition(user_pos, QtGui.QTextCursor.KeepAnchor)
        self.edit_descricao.setTextCursor(restore)

    def _on_descricao_context_menu(self, pos: QtCore.QPoint) -> None:
        if not hasattr(self, "edit_descricao"):
            return
        menu = self.edit_descricao.createStandardContextMenu()
        menu.addSeparator()
        menu.addAction(self._descricao_menu_action)
        menu.exec(self.edit_descricao.mapToGlobal(pos))

    def _open_descricoes_predef_dialog(self) -> None:
        user_id = self._current_user_id()
        if not user_id:
            QtWidgets.QMessageBox.information(self, "Descrições", "Utilizador não identificado para carregar descrições.")
            return
        dialog = DescricoesPredefinidasDialog(parent=self, user_id=user_id)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        entries = dialog.checked_entries()
        if not entries:
            QtWidgets.QMessageBox.information(
                self,
                "Descrições",
                "Marque as caixas das descrições que pretende inserir.",
            )
            return
        self._insert_predefined_descriptions(entries)

    def _insert_predefined_descriptions(self, entries) -> None:
        if not hasattr(self, "edit_descricao") or not entries:
            return
        lines = []
        for entry in entries:
            texto_raw: Optional[str]
            if hasattr(entry, "texto"):
                texto_raw = getattr(entry, "texto")
            elif isinstance(entry, dict):
                texto_raw = entry.get("texto")
            else:
                texto_raw = str(entry)
            texto = (texto_raw or "").strip()
            if not texto:
                continue
            if hasattr(entry, "tipo"):
                tipo_raw = getattr(entry, "tipo")
            elif isinstance(entry, dict):
                tipo_raw = entry.get("tipo")
            else:
                tipo_raw = "-"
            tipo = tipo_raw if tipo_raw in {"-", "*"} else "-"
            lines.append(f"\t{tipo} {texto}")
        if not lines:
            return
        insertion = "\n".join(lines)
        cursor = self.edit_descricao.textCursor()
        cursor.beginEditBlock()
        try:
            cursor.movePosition(QtGui.QTextCursor.End)
            existing = self.edit_descricao.toPlainText()
            if existing.strip() and not existing.endswith("\n"):
                cursor.insertText("\n")
            cursor.insertText(insertion)
        finally:
            cursor.endEditBlock()
        self.edit_descricao.setTextCursor(cursor)
        self._apply_descricao_header_rule()

    # ==========================================================================
    # Tabela: altura das linhas
    # ==========================================================================
    def _apply_row_height(self):
        vh = self.table.verticalHeader()
        if not vh:
            return
        h = self._row_height_expanded if getattr(self, "_rows_expanded", False) else self._row_height_collapsed
        vh.setSectionResizeMode(QHeaderView.Fixed)
        vh.setDefaultSectionSize(h)
        if self.model.rowCount():
            for r in range(self.model.rowCount()):
                vh.resizeSection(r, h)
        self._update_toggle_rows_button(getattr(self, "_rows_expanded", False))

    def _on_table_clicked(self, index: QtCore.QModelIndex) -> None:
        if not index or not index.isValid() or not hasattr(self, "model"):
            return
        try:
            col_def = self.model.columns[index.column()]
            spec = self.model._col_spec(col_def)
        except Exception:
            return
        if spec.get("attr") != "ajuste":
            return
        QtCore.QTimer.singleShot(0, lambda idx=QtCore.QModelIndex(index): self.table.edit(idx))

    def _clear_table_selection(self):
        sm = self.table.selectionModel()
        if not sm:
            return
        blocker = QtCore.QSignalBlocker(sm)
        sm.clearSelection()
        sm.setCurrentIndex(QtCore.QModelIndex(), QItemSelectionModel.Clear)

    def _select_table_row(self, row_index: int) -> None:
        selection_model = self.table.selectionModel()
        if selection_model is None:
            self.table.selectRow(row_index)
            return
        self._suppress_selection_signal = True
        try:
            selection_model.clearSelection()
            index = self.model.index(row_index, 0)
            if index.isValid():
                selection_model.select(
                    index,
                    QtCore.QItemSelectionModel.Select
                    | QtCore.QItemSelectionModel.Rows
                    | QtCore.QItemSelectionModel.ClearAndSelect,
                )
                self.table.setCurrentIndex(index)
                self.table.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)
        finally:
            self._suppress_selection_signal = False

    def _apply_selection_to_form(self) -> None:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return
        try:
            row = self.model.get_row(idx.row())
        except Exception:
            return
        self._populate_form(row)

    def _update_toggle_rows_button(self, expanded: bool) -> None:
        if not hasattr(self, "btn_toggle_rows"):
            return
        style = self._style or self.style() or QtWidgets.QApplication.style()
        blocker = QtCore.QSignalBlocker(self.btn_toggle_rows)
        self.btn_toggle_rows.setChecked(expanded)
        del blocker
        if expanded:
            self.btn_toggle_rows.setText("Colapsar")
            self.btn_toggle_rows.setIcon(style.standardIcon(QtWidgets.QStyle.SP_ArrowUp))
            self.btn_toggle_rows.setToolTip("Reduzir altura das linhas com descrições longas.")
        else:
            self.btn_toggle_rows.setText("Expandir")
            self.btn_toggle_rows.setIcon(style.standardIcon(QtWidgets.QStyle.SP_ArrowDown))
            self.btn_toggle_rows.setToolTip("Expandir descrições longas na tabela.")

    # ==========================================================================
    # Fluxo: novo/selec??o/guardar/eliminar/mover
    # ==========================================================================
    def _prepare_next_item(self, *, focus_codigo: bool = True):
        self._clear_table_selection()
        self._clear_form()
        if not self._orc_id:
            return
        versao_atual = (self.lbl_ver_val.text() or "").strip()
        if not versao_atual:
            return
        versao_norm = versao_atual.zfill(2)
        proximo = self._next_item_number(self._orc_id, versao_norm)
        self.edit_item.setText(str(proximo))
        self.edit_item.setReadOnly(True)
        if focus_codigo:
            self.edit_codigo.setFocus()

    def on_selection_changed(self, selected, deselected):
        idx = self.table.currentIndex()
        suppress_emit = getattr(self, "_suppress_selection_signal", False)
        if not idx.isValid():
            self._prepare_next_item()
            if not suppress_emit:
                self.item_selected.emit(None)
            return
        try:
            row = self.model.get_row(idx.row())
        except Exception:
            self._prepare_next_item()
            if not suppress_emit:
                self.item_selected.emit(None)
            return
        self._populate_form(row)
        item_id = getattr(row, "id_item", None) or getattr(row, "id_item_fk", None)
        if not suppress_emit:
            self.item_selected.emit(item_id)

    def _next_item_number(self, orc_id: int, versao: str) -> int:
        total = self.db.execute(
            select(func.count(OrcamentoItem.id_item)).where(
                OrcamentoItem.id_orcamento == orc_id,
                OrcamentoItem.versao == versao,
            )
        ).scalar() or 0
        return int(total) + 1

    def on_new_item(self):
        if not self._orc_id:
            QMessageBox.warning(self, "Aviso", "Nenhum or?amento selecionado.")
            return
        if not (self.lbl_ver_val.text() or "").strip():
            QMessageBox.warning(self, "Aviso", "Nenhuma vers?o definida.")
            return
        self._prepare_next_item()

    def on_save_item(self):
        if not self._orc_id:
            QMessageBox.warning(self, "Aviso", "Nenhum or?amento selecionado.")
            return
        versao_atual = (self.lbl_ver_val.text() or "").strip()
        if not versao_atual:
            QMessageBox.warning(self, "Aviso", "Nenhuma vers?o definida.")
            return
        versao_norm = versao_atual.zfill(2)

        id_item = self._edit_item_id
        if id_item is None:
            idx = self.table.currentIndex()
            if idx.isValid():
                try:
                    row = self.model.get_row(idx.row())
                    id_item = getattr(row, "id_item", None)
                except Exception:
                    id_item = None

        if not (self.edit_item.text() or "").strip():
            self.edit_item.setText(str(self._next_item_number(self._orc_id, versao_norm)))

        try:
            self._apply_primary_dimensions_to_table(mark_dirty=True)
            form = self._collect_form_data()
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
            return

        new_row = None
        persist_target_id: Optional[int] = None
        try:
            logger.debug("Itens.on_save_item id_item before save: %s", id_item)
            if id_item:
                update_item(
                    self.db,
                    id_item,
                    versao=versao_norm,
                    item=form["item"],
                    codigo=form["codigo"],
                    descricao=form["descricao"],
                    altura=form["altura"],
                    largura=form["largura"],
                    profundidade=form["profundidade"],
                    und=form["und"],
                    qt=form["qt"],
                    updated_by=self._current_user_id(),
                )
                persist_target_id = id_item
                msg = "Item atualizado com sucesso."
            else:
                new_row = create_item(
                    self.db,
                    self._orc_id,
                    versao=versao_norm,
                    item=form["item"],
                    codigo=form["codigo"],
                    descricao=form["descricao"],
                    altura=form["altura"],
                    largura=form["largura"],
                    profundidade=form["profundidade"],
                    und=form["und"] or "und",
                    qt=form["qt"],
                    created_by=self._current_user_id(),
                )
                persist_target_id = getattr(new_row, "id_item", None)
                msg = "Item gravado com sucesso."

            if persist_target_id:
                self._persist_dimensions(persist_target_id, force=True)

            self.db.commit()
            self._dimensions_dirty = False
            target_id = getattr(new_row, "id_item", None) or persist_target_id
            logger.debug("Itens.on_save_item target_id after save: %s", target_id)
            self.refresh(select_id=target_id, select_last=target_id is None)
            QMessageBox.information(self, "Sucesso", msg)
            if target_id:
                logger.debug("Itens.on_save_item emit target_id=%s", target_id)
                self.item_selected.emit(target_id)
            self.production_mode_changed.emit(self._production_mode)
            self._prepare_next_item()

        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Erro", f"Erro ao gravar item:\n{str(e)}")

    def on_del(self):
        id_item = self.selected_id()
        if not id_item:
            return
        row = self.table.currentIndex().row()
        if QtWidgets.QMessageBox.question(self, "Confirmar", f"Eliminar item {id_item}?") != QtWidgets.QMessageBox.Yes:
            return
        try:
            delete_item(self.db, id_item, deleted_by=self._current_user_id())
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar: {e}")
            return
        self.refresh(select_row=row)

    def on_move(self, direction: int):
        id_item = self.selected_id()
        if not id_item:
            return
        try:
            move_item(self.db, id_item, direction, moved_by=self._current_user_id())
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao mover: {e}")
            return
        # Recarrega mantendo o item selecionado no novo posicionamento
        self.refresh(select_id=id_item)

    def on_expand_rows(self):
        if hasattr(self, "btn_toggle_rows"):
            self.btn_toggle_rows.setChecked(True)
        else:
            self._rows_expanded = True
            self._apply_row_height()

    def on_collapse_rows(self):
        if hasattr(self, "btn_toggle_rows"):
            self.btn_toggle_rows.setChecked(False)
        else:
            self._rows_expanded = False
            self._apply_row_height()

    def on_toggle_rows(self, checked: bool):
        self._rows_expanded = checked
        self._apply_row_height()







