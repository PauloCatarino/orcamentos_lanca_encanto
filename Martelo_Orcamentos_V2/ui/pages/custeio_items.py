#-\nROW_PARENT_COLOR = QtGui.QColor(230, 240, 255)  # Azul claro para linhas pai\nROW_CHILD_COLOR = QtGui.QColor(255, 250, 205)   # Amarelo suave para linhas filho\nROW_CHILD_INDENT = '\u2003\u2003'  # Espaços para indentação visual dos filhos\n-- START OF FILE custeio_items.py ---



from __future__ import annotations



from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple
import ast
import re
import unicodedata
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

MANUAL_QT_UND_KEYWORDS: Tuple[str, ...] = (
    "DOBRADICA",
    "DOBRADICAS",
    "SUPORTE PRATELEIRA",
    "SUPORTE PRATELEIRAS",
    "PUXADOR",
    "PUXADORES",
    "SUPORTE VARAO",
    "SUPORTE TERMINAL VARAO",
    "SUPORTE CENTRAL VARAO",
)


def _float_almost_equal(a: Optional[float], b: Optional[float], *, tol: float = 1e-6) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= tol

DIMENSION_KEY_ORDER: Sequence[str] = tuple(svc_custeio.DIMENSION_KEY_ORDER)
DIMENSION_ALLOWED_VARIABLES: Set[str] = set(svc_custeio.DIMENSION_ALLOWED_VARIABLES)
_TOKEN_PATTERN = re.compile(r"[A-Z]+[0-9]*")
_FORMULA_ALLOWED_CHARS = re.compile(r"^[0-9A-Z+\-*/().,\\s]*$")
_AUTO_QTMOD_PATTERN = re.compile(r"^\s*\d+(?:[.,]\d+)?\s*x\s*\d+(?:[.,]\d+)?\s*$", re.IGNORECASE)
_NUMERIC_LITERAL_PATTERN = re.compile(r"^\s*[0-9]+(?:[.,][0-9]+)?\s*$")

DIMENSION_GROUPS: Tuple[Tuple[str, str, str], ...] = (
    ("H", "L", "P"),
    ("H1", "L1", "P1"),
    ("H2", "L2", "P2"),
    ("H3", "L3", "P3"),
    ("H4", "L4", "P4"),
)
DIMENSION_GROUP_COLORS: Tuple[QtGui.QColor, ...] = (
    QtGui.QColor("#FFF2CC"),
    QtGui.QColor("#CCE5FF"),
    QtGui.QColor("#D4EDDA"),
    QtGui.QColor("#F8D7DA"),
    QtGui.QColor("#E2D9FF"),
)
DIMENSION_COLOR_MAP: Dict[str, QtGui.QColor] = {}
for color, group in zip(DIMENSION_GROUP_COLORS, DIMENSION_GROUPS):
    for key in group:
        DIMENSION_COLOR_MAP[key] = color

HEADER_TOOLTIPS = {
    "descricao_livre": "Texto livre editavel para identificar a linha no custeio.",
    "def_peca": "Codigo da peca selecionada na arvore de definicoes.",
    "descricao": "Descricao base importada do material associado.",
    "qt_mod": "Quantidade de modulos a produzir com esta linha.",
    "qt_und": "Quantidade de unidades por modulo.",
    "blk": "Quando ativo bloqueia atualizacoes vindas da tabela Dados Items.",
    "nst": "Indica que o material foi marcado como Nao-Stock nos Dados Items.",
    "mat_default": "Grupo de material usado como origem das informacoes desta linha.",
    "acabamento_sup": "Acabamento aplicado na face superior (selecionado a partir da lista de acabamentos).",
    "acabamento_inf": "Acabamento aplicado na face inferior (selecionado a partir da lista de acabamentos).",
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
    "area_m2_und": "Area (m2) calculada por unidade com base em comp_res e larg_res.",
    "perimetro_und": "Perimetro (m) calculado por unidade (2 x (comp_res + larg_res) em metros).",
    "spp_ml_und": "Comprimento (m) por unidade gerado a partir de COMP_res quando a peca e classificada como SPP/ML.",
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
    "acabamento_sup": 150,
    "acabamento_inf": 150,
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
    "area_m2_und": 90,
    "perimetro_und": 90,
}

# Row display helpers
# Background colors for parent/child rows in the `def_peca` column.
ROW_PARENT_COLOR = QtGui.QColor(220, 220, 220)  # slightly darker background for parent rows
ROW_CHILD_COLOR = QtGui.QColor(245, 245, 245)   # light background for child rows
# Indentation prefix used for child rows' text in the `def_peca` column.
ROW_CHILD_INDENT = "    "


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
        self._manual_override_font = QtGui.QFont(self._italic_font)
        self._manual_override_font.setUnderline(True)
        # Font used to render child component names (italic + underline)
        self._child_font = QtGui.QFont(self._italic_font)
        self._child_font.setUnderline(True)

        base_font = QtWidgets.QApplication.font()
        self._division_font = QtGui.QFont(base_font)
        point_size = base_font.pointSizeF()
        if point_size <= 0:
            point_size = 10.0
        self._division_font.setPointSizeF(point_size + 2.0)
        self._division_font.setBold(True)

        self._bold_font = QtGui.QFont(base_font)
        self._bold_font.setBold(True)

        self.rows: List[Dict[str, Any]] = []
        self._orla_info_cache: Dict[Tuple[str, Optional[float]], Tuple[float, float, Optional[str]]] = {}

    # --- Helpers ------------------------------------------------------

    def _mark_dirty(self, dirty: bool = True) -> None:
        page = getattr(self, "_page", None)
        if page is not None and hasattr(page, "_set_rows_dirty"):
            page._set_rows_dirty(bool(dirty))

    def _normalized_token(self, row: Mapping[str, Any]) -> str:
        normalized = row.get("_normalized_child") or row.get("_normalized_def")
        if normalized:
            return str(normalized)

        raw = (
            row.get("_child_source")
            or row.get("descricao")
            or row.get("tipo")
            or row.get("def_peca")
            or ""
        )
        normalized = self._normalize_def_peca(raw)
        if isinstance(row, dict):
            row["_normalized_child"] = normalized
            row["_normalized_def"] = normalized
        return normalized

    @staticmethod
    def _is_varao_child_token(token: str) -> bool:
        if not token:
            return False
        has_varao = "VARAO" in token
        has_support = "SUPORTE" in token
        return has_varao and not has_support

    def _supports_qt_und_override(self, row: Mapping[str, Any]) -> bool:
        """Return True when the row is an automatic child eligible for override."""
        if not isinstance(row, Mapping):
            return False

        if (row.get("_row_type") or "").lower() != "child":
            return False

        normalized = self._normalized_token(row)
        if not normalized:
            return False

        if self._is_varao_child_token(normalized):
            return False

        return any(keyword in normalized for keyword in MANUAL_QT_UND_KEYWORDS)

    @staticmethod
    def _coerce_numeric(value: Any) -> Optional[float]:
        if value in (None, "", False):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _ensure_orla_info(self, row_data: Dict[str, Any], side: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Garante que os campos orl_pliq e orl_desp para o lado indicado estão preenchidos a partir da Materia Prima."""
        ref_raw = row_data.get(f"orl_ref_{side}") or row_data.get("ref_le")
        ref_clean = None
        if ref_raw not in (None, ""):
            try:
                ref_clean = str(ref_raw).strip()
            except Exception:
                ref_clean = str(ref_raw)
            ref_clean = ref_clean or None

        pliq = row_data.get(f"orl_pliq_{side}")
        desp = row_data.get(f"orl_desp_{side}")

        base_pliq = row_data.get("pliq")

        needs_lookup = False
        if ref_clean is None:
            needs_lookup = False
        else:
            if pliq in (None, ""):
                needs_lookup = True
            else:
                try:
                    pliq_float = float(pliq)
                    base_float = float(base_pliq) if base_pliq not in (None, "") else None
                except (TypeError, ValueError):
                    pliq_float = None
                    base_float = None
                if pliq_float is None:
                    needs_lookup = True
                elif base_float is not None and abs(pliq_float - base_float) < 1e-6:
                    needs_lookup = True
            if desp in (None, ""):
                needs_lookup = True

        if needs_lookup and ref_clean:
            page = getattr(self, "_page", None)
            session = getattr(page, "session", None) if page is not None else None

            if session is not None:
                esp_raw = row_data.get(f"orl_{side}")
                try:
                    esp_val = float(str(esp_raw).replace(",", ".")) if esp_raw not in (None, "") else None
                except (TypeError, ValueError):
                    esp_val = None

                cache_key = (ref_clean, esp_val)
                info = self._orla_info_cache.get(cache_key)
                if info is None:
                    try:
                        info = svc_custeio._obter_info_orla_por_ref(session, ref_clean, esp_esperada=esp_val)
                    except Exception:
                        info = (0.0, 0.0, ref_clean)
                    self._orla_info_cache[cache_key] = info
                preco_m2, desp_percent, matched = info
                if preco_m2:
                    row_data[f"orl_pliq_{side}"] = preco_m2
                    pliq = preco_m2
                if desp_percent not in (None, ""):
                    row_data[f"orl_desp_{side}"] = desp_percent
                    desp = desp_percent
                if matched:
                    row_data[f"orl_ref_{side}"] = matched
                    ref_clean = matched

        return pliq, desp, ref_clean

    def _process_qt_und_edit(self, row_index: int, value: Any) -> bool:
        if not (0 <= row_index < len(self.rows)):
            return False
        row = self.rows[row_index]
        new_value = self._coerce_numeric(value)
        manual_allowed = self._supports_qt_und_override(row)
        formula_val = self._coerce_numeric(row.get("_qt_formula_value"))
        row_type = (row.get("_row_type") or "").lower()

        if manual_allowed:
            manual_override = False
            manual_value: Optional[float] = None
            stored_child = self._coerce_numeric(row.get("qt_und"))

            if new_value is None:
                manual_override = False
            elif formula_val is not None and _float_almost_equal(new_value, formula_val):
                manual_override = False
            else:
                page = getattr(self, "_page", None)
                confirmer = getattr(page, "confirm_qt_und_override", None)
                if callable(confirmer):
                    if not confirmer(row, new_value):
                        return False
                manual_override = True
                manual_value = new_value

            if manual_allowed and not manual_override and manual_value is None:
                if manual_value is None and stored_child is not None and formula_val is not None and not _float_almost_equal(stored_child, formula_val):
                    manual_override = True
                    manual_value = stored_child

            if manual_override and manual_value is not None:
                row["qt_und"] = manual_value
                row["_qt_manual_override"] = True
                row["_qt_manual_value"] = manual_value
                formatted_formula = self._format_result_number(formula_val) or str(formula_val) if formula_val is not None else ""
                row["_qt_manual_tooltip"] = f"Valor manual (formula: {formatted_formula})" if formatted_formula else "Valor manual"
            else:
                row["_qt_manual_override"] = False
                row["_qt_manual_value"] = None
                if formula_val is not None:
                    row["qt_und"] = formula_val
                else:
                    row["qt_und"] = new_value
                row["_qt_manual_tooltip"] = None
            self._mark_dirty()
            return True

        if row_type == "child":
            if formula_val is not None:
                row["qt_und"] = formula_val
            else:
                row["qt_und"] = new_value
        else:
            row["qt_und"] = new_value
        row["_qt_manual_override"] = False
        row["_qt_manual_value"] = None
        row["_qt_manual_tooltip"] = None
        self._mark_dirty()
        return True

    def is_qt_und_manual(self, row_index: int) -> bool:
        if not (0 <= row_index < len(self.rows)):
            return False
        row = self.rows[row_index]
        if (row.get("_row_type") or "").lower() != "child":
            return False
        manual_value = self._coerce_numeric(row.get("_qt_manual_value"))
        if manual_value is not None:
            return True
        if not self._supports_qt_und_override(row):
            return False
        stored = self._coerce_numeric(row.get("qt_und"))
        formula = self._coerce_numeric(row.get("_qt_formula_value"))
        if stored is None or formula is None:
            return False
        return not _float_almost_equal(stored, formula)

    def revert_qt_und(self, row_indices: Sequence[int]) -> None:
        if not row_indices:
            return
        changed = False
        for row_index in sorted(set(row_indices)):
            if not self.is_qt_und_manual(row_index):
                continue
            row = self.rows[row_index]
            formula = self._coerce_numeric(row.get("_qt_formula_value"))
            if formula is None:
                continue
            row["qt_und"] = formula
            row["_qt_manual_override"] = False
            row["_qt_manual_value"] = None
            row["_qt_manual_tooltip"] = None
            changed = True
        if not changed:
            return
        self._mark_dirty()
        self.recalculate_all()

    @staticmethod
    def _normalize_def_peca(value: Optional[str]) -> str:
        text = (value or "").strip()
        if not text:
            return ""
        normalized = unicodedata.normalize("NFKD", text)
        cleaned = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        return cleaned.upper()

    def _is_division_row(self, row: Mapping[str, Any]) -> bool:
        return self._normalize_def_peca(row.get("def_peca")) == "DIVISAO INDEPENDENTE"

    def _is_modulo_row(self, row: Mapping[str, Any]) -> bool:
        return self._normalize_def_peca(row.get("def_peca")) == "MODULO"

    def _is_spp_row(self, row: Mapping[str, Any]) -> bool:
        und = (row.get("und") or "").strip().upper()
        if und == "ML":
            return True
        def_peca_norm = self._normalize_def_peca(row.get("def_peca"))
        raw_def = (row.get("def_peca") or "").upper()
        if "{SPP}" in raw_def:
            return True
        return def_peca_norm.startswith("SPP")

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
        # Division rows: mostrar apenas o valor de qt_mod da divisão
        if self._is_division_row(row):
            return self._format_factor(row.get("qt_mod")) or ""

        parts: List[str] = []

        # Mostra o divisor (valor da divisão) se existir
        divisor_raw = row.get("_qt_divisor")
        divisor_text = self._format_factor(divisor_raw)
        if divisor_text:
            parts.append(divisor_text)

        # Para linhas do tipo 'parent' queremos: divisor x qt_und
        if row_type == "parent":
            parent_raw = row.get("qt_und")
            if parent_raw not in (None, ""):
                parent_text = self._format_factor(parent_raw) or str(parent_raw)
                parts.append(parent_text)
            return " x ".join(parts)

        # Para componentes child: divisor x parent_qt_und x child_qt_und
        if row_type == "child":
            parent_id = row.get("_parent_uid")
            parent_row = next((r for r in self.rows if r.get("_uid") == parent_id), None)
            if parent_row is not None:
                p_raw = parent_row.get("qt_und")
                if p_raw not in (None, ""):
                    p_text = self._format_factor(p_raw) or str(p_raw)
                    parts.append(p_text)
            # child qt_und - show even if equals 1 when explicitly set
            c_raw = row.get("qt_und")
            if c_raw not in (None, ""):
                c_text = self._format_factor(c_raw) or str(c_raw)
                parts.append(c_text)
            return " x ".join(parts)

        # Outros tipos (normal): mostrar qt_und quando presente
        q_raw = row.get("qt_und")
        if q_raw not in (None, ""):
            q_text = self._format_factor(q_raw) or str(q_raw)
            parts.append(q_text)

        return " x ".join(parts)

    def _sanitize_formula_input(self, value: Any) -> Optional[str]:
        if value in (None, False):
            return ""
        text = str(value)
        if not text:
            return ""
        text = text.replace(",", ".").upper()
        # Allow spaces in the expression
        if not _FORMULA_ALLOWED_CHARS.match(text):
            return None
        tokens = _TOKEN_PATTERN.findall(text)
        for token in tokens:
            if token not in DIMENSION_ALLOWED_VARIABLES:
                return None
        return text.strip()

    @staticmethod
    def _format_result_number(value: Optional[float]) -> Optional[str]:
        if value is None:
            return None
        if abs(value - int(round(value))) < 1e-6:
            return str(int(round(value)))
        return f"{value:.4f}".rstrip("0").rstrip(".")

    def _prepare_formula_expression(self, value: Any) -> str:
        if value in (None, ""):
            return ""
        text = str(value).replace(",", ".").upper()
        return text.strip()

    def _build_formula_tooltip(
        self,
        expression: str,
        result: Optional[float],
        error: Optional[str],
        *,
        substitutions: Optional[str] = None,
    ) -> Optional[str]:
        expression = expression.strip()
        substitutions = (substitutions or "").strip()
        if substitutions.startswith("(") and substitutions.endswith(")"):
            inner = substitutions[1:-1].strip()
            if inner.count("(") == inner.count(")"):
                substitutions = inner or substitutions

        if error:
            base = f"{expression} = erro: {error}" if expression else f"Erro: {error}"
            return base
        if expression and substitutions and result is not None:
            if substitutions.strip() and substitutions.strip() != expression.strip():
                rendered = f"{expression} = {substitutions} = {self._format_result_number(result)}"
                return rendered
        if expression and result is not None:
            return f"{expression} = {self._format_result_number(result)}"
        if expression:
            return expression
        if result is not None:
            return self._format_result_number(result)
        return None

    def _evaluate_formula_expression(
        self,
        expression: str,
        context: Mapping[str, Optional[float]],
    ) -> Tuple[Optional[float], Optional[str]]:
        expr = expression.strip()
        if not expr:
            return (None, None)

        safe_context: Dict[str, Optional[float]] = {}
        for key, value in (context or {}).items():
            if key is None:
                continue
            safe_context[key.upper()] = value

        try:
            node = ast.parse(expr, mode="eval")
            value, substitution = self._eval_formula_ast(node.body, safe_context)
            return (float(value), None)
        except ZeroDivisionError:
            return (None, "Divisao por zero")
        except Exception as exc:
            msg = str(exc).lower()
            if "variavel" in msg and ("hm" in msg or "lm" in msg or "pm" in msg):
                return (None, f"Variavel local nao definida: {exc}")
            return (None, str(exc))

    def _render_formula_substitution(
        self,
        expression: str,
        context: Mapping[str, Optional[float]],
    ) -> Optional[str]:
        expr = expression.strip()
        if not expr:
            return None

        def replace(match: re.Match) -> str:
            token = match.group(0)
            value = context.get(token.upper())
            if value is None:
                return token
            formatted = self._format_result_number(float(value))
            return formatted or str(value)

        substituted = _TOKEN_PATTERN.sub(replace, expr)
        substituted = substituted.strip()
        return substituted or None

    def _evaluate_formula_with_env(
        self,
        prepared_expression: str,
        context: Mapping[str, Optional[float]],
    ) -> Tuple[Optional[float], Optional[str], Optional[str]]:
        if not prepared_expression:
            return (None, None, None)
        value, error = self._evaluate_formula_expression(prepared_expression, context)
        substitution = self._render_formula_substitution(prepared_expression, context)
        if error is None and value is not None:
            value = round(value, 1)
        return (value, error, substitution)

    def _eval_formula_ast(self, node: ast.AST, variables: Mapping[str, Optional[float]]) -> Tuple[float, str]:
        if isinstance(node, ast.BinOp):
            left_val, left_expr = self._eval_formula_ast(node.left, variables)
            right_val, right_expr = self._eval_formula_ast(node.right, variables)
            if isinstance(node.op, ast.Add):
                return left_val + right_val, f"({left_expr}+{right_expr})"
            if isinstance(node.op, ast.Sub):
                return left_val - right_val, f"({left_expr}-{right_expr})"
            if isinstance(node.op, ast.Mult):
                return left_val * right_val, f"({left_expr}*{right_expr})"
            if isinstance(node.op, ast.Div):
                return left_val / right_val, f"({left_expr}/{right_expr})"
            raise ValueError("Operador nao suportado")
        if isinstance(node, ast.UnaryOp):
            operand_val, operand_expr = self._eval_formula_ast(node.operand, variables)
            if isinstance(node.op, ast.UAdd):
                return operand_val, f"+{operand_expr}"
            if isinstance(node.op, ast.USub):
                return -operand_val, f"-{operand_expr}"
            raise ValueError("Operador nao suportado")
        if isinstance(node, ast.Name):
            key = node.id.upper()
            if key not in variables:
                raise ValueError(f"Variavel {key} desconhecida")
            valor = variables[key]
            if valor is None:
                raise ValueError(f"Variavel {key} sem valor")
            return float(valor), self._format_result_number(float(valor)) or str(float(valor))
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value), self._format_result_number(float(node.value)) or str(float(node.value))
            raise ValueError("Constante invalida")
        if isinstance(node, ast.Num):  # type: ignore[attr-defined]
            val = float(node.n)  # pragma: no cover
            return val, self._format_result_number(val) or str(val)
        raise ValueError("Expressao invalida")



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

        if key in {"comp", "larg", "esp"}:
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
                return value or ""
            if role == QtCore.Qt.ToolTipRole:
                tooltip = row_data.get(f"_{key}_tooltip")
                if tooltip:
                    return tooltip
                return None

        if key == "def_peca":
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
                value = row_data.get("def_peca") or ""
                if row_type == "child" and value:
                    return ROW_CHILD_INDENT + value.lstrip()
                return value

        ORLA_ML_KEYS = {"ml_orl_c1", "ml_orl_c2", "ml_orl_l1", "ml_orl_l2"}
        ORLA_COST_KEYS = {"custo_orl_c1", "custo_orl_c2", "custo_orl_l1", "custo_orl_l2"}
        ORLA_TOTAL_KEYS = {"soma_total_ml_orla", "custo_total_orla"}

        if role == QtCore.Qt.ToolTipRole and key in ORLA_ML_KEYS:
            side = key.replace("ml_orl_", "")
            dim_mm = row_data.get("comp_res") if side in ("c1", "c2") else row_data.get("larg_res")
            ml_val = row_data.get(key) or 0
            esp_orla = row_data.get(f"orl_{side}")

            def _clean_ref(ref_val: Any) -> Optional[str]:
                if ref_val in (None, ""):
                    return None
                try:
                    cleaned = str(ref_val).strip()
                except Exception:
                    cleaned = str(ref_val)
                return cleaned or None

            raw_orl_04 = _clean_ref(row_data.get("orl_0_4"))
            raw_orl_10 = _clean_ref(row_data.get("orl_1_0"))
            matched_ref = _clean_ref(row_data.get(f"orl_ref_{side}"))

            ensured_pliq, ensured_desp, ensured_ref = self._ensure_orla_info(row_data, side)
            if ensured_ref:
                matched_ref = ensured_ref

            chosen_ref = matched_ref
            source_labels: List[str] = []
            if matched_ref and matched_ref == raw_orl_04:
                source_labels.append("ORL 0.4")
            if matched_ref and matched_ref == raw_orl_10:
                source_labels.append("ORL 1.0")
            if not source_labels:
                if matched_ref:
                    source_labels.append("Materia Prima (ref_le)")
                elif raw_orl_04 or raw_orl_10:
                    if esp_orla not in (None, 0):
                        try:
                            esp_float = float(esp_orla)
                        except Exception:
                            esp_float = None
                        if esp_float is not None:
                            if abs(esp_float - 0.4) < 0.01 and raw_orl_04:
                                chosen_ref = raw_orl_04
                                source_labels.append("ORL 0.4")
                            elif abs(esp_float - 1.0) < 0.01 and raw_orl_10:
                                chosen_ref = raw_orl_10
                                source_labels.append("ORL 1.0")
                            elif raw_orl_10:
                                chosen_ref = raw_orl_10
                                source_labels.append("ORL 1.0")
                            elif raw_orl_04:
                                chosen_ref = raw_orl_04
                                source_labels.append("ORL 0.4")

            pliq_orla = ensured_pliq if ensured_pliq not in (None, "") else row_data.get(f"orl_pliq_{side}")
            if pliq_orla in (None, ""):
                pliq_orla = row_data.get("pliq")

            desp_orla = ensured_desp if ensured_desp not in (None, "") else row_data.get(f"orl_desp_{side}")
            if desp_orla in (None, ""):
                desp_orla = row_data.get("desp")

            try:
                qt_total = float(row_data.get("qt_total") or 1)
            except Exception:
                qt_total = 1.0

            try:
                ml_per_unit_base = float(dim_mm) / 1000.0 if dim_mm not in (None, "") else 0.0
            except Exception:
                ml_per_unit_base = 0.0

            try:
                ml_total_float = float(ml_val)
            except Exception:
                ml_total_float = 0.0

            try:
                per_unit_with_waste = ml_total_float / qt_total if qt_total else ml_total_float
            except Exception:
                per_unit_with_waste = ml_total_float

            try:
                desp_pct = float(desp_orla or 0.0)
                if desp_pct <= 1:
                    desp_pct *= 100.0
                desp_from_default = False
            except Exception:
                desp_pct = 8.0
                desp_from_default = True

            if abs(desp_pct - int(desp_pct)) < 1e-6:
                desp_display = f"{int(desp_pct)}%"
            else:
                desp_display = f"{desp_pct:.2f}%"
            if desp_from_default or desp_orla in (None, "", 0):
                desp_display = f"{desp_display} (default)"

            ml_base_display = self._format_result_number(ml_per_unit_base) or "0"
            per_unit_display = self._format_result_number(per_unit_with_waste) or "0"
            ml_total_display = self._format_result_number(ml_total_float) or "0"
            qt_total_display = self._format_result_number(qt_total) or str(qt_total)

            esp_display = None
            if esp_orla not in (None, "", 0):
                try:
                    esp_val = float(esp_orla)
                    esp_display = int(esp_val) if abs(esp_val - int(esp_val)) < 1e-6 else round(esp_val, 2)
                except Exception:
                    esp_display = esp_orla

            lines: List[str] = []
            base_dim = dim_mm if dim_mm not in (None, "") else "0"
            lines.append(f"ML {side.upper()} - passos do calculo")
            lines.append(f"1) Dimensao base: {base_dim} mm -> {ml_base_display} m")
            lines.append(f"2) Desperdicio aplicado: {desp_display}")
            lines.append(f"3) ML por unidade (com desperdicio): {per_unit_display} m")
            lines.append(f"4) Qt_total: {qt_total_display} -> ML total: {ml_total_display} m")

            if chosen_ref:
                label = " | ".join(source_labels) if source_labels else "referencia"
                ref_line = f"5) Referencia orla ({label}): {chosen_ref}"
                if esp_display is not None:
                    ref_line += f" | Espessura lado: {esp_display}"
                lines.append(ref_line)
            else:
                missing_line = "5) Referencia orla: nao encontrada nas colunas ORL 0.4/1.0"
                if esp_display is not None:
                    missing_line += f" | Espessura lado: {esp_display}"
                lines.append(missing_line)

            if pliq_orla not in (None, "", 0):
                try:
                    pliq_val = float(pliq_orla)
                    lines.append(f"6) PliQ materia-prima: {pliq_val:.2f} €/m2")
                except Exception:
                    lines.append(f"6) PliQ materia-prima: {pliq_orla} €/m2")
            else:
                lines.append("6) PliQ materia-prima: sem valor disponivel")

            if chosen_ref:
                fonte_label = " | ".join(source_labels) if source_labels else "Materia Prima"
                lines.append(f"7) Fonte PliQ/Desperdicio: {fonte_label}")

            return "\n".join(lines)



        if role == QtCore.Qt.ToolTipRole and key in ORLA_COST_KEYS:
            side = key.replace("custo_orl_", "")
            ml_key = f"ml_orl_{side}"
            ml_val = row_data.get(ml_key) or 0
            custo_val = row_data.get(key) or 0
            esp_orla = row_data.get(f"orl_{side}")

            def _clean_ref(ref_val: Any) -> Optional[str]:
                if ref_val in (None, ""):
                    return None
                try:
                    cleaned = str(ref_val).strip()
                except Exception:
                    cleaned = str(ref_val)
                return cleaned or None

            raw_orl_04 = _clean_ref(row_data.get("orl_0_4"))
            raw_orl_10 = _clean_ref(row_data.get("orl_1_0"))
            matched_ref = _clean_ref(row_data.get(f"orl_ref_{side}"))

            ensured_pliq, ensured_desp, ensured_ref = self._ensure_orla_info(row_data, side)
            if ensured_ref:
                matched_ref = ensured_ref

            chosen_ref = matched_ref
            source_labels: List[str] = []
            if matched_ref and matched_ref == raw_orl_04:
                source_labels.append("ORL 0.4")
            if matched_ref and matched_ref == raw_orl_10:
                source_labels.append("ORL 1.0")
            if not source_labels:
                if matched_ref:
                    source_labels.append("Materia Prima (ref_le)")
                elif raw_orl_04 or raw_orl_10:
                    if esp_orla not in (None, 0):
                        try:
                            esp_float = float(esp_orla)
                        except Exception:
                            esp_float = None
                        if esp_float is not None:
                            if abs(esp_float - 0.4) < 0.01 and raw_orl_04:
                                chosen_ref = raw_orl_04
                                source_labels.append("ORL 0.4")
                            elif abs(esp_float - 1.0) < 0.01 and raw_orl_10:
                                chosen_ref = raw_orl_10
                                source_labels.append("ORL 1.0")
                            elif raw_orl_10:
                                chosen_ref = raw_orl_10
                                source_labels.append("ORL 1.0")
                            elif raw_orl_04:
                                chosen_ref = raw_orl_04
                                source_labels.append("ORL 0.4")

            pliq_orla = ensured_pliq if ensured_pliq not in (None, "") else row_data.get(f"orl_pliq_{side}")
            if pliq_orla in (None, ""):
                pliq_orla = row_data.get("pliq")

            desp_orla = ensured_desp if ensured_desp not in (None, "") else row_data.get(f"orl_desp_{side}")
            if desp_orla in (None, ""):
                desp_orla = row_data.get("desp")

            try:
                qt_total = float(row_data.get("qt_total") or 1)
            except Exception:
                qt_total = 1.0

            dim_mm = row_data.get("comp_res") if side in ("c1", "c2") else row_data.get("larg_res")
            try:
                ml_per_unit_base = float(dim_mm) / 1000.0 if dim_mm not in (None, "") else 0.0
            except Exception:
                ml_per_unit_base = 0.0

            try:
                ml_total_float = float(ml_val)
            except Exception:
                ml_total_float = 0.0

            try:
                per_unit_with_waste = ml_total_float / qt_total if qt_total else ml_total_float
            except Exception:
                per_unit_with_waste = ml_total_float

            try:
                desp_pct = float(desp_orla or 0.0)
                if desp_pct <= 1:
                    desp_pct *= 100.0
                desp_from_default = False
            except Exception:
                desp_pct = 8.0
                desp_from_default = True

            if abs(desp_pct - int(desp_pct)) < 1e-6:
                desp_display = f"{int(desp_pct)}%"
            else:
                desp_display = f"{desp_pct:.2f}%"
            if desp_from_default or desp_orla in (None, "", 0):
                desp_display = f"{desp_display} (default)"

            try:
                custo_total_float = float(custo_val)
            except Exception:
                custo_total_float = 0.0

            try:
                pliq_val = float(pliq_orla or 0.0)
            except Exception:
                pliq_val = 0.0

            try:
                _, fator = svc_custeio._get_orla_width_factor(row_data.get("esp_res"))
                fator_float = float(fator)
            except Exception:
                fator_float = 0.0

            euro_ml_val = (pliq_val / fator_float) if fator_float else 0.0

            ml_base_display = self._format_result_number(ml_per_unit_base) or "0"
            per_unit_display = self._format_result_number(per_unit_with_waste) or "0"
            ml_total_display = self._format_result_number(ml_total_float) or "0"
            qt_total_display = self._format_result_number(qt_total) or str(qt_total)
            custo_total_display = f"{custo_total_float:.2f} €"

            esp_display = None
            if esp_orla not in (None, "", 0):
                try:
                    esp_val = float(esp_orla)
                    esp_display = int(esp_val) if abs(esp_val - int(esp_val)) < 1e-6 else round(esp_val, 2)
                except Exception:
                    esp_display = esp_orla

            lines: List[str] = []
            base_dim = dim_mm if dim_mm not in (None, "") else "0"
            lines.append(f"Custo ORL {side.upper()} - passos do calculo")
            lines.append(f"1) Dimensao base: {base_dim} mm -> {ml_base_display} m")
            lines.append(f"2) Desperdicio aplicado: {desp_display}")
            lines.append(f"3) ML/unidade (com desperdicio): {per_unit_display} m | Qt_total: {qt_total_display} -> ML total: {ml_total_display} m")

            if chosen_ref:
                label = " | ".join(source_labels) if source_labels else "referencia"
                ref_line = f"4) Referencia orla ({label}): {chosen_ref}"
                if esp_display is not None:
                    ref_line += f" | Espessura lado: {esp_display}"
                lines.append(ref_line)
            else:
                missing_line = "4) Referencia orla: nao encontrada nas colunas ORL 0.4/1.0"
                if esp_display is not None:
                    missing_line += f" | Espessura lado: {esp_display}"
                lines.append(missing_line)

            if pliq_val and fator_float:
                fator_display = int(fator_float) if abs(fator_float - int(fator_float)) < 1e-6 else round(fator_float, 2)
                lines.append(f"5) Conversao preco: {pliq_val:.2f} €/m2 @ fator {fator_display} = {euro_ml_val:.2f} €/ml")
            elif pliq_val:
                lines.append(f"5) Conversao preco: {pliq_val:.2f} €/m2 (fator indisponivel)")
            else:
                lines.append("5) Conversao preco: sem dados de PliQ")

            if euro_ml_val:
                per_unit_cost = (per_unit_with_waste * euro_ml_val) if per_unit_with_waste else 0.0
                lines.append(f"6) Custo total: {ml_total_display} m x {euro_ml_val:.2f} €/ml = {custo_total_display}")
                lines.append(f"   Custo por unidade: {per_unit_display} m x {euro_ml_val:.2f} €/ml = {per_unit_cost:.2f} €")
            else:
                lines.append(f"6) Custo total: {custo_total_display}")

            if chosen_ref:
                fonte_label = " | ".join(source_labels) if source_labels else "Materia Prima"
                lines.append(f"7) Fonte PliQ/Desperdicio: {fonte_label}")

            return "\n".join(lines)



        if role == QtCore.Qt.ToolTipRole and key in ORLA_TOTAL_KEYS:
            parts: List[str] = []
            for side in ("c1", "c2", "l1", "l2"):
                ml_side = row_data.get(f"ml_orl_{side}") or 0
                custo_side = row_data.get(f"custo_orl_{side}") or 0
                try:
                    ml_fmt = self._format_result_number(float(ml_side)) or "0"
                except Exception:
                    ml_fmt = str(ml_side)
                try:
                    custo_fmt = f"{float(custo_side):.2f} €"
                except Exception:
                    custo_fmt = f"{custo_side} €"
                parts.append(f"{side.upper()}: ML={ml_fmt} m | Custo={custo_fmt}")
            total_ml = row_data.get("soma_total_ml_orla") or 0
            total_custo = row_data.get("custo_total_orla") or 0
            try:
                total_ml_fmt = self._format_result_number(float(total_ml)) or "0"
            except Exception:
                total_ml_fmt = str(total_ml)
            try:
                total_custo_fmt = f"{float(total_custo):.2f} €"
            except Exception:
                total_custo_fmt = f"{total_custo} €"
            parts.append(f"Totais: ML={total_ml_fmt} m | Custo={total_custo_fmt}")
            return "\n".join(parts)

        if role == QtCore.Qt.ToolTipRole and key == "spp_ml_und":
            if not self._is_spp_row(row_data):
                return None
            und_value = (row_data.get("und") or "-").strip() or "-"
            comp_res = row_data.get("comp_res")
            try:
                comp_float = float(comp_res) if comp_res not in (None, "") else None
            except (TypeError, ValueError):
                comp_float = None
            spp_val = row_data.get("spp_ml_und")
            try:
                spp_float = float(spp_val) if spp_val not in (None, "") else None
            except (TypeError, ValueError):
                spp_float = None
            lines = [f"SPP ML por unidade (und={und_value})"]
            reason_bits = []
            if (row_data.get("und") or "").strip().upper() == "ML":
                reason_bits.append("und=ML")
            def_peca_raw = (row_data.get("def_peca") or "").upper()
            if "{SPP}" in def_peca_raw:
                reason_bits.append("marcador {SPP}")
            if reason_bits:
                lines.append("Deteccao SPP: " + " + ".join(reason_bits))
            if comp_float is not None:
                comp_m = comp_float / 1000.0
                lines.append(f"COMP_res: {comp_float:.2f} mm -> {comp_m:.2f} m")
            else:
                lines.append("COMP_res: valor indisponivel")
            if spp_float is not None:
                stored = self._format_result_number(spp_float) or f"{spp_float:.2f}"
                lines.append(f"Valor apresentado: {stored} m")
            else:
                lines.append("Valor apresentado: -")
            return "\n".join(lines)

        if role == QtCore.Qt.ToolTipRole and key in {"area_m2_und", "perimetro_und"}:
            comp_res = row_data.get("comp_res")
            larg_res = row_data.get("larg_res")

            try:
                comp_float = float(comp_res) if comp_res not in (None, "") else None
            except (TypeError, ValueError):
                comp_float = None
            try:
                larg_float = float(larg_res) if larg_res not in (None, "") else None
            except (TypeError, ValueError):
                larg_float = None

            lines: List[str] = []
            if comp_float is not None and larg_float is not None:
                comp_m = comp_float / 1000.0
                larg_m = larg_float / 1000.0
                if key == "area_m2_und":
                    try:
                        area_val = float(row_data.get("area_m2_und") or (comp_m * larg_m))
                    except (TypeError, ValueError):
                        area_val = comp_m * larg_m
                    lines.append("Area por unidade")
                    lines.append(f"Comprimento: {comp_float} mm -> {comp_m:.3f} m")
                    lines.append(f"Largura: {larg_float} mm -> {larg_m:.3f} m")
                    lines.append(f"Calculo: {comp_m:.3f} m * {larg_m:.3f} m = {area_val:.4f} m2")
                else:
                    try:
                        per_val = float(row_data.get("perimetro_und") or (2 * (comp_m + larg_m)))
                    except (TypeError, ValueError):
                        per_val = 2 * (comp_m + larg_m)
                    lines.append("Perimetro por unidade")
                    lines.append(f"Comprimento: {comp_float} mm -> {comp_m:.3f} m")
                    lines.append(f"Largura: {larg_float} mm -> {larg_m:.3f} m")
                    lines.append(f"Calculo: 2 * ({comp_m:.3f} m + {larg_m:.3f} m) = {per_val:.4f} m")
            else:
                if key == "area_m2_und":
                    lines.append("Area por unidade")
                    lines.append("Dimensoes incompletas para calcular a area.")
                else:
                    lines.append("Perimetro por unidade")
                    lines.append("Dimensoes incompletas para calcular o perimetro.")
            return "\n".join(lines)

        if key == "id":
            if role == QtCore.Qt.DisplayRole:
                if row_type == "division":
                    page_ref = getattr(self, "_page", None)
                    collapsed_groups = getattr(page_ref, "_collapsed_groups", set()) if page_ref is not None else set()
                    is_collapsed = row_data.get("_group_uid") in collapsed_groups
                    symbol = "+" if is_collapsed else "-"
                    return f" {symbol} "
                raw_id = row_data.get("id")
                return "" if raw_id in (None, "") else str(raw_id)
            if role == QtCore.Qt.DecorationRole:
                if row_type == "division":
                    page_ref = getattr(self, "_page", None)
                    if page_ref is not None:
                        return page_ref._icon("division")
                return None
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignCenter
            if role == QtCore.Qt.ToolTipRole:
                if row_type == "division":
                    return "Clique para expandir/contrair este grupo."
                raw_id = row_data.get("id")
                if raw_id not in (None, ""):
                    return f"ID: {raw_id}"
                return None

        if key == "icon_hint":
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, QtCore.Qt.DecorationRole):
                return ""
            return None

        if role == QtCore.Qt.BackgroundRole:
            # Apply parent/child background only to specific visible columns
            highlight_keys = {"def_peca", "descricao", "qt_mod", "qt_und", "comp", "larg", "esp"}
            if key in highlight_keys:
                if row_type == "parent":
                    return ROW_PARENT_COLOR
                if row_type == "child":
                    return ROW_CHILD_COLOR

            if row_type == "division":
                return QtGui.QColor(160, 160, 160)  # Cinza mais escuro

            if row_type == "separator":
                return QtGui.QColor(235, 235, 235)

        if key == "qt_und" and role == QtCore.Qt.ToolTipRole:
            tooltips: List[str] = []
            manual_tip = row_data.get("_qt_manual_tooltip")
            if manual_tip:
                tooltips.append(str(manual_tip))
            rule_tip = row_data.get("_qt_rule_tooltip")
            if rule_tip:
                tooltips.append(str(rule_tip))
            if tooltips:
                return "\n".join(tooltips)
            return None

        if role == QtCore.Qt.FontRole:
            # Parent def_peca should be bold
            if key == "def_peca" and row_type == "parent":
                return self._bold_font
            # Child def_peca should be italic + underline to differentiate
            if key == "def_peca" and row_type == "child":
                return self._child_font
            # Manual override styling for qt_und (keeps previous behaviour)
            if key == "qt_und" and row_data.get("_qt_manual_override"):
                return self._manual_override_font
            if row_type == "division":
                return self._division_font
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
                return self._format_qt_mod_display(index.row())
            if role == QtCore.Qt.ToolTipRole:
                row_obj = self.rows[index.row()]
                formula = self._format_qt_mod_display(index.row())
                if not formula:
                    return None
                # Use computed numeric factors stored during recalc for accuracy
                try:
                    divisor_val = float(row_obj.get("_qt_divisor") or 1.0)
                except Exception:
                    divisor_val = 1.0
                try:
                    parent_val = float(row_obj.get("_qt_parent_factor") or 1.0)
                except Exception:
                    parent_val = 1.0
                try:
                    child_val = float(row_obj.get("_qt_child_factor") or 1.0)
                except Exception:
                    child_val = 1.0
                # The displayed formula may omit factors that are empty; compute product accordingly
                result = divisor_val * parent_val * child_val
                return f"{formula} = {result:.2f}"

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

            # Disallow editing qt_und for child rows: child quantities are
            # computed automatically from the parent and must not be changed
            # by the user. Division rows also remain non-editable for qt_und.
            if key == "qt_und":
                if self._is_division_row(row_data):
                    return flags
                if (row_data.get("_row_type") or "").lower() == "child":
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
            self._mark_dirty()

            return True



        if role != QtCore.Qt.EditRole or not spec.get("editable", False):

            return False



        manual_lock = spec["key"] in MANUAL_LOCK_KEYS



        requires_recalc = False

        if key in {"comp", "larg", "esp"}:
            sanitized = self._sanitize_formula_input(value)
            if sanitized is None and value not in (None, ""):
                return False
            self.rows[row][key] = sanitized or ""
            self._mark_dirty()
            requires_recalc = True
        elif spec["type"] == "numeric":

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
                self._mark_dirty()

            elif key == "qt_und":

                if not self._process_qt_und_edit(row, value):

                    return False

                requires_recalc = True

            else:

                coerced = self._coerce_numeric(value)

                if value not in (None, "", False) and coerced is None:

                    return False

                self.rows[row][key] = coerced

                if key == "qt_mod":

                    requires_recalc = True

                self._mark_dirty()

        else:

            self.rows[row][key] = value
            self._mark_dirty()

        if key in {"orl_0_4", "orl_1_0", "orl_c1", "orl_c2", "orl_l1", "orl_l2"}:
            self._orla_info_cache.clear()
            for lado in ("c1", "c2", "l1", "l2"):
                self._ensure_orla_info(self.rows[row], lado)
            requires_recalc = True

        if requires_recalc:

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
        self._orla_info_cache.clear()

        self.endResetModel()
        self._mark_dirty(False)



    def load_rows(self, rows: Sequence[Mapping[str, Any]]) -> None:

        self.beginResetModel()

        self.rows = [self._coerce_row_impl(row) for row in rows]
        self._orla_info_cache.clear()

        self.endResetModel()
        self._mark_dirty(False)



    def append_rows(self, rows: Sequence[Mapping[str, Any]]) -> None:

        if not rows:

            return

        start = len(self.rows)

        end = start + len(rows) - 1

        self.beginInsertRows(QtCore.QModelIndex(), start, end)

        for row in rows:

            self.rows.append(self._coerce_row_impl(row))

        self.endInsertRows()
        self._mark_dirty()


    def insert_rows(self, position: int, rows: Sequence[Mapping[str, Any]]) -> None:

        if not rows:

            return

        position = max(0, min(position, len(self.rows)))

        self.beginInsertRows(QtCore.QModelIndex(), position, position + len(rows) - 1)

        for offset, row in enumerate(rows):

            self.rows.insert(position + offset, self._coerce_row_impl(row))

        self.endInsertRows()
        self._mark_dirty()


    def remove_rows(self, indices: Sequence[int]) -> None:

        if not indices:

            return

        modified = False
        for row in sorted(set(indices), reverse=True):

            if 0 <= row < len(self.rows):

                self.beginRemoveRows(QtCore.QModelIndex(), row, row)

                del self.rows[row]

                self.endRemoveRows()
                modified = True
        if modified:
            self._mark_dirty()

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

                if key in {"comp", "larg", "esp"}:
                    sanitized = self._sanitize_formula_input(value)
                    if sanitized is None and value not in (None, ""):
                        sanitized = str(value).replace(",", ".").upper().strip()
                    coerced[key] = sanitized or ""
                else:
                    coerced[key] = value

        if isinstance(row, Mapping):
            for extra_key in ("_row_type", "_parent_uid", "_group_uid", "_child_source", "_normalized_child", "_qt_manual_override", "_qt_manual_value", "_qt_manual_tooltip", "_qt_formula_value", "_regra_nome"):
                if extra_key in row:
                    coerced[extra_key] = row[extra_key]

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

        def _coerce_dimension(raw: Any) -> Optional[float]:
            if page_ref is not None and hasattr(page_ref, "_coerce_dimension_value"):
                try:
                    coerced = page_ref._coerce_dimension_value(raw)
                except Exception:
                    coerced = None
                if coerced is not None:
                    return coerced
            if raw in (None, "", False):
                return None
            if isinstance(raw, (int, float)):
                return float(raw)
            try:
                return float(str(raw).replace(",", "."))
            except (TypeError, ValueError):
                return None

        if session is not None and context is not None:

            try:

                rules = svc_custeio.load_qt_rules(session, context)

            except Exception:

                rules = svc_custeio.DEFAULT_QT_RULES

        else:

            rules = svc_custeio.DEFAULT_QT_RULES

        global_dimensions: Dict[str, Optional[float]] = {key: None for key in DIMENSION_KEY_ORDER}
        if page_ref is not None and hasattr(page_ref, "dimension_values"):
            try:
                dimension_values = page_ref.dimension_values()
            except Exception:
                dimension_values = {}
            for key in DIMENSION_KEY_ORDER:
                global_dimensions[key] = _coerce_dimension(dimension_values.get(key))
        global_context_base: Dict[str, Optional[float]] = {key.upper(): value for key, value in global_dimensions.items()}


        divisor = 1.0

        current_group_uid = str(uuid.uuid4())

        current_parent_row: Optional[Dict[str, Any]] = None

        current_parent_uid: Optional[str] = None

        current_local_dimensions: Dict[str, Optional[float]] = {"HM": None, "LM": None, "PM": None}

        def _build_eval_env(include_locals: bool = True) -> Dict[str, Optional[float]]:
            env: Dict[str, Optional[float]] = dict(global_context_base)
            if include_locals:
                for key in ("HM", "LM", "PM"):
                    env[key] = current_local_dimensions.get(key)
            else:
                for key in ("HM", "LM", "PM"):
                    env.setdefault(key, None)
            return env

        def _evaluate_dimension(
            expression: str, env: Mapping[str, Optional[float]]
        ) -> Tuple[Optional[float], Optional[str], Optional[str]]:
            value, error = self._evaluate_formula_expression(expression, env)
            substitution = self._render_formula_substitution(expression, env)
            if error is None and value is not None:
                value = round(value, 1)
            return value, error, substitution

        def _update_qt_mod_expression(row: Dict[str, Any], divisor_value: Optional[float], parent_factor_value: Optional[float]) -> None:
            row_type_local = row.get("_row_type")
            if row_type_local in ("child", "division", "parent"):
                return
            raw_qt_mod = row.get("qt_mod")
            auto_manage = False
            if raw_qt_mod in (None, ""):
                auto_manage = True
            elif isinstance(raw_qt_mod, str):
                if _AUTO_QTMOD_PATTERN.match(raw_qt_mod.strip()):
                    auto_manage = True
            elif isinstance(raw_qt_mod, (int, float)):
                auto_manage = True
            if not auto_manage:
                return
            if divisor_value is None or parent_factor_value is None:
                return
            divisor_text = self._format_factor(divisor_value)
            parent_text = self._format_factor(parent_factor_value)
            if not divisor_text or not parent_text:
                return
            new_value = f"{divisor_text} x {parent_text}"
            if row.get("qt_mod") != new_value:
                row["qt_mod"] = new_value

        def _coerce_factor_value(raw: Any) -> Optional[float]:
            if raw in (None, "", False):
                return None
            if isinstance(raw, (int, float)):
                try:
                    return float(raw)
                except (TypeError, ValueError):
                    return None
            text = str(raw).strip()
            if not text:
                return None
            text = text.replace(",", ".")
            try:
                return float(text)
            except (TypeError, ValueError):
                pass
            matches = re.findall(r"[0-9]+(?:\\.[0-9]+)?", text)
            if matches:
                try:
                    return float(matches[-1])
                except (TypeError, ValueError):
                    return None
            return None

        def _maybe_update_dimension_literal(row_dict: Dict[str, Any], key: str, value: Optional[float]) -> None:
            if value is None:
                return
            raw_expr = (row_dict.get(key) or "").strip()
            if raw_expr and not _NUMERIC_LITERAL_PATTERN.match(raw_expr):
                return
            formatted = self._format_result_number(value)
            if formatted:
                row_dict[key] = formatted

        for row in self.rows:

            row["_uid"] = row.get("_uid") or str(uuid.uuid4())

            row["_comp_error"] = None
            row["_comp_tooltip"] = None
            row["_larg_error"] = None
            row["_larg_tooltip"] = None
            row["_esp_error"] = None
            row["_esp_tooltip"] = None

            row["comp_res"] = None
            row["larg_res"] = None
            row["esp_res"] = None

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

            is_division = self._is_division_row(row)

            if is_division:

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

                row["qt_und"] = None

                row["qt_total"] = divisor

                if getattr(self, "_page", None):

                    row["icon_hint"] = self._page._icon("division")

                current_parent_row = None

                current_parent_uid = None

                row["_regra_nome"] = None

            elif "+" in def_peca:

                row["_row_type"] = "parent"
                row["_is_parent"] = True

                current_group_uid = row.get("_group_uid") or str(uuid.uuid4())

                row["_group_uid"] = current_group_uid

                current_parent_row = row

                current_parent_uid = row["_uid"]

                row["_regra_nome"] = None

            else:

                regra_nome = svc_custeio.identificar_regra(def_peca, rules)

                if regra_nome and current_parent_row is not None:

                    row["_row_type"] = "child"
                    row["_is_associated"] = True

                    row["_group_uid"] = row.get("_group_uid") or current_group_uid

                    row["_parent_uid"] = current_parent_uid

                    row["_regra_nome"] = regra_nome

                else:

                    row["_row_type"] = "normal"

                    row["_group_uid"] = row.get("_group_uid") or current_group_uid

                    current_parent_row = None

                    current_parent_uid = None

                    row["_regra_nome"] = None

            expr_comp = self._prepare_formula_expression(row.get("comp"))
            row["comp"] = expr_comp
            # Normalized token for this row (used to detect VARAO even when not a 'child')
            raw_row_token = def_peca or row.get("descricao") or row.get("tipo") or ""
            normalized_row_token = self._normalize_def_peca(raw_row_token)
            if isinstance(row, dict):
                row["_normalized_def"] = normalized_row_token
            expr_larg = self._prepare_formula_expression(row.get("larg"))
            row["larg"] = expr_larg
            expr_esp = self._prepare_formula_expression(row.get("esp"))
            row["esp"] = expr_esp

            if row.get("_row_type") == "division":
                division_env: Dict[str, Optional[float]] = dict(global_context_base)
                for key in ("HM", "LM", "PM"):
                    division_env.setdefault(key, None)
                comp_val, comp_error, comp_sub = _evaluate_dimension(expr_comp, division_env)
                row["comp_res"] = comp_val
                row["_comp_error"] = comp_error
                comp_expr_for_tooltip = row.get("comp") or expr_comp
                comp_sub_for_tooltip = comp_sub
                if comp_expr_for_tooltip != expr_comp:
                    comp_sub_for_tooltip = self._render_formula_substitution(comp_expr_for_tooltip, division_env)
                row["_comp_tooltip"] = self._build_formula_tooltip(comp_expr_for_tooltip, comp_val, comp_error, substitutions=comp_sub_for_tooltip)

                larg_val, larg_error, larg_sub = _evaluate_dimension(expr_larg, division_env)
                row["larg_res"] = larg_val
                row["_larg_error"] = larg_error
                larg_expr_for_tooltip = row.get("larg") or expr_larg
                larg_sub_for_tooltip = larg_sub
                if larg_expr_for_tooltip != expr_larg:
                    larg_sub_for_tooltip = self._render_formula_substitution(larg_expr_for_tooltip, division_env)
                row["_larg_tooltip"] = self._build_formula_tooltip(larg_expr_for_tooltip, larg_val, larg_error, substitutions=larg_sub_for_tooltip)

                esp_val, esp_error, esp_sub = _evaluate_dimension(expr_esp, division_env)
                row["esp_res"] = esp_val
                row["_esp_error"] = esp_error
                esp_expr_for_tooltip = row.get("esp") or expr_esp
                esp_sub_for_tooltip = esp_sub
                if esp_expr_for_tooltip != expr_esp:
                    esp_sub_for_tooltip = self._render_formula_substitution(esp_expr_for_tooltip, division_env)
                row["_esp_tooltip"] = self._build_formula_tooltip(esp_expr_for_tooltip, esp_val, esp_error, substitutions=esp_sub_for_tooltip)

                current_local_dimensions["HM"] = comp_val
                current_local_dimensions["LM"] = larg_val
                current_local_dimensions["PM"] = esp_val
                row["_qt_divisor"] = divisor
                row["_qt_parent_factor"] = None
                row["_qt_child_factor"] = None
                row["qt_und"] = None
                row["qt_total"] = divisor
                row["spp_ml_und"] = None
                current_parent_row = row
                current_parent_uid = row["_uid"]
                continue

            merged_context = _build_eval_env()
            comp_val, comp_error, comp_sub = _evaluate_dimension(expr_comp, merged_context)
            row["comp_res"] = comp_val
            row["_comp_error"] = comp_error
            _maybe_update_dimension_literal(row, "comp", comp_val)
            comp_expr_for_tooltip = row.get("comp") or expr_comp
            comp_sub_for_tooltip = comp_sub
            if comp_expr_for_tooltip != expr_comp:
                comp_sub_for_tooltip = self._render_formula_substitution(comp_expr_for_tooltip, merged_context)
            row["_comp_tooltip"] = self._build_formula_tooltip(comp_expr_for_tooltip, comp_val, comp_error, substitutions=comp_sub_for_tooltip)

            larg_val, larg_error, larg_sub = _evaluate_dimension(expr_larg, merged_context)
            row["larg_res"] = larg_val
            row["_larg_error"] = larg_error
            _maybe_update_dimension_literal(row, "larg", larg_val)
            larg_expr_for_tooltip = row.get("larg") or expr_larg
            larg_sub_for_tooltip = larg_sub
            if larg_expr_for_tooltip != expr_larg:
                larg_sub_for_tooltip = self._render_formula_substitution(larg_expr_for_tooltip, merged_context)
            row["_larg_tooltip"] = self._build_formula_tooltip(larg_expr_for_tooltip, larg_val, larg_error, substitutions=larg_sub_for_tooltip)

            esp_val, esp_error, esp_sub = _evaluate_dimension(expr_esp, merged_context)
            row["esp_res"] = esp_val
            row["_esp_error"] = esp_error
            _maybe_update_dimension_literal(row, "esp", esp_val)
            esp_expr_for_tooltip = row.get("esp") or expr_esp
            esp_sub_for_tooltip = esp_sub
            if esp_expr_for_tooltip != expr_esp:
                esp_sub_for_tooltip = self._render_formula_substitution(esp_expr_for_tooltip, merged_context)
            row["_esp_tooltip"] = self._build_formula_tooltip(esp_expr_for_tooltip, esp_val, esp_error, substitutions=esp_sub_for_tooltip)

            # Herança de comprimento para VARAO e componentes ML mesmo quando não são marcados como 'child'
            # Isto garante que linhas "VARAO" exibam o comprimento do componente PAI (ex.: 1000)
            try:
                is_ml = (row.get("und") or "").strip().upper() == "ML"
            except Exception:
                is_ml = False
            if current_parent_row is not None and row.get("_row_type") != "division" and row.get("_row_type") != "parent":
                if is_ml or (normalized_row_token and "VARAO" in normalized_row_token):
                    inherited_comp = current_parent_row.get("comp_res")
                    if inherited_comp is None:
                        inherited_comp = _coerce_dimension(current_parent_row.get("comp"))
                    if inherited_comp is not None:
                        row["comp_res"] = inherited_comp
                        row["_comp_error"] = None
                        _maybe_update_dimension_literal(row, "comp", inherited_comp)
                        formatted = self._format_result_number(inherited_comp)
                        expr_for_tooltip = (row.get("comp") or formatted or "").strip()
                        row["_comp_tooltip"] = self._build_formula_tooltip(expr_for_tooltip, inherited_comp, None, substitutions=formatted or None)
            row["_qt_divisor"] = divisor

            row_type = row.get("_row_type")

            if row_type != "division":
                row.pop("icon_hint", None)

            if row_type == "child" and current_parent_row is not None:
                try:
                    parent_factor = float(current_parent_row.get("qt_und") or 1.0)
                except Exception:
                    parent_factor = 1.0
            elif row_type == "parent":
                try:
                    parent_factor = float(row.get("qt_und") or 1.0)
                except Exception:
                    parent_factor = 1.0
                if row.get("qt_und") in (None, ""):
                    row["qt_und"] = parent_factor
            else:
                tipo_val = (row.get("tipo") or "").strip().casefold()
                if tipo_val == "pai":
                    try:
                        parent_factor = float(row.get("qt_und") or 1.0)
                    except Exception:
                        parent_factor = 1.0
                    if row.get("qt_und") in (None, ""):
                        row["qt_und"] = parent_factor
                else:
                    raw_qt_mod = row.get("qt_mod")
                    parent_factor = _coerce_factor_value(raw_qt_mod)
                    qt_und_val = self._coerce_numeric(row.get("qt_und"))
                    if qt_und_val is not None and qt_und_val > 0:
                        parent_factor = qt_und_val
                    elif parent_factor is None or parent_factor <= 0:
                        parent_factor = 1.0
                    if row_type not in ("child", "separator") and row.get("qt_mod") in (None, ""):
                        row["qt_mod"] = parent_factor

            if row_type != "child":
                _update_qt_mod_expression(row, divisor, parent_factor)

            if row_type == "child" and current_parent_row is not None:

                regra_base = row.get("_regra_nome") or row.get("_child_source")

                regra_nome = svc_custeio.identificar_regra(regra_base or "", rules)

                rule_data = rules.get(regra_nome) if regra_nome else None

                existing_child = self._coerce_numeric(row.get("qt_und"))

                try:
                    child_factor = svc_custeio.calcular_qt_filhos(regra_nome, current_parent_row, row, divisor, parent_factor, rules)
                except Exception:
                    try:
                        child_factor = float(existing_child if existing_child is not None else 1.0)
                    except Exception:
                        child_factor = 1.0

                try:
                    parent_qt = float(current_parent_row.get("qt_und") or 1.0)
                except Exception:
                    parent_qt = 1.0

                raw_child_token = row.get("_child_source") or row.get("descricao") or row.get("tipo")
                normalized_child = self._normalize_def_peca(raw_child_token)
                row["_normalized_child"] = normalized_child

                if "VARAO" in normalized_child:
                    # VARAO (bar) children are measured in ML: default qt_und is 1 and
                    # they inherit the parent's comp (length). For support varao, use qt_und=2
                    if "SUPORTE" in normalized_child:
                        # support for varao: typically two supports per parent
                        try:
                            child_factor = 2
                        except Exception:
                            child_factor = 2
                        # for supports we do not inherit comp; leave comp empty
                        row["comp_res"] = None
                        if isinstance(row, dict):
                            row["comp"] = ""
                    else:
                        # regular VARAO: one rod per parent module; inherit length
                        try:
                            child_factor = 1
                        except Exception:
                            child_factor = 1
                        # inherit comp_res from parent so comp shows parent's length
                        inherited_comp = current_parent_row.get("comp_res")
                        if inherited_comp is None:
                            inherited_comp = _coerce_dimension(current_parent_row.get("comp"))
                        if inherited_comp is not None:
                            row["comp_res"] = inherited_comp
                            row["_comp_error"] = None
                            _maybe_update_dimension_literal(row, "comp", inherited_comp)
                            formatted = self._format_result_number(inherited_comp)
                            expr_for_tooltip = (row.get("comp") or formatted or "").strip()
                            row["_comp_tooltip"] = self._build_formula_tooltip(expr_for_tooltip, inherited_comp, None, substitutions=formatted or None)

                row["_regra_nome"] = regra_nome

                row["_qt_rule_tooltip"] = rule_data.get("tooltip") if rule_data else None

                formula_child = child_factor
                row["_qt_formula_value"] = formula_child

                manual_allowed = self._supports_qt_und_override(row)
                manual_value = self._coerce_numeric(row.get("_qt_manual_value"))
                stored_child = self._coerce_numeric(row.get("qt_und"))
                manual_override_flag = bool(row.get("_qt_manual_override"))

                if manual_allowed:
                    if manual_value is not None:
                        effective_child = manual_value
                        manual_override_flag = True
                    elif manual_override_flag and stored_child is not None and not _float_almost_equal(stored_child, formula_child):
                        manual_value = stored_child
                        effective_child = stored_child
                    elif stored_child is not None and not _float_almost_equal(stored_child, formula_child):
                        manual_override_flag = True
                        manual_value = stored_child
                        effective_child = stored_child
                    else:
                        manual_override_flag = False
                        manual_value = None
                        effective_child = formula_child
                else:
                    manual_override_flag = False
                    manual_value = None
                    effective_child = formula_child

                row["qt_und"] = effective_child
                row["_qt_manual_override"] = manual_override_flag
                if manual_override_flag and manual_value is not None:
                    row["_qt_manual_value"] = manual_value
                    formatted_formula = self._format_result_number(formula_child) or str(formula_child)
                    row["_qt_manual_tooltip"] = f"Valor manual (formula: {formatted_formula})"
                else:
                    row["_qt_manual_value"] = None
                    row["_qt_manual_tooltip"] = None

                # Herança de comprimento para VARAO e componentes ML (skip supports)
                is_ml = ((row.get("und") or "").strip().upper() == "ML")
                is_varao = ("VARAO" in (normalized_child or ""))
                is_support_varao = ("SUPORTE" in (normalized_child or ""))
                if (is_ml or is_varao) and current_parent_row is not None and not is_support_varao:
                    inherited_comp = current_parent_row.get("comp_res")
                    if inherited_comp is None:
                        inherited_comp = _coerce_dimension(current_parent_row.get("comp"))
                    row["comp_res"] = inherited_comp
                    row["_comp_error"] = None
                    _maybe_update_dimension_literal(row, "comp", inherited_comp)
                    formatted = self._format_result_number(inherited_comp)
                    expr_for_tooltip = (row.get("comp") or formatted or "").strip()
                    row["_comp_tooltip"] = self._build_formula_tooltip(expr_for_tooltip, inherited_comp, None, substitutions=formatted or None)

            else:

                row["_qt_rule_tooltip"] = None

                # Para linhas do tipo 'parent' não tratamos qt_und como factor filho
                if row_type == "parent":
                    # parent rows contribute via _qt_parent_factor; child factor must be 1
                    formula_child = 1.0
                    row["_qt_formula_value"] = formula_child
                    row["_qt_manual_override"] = False
                    row["_qt_manual_tooltip"] = None
                    row["_qt_manual_value"] = None
                    effective_child = formula_child
                else:
                    formula_child = 1.0
                    row["_qt_formula_value"] = formula_child
                    row["_qt_manual_override"] = False
                    row["_qt_manual_tooltip"] = None
                    row["_qt_manual_value"] = None
                    effective_child = formula_child

            row["_qt_parent_factor"] = parent_factor

            row["_qt_child_factor"] = effective_child

            try:
                total = float(divisor) * float(parent_factor) * float(effective_child)
            except Exception:
                total = 0.0

            row["qt_total"] = total if total else None

            # Atualizar métricas derivadas (área e perímetro por unidade)
            comp_res_val = row.get("comp_res")
            larg_res_val = row.get("larg_res")
            area_val: Optional[float] = None
            perimetro_val: Optional[float] = None
            try:
                comp_float = float(comp_res_val) if comp_res_val not in (None, "") else None
            except (TypeError, ValueError):
                comp_float = None
            try:
                larg_float = float(larg_res_val) if larg_res_val not in (None, "") else None
            except (TypeError, ValueError):
                larg_float = None
            if comp_float is not None and larg_float is not None:
                comp_m = comp_float / 1000.0
                larg_m = larg_float / 1000.0
                area_val = round(comp_m * larg_m, 4)
                perimetro_val = round(2 * (comp_m + larg_m), 4)
            row["area_m2_und"] = area_val
            row["perimetro_und"] = perimetro_val
            if self._is_spp_row(row):
                if comp_float is not None:
                    row["spp_ml_und"] = round(comp_float / 1000.0, 2)
                else:
                    row["spp_ml_und"] = None
            else:
                row["spp_ml_und"] = None

            if row.get("esp_mp") not in (None, "") and not expr_esp:

                default_esp = _coerce_dimension(row.get("esp_mp"))

                row["esp_res"] = default_esp

                row["_esp_error"] = None

                substitution = self._format_result_number(default_esp) or row.get("esp")

                row["_esp_tooltip"] = self._build_formula_tooltip(expr_esp or (row.get("esp") or substitution or ""), default_esp, None, substitutions=substitution or None)

        if session is not None:
            self._orla_info_cache.clear()
            ref_cache: Dict[str, Tuple[float, float, Optional[str]]] = {}
            for row in self.rows:
                try:
                    svc_custeio.preencher_info_orlas_linha(session, row, ref_cache)
                except Exception:
                    continue

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

        try:

            row = page.table_model.rows[index.row()]

        except Exception:

            row = {}

        familia_val = (row.get("familia") or "").strip()

        row_type = (row or {}).get("_row_type")

        info_ferragem = None
        is_ferragens = False

        if row_type == "child":

            info_ferragem = svc_custeio.inferir_ferragem_info(row) if row else None

            is_ferragens = bool(familia_val) and familia_val.casefold() == "ferragens"

            if not is_ferragens and info_ferragem:

                familia_info = (info_ferragem.get("familia") or "").strip()

                if familia_info and familia_info.casefold() == "ferragens":

                    is_ferragens = True

        if is_ferragens:

            tipo_hint: Optional[str] = None

            if info_ferragem and info_ferragem.get("tipo"):

                tipo_hint = info_ferragem["tipo"]

            elif row.get("tipo"):

                tipo_hint = row.get("tipo")

            options = svc_custeio.lista_mat_default_ferragens(session, context, tipo_hint)

            if options:

                return options

        familia = row.get("familia") or row.get("mat_default")

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

        if isinstance(row, Mapping):
            for extra_key in (
                "_qt_manual_override",
                "_qt_formula_value",
                "_child_source",
                "_parent_uid",
                "_group_uid",
                "_row_type",
                "_normalized_child",
            ):
                if extra_key in row:
                    coerced[extra_key] = row[extra_key]
        return coerced


class AcabamentoDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate para colunas de acabamento que preenche um QComboBox com as
    opcoes de acabamentos disponiveis para o item em contexto."""

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
        "revert_formula": QtWidgets.QStyle.SP_ArrowBack,
    }



    def __init__(self, parent=None, current_user=None):

        super().__init__(parent)

        self.current_user = current_user
        self.current_user_id = getattr(current_user, "id", None) if current_user is not None else None

        self.session = SessionLocal()

        self.context = None

        self.current_orcamento_id: Optional[int] = None

        self.current_item_id: Optional[int] = None
        self._current_item_obj: Optional[OrcamentoItem] = None



        self._updating_checks = False  # guarda contra reentrÃ¢ncia ao propagar check

        self._clipboard_rows: List[Dict[str, Any]] = []

        self.table_model = CusteioTableModel(self)

        self.table_model._page = self

        self._collapsed_groups: Set[str] = set()
        self._rows_dirty = False

        self._setup_ui()

        self._populate_tree()

        self._update_summary()


    def _auto_dimensions_enabled(self) -> bool:

        if self.current_user_id is None:

            return False

        try:

            return svc_custeio.is_auto_dimension_enabled(self.session, self.current_user_id)

        except Exception:

            return False



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
        self._save_button_base_text = self.btn_save.text()

        actions_layout.addWidget(self.btn_refresh)

        actions_layout.addWidget(self.btn_save)

        actions_layout.addStretch(1)

        right_layout.addLayout(actions_layout)

        self._dimension_values: Dict[str, Optional[float]] = {key: None for key in DIMENSION_KEY_ORDER}
        self._dimension_col_map: Dict[str, int] = {key: idx for idx, key in enumerate(DIMENSION_KEY_ORDER)}
        self._dimensions_dirty = False
        self.dimensions_table = QtWidgets.QTableWidget(2, len(DIMENSION_KEY_ORDER))
        self.dimensions_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.dimensions_table.setFixedHeight(72)
        self.dimensions_table.verticalHeader().setVisible(False)
        self.dimensions_table.horizontalHeader().setVisible(False)
        self.dimensions_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.dimensions_table.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.dimensions_table.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        self.dimensions_table.setAlternatingRowColors(True)
        self.dimensions_table.setStyleSheet("QTableWidget { gridline-color: #d0d0d0; }")
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
            self.dimensions_table.setItem(1, col, value_item)
            self.dimensions_table.setColumnWidth(col, 60)
        self.dimensions_table.itemChanged.connect(self._on_dimension_item_changed)
        self.dimensions_table.setEnabled(False)
        right_layout.addWidget(self.dimensions_table)
        self._update_dimension_table()


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

        # Registar delegates para colunas de acabamento (drop-down de acabamentos)
        for acb_key in ("acabamento_sup", "acabamento_inf"):
            try:
                acb_col = self.table_model.column_keys.index(acb_key)
                self.table_view.setItemDelegateForColumn(acb_col, AcabamentoDelegate(self.table_view, self))
            except ValueError:
                continue

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
        self._update_save_button_text()



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
        try:
            return float(stripped.replace(",", "."))
        except ValueError:
            return None


    def _style_dimension_cell(self, key: str, item: Optional[QtWidgets.QTableWidgetItem] = None) -> None:
        if not hasattr(self, "dimensions_table"):
            return
        if item is None:
            col = self._dimension_col_map.get(key) if hasattr(self, "_dimension_col_map") else None
            if col is None:
                return
            item = self.dimensions_table.item(1, col)
            if item is None:
                return
        text = (item.text() or "").strip()
        has_value = bool(text)
        color = DIMENSION_COLOR_MAP.get(key)
        brush = QtGui.QBrush(color) if has_value and color is not None else QtGui.QBrush(QtCore.Qt.transparent)
        item.setBackground(brush)
        font = item.font()
        font.setBold(has_value)
        item.setFont(font)



    def _update_dimension_table(self) -> None:
        if not hasattr(self, "dimensions_table"):
            return
        self.dimensions_table.blockSignals(True)
        for col, key in enumerate(DIMENSION_KEY_ORDER):
            item = self.dimensions_table.item(1, col)
            if item is None:
                item = QtWidgets.QTableWidgetItem("")
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.dimensions_table.setItem(1, col, item)
            item.setText(self._format_dimension_value(self._dimension_values.get(key)))
            self._style_dimension_cell(key, item)
        self.dimensions_table.blockSignals(False)



    def _set_dimensions_enabled(self, enabled: bool) -> None:
        if hasattr(self, "dimensions_table"):
            self.dimensions_table.setEnabled(enabled)



    def _clear_dimension_values(self) -> None:
        self._dimension_values = {key: None for key in DIMENSION_KEY_ORDER}
        self._dimensions_dirty = False
        self._set_dimensions_enabled(False)
        self._update_dimension_table()
        self._update_save_button_text()



    def _load_dimension_values(self, item_obj: Optional[OrcamentoItem]) -> None:
        if self.context is None:
            self._clear_dimension_values()
            return
        try:
            armazenados, tem_registro = svc_custeio.carregar_dimensoes(self.session, self.context)
        except Exception:
            armazenados, tem_registro = {}, False
        defaults = svc_custeio.dimensoes_default_por_item(item_obj)
        for key in DIMENSION_KEY_ORDER:
            valor = armazenados.get(key)
            if not tem_registro and valor is None:
                valor = defaults.get(key)
            self._dimension_values[key] = valor
        self._dimensions_dirty = False
        self._set_dimensions_enabled(True)
        self._update_dimension_table()
        self._update_save_button_text()



    def _on_dimension_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if item.row() != 1:
            return
        key = DIMENSION_KEY_ORDER[item.column()]
        novo_valor = self._coerce_dimension_value(item.text())
        if item.text().strip() and novo_valor is None:
            self.dimensions_table.blockSignals(True)
            item.setText(self._format_dimension_value(self._dimension_values.get(key)))
            self.dimensions_table.blockSignals(False)
            self._style_dimension_cell(key, item)
            return
        self._dimension_values[key] = novo_valor
        self.dimensions_table.blockSignals(True)
        item.setText(self._format_dimension_value(novo_valor))
        self.dimensions_table.blockSignals(False)
        self._style_dimension_cell(key, item)
        self._dimensions_dirty = True
        self._update_save_button_text()
        if self.context:
            self.table_model.recalculate_all()



    def dimension_values(self) -> Dict[str, Optional[float]]:
        return {key: self._dimension_values.get(key) for key in DIMENSION_KEY_ORDER}



    def _collect_dimension_payload(self) -> Dict[str, Optional[float]]:
        return self.dimension_values()


    def is_dirty(self) -> bool:

        return bool(self._rows_dirty or self._dimensions_dirty)


    def _update_save_button_text(self) -> None:

        if hasattr(self, "btn_save"):

            base = getattr(self, "_save_button_base_text", "Guardar Dados Custeio")

            suffix = "*" if self.is_dirty() else ""

            self.btn_save.setText(f"{base}{suffix}")


    def _set_rows_dirty(self, dirty: bool) -> None:

        new_state = bool(dirty)

        if self._rows_dirty == new_state:

            return

        self._rows_dirty = new_state

        self._update_save_button_text()



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



        auto_dimensions = self._auto_dimensions_enabled()

        novas_linhas = svc_custeio.gerar_linhas_para_selecoes(self.session, self.context, selections)

        if auto_dimensions:

            try:

                svc_custeio.aplicar_dimensoes_automaticas(novas_linhas)

            except Exception:

                pass

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


    def _save_custeio(self, *, auto: bool = False) -> bool:

        if not self.context:

            if not auto:

                QtWidgets.QMessageBox.information(self, "Informacao", "Nenhum item selecionado.")

            return False

        self.table_model.recalculate_all()

        dimensoes = self._collect_dimension_payload()

        linhas = self.table_model.export_rows()

        try:

            svc_custeio.salvar_custeio_items(self.session, self.context, linhas, dimensoes)

        except Exception as exc:

            self.session.rollback()

            QtWidgets.QMessageBox.critical(

                self,

                "Erro",

                f"Falha ao guardar Dados Custeio: {exc}",

            )

            return False

        if not auto:

            QtWidgets.QMessageBox.information(self, "Sucesso", "Dados de custeio guardados.")

        self._dimensions_dirty = False

        self._set_rows_dirty(False)

        self._reload_custeio_rows()

        self._apply_updates_from_items()

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()

        self._update_save_button_text()

        return True


    def _on_save_custeio(self) -> None:

        self._save_custeio(auto=False)


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
        self._update_save_button_text()



    def _apply_collapse_state(self) -> None:

        if not hasattr(self, "table_view"):
            return

        collapsed = getattr(self, "_collapsed_groups", set())
        current_group = None
        row_count = self.table_model.rowCount()

        # First pass: determine visibility based on groups
        visibility: List[bool] = [True] * row_count
        for idx in range(row_count):
            row = self.table_model.rows[idx]
            row_type = row.get("_row_type")
            group_uid = row.get("_group_uid")

            if row_type == "division":
                current_group = group_uid
                visibility[idx] = True
                continue

            if current_group and current_group in collapsed:
                visibility[idx] = False
            else:
                visibility[idx] = True
        
        # Second pass: apply visibility
        for idx in range(row_count):
            self.table_view.setRowHidden(idx, not visibility[idx])

        self.table_view.viewport().update()

        id_col = self.table_model._column_index.get("id")
        if id_col is not None and row_count:
            top_left = self.table_model.index(0, id_col)
            bottom_right = self.table_model.index(row_count - 1, id_col)
            self.table_model.dataChanged.emit(top_left, bottom_right, [QtCore.Qt.DisplayRole])


    def _icon(self, key: str) -> QtGui.QIcon:

        style = self.style() or QtWidgets.QApplication.style()

        return style.standardIcon(self.ICON_MAP.get(key, QtWidgets.QStyle.SP_FileIcon))


    def _selected_table_rows(self) -> List[int]:

        selection = self.table_view.selectionModel()

        if not selection:

            return []

        return sorted({index.row() for index in selection.selectedRows()})


    def confirm_qt_und_override(self, row_data: Mapping[str, Any], new_value: Optional[float]) -> bool:

        descricao = str(row_data.get("descricao") or row_data.get("def_peca") or "").strip()

        if not descricao:

            descricao = "linha selecionada"

        value_display = "-" if new_value is None else (self.table_model._format_result_number(new_value) or str(new_value))

        message = (

            f"O valor de QT_und para {descricao} resulta de uma formula.\n"

            f"Pretende alterar manualmente para {value_display}?"

        )

        reply = QtWidgets.QMessageBox.question(

            self,

            "Confirmar alteracao",

            message,

            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,

            QtWidgets.QMessageBox.No,

        )

        return reply == QtWidgets.QMessageBox.Yes


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

    # Removed manual revert action: child/associated components are no
    # longer editable by the user and revert option is not available.

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

    # revert action removed

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

        # revert action removed: no handling

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
        uid_map = {row.get("_uid"): row for row in self.table_model.rows if row.get("_uid")}

        for idx, row in enumerate(self.table_model.rows):

            if row.get("blk"):

                continue

            row_type = row.get("_row_type")

            familia_hint = row.get("familia")

            if row_type == "child" and not familia_hint:

                parent_uid = row.get("_parent_uid")

                parent_row = uid_map.get(parent_uid)

                if parent_row:

                    familia_hint = parent_row.get("familia")

            mat_default = (row.get("mat_default") or "").strip()

            if mat_default:

                grupo = mat_default

            else:

                def_peca = (row.get("def_peca") or "").strip()

                grupo = svc_custeio.grupo_por_def_peca(def_peca)

                if not grupo and row.get("_child_source"):

                    grupo = svc_custeio.grupo_por_def_peca(row["_child_source"]) or row.get("_child_source")

            grupo_norm = (grupo or "").strip()

            familia_norm = (familia_hint or "").strip()

            material = None

            if grupo_norm:

                cache_key = ("grupo", grupo_norm.casefold(), familia_norm.casefold())

                if cache_key not in cache:

                    cache[cache_key] = svc_custeio.obter_material_por_grupo(

                        self.session,

                        self.context,

                        grupo_norm,

                        familia_hint,

                    )

                material = cache[cache_key]

            ferragem_info = None

            if not material:

                ferragem_info = svc_custeio.inferir_ferragem_info(row)

                if ferragem_info:

                    tipo_val = ferragem_info.get("tipo")

                    familia_val = ferragem_info.get("familia")

                    cache_key = ("ferragem", (tipo_val or "").strip().casefold(), (familia_val or "").strip().casefold())

                    if cache_key not in cache:

                        cache[cache_key] = svc_custeio.obter_ferragem_por_tipo(

                            self.session,

                            self.context,

                            tipo_val,

                            familia_val,

                        )

                    material = cache[cache_key]

                    if familia_val and not row.get("familia"):

                        row["familia"] = familia_val

                    if tipo_val and not row.get("tipo"):

                        row["tipo"] = tipo_val

                    if not row.get("mat_default"):

                        lista = svc_custeio.lista_mat_default_ferragens(self.session, self.context, tipo_val)

                        if lista:

                            row["mat_default"] = lista[0]

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

    def auto_save_if_dirty(self) -> bool:

        if not self.is_dirty():

            return True

        if not self.context:

            return True

        return self._save_custeio(auto=True)


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

        self._current_item_obj = item_obj



        if item_obj is not None:

            try:

                self.context = svc_custeio.carregar_contexto(

                    self.session, orcamento_id, item_id=getattr(item_obj, "id_item", normalized_item_id)

                )

            except Exception:

                self.context = None

        else:

            self.context = None



        if self.context is not None:
            self._load_dimension_values(item_obj)
        else:
            self._clear_dimension_values()



        self._reload_custeio_rows()

        self._apply_updates_from_items()

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()



    def clear_context(self) -> None:

        self.context = None

        self.current_orcamento_id = None

        self.current_item_id = None

        self._current_item_obj = None

        self._clear_dimension_values()

        self._collapsed_groups.clear()

        self._reset_header()

        self._clear_all_checks()

        self.table_model.clear()

        self._update_table_placeholder_visibility()



