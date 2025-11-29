#-\nROW_PARENT_COLOR = QtGui.QColor(230, 240, 255)  # Azul claro para linhas pai\nROW_CHILD_COLOR = QtGui.QColor(255, 250, 205)   # Amarelo suave para linhas filho\nROW_CHILD_INDENT = '\u2003\u2003'  # Espa├ºos para indenta├º├úo visual dos filhos\n-- START OF FILE custeio_items.py ---



from __future__ import annotations



from copy import deepcopy
from functools import partial
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple
import logging
import ast
import re
import unicodedata
import uuid


from PySide6 import QtCore, QtGui, QtWidgets
import shiboken6



from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento, OrcamentoItem

from Martelo_Orcamentos_V2.app.services import custeio_items as svc_custeio
from Martelo_Orcamentos_V2.app.services import modulos as svc_modulos
from Martelo_Orcamentos_V2.app.services import producao as svc_producao
from Martelo_Orcamentos_V2.app.services import def_pecas as svc_def_pecas
from Martelo_Orcamentos_V2.app.services import dados_items as svc_dados_items

from Martelo_Orcamentos_V2.app.db import SessionLocal
from sqlalchemy import select
from .dados_gerais import MateriaPrimaPicker
from ..utils.header import apply_highlight_text, init_highlight_label
from Martelo_Orcamentos_V2.ui.delegates import DadosGeraisDelegate, BoolDelegate
from ..dialogs.custeio_modulos import ImportModuloDialog, SaveModuloDialog

SPECIAL_MAT_DEFAULTS = {
    "divisoria": "Divisorias",
    "travessa": "Travessas",
    "prumo": "Prumos",
    "fundo aluminio 1": "Fundo aluminio",
}
PAINEL_SIS_CORRER_OPTIONS: Tuple[str, ...] = (
    "Painel Porta Correr 1",
    "Painel Porta Correr 2",
    "Painel Porta Correr 3",
    "Painel Porta Correr 4",
    "Painel Porta Correr 5",
    "Painel Espelho Correr 1",
    "Painel Espelho Correr 2",
    "Painel Espelho Correr 3",
)
SPP_DEF_LABELS: Tuple[str, ...] = (
    "PUXADOR VERTICAL 1",
    "PUXADOR VERTICAL 2",
    "CALHA SUPERIOR {SPP} 1 CORRER",
    "CALHA SUPERIOR {SPP} 2 CORRER",
    "CALHA INFERIOR {SPP} 1 CORRER",
    "CALHA INFERIOR {SPP} 2 CORRER",
    "PERFIL HORIZONTAL H {SPP}",
    "PERFIL HORIZONTAL U {SPP}",
    "PERFIL HORIZONTAL L {SPP}",
    "ACESSORIO {SPP} 7 CORRER",
    "ACESSORIO {SPP} 8 CORRER",
)
SPP_DEF_TOKENS: Set[str] = {
    svc_custeio._normalize_token(label) for label in SPP_DEF_LABELS
}
SPP_SIS_CORRER_OPTIONS: Tuple[str, ...] = (
    "Puxador Vertical 1",
    "Puxador Vertical 2",
    "Calha Superior 1 SPP",
    "Calha Superior 2 SPP",
    "Calha Inferior 1 SPP",
    "Calha Inferior 2 SPP",
    "Perfil Horizontal H SPP",
    "Perfil Horizontal U SPP",
    "Perfil Horizontal L SPP",
    "Acessorio 7 SPP",
    "Acessorio 8 SPP",
)
RODIZIO_DEF_LABELS: Tuple[str, ...] = (
    "RODIZIO SUP 1",
    "RODIZIO SUP 2",
    "RODIZIO INF 1",
    "RODIZIO INF 2",
)
RODIZIO_DEF_TOKENS: Set[str] = {
    svc_custeio._normalize_token(label) for label in RODIZIO_DEF_LABELS
}
RODIZIO_SIS_CORRER_OPTIONS: Tuple[str, ...] = (
    "Rodizio Sup 1",
    "Rodizio Sup 2",
    "Rodizio Inf 1",
    "Rodizio Inf 2",
)
ACESSORIO_CORRER_LABELS: Tuple[str, ...] = (
    "ACESSORIO 1 CORRER",
    "ACESSORIO 2 CORRER",
    "ACESSORIO 3 CORRER",
    "ACESSORIO 4 CORRER",
    "ACESSORIO 5 CORRER",
    "ACESSORIO 6 CORRER",
)
ACESSORIO_CORRER_TOKENS: Set[str] = {
    svc_custeio._normalize_token(label) for label in ACESSORIO_CORRER_LABELS
}
ACESSORIO_CORRER_OPTIONS: Tuple[str, ...] = (
    "Acessorio 1",
    "Acessorio 2",
    "Acessorio 3",
    "Acessorio 4",
    "Acessorio 5",
    "Acessorio 6",
)
COZINHAS_SPECIAL_DEFS: Tuple[str, ...] = (
    "Balde Lixo",
    "Canto Cozinha 1",
    "Canto Cozinha 2",
    "Porta Talheres",
    "Tulha 1",
    "Tulha 2",
    "Fundo Aluminio 1",
    "Fundo Aluminio 2",
    "Fundo Plastico Frigorifico",
    "Salva Sifao",
    "Ferragens Diversas 1",
    "Ferragens Diversas 2",
    "Ferragens Diversas 3",
    "Ferragens Diversas 4",
    "Ferragens Diversas 5",
)
COZINHAS_MAT_DEFAULT_OPTIONS: Tuple[str, ...] = (
    "Balde Lixo",
    "Canto Cozinha 1",
    "Canto Cozinha 2",
    "Porta talheres",
    "Porta calcas",
    "Tulha",
    "Fundo aluminio",
    "Grelha Veludo",
    "Acessorio cozinha 1",
    "Acessorio cozinha 2",
    "Acessorio cozinha 3",
    "Ferragens Diversas 1",
    "Ferragens Diversas 2",
    "Ferragens Diversas 3",
    "Ferragens Diversas 4",
    "Ferragens Diversas 5",
    "Ferragens Diversas 6 SPP",
    "Ferragens Diversas 7 SPP",
)
COZINHAS_SPECIAL_TOKENS: Set[str] = {
    svc_custeio._normalize_token(name) for name in COZINHAS_SPECIAL_DEFS
}
COZINHAS_TYPE_HINTS: Tuple[str, ...] = (
    "FERRAGENS & ACESSORIOS",
    "FERRAGENS OU ACESSORIOS",
    "FERRAGENS E ACESSORIOS",
    "FERRAGENS",
    "ACESSORIOS",
)

COLAGEM_LABEL = getattr(svc_custeio, "COLAGEM_REVESTIMENTO_LABEL", "COLAGEM/REVESTIMENTO (M2)")
_COLAGEM_LABEL_ALIASES = {
    COLAGEM_LABEL.strip().casefold(),
    "COLAGEM SANDWICH (M2)".casefold(),
    "SERVICOS COLAGEM (M2)".casefold(),
}
COLAGEM_INFO_TEXT = (
    "Para Colagens ou Revestimentos o preço é calculado por área (m²) e por face. "
    "Mantenha QT_und = 1; para aplicar em 2 faces mantenha QT_und = 1 e indique COMP e LARG "
    "para permitir o cálculo em m²."
)

EMBALAGEM_LABEL = "EMBALAGEM (M3)"
_EMBALAGEM_LABEL_ALIASES = {
    EMBALAGEM_LABEL.strip().casefold(),
}
EMBALAGEM_INFO_TEXT = (
    "Para Embalagem (M3) o cálculo usa o volume (COMP x LARG x ESP). "
    "Preencha COMP, LARG e ESP (> 0 mm) para permitir o cálculo correto."
)


def _is_colagem_label(value: Optional[str]) -> bool:
    if not value:
        return False
    return value.strip().casefold() in _COLAGEM_LABEL_ALIASES


def _is_embalagem_label(value: Optional[str]) -> bool:
    if not value:
        return False
    return value.strip().casefold() in _EMBALAGEM_LABEL_ALIASES


DEF_LABEL_MAO_OBRA_MIN = "MAO OBRA (Min)"
DEF_LABEL_CNC_MIN = "CNC (Min)"
DEF_LABEL_CNC_5_MIN = "CNC (5 Min)"
DEF_LABEL_CNC_15_MIN = "CNC (15 Min)"
DEF_LABEL_EMBALAGEM = EMBALAGEM_LABEL
DEF_LABEL_COLAGEM = COLAGEM_LABEL

DEF_LABEL_MAO_OBRA_MIN_NORM = DEF_LABEL_MAO_OBRA_MIN.casefold()
DEF_LABEL_CNC_MIN_NORM = DEF_LABEL_CNC_MIN.casefold()
DEF_LABEL_CNC_5_MIN_NORM = DEF_LABEL_CNC_5_MIN.casefold()
DEF_LABEL_CNC_15_MIN_NORM = DEF_LABEL_CNC_15_MIN.casefold()
DEF_LABEL_EMBALAGEM_NORM = DEF_LABEL_EMBALAGEM.casefold()
DEF_LABEL_COLAGEM_NORM = DEF_LABEL_COLAGEM.casefold()
MANUAL_CNC_LABELS = {
    DEF_LABEL_CNC_MIN_NORM,
    DEF_LABEL_CNC_5_MIN_NORM,
    DEF_LABEL_CNC_15_MIN_NORM,
}


def _special_default_for_row(row: Mapping[str, Any]) -> Optional[str]:
    def_text = (row.get("def_peca") or row.get("_child_source") or "").strip()
    if not def_text:
        return None
    base = def_text.split("[", 1)[0].strip().casefold()
    return SPECIAL_MAT_DEFAULTS.get(base)



logger = logging.getLogger(__name__)



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
    "soma_custo_acb": "Total de custos de acabamento (faces superior/inferior) calculado a partir da area, preco liquido e desperdicio do acabamento selecionado.",
}

CELL_TOOLTIP_KEYS = set(HEADER_TOOLTIPS.keys()) | {"descricao"}

# Column display/configuration helpers Larguras padrao para colunas na tabela de itens de custeio
COLUMN_WIDTH_DEFAULTS = {
    "id": 55,
    "descricao_livre": 170,
    "icon_hint": 36,
    "def_peca": 170,
    "descricao": 150,
    "qt_mod": 60,
    "qt_und": 50,
    "comp": 50,
    "larg": 50,
    "esp": 40,
    "mps": 40,
    "mo": 40,
    "orla": 40,
    "blk": 40,
    "nst": 40,
    "mat_default": 150,
    "acabamento_sup": 150,
    "acabamento_inf": 150,
    "qt_total": 50,
    "comp_res": 50,
    "larg_res": 50,
    "esp_res": 50,
    "ref_le": 65,
    "descricao_no_orcamento": 250,
    "pliq": 50,
    "und": 30,
    "desp": 45,
    "orl_0_4": 70,
    "orl_1_0": 70,
    "tipo": 100,
    "familia": 100,
    "comp_mp": 60,
    "larg_mp": 60,
    "esp_mp": 60,
    "orl_c1": 50,
    "orl_c2": 50,
    "orl_l1": 50,
    "orl_l2": 50,
    "ml_orl_c1": 70,
    "ml_orl_c2": 70,
    "ml_orl_l1": 70,
    "ml_orl_l2": 70,
    "custo_orl_c1": 70,
    "custo_orl_c2": 70,
    "custo_orl_l1": 70,
    "custo_orl_l2": 70,
    "area_m2_und": 90,
    "perimetro_und": 100,
}

LOCKED_COLUMN_KEYS: Set[str] = {"id", "def_peca", "descricao", "qt_mod", "qt_und", "qt_total"}

ORLA_ML_KEYS: Set[str] = {"ml_orl_c1", "ml_orl_c2", "ml_orl_l1", "ml_orl_l2"}
ORLA_COST_KEYS: Set[str] = {"custo_orl_c1", "custo_orl_c2", "custo_orl_l1", "custo_orl_l2"}
ORLA_TOTAL_KEYS: Set[str] = {"soma_total_ml_orla", "custo_total_orla"}
PRODUCTION_COST_UND_KEYS: Set[str] = {
    "cp01_sec_und",
    "cp02_orl_und",
    "cp03_cnc_und",
    "cp04_abd_und",
    "cp05_prensa_und",
    "cp06_esquad_und",
    "cp07_embalagem_und",
    "cp08_mao_de_obra_und",
    "cp09_colagem_und",
}
PRODUCTION_CP_SUM_KEYS: Tuple[Tuple[str, str], ...] = (
    ("cp01_sec_und", "CP01_SEC_und"),
    ("cp02_orl_und", "CP02_ORL_und"),
    ("cp03_cnc_und", "CP03_CNC_und"),
    ("cp04_abd_und", "CP04_ABD_und"),
    ("cp05_prensa_und", "CP05_PRENSA_und"),
    ("cp06_esquad_und", "CP06_ESQUAD_und"),
    ("cp07_embalagem_und", "CP07_EMBALAGEM_und"),
    ("cp08_mao_de_obra_und", "CP08_MAO_DE_OBRA_und"),
)
SPP_WASTE_PERCENT: float = 0.06
DEFAULT_MP_DESP_FRACTION: float = 0.18
UNIT_ML_KEYS: Set[str] = ORLA_ML_KEYS | {"soma_total_ml_orla", "perimetro_und", "spp_ml_und"}
UNIT_EURO_KEYS: Set[str] = (
    ORLA_COST_KEYS
    | {"custo_total_orla", "custo_mp_und", "custo_mp_total", "soma_custo_und", "soma_custo_total"}
    | PRODUCTION_COST_UND_KEYS
)
UNIT_M2_KEYS: Set[str] = {"area_m2_und"}
CENTER_ALIGN_KEYS: Set[str] = (
    UNIT_ML_KEYS
    | UNIT_EURO_KEYS
    | UNIT_M2_KEYS
    | {"cp01_sec", "cp02_orl", "cp03_cnc", "cp04_abd", "cp05_prensa", "cp06_esquad", "cp07_embalagem", "cp08_mao_de_obra"}
)

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
                if shiboken6.isValid(top_editor):
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

      - casa texto no n├â┬│ OU em qualquer descendente (expans├â┬úo autom├â┬ítica);

      - opcionalmente mostra s├â┬│ itens marcados.

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

        # J├â┬í estamos a trabalhar sobre sourceModel(), por isso o index ├â┬® do modelo base

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
        self._acabamento_info_cache: Dict[str, Optional[Dict[str, Any]]] = {}

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
        # aceita "." ou "," como separador decimal e ignora símbolos de moeda/percentagem/espaços
        if isinstance(value, str):
            try:
                cleaned = value.strip()
                cleaned = cleaned.replace("€", "").replace("EUR", "").replace("%", "")
                cleaned = cleaned.replace(" ", "").replace(" ", "")
                cleaned = cleaned.replace(",", ".")
                if cleaned.count(".") > 1:
                    # remove separadores de milhar simples (ex: 1.234,56 -> 1234.56)
                    parts = cleaned.split(".")
                    cleaned = "".join(parts[:-1]) + "." + parts[-1]
                return float(cleaned)
            except Exception:
                return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


    @staticmethod
    def _coerce_percent(value: Any) -> Optional[float]:
        if value in (None, "", False):
            return None
        if isinstance(value, (int, float)):
            num = float(value)
        else:
            try:
                text_val = str(value).strip().replace('%', '').replace(',', '.')
            except Exception:
                return None
            if not text_val:
                return None
            try:
                num = float(text_val)
            except (TypeError, ValueError):
                return None
        if abs(num) > 1:
            num /= 100.0
        return num

    @staticmethod
    def _coerce_checked(value: Any) -> bool:
        return svc_custeio._coerce_checkbox_to_bool(value)

    def _ensure_orla_info(self, row_data: Dict[str, Any], side: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Garante que os campos orl_pliq e orl_desp para o lado indicado est├úo preenchidos a partir da Materia Prima."""
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

    def _get_acabamento_info(self, nome: Optional[str]) -> Optional[Dict[str, Any]]:
        if not nome:
            return None
        page = getattr(self, "_page", None)
        session = getattr(page, "session", None) if page is not None else None
        context = getattr(page, "context", None) if page is not None else None
        if session is None or context is None:
            return None
        try:
            return svc_custeio.obter_info_acabamento(session, context, nome, cache=self._acabamento_info_cache)
        except Exception:
            return None

    def _build_acabamento_tooltip(self, row_data: Mapping[str, Any]) -> Optional[str]:
        sup_nome = str(row_data.get("acabamento_sup") or "").strip()
        inf_nome = str(row_data.get("acabamento_inf") or "").strip()
        if not sup_nome and not inf_nome:
            return None

        def _fmt_currency(valor: Optional[float]) -> str:
            if valor is None:
                return "-"
            return f"{valor:.2f}".replace(".", ",")

        area_val = self._coerce_numeric(row_data.get("area_m2_und"))
        qt_total_val = self._coerce_numeric(row_data.get("qt_total")) or 0.0
        total_val = self._coerce_numeric(row_data.get("soma_custo_acb"))

        lines: List[str] = ["Acabamentos - detalhes do c\u00E1lculo"]
        if area_val is not None:
            lines.append(f"\u00C1rea por unidade: {area_val:.4f} m\u00B2")
        if qt_total_val:
            qt_display = self._format_result_number(qt_total_val) or f"{qt_total_val:.2f}"
            lines.append(f"Qt_total: {qt_display}")

        unit_sum = 0.0
        has_formula_values = False

        def _append_info(label: str, nome: str) -> None:
            nonlocal unit_sum, has_formula_values
            info = self._get_acabamento_info(nome)
            if not info:
                lines.append(f"{label}: {nome} (sem dados dispon\u00EDveis na tabela de acabamentos)")
                return

            preco = info.get("preco_liq") or 0.0
            desp_fraction = info.get("desp_fraction") or 0.0
            desp_percent = info.get("desp_percent")
            if desp_percent is None:
                desp_percent = desp_fraction * 100.0
            fator = 1.0 + desp_fraction

            lines.append(f"{label}: {nome}")
            lines.append(
                f"  Pre\u00E7o l\u00EDq.: {_fmt_currency(preco)} \u20AC/m\u00B2 | Desperd\u00EDcio: {desp_percent:.2f}% (fator {fator:.3f})"
            )

            if area_val is not None and preco:
                custo_unit = area_val * preco * fator
                unit_sum_local = round(custo_unit, 6)
                unit_sum += unit_sum_local
                has_formula_values = True
                lines.append(
                    f"  Custo unit\u00E1rio: {area_val:.4f} m\u00B2 x {_fmt_currency(preco)} \u20AC/m\u00B2 x {fator:.3f} = {_fmt_currency(unit_sum_local)} \u20AC/und"
                )
            else:
                lines.append("  Custo unit\u00E1rio: insuficiente (\u00E1rea/pre\u00E7o em falta)")

        if sup_nome:
            _append_info("Superior", sup_nome)
        if inf_nome:
            _append_info("Inferior", inf_nome)

        if not has_formula_values and total_val is not None and qt_total_val:
            unit_sum = round(total_val / qt_total_val, 6)
        unit_sum = round(unit_sum, 2)
        lines.append(f"Soma unit\u00E1ria (calculada): {_fmt_currency(unit_sum)} \u20AC/und")

        if total_val is not None:
            total_display = _fmt_currency(total_val)
            if qt_total_val:
                qt_display = self._format_result_number(qt_total_val) or f"{qt_total_val:.2f}"
                lines.append(
                    f"Custo total registado: {total_display} \u20AC (= {_fmt_currency(unit_sum)} \u20AC/und x {qt_display})"
                )
            else:
                lines.append(f"Custo total registado: {total_display} \u20AC")
        else:
            lines.append("Custo total registado: -")

        return "\n".join(lines)

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

    @staticmethod
    def _extract_child_tokens(def_peca: Optional[str]) -> List[str]:
        if not def_peca or "+" not in def_peca:
            return []
        tokens: List[str] = []
        for part in def_peca.split("+")[1:]:
            normalized = CusteioTableModel._normalize_def_peca(part)
            if normalized:
                tokens.append(normalized)
        return tokens

    @staticmethod
    def _match_expected_child(normalized_child: str, expected_tokens: List[str]) -> bool:
        if not normalized_child or not expected_tokens:
            return False
        stripped = normalized_child.lstrip("_")
        candidates = {normalized_child, stripped}
        for idx, token in enumerate(expected_tokens):
            if not token:
                continue
            token_clean = token.lstrip("_")
            token_match = any(
                cand == token_clean or cand.startswith(f"{token_clean}_")
                for cand in candidates
            )
            if token_match:
                expected_tokens.pop(idx)
                return True
        return False

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
        # Division rows: mostrar apenas o valor de qt_mod da divis├úo
        if self._is_division_row(row):
            return self._format_factor(row.get("qt_mod")) or ""

        parts: List[str] = []

        # Mostra o divisor (valor da divis├úo) se existir
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

        if role == QtCore.Qt.TextAlignmentRole:
            if spec["type"] == "bool" or key in CENTER_ALIGN_KEYS:
                return QtCore.Qt.AlignCenter

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
            if role == QtCore.Qt.ToolTipRole:
                tooltip_value = row_data.get("def_peca") or ""
                if _is_colagem_label(tooltip_value):
                    return COLAGEM_INFO_TEXT
                if _is_embalagem_label(tooltip_value):
                    return EMBALAGEM_INFO_TEXT
                return tooltip_value or None


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



        if role == QtCore.Qt.ToolTipRole and key == "cp01_sec_und":
            tooltip = row_data.get("_cp01_sec_und_tooltip")
            if tooltip:
                return tooltip
            return None

        if role == QtCore.Qt.ToolTipRole and key == "cp02_orl_und":
            tooltip = row_data.get("_cp02_orl_und_tooltip")
            if tooltip:
                return tooltip
            return None

        if role == QtCore.Qt.ToolTipRole and key == "cp03_cnc_und":
            tooltip = row_data.get("_cp03_cnc_und_tooltip")
            if tooltip:
                return tooltip
            return None

        if role == QtCore.Qt.ToolTipRole and key == "cp04_abd_und":
            tooltip = row_data.get("_cp04_abd_und_tooltip")
            if tooltip:
                return tooltip
            return None

        if role == QtCore.Qt.ToolTipRole and key == "cp05_prensa_und":
            tooltip = row_data.get("_cp05_prensa_und_tooltip")
            if tooltip:
                return tooltip
            return None

        if role == QtCore.Qt.ToolTipRole and key == "cp06_esquad_und":
            tooltip = row_data.get("_cp06_esquad_und_tooltip")
            if tooltip:
                return tooltip
            return None

        if role == QtCore.Qt.ToolTipRole and key == "cp07_embalagem_und":
            tooltip = row_data.get("_cp07_embalagem_und_tooltip")
            if tooltip:
                return tooltip
            return None

        if role == QtCore.Qt.ToolTipRole and key == "cp08_mao_de_obra_und":
            tooltip = row_data.get("_cp08_mao_de_obra_und_tooltip")
            if tooltip:
                return tooltip
            return None

        if role == QtCore.Qt.ToolTipRole and key == "cp09_colagem_und":
            tooltip = row_data.get("_cp09_colagem_und_tooltip")
            if tooltip:
                return tooltip
            return None

        if role == QtCore.Qt.ToolTipRole and key == "custo_mp_und":
            tooltip = row_data.get("_custo_mp_und_tooltip")
            if tooltip:
                return tooltip
            return None

        if role == QtCore.Qt.ToolTipRole and key == "custo_mp_total":
            tooltip = row_data.get("_custo_mp_total_tooltip")
            if tooltip:
                return tooltip
            return None

        if role == QtCore.Qt.ToolTipRole and key == "soma_custo_und":
            tooltip = row_data.get("_soma_custo_und_tooltip")
            if tooltip:
                return tooltip
            return None

        if role == QtCore.Qt.ToolTipRole and key == "soma_custo_total":
            tooltip = row_data.get("_soma_custo_total_tooltip")
            if tooltip:
                return tooltip
            return None

        if role == QtCore.Qt.ToolTipRole and key == "spp_ml_und":
            tooltip = row_data.get("_spp_ml_und_tooltip")
            if tooltip:
                return tooltip
            return None

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
            if self._coerce_checked(row_data.get("orla")):
                return "Custo das orlas = 0 € (checkbox Orla ativo)."
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

        if role == QtCore.Qt.ToolTipRole and key == "soma_custo_acb":
            return self._build_acabamento_tooltip(row_data)

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

                symbol = "+" if collapsed else "-"

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

                if key in UNIT_ML_KEYS:
                    return f"{num:.2f} ML"

                if key in UNIT_EURO_KEYS:
                    return f"{num:.2f} €"

                if key in UNIT_M2_KEYS:
                    return f"{num:.2f} M2"

                if fmt == "money":
                    texto = f"{num:.2f}".replace(".", ",")
                    return f"{texto} €"

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



        # tratar booleanos: aceitar CheckStateRole E EditRole (algumas vers├Áes do Qt usam EditRole)
        if spec["type"] == "bool" and role in (QtCore.Qt.CheckStateRole, QtCore.Qt.EditRole):
            # normalizar para True/False
            if role == QtCore.Qt.CheckStateRole:
                new_state = bool(value == QtCore.Qt.Checked)
            else:
                # EditRole: pode ser bool, int(0/1), string, ou at├® o valor Qt.Checked/Unchecked numericamente
                if isinstance(value, (int, float)):
                    try:
                        new_state = int(value) != 0
                    except Exception:
                        new_state = bool(value)
                else:
                    new_state = bool(value)

            # sem altera├º├úo => OK (evita triggers)
            if self.rows[row].get(key) == new_state:
                return True

            self.rows[row][key] = new_state
            roles = [QtCore.Qt.DisplayRole, QtCore.Qt.CheckStateRole]

            # caso especial 'blk' altera fontes
            if key == "blk":
                roles.append(QtCore.Qt.FontRole)
                self._emit_font_updates(row)

            if key == "nst":
                source_val = self.rows[row].get("_nst_source")
                if source_val is None:
                    manual_flag = bool(self.rows[row].get("_nst_manual_override"))
                else:
                    manual_flag = bool(new_state) != bool(svc_custeio._coerce_checkbox_to_bool(source_val))
                self.rows[row]["_nst_manual_override"] = manual_flag

            logger.debug("CusteioTableModel.setData - row=%s col=%s key=%s new_state=%r", row, col, key, new_state)

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
            if key in {"acabamento_sup", "acabamento_inf"}:
                self._acabamento_info_cache.clear()
                requires_recalc = True

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
        self._acabamento_info_cache.clear()

        self.endResetModel()
        self._mark_dirty(False)



    def load_rows(self, rows: Sequence[Mapping[str, Any]]) -> None:

        self.beginResetModel()

        self.rows = [self._coerce_row_impl(row) for row in rows]
        self._orla_info_cache.clear()
        self._acabamento_info_cache.clear()

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

                coerced[key] = svc_custeio._coerce_checkbox_to_bool(value)

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
            for extra_key in ("_row_type", "_parent_uid", "_group_uid", "_child_source", "_normalized_child", "_qt_manual_override", "_qt_manual_value", "_qt_manual_tooltip", "_qt_formula_value", "_regra_nome", "_nst_manual_override", "_nst_source"):
                if extra_key in row:
                    coerced[extra_key] = row[extra_key]

        coerced["_nst_manual_override"] = bool(coerced.get("_nst_manual_override"))
        if "_nst_source" not in coerced:
            base_nst = coerced.get("nst")
            if base_nst in (None, ""):
                coerced["_nst_source"] = None
            else:
                coerced["_nst_source"] = svc_custeio._coerce_checkbox_to_bool(base_nst)

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

        production_mode = "STD"
        sec_rate_info: Optional[Dict[str, float]] = None
        sec_rate_value: Optional[float] = None
        sec_rate_std: Optional[float] = None
        sec_rate_serie: Optional[float] = None
        orl_rate_info: Optional[Dict[str, float]] = None
        orl_rate_value: Optional[float] = None
        orl_rate_std: Optional[float] = None
        orl_rate_serie: Optional[float] = None
        cnc_low_info: Optional[Dict[str, float]] = None
        cnc_medium_info: Optional[Dict[str, float]] = None
        cnc_high_info: Optional[Dict[str, float]] = None
        cnc_hour_info: Optional[Dict[str, float]] = None
        abd_rate_info: Optional[Dict[str, float]] = None
        prensa_rate_info: Optional[Dict[str, float]] = None
        esquad_rate_info: Optional[Dict[str, float]] = None
        embal_rate_info: Optional[Dict[str, float]] = None
        colagem_rate_info: Optional[Dict[str, float]] = None
        mo_rate_info: Optional[Dict[str, float]] = None
        cnc_rate_low: Optional[float] = None
        cnc_rate_medium: Optional[float] = None
        cnc_rate_high: Optional[float] = None
        cnc_rate_hour: Optional[float] = None
        abd_rate_value: Optional[float] = None
        prensa_rate_value: Optional[float] = None
        esquad_rate_value: Optional[float] = None
        esquad_rate_std: Optional[float] = None
        esquad_rate_serie: Optional[float] = None
        embal_rate_value: Optional[float] = None
        embal_rate_std: Optional[float] = None
        embal_rate_serie: Optional[float] = None
        colagem_rate_value: Optional[float] = None
        colagem_rate_std: Optional[float] = None
        colagem_rate_serie: Optional[float] = None
        mo_rate_value: Optional[float] = None
        mo_rate_std: Optional[float] = None
        mo_rate_serie: Optional[float] = None
        if page_ref is not None and hasattr(page_ref, "production_mode"):
            try:
                production_mode = page_ref.production_mode()
            except Exception:
                production_mode = "STD"
            production_mode = (production_mode or "STD").upper()

            def _float_or_none(value: Optional[float]) -> Optional[float]:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None

            def _select_rate(info: Optional[Dict[str, float]]) -> Optional[float]:
                if not info:
                    return None
                std_val = _float_or_none(info.get("valor_std"))
                serie_val = _float_or_none(info.get("valor_serie"))
                if production_mode == "SERIE":
                    return serie_val if serie_val is not None else std_val
                return std_val if std_val is not None else serie_val

            try:
                sec_rate_info = page_ref.get_production_rate_info("VALOR_SECCIONADORA")
                if sec_rate_info is None:
                    sec_rate_info = page_ref.get_production_rate_info("SEC")
            except Exception:
                sec_rate_info = None
            sec_rate_std = _float_or_none(sec_rate_info.get("valor_std")) if sec_rate_info else None
            sec_rate_serie = _float_or_none(sec_rate_info.get("valor_serie")) if sec_rate_info else None
            sec_rate_value = _select_rate(sec_rate_info)

            try:
                orl_rate_info = page_ref.get_production_rate_info("VALOR_ORLADORA")
                if orl_rate_info is None:
                    orl_rate_info = page_ref.get_production_rate_info("ORL")
            except Exception:
                orl_rate_info = None
            orl_rate_std = _float_or_none(orl_rate_info.get("valor_std")) if orl_rate_info else None
            orl_rate_serie = _float_or_none(orl_rate_info.get("valor_serie")) if orl_rate_info else None
            orl_rate_value = _select_rate(orl_rate_info)

            try:
                cnc_low_info = page_ref.get_production_rate_info("CNC_PRECO_PECA_BAIXO")
            except Exception:
                cnc_low_info = None
            try:
                cnc_medium_info = page_ref.get_production_rate_info("CNC_PRECO_PECA_MEDIO")
            except Exception:
                cnc_medium_info = None
            try:
                cnc_high_info = page_ref.get_production_rate_info("CNC_PRECO_PECA_ALTO")
            except Exception:
                cnc_high_info = None
            try:
                cnc_hour_info = page_ref.get_production_rate_info("EUROS_HORA_CNC")
            except Exception:
                cnc_hour_info = None
            try:
                abd_rate_info = page_ref.get_production_rate_info("VALOR_ABD")
            except Exception:
                abd_rate_info = None
            try:
                prensa_rate_info = page_ref.get_production_rate_info("EUROS_HORA_PRENSA")
            except Exception:
                prensa_rate_info = None
            try:
                esquad_rate_info = page_ref.get_production_rate_info("EUROS_HORA_ESQUAD")
            except Exception:
                esquad_rate_info = None
            try:
                embal_rate_info = page_ref.get_production_rate_info("EUROS_EMBALAGEM_M3")
            except Exception:
                embal_rate_info = None
            try:
                colagem_rate_info = page_ref.get_production_rate_info("COLAGEM/REVESTIMENTO")
            except Exception:
                colagem_rate_info = None
            try:
                mo_rate_info = page_ref.get_production_rate_info("EUROS_HORA_MO")
            except Exception:
                mo_rate_info = None

            cnc_rate_low = _select_rate(cnc_low_info)
            cnc_rate_medium = _select_rate(cnc_medium_info)
            cnc_rate_high = _select_rate(cnc_high_info)
            cnc_rate_hour = _select_rate(cnc_hour_info)
            abd_rate_value = _select_rate(abd_rate_info)
            prensa_rate_value = _select_rate(prensa_rate_info)
            esquad_rate_value = _select_rate(esquad_rate_info)
            if esquad_rate_info:
                esquad_rate_std = _float_or_none(esquad_rate_info.get("valor_std"))
                esquad_rate_serie = _float_or_none(esquad_rate_info.get("valor_serie"))
            embal_rate_value = _select_rate(embal_rate_info)
            if embal_rate_info:
                embal_rate_std = _float_or_none(embal_rate_info.get("valor_std"))
                embal_rate_serie = _float_or_none(embal_rate_info.get("valor_serie"))
            colagem_rate_value = _select_rate(colagem_rate_info)
            if colagem_rate_info:
                colagem_rate_std = _float_or_none(colagem_rate_info.get("valor_std"))
                colagem_rate_serie = _float_or_none(colagem_rate_info.get("valor_serie"))
            mo_rate_value = _select_rate(mo_rate_info)
            if mo_rate_info:
                mo_rate_std = _float_or_none(mo_rate_info.get("valor_std"))
                mo_rate_serie = _float_or_none(mo_rate_info.get("valor_serie"))


        divisor = 1.0

        current_group_uid = str(uuid.uuid4())

        current_parent_row: Optional[Dict[str, Any]] = None
        current_parent_uid: Optional[str] = None
        current_parent_child_tokens: List[str] = []
        current_parent_has_explicit_children = False

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

        production_cost_changed = False

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
            normalized_def_peca = self._normalize_def_peca(def_peca)

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
                current_parent_child_tokens = []
                current_parent_has_explicit_children = False

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
                current_parent_child_tokens = []
                current_parent_has_explicit_children = False

            elif "+" in def_peca:

                row["_row_type"] = "parent"
                row["_is_parent"] = True

                current_group_uid = row.get("_group_uid") or str(uuid.uuid4())

                row["_group_uid"] = current_group_uid

                current_parent_row = row

                current_parent_uid = row["_uid"]

                row["_regra_nome"] = None
                current_parent_child_tokens = self._extract_child_tokens(def_peca)
                current_parent_has_explicit_children = bool(current_parent_child_tokens)

            else:

                regra_nome = svc_custeio.identificar_regra(def_peca, rules)
                attach_to_parent = False
                if regra_nome and current_parent_row is not None:
                    if current_parent_has_explicit_children:
                        attach_to_parent = self._match_expected_child(
                            normalized_def_peca,
                            current_parent_child_tokens,
                        )
                    else:
                        attach_to_parent = True

                if attach_to_parent:

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
                    current_parent_child_tokens = []
                    current_parent_has_explicit_children = False

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

            def_peca_value = (row.get("def_peca") or "").strip()
            def_peca_norm = def_peca_value.casefold()

            manual_cnc_override = None
            if def_peca_norm == DEF_LABEL_CNC_5_MIN_NORM:
                qt_und_manual = self._coerce_numeric(row.get("qt_und"))
                if qt_und_manual not in (None, 0):
                    manual_cnc_override = qt_und_manual * 5.0
            elif def_peca_norm == DEF_LABEL_CNC_15_MIN_NORM:
                qt_und_manual = self._coerce_numeric(row.get("qt_und"))
                if qt_und_manual not in (None, 0):
                    manual_cnc_override = qt_und_manual * 15.0
            if manual_cnc_override is not None:
                row["qt_total"] = manual_cnc_override

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

            # HeranÃ§a de comprimento para VARAO e componentes ML mesmo quando nÃ£o sÃ£o marcados como 'child'
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

                # HeranÃ§a de comprimento para VARAO e componentes ML (skip supports)
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

                if current_parent_has_explicit_children and not current_parent_child_tokens:
                    current_parent_row = None
                    current_parent_uid = None
                    current_parent_has_explicit_children = False

            else:

                row["_qt_rule_tooltip"] = None

                # Para linhas do tipo 'parent' nÃ£o tratamos qt_und como factor filho
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

            # Atualizar mÃ©tricas derivadas (Ã¡rea e perÃ­metro por unidade)
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
            spp_precise_value: Optional[float] = None
            custo_mp_und_value: Optional[float] = None
            custo_mp_total_value: Optional[float] = None
            mp_tooltip: Optional[str] = None
            mp_total_tooltip: Optional[str] = None
            qt_total_numeric = self._coerce_numeric(row.get("qt_total"))

            mps_checked = self._coerce_checked(row.get("mps"))
            mo_checked = self._coerce_checked(row.get("mo"))
            orla_checked = self._coerce_checked(row.get("orla"))

            if self._is_spp_row(row):
                if comp_float is not None:
                    comp_m_val = comp_float / 1000.0
                    spp_precise_value = comp_m_val * (1.0 + SPP_WASTE_PERCENT)
                    row["spp_ml_und"] = round(spp_precise_value, 2)
                    row["_spp_ml_und_tooltip"] = (
                        "SPP calculado com desperdicio padrao\n"
                        f"COMP_res: {comp_float:.2f} mm -> {comp_m_val:.4f} ML\n"
                        f"Desp_SPP: {SPP_WASTE_PERCENT * 100:.2f}% (fator {1.0 + SPP_WASTE_PERCENT:.3f})\n"
                        f"Calculo: {comp_m_val:.4f} ML * (1 + {SPP_WASTE_PERCENT * 100:.2f}%) = {spp_precise_value:.4f} ML"
                    )
                else:
                    row["spp_ml_und"] = None
                    row["_spp_ml_und_tooltip"] = "Dimensoes insuficientes para calcular ML"
            else:
                row["spp_ml_und"] = None
                row["_spp_ml_und_tooltip"] = None

            if mps_checked:
                custo_mp_und_value = 0.0
                row["custo_mp_und"] = 0.0
                mp_tooltip = "CUSTO_MP_und = 0 € (checkbox MPs ativo)."
            elif row_type not in {"division", "separator"}:
                pliq_value = self._coerce_numeric(row.get("pliq"))
                desp_fraction = self._coerce_percent(row.get("desp"))
                if desp_fraction is None:
                    desp_fraction = DEFAULT_MP_DESP_FRACTION
                fator_desp = 1.0 + max(desp_fraction, 0.0)
                und_text = (row.get("und") or "").strip().upper()
                base_value: Optional[float] = None
                base_label: Optional[str] = None
                if und_text == "M2" and area_val not in (None, 0):
                    base_value = area_val
                    base_label = "AREA_M2_und"
                elif und_text == "ML" and spp_precise_value not in (None, 0):
                    base_value = spp_precise_value
                    base_label = "SPP_ML_und"
                elif und_text == "UND":
                    base_value = 1.0
                    base_label = "UND"

                if base_value is not None and pliq_value not in (None, 0):
                    custo_mp_und_value = round(base_value * fator_desp * pliq_value, 2)
                    row["custo_mp_und"] = custo_mp_und_value
                    desp_percent = desp_fraction * 100.0
                    base_desc = (
                        f"{base_label}: {base_value:.4f} {'m2' if base_label == 'AREA_M2_und' else ('ML' if base_label == 'SPP_ML_und' else 'und')}"
                    )
                    mp_tooltip = "\n".join(
                        [
                            "Custo Materias Primas (por unidade)",
                            f"Und: {und_text or '-'}",
                            base_desc,
                            f"PliQ: {pliq_value:.2f} €",
                            f"Desperdicio: {desp_percent:.2f}% (fator {fator_desp:.3f})",
                            f"Calculo: {base_value:.4f} x (1 + {desp_percent:.2f}%) x {pliq_value:.2f} € = {custo_mp_und_value:.2f} €",
                        ]
                    )
                else:
                    row["custo_mp_und"] = None
                    if pliq_value in (None, 0):
                        mp_tooltip = "CUSTO_MP_und indisponivel: PliQ sem valor."
                    elif base_label is None:
                        mp_tooltip = "CUSTO_MP_und indisponivel: dimensoes/und sem base valida."
                    else:
                        mp_tooltip = "CUSTO_MP_und indisponivel."
            else:
                row["custo_mp_und"] = None

            if mps_checked:
                custo_mp_total_value = 0.0
                row["custo_mp_total"] = 0.0
                mp_total_tooltip = "CUSTO_MP_Total = 0 € (checkbox MPs ativo)."
            elif (
                custo_mp_und_value is not None
                and qt_total_numeric not in (None, 0)
            ):
                custo_mp_total_value = round(custo_mp_und_value * qt_total_numeric, 2)
                row["custo_mp_total"] = custo_mp_total_value
                mp_total_tooltip = "\n".join(
                    [
                        "Custo Materias Primas (total)",
                        f"CUSTO_MP_und: {custo_mp_und_value:.2f} €",
                        f"Qt_Total: {qt_total_numeric:.2f}",
                        f"Calculo: {custo_mp_und_value:.2f} € * {qt_total_numeric:.2f} = {custo_mp_total_value:.2f} €",
                    ]
                )
            elif row_type in {"division", "separator"}:
                row["custo_mp_total"] = None
                mp_total_tooltip = None
            else:
                row["custo_mp_total"] = None
                if custo_mp_und_value is None:
                    mp_total_tooltip = "CUSTO_MP_Total depende do valor unitario."
                elif qt_total_numeric in (None, 0):
                    mp_total_tooltip = "CUSTO_MP_Total indisponivel: Qt_Total sem valor."
                else:
                    mp_total_tooltip = None
            row["_custo_mp_und_tooltip"] = mp_tooltip
            row["_custo_mp_total_tooltip"] = mp_total_tooltip

            cp_prev_val = self._coerce_numeric(row.get("cp01_sec_und"))
            cp_factor = self._coerce_numeric(row.get("cp01_sec"))
            perimetro_calc = perimetro_val if perimetro_val is not None else self._coerce_numeric(row.get("perimetro_und"))
            tooltip_text: Optional[str] = None
            new_cp_value: Optional[float] = None
            if (
                row_type not in {"division", "separator"}
                and sec_rate_value is not None
                and cp_factor is not None
                and cp_factor > 0
                and perimetro_calc is not None
            ):
                try:
                    new_cp_value = round(cp_factor * perimetro_calc * sec_rate_value, 2)
                except Exception:
                    new_cp_value = None
                if new_cp_value is not None:
                    tooltip_lines = [
                        f"Modo: {production_mode}",
                        f"CP01_SEC: {cp_factor:.2f}",
                        f"Perimetro_und: {perimetro_calc:.2f} ML",
                        f"Tarifa {production_mode}: {sec_rate_value:.4f} \u20AC/ML",
                        f"Calculo: {cp_factor:.2f} x {perimetro_calc:.2f} x {sec_rate_value:.4f} = {new_cp_value:.2f} \u20AC",
                    ]
                    if sec_rate_std is not None and sec_rate_serie is not None:
                        tooltip_lines.append(
                            f"STD: {sec_rate_std:.4f} \u20AC/ML | SERIE: {sec_rate_serie:.4f} \u20AC/ML"
                        )
                    tooltip_text = "\n".join(tooltip_lines)
            else:
                new_cp_value = None

            if new_cp_value is None:
                if cp_prev_val is not None:
                    production_cost_changed = True
                row["cp01_sec_und"] = None
            else:
                if cp_prev_val is None or not _float_almost_equal(cp_prev_val, new_cp_value, tol=1e-4):
                    production_cost_changed = True
                row["cp01_sec_und"] = new_cp_value
            row["_cp01_sec_und_tooltip"] = tooltip_text

            cp02_prev_val = self._coerce_numeric(row.get("cp02_orl_und"))
            cp02_factor = self._coerce_numeric(row.get("cp02_orl"))
            soma_ml_total = self._coerce_numeric(row.get("soma_total_ml_orla"))
            qt_total_val = self._coerce_numeric(row.get("qt_total"))
            tooltip_cp02: Optional[str] = None
            cp02_new_value: Optional[float] = None
            ml_per_piece: Optional[float] = None
            if (
                soma_ml_total is not None
                and qt_total_val is not None
                and qt_total_val > 0
            ):
                try:
                    ml_per_piece = float(soma_ml_total) / float(qt_total_val)
                except Exception:
                    ml_per_piece = None
            if (
                row_type not in {"division", "separator"}
                and orl_rate_value is not None
                and cp02_factor is not None
                and cp02_factor > 0
                and ml_per_piece is not None
            ):
                try:
                    cp02_new_value = round(cp02_factor * ml_per_piece * orl_rate_value, 2)
                except Exception:
                    cp02_new_value = None
                if cp02_new_value is not None:
                    tooltip_lines_cp02 = [
                        f"Modo: {production_mode}",
                        f"CP02_ORL: {cp02_factor:.2f}",
                        f"SOMA_TOTAL_ML_ORLA: {(soma_ml_total or 0):.2f} ML",
                        f"QT_total: {(qt_total_val or 0):.2f}",
                        f"ML por unidade: {ml_per_piece:.4f} ML",
                        f"Tarifa {production_mode}: {orl_rate_value:.4f} \u20AC/ML",
                        f"Calculo: {cp02_factor:.2f} x {ml_per_piece:.4f} x {orl_rate_value:.4f} = {cp02_new_value:.2f} \u20AC",
                    ]
                    if orl_rate_std is not None and orl_rate_serie is not None:
                        tooltip_lines_cp02.append(
                            f"STD: {orl_rate_std:.4f} \u20AC/ML | SERIE: {orl_rate_serie:.4f} \u20AC/ML"
                        )
                    tooltip_cp02 = "\n".join(tooltip_lines_cp02)
            else:
                cp02_new_value = None

            if cp02_new_value is None:
                if cp02_prev_val is not None:
                    production_cost_changed = True
                row["cp02_orl_und"] = None
            else:
                if cp02_prev_val is None or not _float_almost_equal(cp02_prev_val, cp02_new_value, tol=1e-4):
                    production_cost_changed = True
                row["cp02_orl_und"] = cp02_new_value
            row["_cp02_orl_und_tooltip"] = tooltip_cp02

            cp03_prev_val = self._coerce_numeric(row.get("cp03_cnc_und"))
            cp03_factor = self._coerce_numeric(row.get("cp03_cnc"))
            tooltip_cp03: Optional[str] = None
            cp03_new_value: Optional[float] = None
            manual_cnc_applied = False
            # For manual CNC service pieces, compute per-unit minutes from `qt_und` (e.g. 5,15)
            # and compute cp03_cnc_und as cost per unit (minutes_per_unit * rate_per_minute).
            minutes_per_unit: Optional[float] = None
            if def_peca_norm in MANUAL_CNC_LABELS:
                minutes_per_unit = self._coerce_numeric(row.get("qt_und")) or 1.0
            if (
                minutes_per_unit not in (None, 0)
                and cnc_rate_hour not in (None, 0)
                and row_type not in {"division", "separator"}
                and def_peca_norm in MANUAL_CNC_LABELS
            ):
                try:
                    rate_hour_val = float(cnc_rate_hour)
                    per_minute = rate_hour_val / 60.0
                    # cp03_cnc_und must represent the price PER MINUTE (not per-unit). Totais usam qt_total.
                    cp03_new_value = round(per_minute, 4)
                except Exception:
                    cp03_new_value = None
                if cp03_new_value is not None:
                    tooltip_lines_cp03 = [
                        f"Modo: {production_mode}",
                        f"Tarifa EUROS_HORA_CNC: {rate_hour_val:.4f} €/hora",
                        f"Calculo (por minuto): ({rate_hour_val:.4f} €/hora / 60) = {cp03_new_value:.4f} €/min",
                        f"Observacao: Qt_total acumula minutos totais; cp03_cnc_und e' preco por minuto.",
                    ]
                    tooltip_cp03 = "\n".join(tooltip_lines_cp03)
                    manual_cnc_applied = True
            if (
                not manual_cnc_applied
                and row_type not in {"division", "separator"}
                and cp03_factor is not None
                and cp03_factor > 0
                and cp02_factor is not None
                and cp02_factor > 0
            ):
                familia_val = (row.get("familia") or "").strip().upper()
                is_ferragens = familia_val == "FERRAGENS"
                if is_ferragens and cnc_rate_hour not in (None, 0):
                    try:
                        rate_hour_val = float(cnc_rate_hour)
                        per_minute = rate_hour_val / 60.0
                        cp03_new_value = round(cp03_factor * per_minute, 2)
                    except Exception:
                        cp03_new_value = None
                    if cp03_new_value is not None:
                        tooltip_lines_cp03 = [
                            f"Modo: {production_mode}",
                            f"CP03_CNC: {cp03_factor:.2f}",
                            f"Tarifa EUROS_HORA_CNC: {rate_hour_val:.4f} €/hora",
                            f"Calculo: {cp03_factor:.2f} x ({rate_hour_val:.4f} €/hora / 60) = {cp03_new_value:.2f} €",
                        ]
                        tooltip_cp03 = "\n".join(tooltip_lines_cp03)
                else:
                    area_unit = self._coerce_numeric(row.get("area_m2_und"))
                    if area_unit is not None and area_unit >= 0:
                        rate_value: Optional[float] = None
                        categoria = ""
                        if area_unit < 0.7:
                            rate_value = cnc_rate_low
                            categoria = "CNC_PRECO_PECA_BAIXO"
                        elif area_unit < 1.0:
                            rate_value = cnc_rate_medium
                            categoria = "CNC_PRECO_PECA_MEDIO"
                        else:
                            rate_value = cnc_rate_high
                            categoria = "CNC_PRECO_PECA_ALTO"
                        if rate_value is not None:
                            try:
                                rate_peca = float(rate_value)
                                cp03_new_value = round(cp03_factor * rate_peca, 2)
                            except Exception:
                                cp03_new_value = None
                            if cp03_new_value is not None:
                                tooltip_lines_cp03 = [
                                    f"Modo: {production_mode}",
                                    f"CP03_CNC: {cp03_factor:.2f}",
                                    f"AREA_M2_und: {area_unit:.4f} m2",
                                    f"Tarifa {categoria}: {rate_peca:.4f} €/peca",
                                    f"Calculo: {cp03_factor:.2f} x {rate_peca:.4f} = {cp03_new_value:.2f} €",
                                    f"Criterio de selecao: AREA_M2_und = {area_unit:.4f} m2",
                                ]
                                tooltip_cp03 = "\n".join(tooltip_lines_cp03)
            if cp03_new_value is None:
                if cp03_prev_val is not None:
                    production_cost_changed = True
                row["cp03_cnc_und"] = None
            else:
                if cp03_prev_val is None or not _float_almost_equal(cp03_prev_val, cp03_new_value, tol=1e-4):
                    production_cost_changed = True
                row["cp03_cnc_und"] = cp03_new_value
            row["_cp03_cnc_und_tooltip"] = tooltip_cp03

            cp04_prev_val = self._coerce_numeric(row.get("cp04_abd_und"))
            cp04_factor = self._coerce_numeric(row.get("cp04_abd"))
            tooltip_cp04: Optional[str] = None
            cp04_new_value: Optional[float] = None
            if (
                row_type not in {"division", "separator"}
                and cp04_factor is not None
                and cp04_factor > 0
                and abd_rate_value not in (None, 0)
            ):
                try:
                    rate_abd = float(abd_rate_value)
                    cp04_new_value = round(cp04_factor * rate_abd, 2)
                except Exception:
                    cp04_new_value = None
                if cp04_new_value is not None:
                    tooltip_lines_cp04 = [
                        f"Modo: {production_mode}",
                        f"CP04_ABD: {cp04_factor:.2f}",
                        f"Tarifa VALOR_ABD: {rate_abd:.4f} €",
                        f"Calculo: {cp04_factor:.2f} x {rate_abd:.4f} = {cp04_new_value:.2f} €",
                    ]
                    tooltip_cp04 = "\n".join(tooltip_lines_cp04)
            if cp04_new_value is None:
                if cp04_prev_val is not None:
                    production_cost_changed = True
                row["cp04_abd_und"] = None
            else:
                if cp04_prev_val is None or not _float_almost_equal(cp04_prev_val, cp04_new_value, tol=1e-4):
                    production_cost_changed = True
                row["cp04_abd_und"] = cp04_new_value
            row["_cp04_abd_und_tooltip"] = tooltip_cp04

            cp05_prev_val = self._coerce_numeric(row.get("cp05_prensa_und"))
            cp05_factor = self._coerce_numeric(row.get("cp05_prensa"))
            tooltip_cp05: Optional[str] = None
            cp05_new_value: Optional[float] = None
            area_for_prensa = self._coerce_numeric(row.get("area_m2_und"))
            if (
                row_type not in {"division", "separator"}
                and cp05_factor is not None
                and cp05_factor > 0
                and area_for_prensa is not None
                and area_for_prensa > 0
                and prensa_rate_value not in (None, 0)
            ):
                try:
                    rate_prensa = float(prensa_rate_value)
                    cp05_new_value = round(cp05_factor * area_for_prensa * rate_prensa, 2)
                except Exception:
                    cp05_new_value = None
                if cp05_new_value is not None:
                    tooltip_lines_cp05 = [
                        f"Modo: {production_mode}",
                        f"CP05_PRENSA: {cp05_factor:.2f}",
                        f"AREA_M2_und: {area_for_prensa:.4f} m2",
                        f"Tarifa EUROS_HORA_PRENSA: {rate_prensa:.4f} €",
                        f"Calculo: {cp05_factor:.2f} x {area_for_prensa:.4f} x {rate_prensa:.4f} = {cp05_new_value:.2f} €",
                    ]
                    tooltip_cp05 = "\n".join(tooltip_lines_cp05)
            if cp05_new_value is None:
                if cp05_prev_val is not None:
                    production_cost_changed = True
                row["cp05_prensa_und"] = None
                if tooltip_cp05 is None and cp05_factor not in (None, 0):
                    tooltip_cp05 = "Area ou tarifa nao disponivel para calcular PRENSA"
            else:
                if cp05_prev_val is None or not _float_almost_equal(cp05_prev_val, cp05_new_value, tol=1e-4):
                    production_cost_changed = True
                row["cp05_prensa_und"] = cp05_new_value
            row["_cp05_prensa_und_tooltip"] = tooltip_cp05

            cp06_prev_val = self._coerce_numeric(row.get("cp06_esquad_und"))
            cp06_factor = self._coerce_numeric(row.get("cp06_esquad"))
            tooltip_cp06: Optional[str] = None
            cp06_new_value: Optional[float] = None
            rate_esquad: Optional[float] = None
            if (
                row_type not in {"division", "separator"}
                and cp06_factor is not None
                and cp06_factor > 0
                and esquad_rate_value not in (None, 0)
            ):
                try:
                    rate_esquad = float(esquad_rate_value)
                    cp06_new_value = round(cp06_factor * (rate_esquad / 60.0), 2)
                except Exception:
                    cp06_new_value = None
                if cp06_new_value is not None and rate_esquad is not None:
                    tooltip_lines_cp06 = [
                        f"Modo: {production_mode}",
                        f"CP06_ESQUAD: {cp06_factor:.2f}",
                        f"Tarifa EUROS_HORA_ESQUAD: {rate_esquad:.4f} €/hora",
                        f"Calculo: {cp06_factor:.2f} x ({rate_esquad:.4f} €/hora / 60) = {cp06_new_value:.2f} €",
                    ]
                    if esquad_rate_std is not None and esquad_rate_serie is not None:
                        tooltip_lines_cp06.append(
                            f"STD: {esquad_rate_std:.4f} €/hora | SERIE: {esquad_rate_serie:.4f} €/hora"
                        )
                    tooltip_cp06 = "\n".join(tooltip_lines_cp06)
            if cp06_new_value is None:
                if cp06_prev_val is not None:
                    production_cost_changed = True
                row["cp06_esquad_und"] = None
                if tooltip_cp06 is None and cp06_factor not in (None, 0):
                    tooltip_cp06 = "Tarifa nao disponivel para calcular ESQUADREJADORA"
            else:
                if cp06_prev_val is None or not _float_almost_equal(cp06_prev_val, cp06_new_value, tol=1e-4):
                    production_cost_changed = True
                row["cp06_esquad_und"] = cp06_new_value
            row["_cp06_esquad_und_tooltip"] = tooltip_cp06

            cp07_prev_val = self._coerce_numeric(row.get("cp07_embalagem_und"))
            cp07_factor = self._coerce_numeric(row.get("cp07_embalagem"))
            tooltip_cp07: Optional[str] = None
            cp07_new_value: Optional[float] = None
            qt_total_calc = self._coerce_numeric(row.get("qt_total"))
            comp_res = self._coerce_numeric(row.get("comp_res"))
            larg_res = self._coerce_numeric(row.get("larg_res"))
            esp_res = self._coerce_numeric(row.get("esp_res"))
            volume_m3: Optional[float] = None
            has_dimensions = (
                qt_total_calc not in (None, 0)
                and comp_res not in (None, 0)
                and larg_res not in (None, 0)
                and esp_res not in (None, 0)
            )
            manual_embalagem_applied = False
            if (
                def_peca_norm == DEF_LABEL_EMBALAGEM_NORM
                and row_type not in {"division", "separator"}
                and has_dimensions
                and embal_rate_value not in (None, 0)
            ):
                try:
                    rate_embal = float(embal_rate_value)
                    # Calculate volume per unit (m3) — do NOT multiply by qt_total here.
                    volume_unit_m3 = (
                        float(comp_res)
                        * float(larg_res)
                        * float(esp_res)
                    ) / 1_000_000_000.0
                    cp07_new_value = round(volume_unit_m3 * rate_embal, 2)
                except Exception:
                    cp07_new_value = None
                if cp07_new_value is not None and volume_unit_m3 is not None:
                    tooltip_lines_cp07 = [
                        f"Modo: {production_mode}",
                        f"Qt_total: {qt_total_calc:.2f}",
                        f"Dimensoes por unidade (mm): {comp_res:.2f} x {larg_res:.2f} x {esp_res:.2f}",
                        f"Volume por unidade: {volume_unit_m3:.6f} m\u00B3",
                        f"Tarifa EUROS_EMBALAGEM_M3: {rate_embal:.4f} \u20AC/m\u00B3",
                        f"Calculo (por unidade): ({comp_res:.2f} x {larg_res:.2f} x {esp_res:.2f} mm / 1e9) x {rate_embal:.4f} \u20AC/m\u00B3 = {cp07_new_value:.2f} \u20AC",
                    ]
                    if embal_rate_std is not None and embal_rate_serie is not None:
                        tooltip_lines_cp07.append(
                            f"STD: {embal_rate_std:.4f} \u20AC/m\u00B3 | SERIE: {embal_rate_serie:.4f} \u20AC/m\u00B3"
                        )
                    tooltip_cp07 = "\n".join(tooltip_lines_cp07)
                    manual_embalagem_applied = True
            if (
                not manual_embalagem_applied
                and row_type not in {"division", "separator"}
                and cp07_factor is not None
                and cp07_factor > 0
                and has_dimensions
                and embal_rate_value not in (None, 0)
            ):
                try:
                    rate_embal = float(embal_rate_value)
                    volume_m3 = (
                        float(qt_total_calc)
                        * float(comp_res)
                        * float(larg_res)
                        * float(esp_res)
                    ) / 1_000_000_000.0
                    cp07_new_value = round(cp07_factor * volume_m3 * rate_embal, 2)
                except Exception:
                    cp07_new_value = None
                if cp07_new_value is not None and volume_m3 is not None:
                    tooltip_lines_cp07 = [
                        f"Modo: {production_mode}",
                        f"CP07_EMBALAGEM: {cp07_factor:.2f}",
                    ]
                    tooltip_lines_cp07.append(
                        "Dimensoes (mm): "
                        f"Qt_total {qt_total_calc:.2f} x {comp_res:.2f} x {larg_res:.2f} x {esp_res:.2f}"
                    )
                    tooltip_lines_cp07.append(
                        f"Volume total: {volume_m3:.6f} m\u00B3"
                    )
                    tooltip_lines_cp07.append(
                        f"Tarifa EUROS_EMBALAGEM_M3: {rate_embal:.4f} \u20AC/m\u00B3"
                    )
                    tooltip_lines_cp07.append(
                        f"Calculo: {cp07_factor:.2f} x {volume_m3:.6f} m\u00B3 x {rate_embal:.4f} \u20AC/m\u00B3 = {cp07_new_value:.2f} \u20AC"
                    )
                    if embal_rate_std is not None and embal_rate_serie is not None:
                        tooltip_lines_cp07.append(
                            f"STD: {embal_rate_std:.4f} \u20AC/m\u00B3 | SERIE: {embal_rate_serie:.4f} \u20AC/m\u00B3"
                        )
                    tooltip_cp07 = "\n".join(tooltip_lines_cp07)
            if cp07_new_value is None:
                if cp07_prev_val is not None:
                    production_cost_changed = True
                row["cp07_embalagem_und"] = None
                if tooltip_cp07 is None and cp07_factor not in (None, 0):
                    tooltip_cp07 = "Volume ou tarifa nao disponivel para calcular EMBALAGEM"
            else:
                if cp07_prev_val is None or not _float_almost_equal(cp07_prev_val, cp07_new_value, tol=1e-4):
                    production_cost_changed = True
                row["cp07_embalagem_und"] = cp07_new_value
            row["_cp07_embalagem_und_tooltip"] = tooltip_cp07

            cp08_prev_val = self._coerce_numeric(row.get("cp08_mao_de_obra_und"))
            cp08_factor = self._coerce_numeric(row.get("cp08_mao_de_obra"))
            tooltip_cp08: Optional[str] = None
            cp08_new_value: Optional[float] = None
            rate_mo: Optional[float] = None
            manual_mo_applied = False
            if (
                def_peca_norm == DEF_LABEL_MAO_OBRA_MIN_NORM
                and row_type not in {"division", "separator"}
                and mo_rate_value not in (None, 0)
            ):
                try:
                    rate_mo = float(mo_rate_value)
                    per_minute_mo = rate_mo / 60.0
                    # cp08_mao_de_obra_und = (€/min) × cp08_mao_de_obra (factor)
                    if cp08_factor is not None and cp08_factor > 0:
                        cp08_new_value = round(per_minute_mo * cp08_factor, 4)
                    else:
                        cp08_new_value = round(per_minute_mo, 4)
                except Exception:
                    cp08_new_value = None
                if cp08_new_value is not None and rate_mo is not None:
                    tooltip_lines_cp08 = [
                        f"Modo: {production_mode}",
                        f"Tarifa EUROS_HORA_MO: {rate_mo:.4f} \u20AC/hora",
                    ]
                    if cp08_factor is not None and cp08_factor > 0:
                        tooltip_lines_cp08.append(
                            f"Calculo: ({rate_mo:.4f} \u20AC/h / 60) × {cp08_factor} = {cp08_new_value:.4f} \u20AC"
                        )
                    else:
                        tooltip_lines_cp08.append(
                            f"Calculo (por minuto): ({rate_mo:.4f} \u20AC/h / 60) = {cp08_new_value:.4f} \u20AC/min"
                        )
                    if mo_rate_std is not None and mo_rate_serie is not None:
                        tooltip_lines_cp08.append(
                            f"STD: {mo_rate_std:.4f} \u20AC/hora | SERIE: {mo_rate_serie:.4f} \u20AC/hora"
                        )
                    tooltip_cp08 = "\n".join(tooltip_lines_cp08)
                    manual_mo_applied = True
            if (
                not manual_mo_applied
                and row_type not in {"division", "separator"}
                and cp08_factor is not None
                and cp08_factor > 0
                and mo_rate_value not in (None, 0)
            ):
                try:
                    rate_mo = float(mo_rate_value)
                    per_minute_mo = rate_mo / 60.0
                    # cp08_mao_de_obra_und = (€/min) × cp08_mao_de_obra (factor)
                    cp08_new_value = round(per_minute_mo * cp08_factor, 4)
                except Exception:
                    cp08_new_value = None
                if cp08_new_value is not None and rate_mo is not None:
                    tooltip_lines_cp08 = [
                        f"Modo: {production_mode}",
                        f"Tarifa EUROS_HORA_MO: {rate_mo:.4f} \u20AC/hora",
                        f"CP08_MAO_DE_OBRA factor: {cp08_factor}",
                        f"Calculo: ({rate_mo:.4f} \u20AC/h / 60) × {cp08_factor} = {cp08_new_value:.4f} \u20AC",
                    ]
                    if mo_rate_std is not None and mo_rate_serie is not None:
                        tooltip_lines_cp08.append(
                            f"STD: {mo_rate_std:.4f} \u20AC/hora | SERIE: {mo_rate_serie:.4f} \u20AC/hora"
                        )
                    tooltip_cp08 = "\n".join(tooltip_lines_cp08)
            if cp08_new_value is None:
                if cp08_prev_val is not None:
                    production_cost_changed = True
                row["cp08_mao_de_obra_und"] = None
                if tooltip_cp08 is None and cp08_factor not in (None, 0):
                    tooltip_cp08 = "Tarifa nao disponivel para calcular MAO DE OBRA"
            else:
                if cp08_prev_val is None or not _float_almost_equal(cp08_prev_val, cp08_new_value, tol=1e-4):
                    production_cost_changed = True
                row["cp08_mao_de_obra_und"] = cp08_new_value
            row["_cp08_mao_de_obra_und_tooltip"] = tooltip_cp08

            cp09_prev_val = self._coerce_numeric(row.get("cp09_colagem_und"))
            tooltip_cp09: Optional[str] = None
            cp09_new_value: Optional[float] = None
            if (
                def_peca_norm == DEF_LABEL_COLAGEM_NORM
                and row_type not in {"division", "separator"}
                and comp_res not in (None, 0)
                and larg_res not in (None, 0)
                and colagem_rate_value not in (None, 0)
            ):
                try:
                    rate_colagem = float(colagem_rate_value)
                    # calc area per unit (m2) and store cp09 as cost PER UNIT
                    area_m2 = (float(comp_res) * float(larg_res)) / 1_000_000.0
                    cp09_unit = round(area_m2 * rate_colagem, 4)
                    cp09_new_value = round(cp09_unit, 4)
                except Exception:
                    cp09_new_value = None
                if cp09_new_value is not None:
                    total_area_example = None
                    try:
                        total_area_example = area_m2 * float(qt_total_calc) if qt_total_calc not in (None, 0) else None
                    except Exception:
                        total_area_example = None
                    tooltip_lines_cp09 = [
                        f"Modo: {production_mode}",
                        f"Dimensoes por unidade (mm): {comp_res:.2f} x {larg_res:.2f}",
                        f"Area por unidade: {area_m2:.6f} m\u00B2",
                        f"Tarifa COLAGEM/REVESTIMENTO: {rate_colagem:.4f} \u20AC/m\u00B2",
                        f"Calculo (por unidade): ({comp_res:.2f} x {larg_res:.2f} mm / 1e6) x {rate_colagem:.4f} = {cp09_new_value:.4f} \u20AC/und",
                    ]
                    if total_area_example is not None:
                        tooltip_lines_cp09.insert(2, f"Qt_total (exemplo): {qt_total_calc:.2f} -> Area total: {total_area_example:.6f} m\u00B2")
                    if colagem_rate_std is not None and colagem_rate_serie is not None:
                        tooltip_lines_cp09.append(
                            f"STD: {colagem_rate_std:.4f} \u20AC/m\u00B2 | SERIE: {colagem_rate_serie:.4f} \u20AC/m\u00B2"
                        )
                    tooltip_cp09 = "\n".join(tooltip_lines_cp09)
            if cp09_new_value is None:
                if cp09_prev_val is not None:
                    production_cost_changed = True
                row["cp09_colagem_und"] = None
            else:
                if cp09_prev_val is None or not _float_almost_equal(cp09_prev_val, cp09_new_value, tol=1e-4):
                    production_cost_changed = True
                row["cp09_colagem_und"] = cp09_new_value
            row["_cp09_colagem_und_tooltip"] = tooltip_cp09

            if row_type not in {"division", "separator"}:
                cp_cost_pairs: List[Tuple[str, float]] = []
                soma_custo_und_float = 0.0
                for key, label in PRODUCTION_CP_SUM_KEYS:
                    cp_value = self._coerce_numeric(row.get(key)) or 0.0
                    cp_cost_pairs.append((label, cp_value))
                    soma_custo_und_float += cp_value
                base_soma_value = round(soma_custo_und_float, 2)
                soma_custo_und_value = 0.0 if mo_checked else base_soma_value
                row["soma_custo_und"] = soma_custo_und_value
                soma_lines = ["SOMA_CUSTO_und = CP01_SEC_und + ... + CP08_MAO_DE_OBRA_und"]
                soma_lines.extend(f"{label}: {value:.2f} €" for label, value in cp_cost_pairs)
                if mo_checked:
                    soma_lines.append("Resultado: 0.00 € (checkbox MO ativo)")
                else:
                    soma_lines.append(f"Resultado: {soma_custo_und_value:.2f} €")
                row["_soma_custo_und_tooltip"] = "\n".join(soma_lines)

                if qt_total_numeric not in (None, 0) and not mo_checked:
                    maquinas_total_value: Optional[float] = round(soma_custo_und_value * qt_total_numeric, 2)
                elif mo_checked:
                    maquinas_total_value = 0.0
                else:
                    maquinas_total_value = None

                custo_total_orla_value = self._coerce_numeric(row.get("custo_total_orla"))
                if custo_total_orla_value is None:
                    custo_total_orla_value = 0.0
                if orla_checked:
                    custo_total_orla_value = 0.0
                    row["custo_total_orla"] = 0.0

                if mps_checked:
                    mp_component_total = 0.0
                else:
                    mp_component_total = custo_mp_total_value if custo_mp_total_value is not None else 0.0

                cp09_unit_value = self._coerce_numeric(row.get("cp09_colagem_und"))
                if cp09_unit_value is None:
                    cp09_unit_value = 0.0
                # cp09 contribution to total must be multiplied by qt_total (per-unit -> total)
                cp09_component_total = round((cp09_unit_value * (qt_total_numeric or 0.0)), 2)

                soma_custo_total_value = (
                    (maquinas_total_value or 0.0)
                    + custo_total_orla_value
                    + mp_component_total
                    + cp09_component_total
                )
                soma_custo_total_value = round(soma_custo_total_value, 2)
                row["soma_custo_total"] = soma_custo_total_value

                if mo_checked:
                    maquinas_line = "SOMA_CUSTO_und * Qt_Total = 0.00 € (checkbox MO ativo)"
                elif qt_total_numeric not in (None, 0) and maquinas_total_value is not None:
                    maquinas_line = (
                        f"SOMA_CUSTO_und * Qt_Total = {soma_custo_und_value:.2f} € * {qt_total_numeric:.2f} = {maquinas_total_value:.2f} €"
                    )
                else:
                    maquinas_line = "SOMA_CUSTO_und * Qt_Total: Qt_Total sem valor"

                if mps_checked:
                    mp_line = "CUSTO_MP_und * Qt_Total = 0.00 € (checkbox MPs ativo)"
                elif custo_mp_und_value is not None and qt_total_numeric not in (None, 0) and custo_mp_total_value is not None:
                    mp_line = (
                        f"CUSTO_MP_und * Qt_Total = {custo_mp_und_value:.2f} € * {qt_total_numeric:.2f} = {custo_mp_total_value:.2f} €"
                    )
                elif custo_mp_und_value is None:
                    mp_line = "CUSTO_MP_und * Qt_Total: valor unitario indisponivel"
                else:
                    mp_line = "CUSTO_MP_und * Qt_Total: Qt_Total sem valor"

                custo_orla_line = (
                    f"CUSTO_TOTAL_ORLA = {custo_total_orla_value:.2f} € (checkbox Orla ativo)"
                    if orla_checked
                    else f"CUSTO_TOTAL_ORLA = {custo_total_orla_value:.2f} €"
                )

                cp09_line = f"CP09_COLAGEM_und (por unidade) = {cp09_unit_value:.4f} € | Total: {cp09_component_total:.2f} €"

                soma_total_lines = [
                    "SOMA_CUSTO_TOTAL = (SOMA_CUSTO_und * Qt_Total) + CUSTO_TOTAL_ORLA + (CUSTO_MP_und * Qt_Total) + (CP09_COLAGEM_und * Qt_Total)",
                    maquinas_line,
                    custo_orla_line,
                    mp_line,
                    cp09_line,
                    f"Resultado: {soma_custo_total_value:.2f} €",
                ]
                row["_soma_custo_total_tooltip"] = "\n".join(soma_total_lines)
            else:
                row["soma_custo_und"] = None
                row["soma_custo_total"] = None
                row["_soma_custo_und_tooltip"] = None
                row["_soma_custo_total_tooltip"] = None

            if row.get("esp_mp") not in (None, "") and not expr_esp:

                default_esp = _coerce_dimension(row.get("esp_mp"))

                row["esp_res"] = default_esp

                row["_esp_error"] = None

                substitution = self._format_result_number(default_esp) or row.get("esp")

                row["_esp_tooltip"] = self._build_formula_tooltip(expr_esp or (row.get("esp") or substitution or ""), default_esp, None, substitutions=substitution or None)

        if production_cost_changed:
            self._mark_dirty()

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

                row[key] = svc_custeio._coerce_checkbox_to_bool(value)

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
        familia_norm = familia_val.casefold() if familia_val else ""
        normalized_def = (row.get("_normalized_def") or "").strip().casefold()
        normalized_child = (row.get("_normalized_child") or "").strip().casefold()
        tipo_norm = (row.get("tipo") or "").strip().casefold()

        normalized_candidates = {
            normalized_def,
            normalized_child,
            svc_custeio._normalize_token(row.get("def_peca")),
            svc_custeio._normalize_token(row.get("_child_source")),
            svc_custeio._normalize_token(row.get("descricao")),
            # Note: descricao_livre is excluded (user helper text, not for calculation logic)
        }
        spp_match = any(token in SPP_DEF_TOKENS for token in normalized_candidates if token)
        rodizio_match = any(token in RODIZIO_DEF_TOKENS for token in normalized_candidates if token)
        if rodizio_match:
            options = svc_custeio.lista_mat_default_sis_correr(
                session,
                context,
                grupos=RODIZIO_SIS_CORRER_OPTIONS,
            )
            if options:
                return options
            return list(RODIZIO_SIS_CORRER_OPTIONS)

        acessorio_match = any(token in ACESSORIO_CORRER_TOKENS for token in normalized_candidates if token)
        if acessorio_match:
            options = svc_custeio.lista_mat_default_sis_correr(
                session,
                context,
                grupos=ACESSORIO_CORRER_OPTIONS,
            )
            if options:
                return options
            return list(ACESSORIO_CORRER_OPTIONS)

        if spp_match:
            options = svc_custeio.lista_mat_default_sis_correr(
                session,
                context,
                "FERRAGENS",
                grupos=SPP_SIS_CORRER_OPTIONS,
            )
            if options:
                return options
            return list(SPP_SIS_CORRER_OPTIONS)

        info_ferragem = svc_custeio.inferir_ferragem_info(row) if row else None
        info_familia_norm = (
            (info_ferragem.get("familia") or "").strip().casefold() if info_ferragem else ""
        )
        is_ferragens = familia_norm == "ferragens" or info_familia_norm == "ferragens"

        if is_ferragens:
            tipo_hint: Optional[str] = None
            if row.get("tipo"):
                tipo_hint = row.get("tipo")
            elif info_ferragem and info_ferragem.get("tipo"):
                tipo_hint = info_ferragem["tipo"]
            elif row.get("_child_source"):
                tipo_hint = row.get("_child_source")
            options = svc_custeio.lista_mat_default_ferragens(session, context, tipo_hint)
            if options:
                return options

        painel_match = any(
            token in {
                svc_custeio._normalize_token("PAINEL CORRER [0000]"),
                svc_custeio._normalize_token("PAINEL CORRER [2222]"),
                svc_custeio._normalize_token("PAINEL ESPELHO [2222]"),
                svc_custeio._normalize_token("PAINEL CORRER"),
                svc_custeio._normalize_token("PAINEL ESPELHO"),
                svc_custeio._normalize_token("PAINEL"),
            }
            for token in normalized_candidates
            if token
        )
        painel_family = familia_norm == "sistemas correr" or info_familia_norm == "sistemas correr"
        if painel_family or painel_match:
            options = svc_custeio.lista_mat_default_sis_correr(
                session,
                context,
                "PLACAS",
                grupos=PAINEL_SIS_CORRER_OPTIONS,
            )
            if options:
                return options
            return list(PAINEL_SIS_CORRER_OPTIONS)

        cozinha_match = any(token in COZINHAS_SPECIAL_TOKENS for token in normalized_candidates if token)
        if cozinha_match:
            options = svc_custeio.lista_mat_default_ferragens_multi(session, context, COZINHAS_TYPE_HINTS)
            if options:
                return options
            generic = svc_custeio.lista_mat_default(session, context, "FERRAGENS")
            if generic:
                return generic
            return list(COZINHAS_MAT_DEFAULT_OPTIONS)

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

                coerced[key] = svc_custeio._coerce_checkbox_to_bool(value)

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

        # Preencher op├º├Áes: tenta obter via servi├ºo com session+context, sen├úo usa defaults
        options: List[str] = []
        if self._page is not None:
            session = getattr(self._page, "session", None)
            ctx = getattr(self._page, "context", None)
            try:
                options = svc_custeio.lista_acabamento(session, ctx)
            except Exception:
                options = []

        # Sempre incluir uma op├º├úo vazia
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

    item_context_changed = QtCore.Signal(object)

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
        self._ordered_item_ids: List[int] = []
        self._current_item_index: int = -1



        self._updating_checks = False  # guarda contra reentr├â┬óncia ao propagar check

        self._clipboard_rows: List[Dict[str, Any]] = []

        self.table_model = CusteioTableModel(self)

        self.table_model._page = self

        self._hidden_column_keys: Set[str] = set()
        self._column_visibility_dirty = False
        if self.current_user_id:
            try:
                stored_hidden = svc_custeio.carregar_colunas_ocultas(self.session, self.current_user_id)
            except Exception as exc:
                logger.exception("Falha ao carregar colunas ocultas: %s", exc)
                stored_hidden = set()
            self._hidden_column_keys = {key for key in stored_hidden if key not in LOCKED_COLUMN_KEYS}
        else:
            self._hidden_column_keys = set()
        self._column_actions: Dict[str, QtGui.QAction] = {}

        self._collapsed_groups: Set[str] = set()
        self._rows_dirty = False
        self._nst_override_snapshot: List[bool] = []
        self._production_cache_valid = False
        self._production_mode_cache: str = "STD"
        self._production_rates_by_desc: Dict[str, Dict[str, float]] = {}
        self._production_rates_by_abbrev: Dict[str, Dict[str, float]] = {}
        self._last_gravar_row: Optional[int] = None
        self._bold_font_cache: Dict[str, QtGui.QFont] = {}
        self._full_plates_mode: bool = bool(getattr(svc_custeio, "FULL_PLATES_MODE", False))
        self._full_plates_mode: bool = bool(getattr(svc_custeio, "FULL_PLATES_MODE", False))

        self._setup_ui()

        self._populate_tree()

        self._update_summary()


    # ------------------------------------------------------------------ Production data helpers

    def _production_context(self) -> Optional[svc_producao.ProducaoContext]:
        if not self.current_orcamento_id:
            return None
        user_id = self.current_user_id or getattr(self.current_user, "id", None)
        if not user_id and self.context is not None:
            user_id = getattr(self.context, "user_id", None)
        if not user_id:
            return None
        versao = None
        if self.context is not None:
            versao = getattr(self.context, "versao", None)
        elif self._current_item_obj is not None:
            versao = getattr(self._current_item_obj, "versao", None)
        try:
            return svc_producao.build_context(self.session, self.current_orcamento_id, user_id, versao=versao)
        except Exception as exc:
            logger.exception("Custeio._production_context failed: %s", exc)
            return None

    def _refresh_production_cache(self) -> None:
        self._production_rates_by_desc.clear()
        self._production_rates_by_abbrev.clear()
        self._production_mode_cache = "STD"
        ctx = self._production_context()
        if ctx is None:
            self._production_cache_valid = True
            return
        try:
            modo = svc_producao.get_mode(self.session, ctx)
        except Exception as exc:
            try:
                if getattr(self, "session", None):
                    self.session.rollback()
            except Exception:
                pass
            logger.exception("Custeio._refresh_production_cache get_mode failed: %s", exc)
            modo = "STD"
        self._production_mode_cache = (modo or "STD").upper()
        try:
            valores = svc_producao.load_values(self.session, ctx)
        except Exception as exc:
            try:
                if getattr(self, "session", None):
                    self.session.rollback()
            except Exception:
                pass
            logger.exception("Custeio._refresh_production_cache load_values failed: %s", exc)
            valores = []
        for entry in valores:
            desc_key = str(entry.get("descricao_equipamento") or "").strip().upper()
            abbr_key = str(entry.get("abreviatura") or "").strip().upper()
            data = {
                "descricao": desc_key,
                "abreviatura": abbr_key,
                "valor_std": float(entry.get("valor_std") or 0),
                "valor_serie": float(entry.get("valor_serie") or 0),
            }
            if desc_key:
                self._production_rates_by_desc[desc_key] = data
            if abbr_key:
                self._production_rates_by_abbrev[abbr_key] = data
        self._production_cache_valid = True

    def _ensure_production_cache(self) -> None:
        if not self._production_cache_valid:
            self._refresh_production_cache()

    def production_mode(self) -> str:
        self._ensure_production_cache()
        modo = (self._production_mode_cache or "STD").upper()
        return "SERIE" if modo == "SERIE" else "STD"

    def _update_auto_fill_icon(self, force: bool = False, override_state: Optional[bool] = None) -> None:
        if not hasattr(self, "btn_auto_fill"):
            return
        if self.context is None:
            self.btn_auto_fill.setIcon(QtGui.QIcon())
            self.btn_auto_fill.setStyleSheet("")
            self.btn_auto_fill.setToolTip("Copiar os Dados Gerais para as 4 tabelas de Dados Items do item corrente.")
            return
        if not force and getattr(self, "_auto_fill_icon_busy", False):
            return
        self._auto_fill_icon_busy = True
        try:
            if override_state is None:
                di_ctx = svc_dados_items.carregar_contexto(
                    self.session, self.context.orcamento_id, self.context.item_id
                )
                in_sync = svc_dados_items.dados_items_em_sincronia_com_gerais(self.session, di_ctx)
            else:
                in_sync = bool(override_state)
        except Exception:
            in_sync = False
        if in_sync:
            self.btn_auto_fill.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton))
            self.btn_auto_fill.setStyleSheet("background-color: #d4edda; color: #0f5132;")
            self.btn_auto_fill.setToolTip("Dados Items estão sincronizados com os Dados Gerais.")
        else:
            self.btn_auto_fill.setIcon(QtGui.QIcon())
            self.btn_auto_fill.setStyleSheet("background-color: #f8d7da; color: #842029;")
            self.btn_auto_fill.setToolTip("Dados Items não estão sincronizados com os Dados Gerais. Clique para atualizar.")
        self._auto_fill_icon_busy = False

    def get_production_rate_info(self, key: str) -> Optional[Dict[str, float]]:
        self._ensure_production_cache()
        if not key:
            return None
        key_norm = str(key).strip().upper()
        if not key_norm:
            return None
        data = self._production_rates_by_desc.get(key_norm)
        if data is None:
            data = self._production_rates_by_abbrev.get(key_norm)
        return data

    def current_production_rate(self, key: str) -> Optional[float]:
        info = self.get_production_rate_info(key)
        if not info:
            return None
        modo = (self._production_mode_cache or "STD").upper()
        if modo == "SERIE":
            return info.get("valor_serie")
        return info.get("valor_std")

    def on_production_mode_changed(self, modo: str) -> None:
        modo_norm = (modo or "").upper()
        if modo_norm not in {"STD", "SERIE"}:
            modo_norm = "STD"
        self._production_cache_valid = False
        self._production_mode_cache = modo_norm
        self._ensure_production_cache()
        if self.table_model.rowCount() > 0:
            self.table_model.recalculate_all()


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



        self.lbl_highlight = QtWidgets.QLabel("")
        init_highlight_label(self.lbl_highlight)
        header_layout.addWidget(self.lbl_highlight)

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



        style = self.style() or QtWidgets.QApplication.style()
        self.btn_toggle_tree = QtWidgets.QToolButton()
        self.btn_toggle_tree.setText("Expandir")
        self.btn_toggle_tree.setIcon(style.standardIcon(QtWidgets.QStyle.SP_ArrowDown))
        self.btn_toggle_tree.setCheckable(True)
        self.btn_toggle_tree.setToolTip("Expandir todos os grupos")
        self.btn_toggle_tree.toggled.connect(self._on_toggle_tree_expansion)
        controls_layout.addWidget(self.btn_toggle_tree)



        self.chk_selected_only = QtWidgets.QCheckBox("So selecionados")

        self.chk_selected_only.toggled.connect(self._on_selected_only_toggled)

        controls_layout.addWidget(self.chk_selected_only)

        self.btn_columns = QtWidgets.QToolButton()
        self.btn_columns.setText("Colunas")
        self.btn_columns.setToolTip("Ocultar/mostrar colunas da tabela")
        self.btn_columns.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.menu_columns = QtWidgets.QMenu(self.btn_columns)
        self.menu_columns.aboutToShow.connect(self._sync_column_menu_checks)
        self.btn_columns.setMenu(self.menu_columns)
        controls_layout.addWidget(self.btn_columns)



        controls_layout.addStretch(1)

        panel_layout.addLayout(controls_layout)



        # Modelo/Proxy da ├â┬ürvore

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

        self.btn_prev_item = QtWidgets.QToolButton()
        self.btn_prev_item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowUp))
        self.btn_prev_item.setToolTip("Item anterior")
        self.btn_prev_item.setEnabled(False)
        self.btn_prev_item.clicked.connect(self._on_prev_item_clicked)

        self.btn_next_item = QtWidgets.QToolButton()
        self.btn_next_item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowDown))
        self.btn_next_item.setToolTip("Item seguinte")
        self.btn_next_item.setEnabled(False)
        self.btn_next_item.clicked.connect(self._on_next_item_clicked)

        self.btn_auto_fill = QtWidgets.QPushButton("Preencher Dados Items")
        self.btn_auto_fill.setToolTip("Copiar os Dados Gerais para as 4 tabelas de Dados Items do item corrente.")

        actions_layout.addWidget(self.btn_refresh)

        actions_layout.addWidget(self.btn_save)
        actions_layout.addWidget(self.btn_prev_item)
        actions_layout.addWidget(self.btn_next_item)
        actions_layout.addWidget(self.btn_auto_fill)

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
            self.dimensions_table.setColumnWidth(col, 50)
        self.dimensions_table.itemChanged.connect(self._on_dimension_item_changed)
        self.dimensions_table.setEnabled(False)
        max_width = len(DIMENSION_KEY_ORDER) * 52
        self.dimensions_table.setMaximumWidth(max_width)
        dim_line = QtWidgets.QHBoxLayout()
        dim_line.setSpacing(8)
        dim_line.addWidget(self.dimensions_table, 1)

        module_btns = QtWidgets.QVBoxLayout()
        module_btns.setSpacing(6)
        self.btn_save_module = QtWidgets.QPushButton("Guardar Modulo")
        self.btn_save_module.setToolTip("Guardar linhas selecionadas (coluna GRAVAR_MODULO) como um módulo reutilizável.")
        self.btn_import_module = QtWidgets.QPushButton("Importar Modulo")
        self.btn_import_module.setToolTip("Importar módulos guardados e inserir linhas no custeio.")
        self.btn_save_module.setMaximumWidth(120)
        self.btn_import_module.setMaximumWidth(120)
        self.btn_save_module.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.btn_import_module.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        module_btns.addWidget(self.btn_save_module)
        module_btns.addWidget(self.btn_import_module)
        module_btns.addStretch(1)

        dim_line.addLayout(module_btns)

        right_layout.addLayout(dim_line)
        self._update_dimension_table()

        cache_font = self._bold_font_cache

        def _bold(btn: QtWidgets.QAbstractButton) -> None:
            key = btn.text() or btn.toolTip() or str(id(btn))
            font = cache_font.get(key)
            if font is None:
                font = btn.font()
                font.setBold(True)
                cache_font[key] = font
            btn.setFont(font)

        style = self.style() or QtWidgets.QApplication.style()
        self.btn_refresh.setIcon(style.standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        _bold(self.btn_refresh)
        self.btn_save.setIcon(style.standardIcon(QtWidgets.QStyle.SP_DialogSaveButton))
        _bold(self.btn_save)
        self.btn_auto_fill.setIcon(style.standardIcon(QtWidgets.QStyle.SP_DialogApplyButton))
        _bold(self.btn_auto_fill)
        self.btn_save_module.setIcon(style.standardIcon(QtWidgets.QStyle.SP_DialogSaveButton))
        _bold(self.btn_save_module)
        self.btn_import_module.setIcon(style.standardIcon(QtWidgets.QStyle.SP_DialogOpenButton))
        _bold(self.btn_import_module)
        self._update_auto_fill_icon()

        self.table_view = CusteioTableView()

        self.table_view.setItemDelegate(DadosGeraisDelegate(self.table_view))
        self.table_view.setModel(self.table_model)

        self.table_view.setAlternatingRowColors(True)

        self.table_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.table_view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # Permitir clique direto em checkboxes e outros campos edit├íveis
        self.table_view.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)

        self.table_view.setStyleSheet(
            "QTableView::item:selected { background-color: #555555; color: #ffffff; }\n"
            "QTableView::item:selected:active { background-color: #555555; color: #ffffff; }\n"
            "QTableView::item:selected:!active { background-color: #666666; color: #ffffff; }\n"
            "QTableView::item:hover { background-color: #6a6a6a; color: #ffffff; }"
        )

        self.table_view.setMouseTracking(True)

        self.table_view.horizontalHeader().setStretchLastSection(False)

        self.table_view.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.table_view.horizontalHeader().setDefaultSectionSize(96)

        self._apply_initial_column_widths()

        bool_columns: List[int] = []
        for col_index, spec in enumerate(self.table_model.columns):
            if spec["type"] == "numeric":
                self.table_view.setItemDelegateForColumn(col_index, NumericLineEditDelegate(self.table_view, spec))
            elif spec["type"] == "bool":
                bool_columns.append(col_index)

        for col_index in bool_columns:
            self.table_view.setItemDelegateForColumn(col_index, BoolDelegate(self.table_view))

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
        self.btn_save_module.clicked.connect(self._on_save_modulo_clicked)
        self.btn_import_module.clicked.connect(self._on_import_modulo_clicked)
        self.btn_auto_fill.clicked.connect(self._on_auto_fill_dados_items)

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

        self._apply_column_visibility()
        self._rebuild_columns_menu()
        self._update_columns_button_label()


    def _apply_column_visibility(self) -> None:
        if not hasattr(self, "table_view"):
            return
        valid_hidden: Set[str] = set()
        for key, idx in self.table_model._column_index.items():
            if key in LOCKED_COLUMN_KEYS:
                self.table_view.setColumnHidden(idx, False)
                continue
            hidden = key in self._hidden_column_keys
            if hidden:
                valid_hidden.add(key)
            self.table_view.setColumnHidden(idx, hidden)
        if valid_hidden != self._hidden_column_keys:
            self._hidden_column_keys = valid_hidden
        self._update_columns_button_label()


    def _rebuild_columns_menu(self) -> None:
        if not hasattr(self, "menu_columns"):
            return
        self.menu_columns.clear()
        self._column_actions.clear()
        for spec in self.table_model.columns:
            key = spec["key"]
            label = spec.get("label") or key.upper()
            action = QtGui.QAction(label, self.menu_columns)
            action.setCheckable(True)
            if key in LOCKED_COLUMN_KEYS:
                action.setChecked(True)
                action.setEnabled(False)
            else:
                action.setChecked(key not in self._hidden_column_keys)
                action.toggled.connect(partial(self._handle_column_toggle, key))
            self.menu_columns.addAction(action)
            self._column_actions[key] = action
        self.menu_columns.addSeparator()
        show_all_action = QtGui.QAction("Mostrar todas as colunas", self.menu_columns)
        show_all_action.triggered.connect(self._show_all_columns)
        self.menu_columns.addAction(show_all_action)


    def _sync_column_menu_checks(self) -> None:
        for key, action in self._column_actions.items():
            if key in LOCKED_COLUMN_KEYS:
                action.setChecked(True)
                continue
            desired = key not in self._hidden_column_keys
            if action.isChecked() != desired:
                block = action.blockSignals(True)
                action.setChecked(desired)
                action.blockSignals(block)


    def _handle_column_toggle(self, key: str, checked: bool) -> None:
        if key in LOCKED_COLUMN_KEYS:
            return
        if checked:
            if key in self._hidden_column_keys:
                self._hidden_column_keys.remove(key)
        else:
            self._hidden_column_keys.add(key)
        idx = self.table_model._column_index.get(key)
        if idx is not None:
            self.table_view.setColumnHidden(idx, not checked)
        self._column_visibility_dirty = True
        self._update_columns_button_label()
        self._update_save_button_text()


    def _show_all_columns(self) -> None:
        if not self._hidden_column_keys:
            return
        self._hidden_column_keys.clear()
        self._apply_column_visibility()
        self._column_visibility_dirty = True
        self._update_columns_button_label()
        self._rebuild_columns_menu()
        self._update_save_button_text()


    def _update_columns_button_label(self) -> None:
        if hasattr(self, "btn_columns"):
            hidden_count = len(self._hidden_column_keys)
            if hidden_count:
                self.btn_columns.setText(f"Colunas ({hidden_count})")
            else:
                self.btn_columns.setText("Colunas")



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

        return bool(self._rows_dirty or self._dimensions_dirty or self._column_visibility_dirty)


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

        """Constr├â┬│i a ├â┬írvore a partir do dicion├â┬írio retornado pelo servi├â┬ºo."""

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
        self._update_tree_toggle_button(False)



    def _create_item(self, node: Dict[str, Any], parent_path: Sequence[str]) -> Optional[QtGui.QStandardItem]:

        """

        Cria um QStandardItem:

          - pais: checkable + flags de tri-state; ├â┬¡cone de pasta;

          - folhas: checkable; ├â┬¡cone de ficheiro.

        """

        label = str(node.get("label", "")).strip()

        if not label:

            return None



        item = QtGui.QStandardItem(label)

        item.setEditable(False)

        item.setCheckable(True)

        if _is_colagem_label(label):
            item.setToolTip(COLAGEM_INFO_TEXT)
        elif _is_embalagem_label(label):
            item.setToolTip(EMBALAGEM_INFO_TEXT)
        else:
            item.setToolTip(label)

        item.setCheckState(QtCore.Qt.Unchecked)



        # guarda caminho amig├â┬ível (usado na recolha de sele├â┬º├â┬úo)

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

        cliente_nome = ""
        ano_text = ""
        numero_text = ""
        versao_text = ""
        utilizador = ""

        if orcamento:
            cliente_nome = (
                svc_custeio.obter_cliente_nome(self.session, getattr(orcamento, "client_id", None)) or ""
            )
            utilizador = (
                svc_custeio.obter_user_nome(
                    self.session,
                    getattr(orcamento, "updated_by", None) or getattr(orcamento, "created_by", None),
                )
                or ""
            )
            ano_raw = getattr(orcamento, "ano", "")
            ano_text = str(ano_raw).strip() if ano_raw not in (None, "") else ""
            numero_text = str(getattr(orcamento, "num_orcamento", "") or "")
            versao_raw = getattr(orcamento, "versao", "")
            try:
                versao_text = f"{int(versao_raw):02d}"
            except Exception:
                versao_text = str(versao_raw or "")

        self.lbl_cliente.setText(cliente_nome or "-")
        self.lbl_utilizador.setText(utilizador or "-")
        self.lbl_ano.setText(ano_text or "-")
        self.lbl_num.setText(numero_text or "-")
        self.lbl_ver.setText(versao_text or "-")

        if hasattr(self, "lbl_highlight"):
            apply_highlight_text(
                self.lbl_highlight,
                cliente=cliente_nome,
                numero=numero_text,
                versao=versao_text,
                ano=ano_text,
                utilizador=utilizador,
            )



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
        self._update_tree_toggle_button(True)

    def _on_collapse_all(self) -> None:
        self.tree.collapseAll()
        self._update_tree_toggle_button(False)

    def _on_toggle_tree_expansion(self, checked: bool) -> None:
        if checked:
            self._on_expand_all()
        else:
            self._on_collapse_all()
        self._update_tree_toggle_button(checked)

    def _update_tree_toggle_button(self, expanded: Optional[bool] = None) -> None:
        if not hasattr(self, "btn_toggle_tree"):
            return
        style = self.style() or QtWidgets.QApplication.style()
        if expanded is None:
            expanded = self.btn_toggle_tree.isChecked()
        else:
            if self.btn_toggle_tree.isChecked() != expanded:
                blocker = QtCore.QSignalBlocker(self.btn_toggle_tree)
                self.btn_toggle_tree.setChecked(expanded)
                del blocker
        if expanded:
            self.btn_toggle_tree.setText("Colapsar")
            self.btn_toggle_tree.setIcon(style.standardIcon(QtWidgets.QStyle.SP_ArrowUp))
            self.btn_toggle_tree.setToolTip("Colapsar todos os grupos")
        else:
            self.btn_toggle_tree.setText("Expandir")
            self.btn_toggle_tree.setIcon(style.standardIcon(QtWidgets.QStyle.SP_ArrowDown))
            self.btn_toggle_tree.setToolTip("Expandir todos os grupos")

    def _on_selected_only_toggled(self, checked: bool) -> None:

        self.proxy_model.set_only_checked(checked)

        self.tree.expandAll()

        if not checked:

            self.tree.expandToDepth(0)
            self._update_tree_toggle_button(False)
        else:
            self._update_tree_toggle_button(True)



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

        """Limpa busca + sele├â┬º├â┬úo (todas as folhas e pais)."""

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

                    item.setCheckState(QtCore.Qt.Unchecked)                 # mant├â┬®m pai coerente

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
            self._nst_override_snapshot = []

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

                rules = svc_custeio.get_auto_dimension_rules(self.session, self.current_user_id)
                svc_custeio.aplicar_dimensoes_automaticas(novas_linhas, rules=rules)

            except Exception:

                pass

        if not novas_linhas:

            QtWidgets.QMessageBox.warning(self, "Aviso", "Nao foi possivel gerar dados para as selecoes.")

            return
        added_colagem = any(_is_colagem_label(linha.get("def_peca")) for linha in novas_linhas)
        added_embalagem = any(_is_embalagem_label(linha.get("def_peca")) for linha in novas_linhas)
        self.table_model.append_rows(novas_linhas)

        self.table_model.recalculate_all()
        if added_colagem:
            QtWidgets.QMessageBox.information(
                self,
                "Colagem/Revestimento",
                COLAGEM_INFO_TEXT,
            )
        if added_embalagem:
            QtWidgets.QMessageBox.information(
                self,
                "Embalagem (M3)",
                EMBALAGEM_INFO_TEXT,
            )

        self._update_table_placeholder_visibility()

        self._clear_all_checks()



    def _linhas_para_modulo(self) -> List[Dict[str, Any]]:
        if not getattr(self, "table_model", None):
            return []
        selecionadas: List[Dict[str, Any]] = []
        for row in self.table_model.rows:
            if svc_custeio._coerce_checkbox_to_bool(row.get("gravar_modulo")):
                # Usa limpeza do serviço para evitar objetos Qt (ex.: ícones) no deepcopy
                selecionadas.append(svc_modulos.limpar_linha_para_modulo(row))
        return selecionadas

    def _limpar_marcadores_modulo(self) -> None:
        if not getattr(self, "table_model", None):
            return
        changed = False
        for idx, row in enumerate(self.table_model.rows):
            if svc_custeio._coerce_checkbox_to_bool(row.get("gravar_modulo")):
                self.table_model.update_row_fields(idx, {"gravar_modulo": False})
                changed = True
        if changed:
            self.table_model.recalculate_all()

    def _on_save_modulo_clicked(self) -> None:
        if not self.context:
            QtWidgets.QMessageBox.information(self, "Informacao", "Nenhum item selecionado.")
            return
        linhas = self._linhas_para_modulo()
        if not linhas:
            QtWidgets.QMessageBox.information(
                self,
                "Informacao",
                "Selecione as linhas que pretende gravar marcando a coluna GRAVAR_MODULO.",
            )
            return
        dialog = SaveModuloDialog(self, self.session, self.current_user_id, linhas)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self._limpar_marcadores_modulo()
            QtWidgets.QMessageBox.information(self, "Sucesso", "Modulo gravado com sucesso.")

    def _on_import_modulo_clicked(self) -> None:
        if not self.context:
            QtWidgets.QMessageBox.information(self, "Informacao", "Nenhum item selecionado.")
            return
        dialog = ImportModuloDialog(self, self.session, self.current_user_id)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        linhas = dialog.linhas_importadas()
        if not linhas:
            QtWidgets.QMessageBox.information(self, "Informacao", "Nenhum modulo selecionado para importar.")
            return
        auto_dimensions = self._auto_dimensions_enabled()
        if auto_dimensions:
            try:
                rules = svc_custeio.get_auto_dimension_rules(self.session, self.current_user_id)
                svc_custeio.aplicar_dimensoes_automaticas(linhas, rules=rules)
            except Exception:
                pass
        self.table_model.append_rows(linhas)
        self.table_model.recalculate_all()
        self._update_table_placeholder_visibility()
        self._update_auto_fill_icon()

    def _on_auto_fill_dados_items(self) -> None:
        if not self.context:
            QtWidgets.QMessageBox.information(self, "Informacao", "Nenhum item selecionado.")
            return
        try:
            di_ctx = svc_dados_items.carregar_contexto(self.session, self.context.orcamento_id, self.context.item_id)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao preparar contexto de Dados Items: {exc}")
            return
        # Confirmação se já há dados preenchidos
        try:
            existentes = svc_dados_items.carregar_dados_gerais(self.session, di_ctx)
            ja_tem_dados = any(existing_rows for existing_rows in existentes.values() if existing_rows)
        except Exception:
            ja_tem_dados = False
        if ja_tem_dados:
            resp = QtWidgets.QMessageBox.question(
                self,
                "Confirmar atualização",
                "Já existem dados preenchidos nas 4 tabelas de Dados Items.\nDeseja substituir pelos Dados Gerais?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if resp != QtWidgets.QMessageBox.Yes:
                return
        try:
            svc_dados_items.preencher_com_dados_gerais(self.session, di_ctx)
        except Exception as exc:
            self.session.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao preencher Dados Items: {exc}")
            return
        QtWidgets.QMessageBox.information(
                self,
            "Dados Items atualizados",
            "As 4 tabelas de Dados Items foram preenchidas a partir dos Dados Gerais e gravadas.",
        )
        self._update_auto_fill_icon(force=True, override_state=True)

    def _on_refresh_custeio(self) -> None:
        if not self.context:
            QtWidgets.QMessageBox.information(self, "Informacao", "Nenhum item selecionado.")
            return
        if hasattr(self.session, "expire_all"):
            self.session.expire_all()
        self._apply_updates_from_items()
        self.table_model.recalculate_all()
        self._full_plates_mode = bool(getattr(svc_custeio, "FULL_PLATES_MODE", False))
        self._apply_full_plate_mode(self._full_plates_mode, from_load=True)
        self._update_table_placeholder_visibility()

    def _coerce_float_simple(self, value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(str(value).replace(",", "."))
        except Exception:
            return None

    def _compute_full_plate_desp(self, row: Mapping[str, Any]) -> Optional[float]:
        comp_mp = self._coerce_float_simple(row.get("comp_mp"))
        larg_mp = self._coerce_float_simple(row.get("larg_mp"))
        area_und = self._coerce_float_simple(row.get("area_m2_und"))
        qt_total = self._coerce_float_simple(row.get("qt_total")) or 0.0
        if not comp_mp or not larg_mp or not area_und or qt_total <= 0:
            return None
        area_placa = (comp_mp * larg_mp) / 1_000_000.0
        if area_placa <= 0:
            return None
        area_consumida = area_und * qt_total
        if area_consumida <= 0:
            return None
        placas_necessarias = max(1, math.ceil(area_consumida / area_placa))
        if placas_necessarias <= 0:
            return None
        area_total_comprada = placas_necessarias * area_placa
        desp_fraction = max(area_total_comprada / area_consumida - 1.0, 0.0)
        return round(desp_fraction * 100.0, 2)

    def _apply_full_plate_mode(self, enabled: bool, *, from_load: bool = False) -> None:
        if not getattr(self, "table_model", None):
            return
        self._full_plates_mode = bool(enabled)
        changed = False
        for row in self.table_model.rows:
            familia = (row.get("familia") or "").strip().upper()
            if familia != "PLACAS":
                continue
            nst_checked = bool(row.get("nst"))
            if not nst_checked:
                continue
            if enabled:
                if "_desp_original" not in row:
                    row["_desp_original"] = row.get("desp")
                novo_desp = self._compute_full_plate_desp(row)
                if novo_desp is not None:
                    row["desp"] = novo_desp
                    changed = True
            else:
                if "_desp_original" in row:
                    row["desp"] = row["_desp_original"]
                    del row["_desp_original"]
                    changed = True
        if changed:
            self.table_model.recalculate_all()
            self.table_model.layoutChanged.emit()
            self.table_model._mark_dirty()
            if not from_load:
                self._update_summary()

    def set_full_plate_mode(self, enabled: bool) -> None:
        self._full_plates_mode = bool(enabled)
        try:
            setattr(svc_custeio, "FULL_PLATES_MODE", self._full_plates_mode)
        except Exception:
            pass
        self._apply_full_plate_mode(self._full_plates_mode)

    def _save_custeio(self, *, auto: bool = False) -> bool:

        if not self.context:

            if not auto:

                QtWidgets.QMessageBox.information(self, "Informacao", "Nenhum item selecionado.")

            return False

        save_button = getattr(self, "btn_save", None)
        should_disable_button = bool(save_button) and not auto
        if should_disable_button:
            save_button.setDisabled(True)

        self.table_model.recalculate_all()
        if not self._validate_special_rows():
            if should_disable_button:
                save_button.setEnabled(True)
            return False

        dimensoes = self._collect_dimension_payload()

        linhas = self.table_model.export_rows()
        snapshot = [bool(row.get("_nst_manual_override")) for row in linhas]

        ctx = self.context
        logger.info(
            "custeio.save start auto=%s orcamento_id=%s item_id=%s user_id=%s linhas=%s",
            auto,
            getattr(ctx, "orcamento_id", None),
            getattr(ctx, "item_id", None) if ctx else self.current_item_id,
            self.current_user_id,
            len(linhas),
        )
        try:

            svc_custeio.salvar_custeio_items(self.session, self.context, linhas, dimensoes)

        except Exception as exc:

            self.session.rollback()
            logger.exception(
                "custeio.save erro auto=%s orcamento_id=%s item_id=%s user_id=%s",
                auto,
                getattr(ctx, "orcamento_id", None),
                getattr(ctx, "item_id", None) if ctx else self.current_item_id,
                self.current_user_id,
            )

            QtWidgets.QMessageBox.critical(

                self,

                "Erro",

                f"Falha ao guardar Dados Custeio: {exc}",

            )
            if should_disable_button:
                save_button.setEnabled(True)

            return False

        self._nst_override_snapshot = snapshot if any(snapshot) else []

        self._dimensions_dirty = False

        self._set_rows_dirty(False)

        if not auto and self._column_visibility_dirty:
            try:
                svc_custeio.guardar_colunas_ocultas(self.session, self.current_user_id, self._hidden_column_keys)
            except Exception as exc:
                logger.exception("Falha ao guardar colunas ocultas: %s", exc)
            else:
                self._column_visibility_dirty = False

        self._reload_custeio_rows()

        self._apply_updates_from_items()

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()
        self._update_auto_fill_icon()

        self._update_save_button_text()
        logger.info(
            "custeio.save ok auto=%s orcamento_id=%s item_id=%s user_id=%s",
            auto,
            getattr(ctx, "orcamento_id", None),
            getattr(ctx, "item_id", None) if ctx else self.current_item_id,
            self.current_user_id,
        )

        if should_disable_button:
            save_button.setEnabled(True)

        return True

    def _validate_special_rows(self) -> bool:
        if not getattr(self, "table_model", None):
            return True
        rows = getattr(self.table_model, "rows", [])
        if not rows:
            return True
        colagem_issues: List[str] = []
        embalagem_issues: List[str] = []
        for idx, row in enumerate(rows, start=1):
            def_peca = row.get("def_peca")
            if _is_colagem_label(def_peca):
                comp_val = self._coerce_dimension_value(row.get("comp_res"))
                larg_val = self._coerce_dimension_value(row.get("larg_res"))
                qt_und_val = self._coerce_dimension_value(row.get("qt_und"))
                missing_dims = (
                    comp_val is None
                    or comp_val <= 0
                    or larg_val is None
                    or larg_val <= 0
                )
                invalid_qt = qt_und_val is None or abs(qt_und_val - 1.0) > 1e-6
                if missing_dims or invalid_qt:
                    desc = (
                        row.get("descricao_livre")
                        or row.get("descricao")
                        or def_peca
                        or f"Linha {idx}"
                    )
                    parts: List[str] = []
                    if missing_dims:
                        parts.append("preencher COMP e LARG (> 0 mm)")
                    if invalid_qt:
                        parts.append("manter QT_und = 1")
                    colagem_issues.append(f"- Linha {idx} ({desc}): {', '.join(parts)}")
            elif _is_embalagem_label(def_peca):
                comp_val = self._coerce_dimension_value(row.get("comp_res"))
                larg_val = self._coerce_dimension_value(row.get("larg_res"))
                esp_val = self._coerce_dimension_value(row.get("esp_res"))
                missing_dims = (
                    comp_val is None
                    or comp_val <= 0
                    or larg_val is None
                    or larg_val <= 0
                    or esp_val is None
                    or esp_val <= 0
                )
                if missing_dims:
                    desc = (
                        row.get("descricao_livre")
                        or row.get("descricao")
                        or def_peca
                        or f"Linha {idx}"
                    )
                    embalagem_issues.append(
                        f"- Linha {idx} ({desc}): preencher COMP, LARG e ESP (> 0 mm)"
                    )
        if not colagem_issues and not embalagem_issues:
            return True

        parts: List[str] = []
        if colagem_issues:
            parts.append(COLAGEM_INFO_TEXT + "\n\n" + "\n".join(colagem_issues))
        if embalagem_issues:
            parts.append(EMBALAGEM_INFO_TEXT + "\n\n" + "\n".join(embalagem_issues))
        QtWidgets.QMessageBox.warning(
            self,
            "Validação de peças especiais",
            "\n\n".join(parts),
        )
        return False


    def _on_save_custeio(self) -> None:

        self._save_custeio(auto=False)


    def _reload_custeio_rows(self) -> None:

        if not self.context:

            self.table_model.clear()

            self._update_table_placeholder_visibility()

            return

        self._capture_nst_snapshot_from_model()

        linhas = svc_custeio.listar_custeio_items(self.session, self.context.orcamento_id, self.context.item_id)

        self.table_model.load_rows(linhas)
        self._reapply_nst_override_snapshot()

        self.table_model.recalculate_all()
        self._full_plates_mode = bool(getattr(svc_custeio, "FULL_PLATES_MODE", False))
        self._apply_full_plate_mode(self._full_plates_mode, from_load=True)

        self._update_table_placeholder_visibility()


    def _capture_nst_snapshot_from_model(self) -> None:
        if not self.table_model.rows:
            if self._nst_override_snapshot:
                self._nst_override_snapshot = []
            return
        snapshot = [bool(row.get("_nst_manual_override")) for row in self.table_model.rows]
        if any(snapshot):
            self._nst_override_snapshot = snapshot
        elif self._nst_override_snapshot:
            self._nst_override_snapshot = []


    def _reapply_nst_override_snapshot(self) -> None:
        if not self._nst_override_snapshot or not any(self._nst_override_snapshot):
            if self._nst_override_snapshot:
                self._nst_override_snapshot = []
            return
        row_count = len(self.table_model.rows)
        for idx, flag in enumerate(self._nst_override_snapshot):
            if idx >= row_count:
                break
            row = self.table_model.rows[idx]
            manual_flag = bool(flag)
            row["_nst_manual_override"] = manual_flag
            if "_nst_source" not in row or row["_nst_source"] is None:
                base_nst = row.get("nst")
                if base_nst in (None, ""):
                    row["_nst_source"] = None
                else:
                    row["_nst_source"] = svc_custeio._coerce_checkbox_to_bool(base_nst)
        self._nst_override_snapshot = self._nst_override_snapshot[:row_count]


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
        if hasattr(self, "btn_save_module"):
            self.btn_save_module.setEnabled(self.context is not None and has_rows)
        if hasattr(self, "btn_import_module"):
            self.btn_import_module.setEnabled(self.context is not None)
        if hasattr(self, "btn_auto_fill"):
            self.btn_auto_fill.setEnabled(self.context is not None)
        self._update_save_button_text()
        # atualizar ícone de sincronismo dos Dados Items
        if hasattr(self, "_update_auto_fill_icon"):
            self._update_auto_fill_icon()



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
            if spec["key"] == "gravar_modulo":
                modifiers = QtWidgets.QApplication.keyboardModifiers()
                if modifiers & QtCore.Qt.ShiftModifier and self._last_gravar_row is not None:
                    start = min(self._last_gravar_row, index.row())
                    end = max(self._last_gravar_row, index.row())
                    for row_idx in range(start, end + 1):
                        target_index = self.table_model.index(row_idx, index.column())
                        self.table_model.setData(target_index, new_state, QtCore.Qt.CheckStateRole)
                    self._last_gravar_row = index.row()
                    return
                self._last_gravar_row = index.row()
            self.table_model.setData(index, new_state, QtCore.Qt.CheckStateRole)
            if spec["key"] != "gravar_modulo":
                self._last_gravar_row = None


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
            material = svc_custeio.obter_material_por_grupo(self.session, self.context, selection, familia)

        row["mat_default"] = selection

        if not material:
            def _warn():
                QtWidgets.QMessageBox.warning(self, "Aviso", f"Nao foi possivel localizar dados para '{selection}'.")

            QtCore.QTimer.singleShot(0, _warn)
            self.table_model.update_row_fields(row_index, {"mat_default": selection})
            self.table_model.recalculate_all()
            self._update_table_placeholder_visibility()
            return

        updates = svc_custeio.dados_material(material)

        self.table_model.update_row_fields(row_index, updates, skip_keys=("def_peca", "descricao_livre", "qt_mod", "qt_und", "comp", "larg", "esp"))

        orla_updates = svc_custeio.calcular_espessuras_orla(self.session, row)
        self.table_model.update_row_fields(row_index, orla_updates)

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
        cp_cache = svc_def_pecas.mapa_por_nome(self.session)
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
            if "nst" in updates:
                nst_source = svc_custeio._coerce_checkbox_to_bool(updates.get("nst"))
                row["_nst_source"] = nst_source
                if row.get("_nst_manual_override"):
                    updates.pop("nst", None)
                else:
                    row["_nst_manual_override"] = False
            else:
                if "_nst_source" not in row:
                    row["_nst_source"] = None
            updates.pop("acabamento_sup", None)
            updates.pop("acabamento_inf", None)

            self.table_model.update_row_fields(

                idx,

                updates,

                skip_keys=("def_peca", "descricao_livre", "qt_mod", "qt_und", "comp", "larg", "esp", "mps", "mo", "orla", "blk", "mat_default"),

            )
            svc_custeio.aplicar_definicao_cp_linha(self.session, row, cp_cache)

            novo_default = updates.get("mat_default")

            if novo_default:

                atual_default = (row.get("mat_default") or "").strip().casefold()

                familia_atual = (row.get("familia") or "").strip().casefold()

                if not atual_default or atual_default == familia_atual:

                    row["mat_default"] = novo_default

            special_default = _special_default_for_row(row)
            if special_default:
                current_default = (row.get("mat_default") or "").strip().casefold()
                if not current_default or current_default == "laterais":
                    row["mat_default"] = special_default

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

    def _refresh_item_sequence(self, orcamento_id: Optional[int]) -> None:

        if not orcamento_id:

            self._ordered_item_ids = []
            self._current_item_index = -1
            self._update_item_nav_buttons()
            return

        try:

            stmt = (
                select(OrcamentoItem.id_item)
                .where(OrcamentoItem.id_orcamento == orcamento_id)
                .order_by(OrcamentoItem.item_ord, OrcamentoItem.id_item)
            )
            ids = self.session.execute(stmt).scalars().all()
        except Exception as exc:

            logger.exception("Falha ao obter lista de itens do orçamento %s: %s", orcamento_id, exc)
            ids = []

        self._ordered_item_ids = [int(value) for value in ids if value is not None]
        self._recalculate_nav_index()

    def _recalculate_nav_index(self) -> None:

        if not self._ordered_item_ids or self.current_item_id is None:

            self._current_item_index = -1
            self._update_item_nav_buttons()
            return

        try:
            current_id = int(self.current_item_id)
        except (TypeError, ValueError):
            current_id = self.current_item_id

        try:
            self._current_item_index = self._ordered_item_ids.index(current_id)
        except ValueError:
            self._current_item_index = -1

        self._update_item_nav_buttons()

    def _update_item_nav_buttons(self) -> None:

        has_items = bool(self._ordered_item_ids)
        idx = self._current_item_index

        if not has_items:
            prev_enabled = False
            next_enabled = False
        elif idx < 0:
            prev_enabled = False
            next_enabled = True
        else:
            prev_enabled = idx > 0
            next_enabled = idx < len(self._ordered_item_ids) - 1

        if hasattr(self, "btn_prev_item"):
            self.btn_prev_item.setEnabled(prev_enabled)
        if hasattr(self, "btn_next_item"):
            self.btn_next_item.setEnabled(next_enabled)

    def _emit_item_context_changed(self) -> None:
        try:
            self.item_context_changed.emit(self.current_item_id)
        except Exception:
            logger.debug("Falha ao emitir item_context_changed", exc_info=True)

    def _navigate_item(self, step: int) -> None:

        if not step or not self.current_orcamento_id or not self._ordered_item_ids:

            return

        if not self.auto_save_if_dirty():

            return

        idx = self._current_item_index
        if idx is None or idx < 0:
            idx = 0 if step > 0 else len(self._ordered_item_ids) - 1

        new_idx = max(0, min(idx + step, len(self._ordered_item_ids) - 1))

        if new_idx == self._current_item_index:

            return

        target_id = self._ordered_item_ids[new_idx]

        self.load_item(self.current_orcamento_id, target_id)

    def _on_prev_item_clicked(self) -> None:

        self._navigate_item(-1)

    def _on_next_item_clicked(self) -> None:

        self._navigate_item(1)

    def load_item(self, orcamento_id: int, item_id: Optional[int]) -> None:

        self.current_orcamento_id = orcamento_id
        self._nst_override_snapshot = []

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
        self._refresh_item_sequence(orcamento_id)
        self._emit_item_context_changed()

        self._collapsed_groups.clear()

        logger.debug("Custeio.load_item orcamento_id=%s item_id=%s", orcamento_id, item_id)
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

            self._refresh_item_sequence(None)

            return



        self._reset_header()

        self._apply_orcamento_header(orcamento)



        item_obj: Optional[OrcamentoItem] = None

        if normalized_item_id:

            item_obj = svc_custeio.carregar_item(self.session, normalized_item_id)
            logger.debug(
                "Custeio.load_item fetched item_obj id=%s",
                getattr(item_obj, "id_item", None) if item_obj else None,
            )
            if item_obj is None:

                QtWidgets.QMessageBox.warning(self, "Aviso", "Item nao encontrado para o orcamento selecionado.")
                ids = self.session.execute(select(OrcamentoItem.id_item).where(OrcamentoItem.id_orcamento == orcamento_id)).scalars().all()
                logger.debug("Custeio.load_item available ids=%s", ids)



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

        self._production_cache_valid = False
        if self.context is not None:
            self._ensure_production_cache()

        self._reload_custeio_rows()

        self._apply_updates_from_items()

        self.table_model.recalculate_all()

        self._update_table_placeholder_visibility()



    def clear_context(self) -> None:

        self.context = None

        self.current_orcamento_id = None

        self.current_item_id = None

        self._current_item_obj = None
        self._ordered_item_ids = []
        self._current_item_index = -1
        self._update_item_nav_buttons()

        self._clear_dimension_values()

        self._collapsed_groups.clear()
        self._nst_override_snapshot = []
        self._production_cache_valid = False
        self._production_mode_cache = "STD"
        self._production_rates_by_desc.clear()
        self._production_rates_by_abbrev.clear()

        self._reset_header()

        self._clear_all_checks()

        self.table_model.clear()

        self._update_table_placeholder_visibility()
        self._emit_item_context_changed()
        self._update_auto_fill_icon()


