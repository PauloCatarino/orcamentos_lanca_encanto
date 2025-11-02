# Martelo_Orcamentos_V2/ui/pages/itens.py
# -----------------------------------------------------------------------------
# P?gina de Itens (V2) ? carrega layout do Qt Designer (.ui) com QUiLoader
# - O .ui fica em: Martelo_Orcamentos_V2/ui/forms/itens_form.ui
# - Mant?m toda a l?gica de BD, valida??o e opera??es
# -----------------------------------------------------------------------------

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
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
from ..models.qt_table import SimpleTableModel
from ..utils.header import apply_highlight_text, init_highlight_label

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


# ---------- helper para carregar .ui e expor widgets por objectName ----------
def _load_ui_into(widget: QtWidgets.QWidget, ui_path: str) -> QtWidgets.QWidget:
    """
    Carrega um .ui para dentro de 'widget' usando QUiLoader e
    exp?e todos os filhos (por objectName) como atributos de 'widget'.
    Ex.: no .ui existe QLineEdit com objectName 'edit_codigo' ? podes usar self.edit_codigo.
    """
    loader = QUiLoader()
    f = QFile(ui_path)
    if not f.open(QFile.ReadOnly):
        raise FileNotFoundError(f"N?o consegui abrir UI: {ui_path}")
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


class ItensPage(QtWidgets.QWidget):
    item_selected = Signal(object)
    production_mode_changed = Signal(str)
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.db = SessionLocal()
        self._orc_id: Optional[int] = None
        self._edit_item_id: Optional[int] = None

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
        self.btn_mode_std.setIcon(style.standardIcon(QtWidgets.QStyle.SP_DialogApplyButton))
        self.btn_mode_serie.setIcon(style.standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        self.btn_mode_std.setToolTip("Usar dados STD (standard) no custeio.")
        self.btn_mode_serie.setToolTip("Usar dados em serie no custeio.")
        self.btn_mode_std.clicked.connect(lambda: self._on_mode_clicked("STD"))
        self.btn_mode_serie.clicked.connect(lambda: self._on_mode_clicked("SERIE"))
        self._production_mode = "STD"
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
        table_columns = [
            ("ID", "id_item"),
            ("Item", "item_nome"),
            ("Codigo", "codigo"),
            ("Descricao", "descricao"),
            ("Altura", "altura", _fmt_int),
            ("Largura", "largura", _fmt_int),
            ("Profundidade", "profundidade", _fmt_int),
            ("Und", "und"),
            ("QT", "qt", _fmt_int),
            ("Preco_Unit", "preco_unitario", _fmt_int),
            ("Preco_Total", "preco_total", _fmt_int),
            ("Custo Produzido", "custo_produzido", _fmt_int),
            ("Ajuste", "ajuste", _fmt_int),
            ("Custo Total Orlas (?)", "custo_total_orlas", _fmt_int),
            ("Custo Total M?o de Obra (?)", "custo_total_mao_obra", _fmt_int),
            ("Custo Total Mat?ria Prima (?)", "custo_total_materia_prima", _fmt_int),
            ("Custo Total Acabamentos (?)", "custo_total_acabamentos", _fmt_int),
            ("Margem de Lucro (%)", "margem_lucro_perc", _fmt_int),
            ("Valor da Margem (?)", "valor_margem", _fmt_int),
            ("Custos Administrativos (%)", "custos_admin_perc", _fmt_int),
            ("Valor Custos Admin. (?)", "valor_custos_admin", _fmt_int),
            ("Margem_Acabamentos(%)", "margem_acabamentos_perc", _fmt_int),
            ("Valor Margem_Acabamentos (?)", "valor_acabamentos", _fmt_int),
            ("Margem MP_Orlas (%)", "margem_mp_orlas_perc", _fmt_int),
            ("Valor Margem MP_Orlas (?)", "valor_mp_orlas", _fmt_int),
            ("Margem Mao_Obra (%)", "margem_mao_obra_perc", _fmt_int),
            ("Valor Margem Mao_Obra (?)", "valor_mao_obra", _fmt_int),
            ("reservado_1", "reservado_1"),
            ("reservado_2", "reservado_2"),
            ("reservado_3", "reservado_3"),
        ]

        self.model = SimpleTableModel(columns=table_columns)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.ElideNone)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        f = header.font()
        f.setBold(True)
        header.setFont(f)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Larguras iniciais (podes ajustar no runtime/UI)
        column_widths = {
            "ID": 50, "Item": 60, "Codigo": 110, "Descricao": 320,
            "Altura": 80, "Largura": 80, "Profundidade": 100, "Und": 60, "QT": 60,
            "Preco_Unit": 110, "Preco_Total": 120, "Custo Produzido": 130, "Ajuste": 110,
            "Custo Total Orlas (?)": 150, "Custo Total M?o de Obra (?)": 170,
            "Custo Total Mat?ria Prima (?)": 190, "Custo Total Acabamentos (?)": 180,
            "Margem de Lucro (%)": 150, "Valor da Margem (?)": 150,
            "Custos Administrativos (%)": 160, "Valor Custos Admin. (?)": 170,
            "Margem_Acabamentos(%)": 160, "Valor Margem_Acabamentos (?)": 190,
            "Margem MP_Orlas (%)": 160, "Valor Margem MP_Orlas (?)": 190,
            "Margem Mao_Obra (%)": 160, "Valor Margem Mao_Obra (?)": 190,
            "reservado_1": 120, "reservado_2": 120, "reservado_3": 120,
        }
        for i, col_def in enumerate(table_columns):
            w = column_widths.get(col_def[0])
            if w:
                header.resizeSection(i, w)

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
        self.refresh()

    def refresh(
        self,
        select_row: Optional[int] = None,
        select_last: bool = False,
        select_id: Optional[int] = None,
    ):
        """Atualiza a tabela; se vazia, prepara pr?ximo item."""
        if not self._orc_id:
            self.model.set_rows([])
            self._clear_form()
            return

        rows = list_items(self.db, self._orc_id)
        self.model.set_rows(rows)
        self._apply_row_height()

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
                self.table.selectRow(row_to_select)
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

    def _clear_table_selection(self):
        sm = self.table.selectionModel()
        if not sm:
            return
        blocker = QtCore.QSignalBlocker(sm)
        sm.clearSelection()
        sm.setCurrentIndex(QtCore.QModelIndex(), QItemSelectionModel.Clear)

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
        if not idx.isValid():
            self._prepare_next_item()
            self.item_selected.emit(None)
            return
        try:
            row = self.model.get_row(idx.row())
        except Exception:
            self._prepare_next_item()
            self.item_selected.emit(None)
            return
        self._populate_form(row)
        item_id = getattr(row, "id_item", None) or getattr(row, "id_item_fk", None)
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
        row = self.table.currentIndex().row()
        try:
            move_item(self.db, id_item, direction, moved_by=self._current_user_id())
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao mover: {e}")
            return
        self.refresh(select_row=row)

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
