from __future__ import annotations

from dataclasses import dataclass

from Martelo_Orcamentos_V2.app.utils.bool_converter import bool_to_int, int_to_bool
from Martelo_Orcamentos_V2.ui.delegates import BoolDelegate  # ou caminho correto
import json  # usado em _copy_rows
from collections import deque


from decimal import Decimal


import itertools


from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple







from PySide6 import QtCore, QtWidgets, QtGui



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



    QMenu,



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
from Martelo_Orcamentos_V2.app.services import user_layouts



from Martelo_Orcamentos_V2.ui.delegates import DadosGeraisDelegate

from ..utils.header import apply_highlight_text, init_highlight_label



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







MATERIAL_CLIP_FIELDS = [



    "ref_le",



    "descricao_material",



    "preco_tab",



    "preco_liq",



    "margem",



    "desconto",



    "und",



    "desp",



    "orl_0_4",



    "orl_1_0",



    "tipo",



    "comp_mp",



    "larg_mp",



    "esp_mp",



    "id_mp",



    "nao_stock",



]











def _decimal(value: Optional[Decimal], *, places: int = 4) -> str:



    if value in (None, ""):



        return ""



    try:



        quant = Decimal("1").scaleb(-places)



        dec = Decimal(str(value)).quantize(quant)



        return str(dec).replace('.', ',')



    except Exception:



        return str(value)











def _money(value: Optional[Decimal]) -> str:



    if value in (None, ""):



        return ""



    try:



        amount = Decimal(str(value)).quantize(Decimal("0.01"))



        text = f"{amount:.2f}".replace('.', ',')



        return f"{text} €"



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



    def __init__(self, options_cb: Callable[..., Sequence[str]], parent=None):



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



        def _refresh(index_obj, current_value):
            options = self._options_for_index(index_obj)
            cleaned = list(dict.fromkeys(options))
            current = (current_value or "").strip()
            if current and current not in cleaned:
                cleaned.insert(0, current)
            editor.blockSignals(True)
            editor.clear()
            if cleaned:
                editor.addItems(cleaned)
            editor.blockSignals(False)
            if current:
                pos = editor.findText(current)
                if pos >= 0:
                    editor.setCurrentIndex(pos)
                elif cleaned:
                    editor.setCurrentIndex(0)
            elif cleaned:
                editor.setCurrentIndex(0)

        editor._refresh_options = _refresh  # type: ignore[attr-defined]



        QtCore.QTimer.singleShot(0, editor.showPopup)



        return editor







    def setEditorData(self, editor, index):



        value = index.model().data(index, Qt.EditRole) or ""



        if hasattr(editor, "_refresh_options"):
            editor._refresh_options(index, value)  # type: ignore[attr-defined]



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







    def _options_for_index(self, index) -> Sequence[str]:
        if not callable(self._options_cb):
            return []
        try:
            return self._options_cb(index)
        except TypeError:
            return self._options_cb()











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



            if spec.kind == "money":



                return _decimal(value, places=2)



            if spec.kind == "decimal":



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
            return Qt.Checked if int_to_bool(value) else Qt.Unchecked







        if role == Qt.TextAlignmentRole:



            if spec.kind in {"money", "decimal", "percent", "integer"}:
                return int(Qt.AlignRight | Qt.AlignVCenter)
            if spec.kind == "bool":
                return int(Qt.AlignCenter | Qt.AlignVCenter)







        return None







    def headerData(self, section, orientation, role=Qt.DisplayRole):



        if orientation == Qt.Horizontal:



            if role == Qt.FontRole:



                font = QtGui.QFont()



                font.setBold(True)



                return font



            if role == Qt.DisplayRole and 0 <= section < len(self.columns):



                return self.columns[section].header



        if orientation == Qt.Vertical and role == Qt.DisplayRole:



            return section + 1



        return None





    def flags(self, index):



        if not index.isValid():



            return Qt.NoItemFlags



        spec = self.columns[index.column()]



        base = Qt.ItemIsSelectable | Qt.ItemIsEnabled



        if spec.kind == "bool":



            base |= Qt.ItemIsUserCheckable







        elif not spec.readonly:



            base |= Qt.ItemIsEditable



        return base







    def setData(self, index, value, role=Qt.EditRole):



        if not index.isValid():



            return False



        spec = self.columns[index.column()]



        row = self._rows[index.row()]







        if spec.kind == "bool" and role in (Qt.CheckStateRole, Qt.EditRole):
            if role == Qt.CheckStateRole:
                new_value = bool(value)
            else:
                if isinstance(value, (int, float)):
                    new_value = bool(value)
                elif isinstance(value, str):
                    new_value = value.strip().lower() in {"1", "true", "sim", "yes", "on"}
                else:
                    new_value = bool(value)

            current_bool = int_to_bool(row.get(spec.field))
            if current_bool == new_value:
                return True

            stored = row.get(spec.field)
            if isinstance(stored, (int, float)) and not isinstance(stored, bool):
                row[spec.field] = bool_to_int(new_value)
            else:
                row[spec.field] = new_value

            self.dataChanged.emit(index, index, [Qt.CheckStateRole, Qt.DisplayRole])
            return True
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



            text = text.replace('', '')



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



        pliq = self.svc.calcular_preco_liq(preco_tab, margem, desconto)



        row["preco_liq"] = pliq



        self._rows[row_index] = row



        idx = self._field_index.get("preco_liq")



        if idx is not None:



            model_index = self.index(row_index, idx)



            self.dataChanged.emit(model_index, model_index, [Qt.DisplayRole])











class FerragensTableModel(MateriaisTableModel):



    pass







class SistemasCorrerTableModel(MateriaisTableModel):



    pass







class AcabamentosTableModel(MateriaisTableModel):



    pass









class MateriaPrimaPicker(QDialog):



    def __init__(self, session, parent=None, *, tipo: Optional[str] = None, familia: Optional[str] = None):



        super().__init__(parent)



        self.session = session



        self.filter_tipo = (tipo or "").strip() or None



        self.filter_familia = (familia or "").strip() or None



        self.setWindowTitle("Selecionar Materia-Prima")



        self.resize(1400, 700)







        layout = QVBoxLayout(self)



        search_layout = QHBoxLayout()



        self.ed_search = QLineEdit()



        self.ed_search.setPlaceholderText("Pesquisar... use % para varios termos")



        btn_search = QPushButton("Pesquisar")



        btn_search.clicked.connect(self.refresh)



        btn_clear = QPushButton("Limpar Filtro")



        btn_clear.clicked.connect(self.on_clear_filters)







        search_layout.addWidget(self.ed_search, 1)







        self.lbl_filters = QLabel()



        self.lbl_filters.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)



        self._update_filter_label()







        self._search_timer = QtCore.QTimer(self)



        self._search_timer.setSingleShot(True)



        self._search_timer.timeout.connect(self.refresh)



        self.ed_search.textChanged.connect(self._on_search_text_changed)



        QtCore.QTimer.singleShot(0, self.ed_search.setFocus)



        self.table = QTableView(self)



        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)



        self.table.setSelectionMode(QAbstractItemView.SingleSelection)



        self.table.setSortingEnabled(True)



        self.table.doubleClicked.connect(self.accept)







        columns = [



            ("Ref_LE", "ref_le"),



            ("Descricao", "descricao_orcamento"),



            ("Preco Tabela", "preco_tabela", _money),



            ("Margem", "margem", _percent),



            ("Desconto", "desconto", _percent),



            ("Preco Liq", "pliq", _money),



            ("Und", "und"),



            ("Desp", "desp", _percent),



            ("Comp MP", "comp_mp", _int_value),



            ("Larg MP", "larg_mp", _int_value),



            ("Esp MP", "esp_mp", _int_value),



            ("Tipo", "tipo"),



            ("Familia", "familia"),



            ("ORL 0.4", "orl_0_4"),



            ("ORL 1.0", "orl_1_0"),



            ("Stock", "stock", lambda v: "1" if bool(v) else "0"),



        ]






        self.model = SimpleTableModel(columns=columns)



        self.table.setModel(self.model)



        header = self.table.horizontalHeader()

        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)

        header.setStretchLastSection(False)

        self.table.setColumnWidth(0, 120)

        self.table.setColumnWidth(1, 420)

        controls_row = QHBoxLayout()

        controls_row.setContentsMargins(0, 0, 0, 0)

        controls_row.setSpacing(6)

        controls_row.addWidget(btn_search)

        controls_row.addWidget(btn_clear)

        controls_row.addSpacing(12)

        controls_row.addWidget(self.lbl_filters, 1)



        layout.addLayout(search_layout)



        layout.addLayout(controls_row)



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



        familia = self.filter_familia or "(todas as familias)"



        self.lbl_filters.setText(f"Filtro atual: Tipo {tipo} | Familia {familia}")







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



            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione uma materia-prima")



            return



        super().accept()



















class DadosGeraisPage(QtWidgets.QWidget):

    # --- ÍCONES PADRÃO (classe) -------------------------------------------------
    # Mapa de chaves -> StandardPixmap. Mantém as chaves simples (em inglês)
    # para reutilizar igual em outros ficheiros (ex.: dados_items.py).
    # Podes acrescentar novas chaves conforme precisares.
    _ICON_MAP = {
        "save":         QtWidgets.QStyle.SP_DialogSaveButton,
        "open":         QtWidgets.QStyle.SP_DirOpenIcon,
        "import":       QtWidgets.QStyle.SP_ArrowDown,
        "import_multi": QtWidgets.QStyle.SP_ArrowDown,
        "export":       QtWidgets.QStyle.SP_ArrowUp,
        "delete":       QtWidgets.QStyle.SP_TrashIcon,
        "copy":         QtWidgets.QStyle.SP_FileDialogDetailedView,
        "paste":        QtWidgets.QStyle.SP_DialogApplyButton,
        "clear":        QtWidgets.QStyle.SP_DialogResetButton,
        "add":          QtWidgets.QStyle.SP_FileDialogNewFolder,
        "edit":         QtWidgets.QStyle.SP_FileDialogContentsView,
        "refresh":      QtWidgets.QStyle.SP_BrowserReload,
        "search":       QtWidgets.QStyle.SP_FileDialogContentsView,
        "select_mp":    QtWidgets.QStyle.SP_DirOpenIcon,
        # PySide6 não possui SP_DialogPrintButton; usar ícone de ficheiro.
        "print":        QtWidgets.QStyle.SP_FileIcon,
        # fallback comum
        "file":         QtWidgets.QStyle.SP_FileIcon,
    }

    CENTER_ALIGN_FIELDS = {
        "preco_tab", "preco_liq", "margem", "desconto", "und", "desp",
        "orl_0_4", "orl_1_0", "comp_mp", "larg_mp", "esp_mp",
    }

    COLUMN_DEFAULT_WIDTHS: Dict[str, int] = {
        "grupo_material": 180,
        "grupo_ferragem": 180,
        "grupo_sistema": 200,
        "grupo_acabamento": 200,
        "descricao": 200,
        "ref_le": 120,
        "descricao_material": 320,
        "preco_tab": 90,
        "preco_liq": 100,
        "margem": 80,
        "desconto": 80,
        "und": 60,
        "desp": 80,
        "tipo": 140,
        "familia": 150,
        "comp_mp": 90,
        "larg_mp": 90,
        "esp_mp": 85,
        "orl_0_4": 85,
        "orl_1_0": 85,
        "id_mp": 90,
        "nao_stock": 95,
    }

    HIDDEN_FIELDS = {"reserva_1", "reserva_2", "reserva_3"}

    def _standard_icon(self, key: str):

        style = self.style() or QtWidgets.QApplication.style()
        return style.standardIcon(self._ICON_MAP.get(key, QtWidgets.QStyle.SP_FileIcon))









    def __init__(
        self,
        parent=None,
        current_user=None,
        *,
        svc_module=svc_dg,
        page_title="Dados Gerais",
        save_button_text="Guardar Dados Gerais",
        menu_save_button_text="Guardar Modelo",
        import_button_text="Importar Modelo",
        import_multi_button_text="Importar Multi Modelos",
    ):



        super().__init__(parent)



        self.current_user = current_user



        self.svc = svc_module



        self.page_title = page_title



        self.save_button_text = save_button_text
        self._base_save_button_text = save_button_text
        self._dirty = False



        self.menu_save_button_text = menu_save_button_text



        self.import_button_text = import_button_text



        self.import_multi_button_text = import_multi_button_text



        self._menus_select_mp = {



            getattr(self.svc, "MENU_MATERIAIS", None),



            getattr(self.svc, "MENU_FERRAGENS", None),



            getattr(self.svc, "MENU_SIS_CORRER", None),



            getattr(self.svc, "MENU_ACABAMENTOS", None),



        }



        self._menus_select_mp = {menu for menu in self._menus_select_mp if menu}



        self.session = SessionLocal()



        self.context: Optional[Any] = None



        self._tipos_cache: List[str] = []
        self._tipos_por_familia: Dict[str, Sequence[str]] = {}


        self._familias_cache: List[str] = []



        self._copied_rows: Dict[str, List[Dict[str, Any]]] = {}



        self.tab_order = [



            "materiais",



            "ferragens",



            "sistemas_correr",



            "acabamentos",



        ]

        self.layout_namespace = getattr(self.svc, "LAYOUT_NAMESPACE", svc_dg.LAYOUT_NAMESPACE)

        self._layout_user_id = getattr(self.current_user, "id", None)

        self._column_layout_cache: Dict[str, Dict[str, int]] = user_layouts.load_table_layout(
            self.session,
            self._layout_user_id,
            self.layout_namespace,
        )

        self._layout_save_timer = QtCore.QTimer(self)

        self._layout_save_timer.setSingleShot(True)

        self._layout_save_timer.timeout.connect(self._persist_column_layouts)

        self._layout_blocking_keys: set[str] = set()




   
        self._setup_ui()

    # ------------------------------------------------------------------ UI

    # --- opções das combos ("Tipo" e "Familia") -------------------------------
    def _tipos_options(self) -> list[str]:
        """Mantido para compatibilidade: devolve família padrão dos Materiais."""
        return self._familia_options_for_menu(self.svc.MENU_MATERIAIS)

    def _tipo_options_for_menu(
        self,
        menu: str,
        index: Optional[QtCore.QModelIndex] = None,
    ) -> list[str]:
        familia = self._familia_value_for_menu(menu, index)
        mapping: Dict[str, Sequence[str]] = getattr(self, "_tipos_por_familia", {})
        options = list(mapping.get(familia.upper(), []))
        if options:
            return options
        if any(mapping.values()):
            return []
        cache = list(getattr(self, "_tipos_cache", []) or [])
        return cache

    def _familia_options_for_menu(
        self,
        menu: str,
        index: Optional[QtCore.QModelIndex] = None,
    ) -> list[str]:
        default = self.svc.MENU_DEFAULT_FAMILIA.get(menu, "PLACAS")
        value = self._familia_value_for_menu(menu, index)
        if not value:
            value = default
        normalized = str(value).strip().upper() or default
        return [normalized]

    def _familia_value_for_menu(
        self,
        menu: str,
        index: Optional[QtCore.QModelIndex] = None,
    ) -> str:
        default = self.svc.MENU_DEFAULT_FAMILIA.get(menu, "PLACAS")
        value: Optional[str] = None
        if index is not None:
            model = index.model()
            if hasattr(model, "row_at"):
                try:
                    row = model.row_at(index.row())
                except Exception:
                    row = None
                if isinstance(row, Mapping):
                    value = row.get("familia")
                elif row is not None:
                    value = getattr(row, "familia", None)
        if not value:
            value = default
        return str(value or default).strip().upper()

    def _tab_title(self, key: str) -> str:
        mapping = {
            self.svc.MENU_MATERIAIS: "Materiais",
            self.svc.MENU_FERRAGENS: "Ferragens",
            self.svc.MENU_SIS_CORRER: "Sistemas Correr",
            self.svc.MENU_ACABAMENTOS: "Acabamentos",
        }
        return mapping.get(key, key.title())

    def _column_width_spec(self, key: str) -> Dict[str, int]:
        return dict(self.COLUMN_DEFAULT_WIDTHS)

    def _default_info_pairs(self) -> List[Tuple[str, QtWidgets.QLabel]]:

        return []

    def _set_dirty(self, dirty: bool) -> None:
        dirty = bool(dirty)
        if getattr(self, "_dirty", False) == dirty:
            return
        self._dirty = dirty
        self._update_save_button_texts()

    def _update_save_button_texts(self) -> None:
        text = self._base_save_button_text
        if getattr(self, "_dirty", False) and not text.endswith("*"):
            text = f"{text}*"
        elif not getattr(self, "_dirty", False):
            text = self._base_save_button_text
        for btn in getattr(self, "_save_buttons", []):
            try:
                btn.setText(text)
            except Exception:
                continue
        if getattr(self, "btn_guardar", None) and self.btn_guardar.text() != text:
            self.btn_guardar.setText(text)



    def _clear_layout(self, layout: QtWidgets.QLayout) -> None:

        while layout.count():

            item = layout.takeAt(0)

            widget = item.widget()

            if widget is not None:

                widget.setParent(None)

                continue

            child = item.layout()

            if child is not None:

                self._clear_layout(child)



    def _populate_info_pairs(self, pairs: Sequence[Tuple[str, QtWidgets.QLabel]]) -> None:

        self._clear_layout(self._info_pairs_layout)

        for caption_text, value_label in pairs:

            caption = QLabel(caption_text)

            self._info_pairs_layout.addWidget(caption)

            self._info_pairs_layout.addWidget(value_label)

            self._info_pairs_layout.addSpacing(16)

        self._info_pairs_layout.addStretch(1)

    def _apply_column_layout(self, key: str) -> None:
        table = self.tables.get(key)
        model = self.models.get(key)
        if not table or not model:
            return
        header = table.horizontalHeader()
        header_font = header.font()
        if not header_font.bold():
            header_font.setBold(True)
            header.setFont(header_font)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        saved_widths = self._column_layout_cache.get(key, {})
        self._layout_blocking_keys.add(key)
        try:
            for idx, spec in enumerate(model.columns):
                table.setColumnHidden(idx, not spec.visible)
                if not spec.visible:
                    continue
                width = saved_widths.get(spec.field) or spec.width
                if width:
                    table.setColumnWidth(idx, int(width))
        finally:
            self._layout_blocking_keys.discard(key)
        header.sectionResized.connect(
            lambda logical, _old, new, menu_key=key: self._on_column_resized(menu_key, logical, new)
        )

    def _on_column_resized(self, key: str, logical: int, new_size: int) -> None:
        if key in self._layout_blocking_keys:
            return
        model = self.models.get(key)
        if not model or not (0 <= logical < len(model.columns)):
            return
        field = model.columns[logical].field
        widths = self._column_layout_cache.setdefault(key, {})
        widths[field] = max(40, int(new_size))
        self._layout_save_timer.start(800)

    def _persist_column_layouts(self) -> None:
        if not self._layout_user_id:
            return
        try:
            user_layouts.save_table_layout(
                self.session,
                self._layout_user_id,
                self.layout_namespace,
                self._column_layout_cache,
            )
            self.session.flush()
        except Exception:
            pass

    def _create_model(self, key: str) -> DadosGeraisTableModel:
        header_map = {
            'grupo_material': 'Materiais',
            'grupo_ferragem': 'Ferragens',
            'grupo_sistema': 'Sistemas Correr',
            'grupo_acabamento': 'Acabamentos',
            'ref_le': 'Ref_LE',
            'descricao_material': 'Descrição Material',
            'preco_tab': 'Preço Tabela',
            'preco_liq': 'Preço Líquido',
            'margem': 'Margem',
            'desconto': 'Desconto',
            'und': 'Und',
            'desp': 'Desp',
            'tipo': 'Tipo',
            'familia': 'Família',
            'comp_mp': 'Comp MP',
            'larg_mp': 'Larg MP',
            'esp_mp': 'Esp MP',
            'orl_0_4': 'ORL 0.4',
            'orl_1_0': 'ORL 1.0',
            'linha': 'Linha',
            'custo_mp_und': 'Custo MP Und',
            'custo_mp_total': 'Custo MP Total',
            'spp_ml_und': 'SPP ML Und',
            'custo_acb_und': 'Custo ACB Und',
            'custo_acb_total': 'Custo ACB Total',
        }

        fields = self.svc.MENU_FIELDS.get(key, ())
        field_set = set(fields)
        field_types = self.svc.MENU_FIELD_TYPES.get(key, {})
        kind_map = {kind: set(values) for kind, values in field_types.items()}
        primary = self.svc.MENU_PRIMARY_FIELD.get(key)

        width_spec = self._column_width_spec(key)
        columns: List[ColumnSpec] = []
        for field in fields:
            header = header_map.get(field, field.replace('_', ' ').title())
            kind = 'text'
            if field in kind_map.get('money', ()):
                kind = 'money'
            elif field in kind_map.get('percent', ()):
                kind = 'percent'
            elif field in kind_map.get('integer', ()):
                kind = 'integer'
            elif field in kind_map.get('decimal', ()):
                kind = 'decimal'
            elif field in kind_map.get('bool', ()):
                kind = 'bool'

            options = None
            if field == 'tipo':
                kind = 'choice'
                options = lambda idx, menu=key: self._tipo_options_for_menu(menu, idx)
            elif field == 'familia':
                kind = 'choice'
                options = lambda idx, menu=key: self._familia_options_for_menu(menu, idx)

            readonly = field in {primary, 'id', 'id_mp', 'preco_liq', 'ref_le'}
            width = width_spec.get(field)
            visible = field not in self.HIDDEN_FIELDS
            columns.append(
                ColumnSpec(
                    header,
                    field,
                    kind,
                    width=width,
                    readonly=readonly,
                    options=options,
                    visible=visible,
                )
            )

        needs_preco_liq = {"preco_tab", "preco_liq", "margem", "desconto"}.issubset(field_set)
        model_cls = MateriaisTableModel if needs_preco_liq else DadosGeraisTableModel
        model = model_cls(columns=columns, parent=self)
        setattr(model, "svc", self.svc)
        return model

    def _setup_ui(self) -> None:



        root = QVBoxLayout(self)



        root.setContentsMargins(8, 8, 8, 8)

        root.setSpacing(8)



        header = QtWidgets.QWidget(self)

        grid = QGridLayout(header)

        grid.setContentsMargins(0, 0, 0, 0)

        grid.setHorizontalSpacing(12)

        grid.setVerticalSpacing(4)



        self.lbl_title = QLabel(self.page_title)

        title_font = self.lbl_title.font()

        title_font.setBold(True)

        title_font.setPointSize(title_font.pointSize() + 2)

        self.lbl_title.setFont(title_font)



        self.lbl_cliente = QLabel("-")

        self.lbl_utilizador = QLabel("-")

        self.lbl_ano = QLabel("-")

        self.lbl_num = QLabel("-")

        self.lbl_ver = QLabel("-")

        self.lbl_highlight = QLabel("")
        init_highlight_label(self.lbl_highlight)



        grid.addWidget(self.lbl_title, 0, 0, 1, 4)
        grid.addWidget(self.lbl_highlight, 1, 0, 1, 6)





        self._header_grid = grid





        grid.setColumnStretch(0, 0)





        grid.setColumnStretch(1, 0)





        grid.setColumnStretch(2, 0)





        grid.setColumnStretch(3, 1)





        grid.setColumnStretch(4, 0)





        grid.setColumnStretch(5, 0)





        self._info_pairs_layout = QHBoxLayout()





        self._info_pairs_layout.setContentsMargins(0, 0, 0, 0)





        self._info_pairs_layout.setSpacing(16)





        grid.addLayout(self._info_pairs_layout, 2, 0, 1, 6)





        self._populate_info_pairs(self._default_info_pairs())





        lbl_altura_caption = QLabel("Altura:")

        lbl_largura_caption = QLabel("Largura:")

        lbl_profundidade_caption = QLabel("Profundidade:")

        self.lbl_altura = QLabel("-")

        self.lbl_largura = QLabel("-")

        self.lbl_profundidade = QLabel("-")



        self._dimension_labels = {

            "captions": [lbl_altura_caption, lbl_largura_caption, lbl_profundidade_caption],

            "values": [self.lbl_altura, self.lbl_largura, self.lbl_profundidade],

        }







        self._dimensions_layout = QHBoxLayout()





        self._dimensions_layout.setContentsMargins(0, 0, 0, 0)





        self._dimensions_layout.setSpacing(16)





        grid.addLayout(self._dimensions_layout, 3, 0, 1, 6)





        for caption, value in zip(





            self._dimension_labels["captions"],





            self._dimension_labels["values"],





        ):





            self._dimensions_layout.addWidget(caption)





            self._dimensions_layout.addWidget(value)





            self._dimensions_layout.addSpacing(16)





        self._dimensions_layout.addStretch(1)





        # Botão global de guardar movido para a barra de ferramentas de cada separador.



        root.addWidget(header)



        self._update_dimensions_labels(visible=False)



        self.tabs = QTabWidget(self)

        root.addWidget(self.tabs, 1)



        self.models: Dict[str, DadosGeraisTableModel] = {}

        self.tables: Dict[str, QTableView] = {}

        self._save_buttons: List[QtWidgets.QPushButton] = []

        self.btn_guardar: Optional[QtWidgets.QPushButton] = None



        for key in self.tab_order:

            widget = QtWidgets.QWidget()

            layout = QVBoxLayout(widget)

            layout.setContentsMargins(0, 0, 0, 0)

            layout.setSpacing(4)



            toolbar = QHBoxLayout()

            toolbar.setSpacing(6)



            btn_save_model = QPushButton(self.menu_save_button_text)

            btn_save_model.setIcon(self._standard_icon("save"))

            btn_save_model.clicked.connect(lambda _, k=key: self.on_guardar_modelo(k))



            btn_import_model = QPushButton(self.import_button_text)

            btn_import_model.setIcon(self._standard_icon("import"))

            btn_import_model.clicked.connect(lambda _, k=key: self.on_importar_modelo(k))



            btn_import_multi = QPushButton(self.import_multi_button_text)

            btn_import_multi.setIcon(self._standard_icon("import_multi"))

            btn_import_multi.clicked.connect(self.on_importar_multi_modelos)



            toolbar.addWidget(btn_save_model)

            toolbar.addWidget(btn_import_model)

            toolbar.addWidget(btn_import_multi)



            btn_select_mp = QPushButton("Selecionar Materia-Prima")

            btn_select_mp.setIcon(self._standard_icon("select_mp"))

            btn_select_mp.clicked.connect(lambda _, k=key: self.on_selecionar_mp(k))

            btn_select_mp.setVisible(key in self._menus_select_mp)

            toolbar.addWidget(btn_select_mp)



            btn_guardar_tab = QPushButton(self.save_button_text)

            btn_guardar_tab.setIcon(self._standard_icon("save"))

            btn_guardar_tab.clicked.connect(self.on_guardar)

            toolbar.addWidget(btn_guardar_tab)

            self._save_buttons.append(btn_guardar_tab)

            if self.btn_guardar is None:

                self.btn_guardar = btn_guardar_tab



            toolbar.addStretch(1)



            layout.addLayout(toolbar)



            table = QTableView(self)

            table.setSelectionBehavior(QAbstractItemView.SelectRows)

            table.setSelectionMode(QAbstractItemView.ExtendedSelection)
            table.setAlternatingRowColors(True)
            table.setItemDelegate(DadosGeraisDelegate(table))

            table.horizontalHeader().setStretchLastSection(False)

            table.setStyleSheet(

                "QTableView::item:selected{background-color:#555555;color:#ffffff;}"

                "QTableView::item:selected:!active{background-color:#666666;color:#ffffff;}"

            )

            table.setSortingEnabled(True)

            table.setEditTriggers(
                QAbstractItemView.EditTrigger.DoubleClicked
                | QAbstractItemView.EditTrigger.SelectedClicked
                | QAbstractItemView.EditTrigger.EditKeyPressed
                | QAbstractItemView.EditTrigger.AnyKeyPressed
            )

            table.setContextMenuPolicy(Qt.CustomContextMenu)

            table.customContextMenuRequested.connect(lambda pos, k=key: self._on_context_menu(pos, k))

            layout.addWidget(table, 1)



            self.tabs.addTab(widget, self._tab_title(key))



            model = self._create_model(key)

            self.models[key] = model

            self.tables[key] = table

            table.setModel(model)
            try:
                model.dataChanged.connect(lambda *_, **__: self._set_dirty(True))
                model.rowsInserted.connect(lambda *_, **__: self._set_dirty(True))
                model.rowsRemoved.connect(lambda *_, **__: self._set_dirty(True))
            except Exception:
                pass

            self._apply_column_layout(key)




            self._post_table_setup(key)

            self._configure_delegates(key)

        self._update_save_button_texts()


    # --- delegates por coluna (combos, etc.) ----------------------------------
    def _configure_delegates(self, key: str) -> None:
        """
        Atribui delegates às colunas que precisam de editor customizado.
        Neste momento, apenas 'choice' usa um QComboBox (ChoiceDelegate).
        """
        table = self.tables.get(key)
        model = self.models.get(key)
        if not table or not model:
            return

        # Limpa delegates antigos (opcional; o Qt troca automaticamente)
        # for col in range(table.model().columnCount()):
        #     table.setItemDelegateForColumn(col, None)

        for col_idx, spec in enumerate(model.columns):
            if spec.kind == "choice" and callable(spec.options):
                table.setItemDelegateForColumn(col_idx, ChoiceDelegate(spec.options, table))
            elif spec.kind == "bool":
                # um delegate simples para checkbox, evita o dropdown True/False
                table.setItemDelegateForColumn(col_idx, BoolDelegate(table))
    



    def _clipboard_data(self) -> Dict[str, Any]:

        data = getattr(type(self), "_shared_clipboard", None)

        if not isinstance(data, dict):

            data = {"menu": None, "rows": []}

            type(self)._shared_clipboard = data

        data.setdefault("menu", None)

        data.setdefault("rows", [])

        return data



    def _format_dimension_value(self, value: Any) -> str:

        if value in (None, "", 0, 0.0):

            return "-"

        try:

            return _decimal(Decimal(str(value)), places=1)

        except Exception:

            return str(value)



    def _update_dimensions_labels(self, *, altura=None, largura=None, profundidade=None, visible: bool = False) -> None:

        widgets = getattr(self, "_dimension_labels", None)

        if not widgets:

            return

        captions = widgets.get("captions", [])

        values = widgets.get("values", [])

        formatted = [

            self._format_dimension_value(altura),

            self._format_dimension_value(largura),

            self._format_dimension_value(profundidade),

        ]

        for label, value in zip(values, formatted):

            label.setText(value)

        for widget in itertools.chain(captions, values):

            widget.setVisible(visible)



    def _post_table_setup(self, key: str) -> None:
        """Hook para ajustes adicionais; activa clique unico nos checkboxes."""
        table = self.tables.get(key)
        if not table:
            return
        table.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        table.setItemDelegate(DadosGeraisDelegate(table))



    def _selected_rows_from_table(self, table: QTableView) -> List[int]:

        selection = table.selectionModel()

        if not selection:

            return []

        rows = {index.row() for index in selection.selectedRows()}

        if not rows:

            current = table.currentIndex()
            if current.isValid():

                rows.add(current.row())

        return sorted(rows)



    def _copy_rows(self, key: str, row_indices: Sequence[int]) -> None:

        model = self.models.get(key)

        if not model or not row_indices:

            return

        rows_data: List[Dict[str, Any]] = []

        for row_index in row_indices:

            try:

                row = dict(model.row_at(row_index))

            except Exception:

                continue

            row.pop("id", None)

            primary_field = self.svc.MENU_PRIMARY_FIELD.get(key)
            if primary_field:
                row.pop(primary_field, None)


            rows_data.append(row)

        if not rows_data:

            return

        clipboard = self._clipboard_data()

        clipboard["menu"] = key

        clipboard["rows"] = rows_data

        try:

            QtWidgets.QApplication.clipboard().setText(json.dumps(rows_data, ensure_ascii=False))

        except Exception:

            pass



    def _paste_rows(self, key: str, table: QTableView, row_indices: Sequence[int]) -> None:

        model = self.models.get(key)

        if not model:

            return

        clipboard = self._clipboard_data()

        if clipboard.get("menu") != key:

            return

        rows = clipboard.get("rows") or []

        if not rows:

            return

        target_rows = list(row_indices)

        source_count = len(rows)
        if source_count == 1 and target_rows:
            rows = rows * len(target_rows)
            source_count = len(rows)

        primary_field = self.svc.MENU_PRIMARY_FIELD.get(key)

        allowed_fields = {spec.field for spec in model.columns}

        for idx, row_data in enumerate(rows):

            if not isinstance(row_data, dict):

                continue

            target_idx = idx
            if source_count == 1 and target_rows:
                target_idx = min(idx, len(target_rows) - 1)
            if target_idx < len(target_rows):

                target_row = target_rows[target_idx]

            else:

                target_row = model.append_row({})

                target_rows.append(target_row)

            payload = {}

            for field, value in row_data.items():

                if field == "id" or field == primary_field:

                    continue

                if field in allowed_fields:

                    payload[field] = value

            if not payload:

                continue

            model.update_row(target_row, payload)

            if hasattr(model, "recalculate"):

                try:

                    model.recalculate(target_row)  # type: ignore[attr-defined]

                except Exception:

                    pass

        model._reindex()

        if not hasattr(model, "recalculate"):

            self._recalculate_menu_rows(key)
        self._set_dirty(True)

        for row in target_rows:

            table.selectRow(row)
        self._set_dirty(True)



    def _clear_rows(self, key: str, row_indices: Sequence[int]) -> None:

        model = self.models.get(key)

        if not model or not row_indices:

            return

        primary_field = self.svc.MENU_PRIMARY_FIELD.get(key)
        first_column_field = model.columns[0].field if model.columns else None
        protected_fields = {"id", "ordem", "familia", "tipo"}
        if primary_field:
            protected_fields.add(primary_field)
        if first_column_field:
            protected_fields.add(first_column_field)

        for row_index in row_indices:

            clear_data: Dict[str, Any] = {}

            for spec in model.columns:

                field = spec.field

                if field in protected_fields:

                    continue

                if spec.kind == "bool":

                    clear_data[field] = False

                else:

                    clear_data[field] = None

            model.update_row(row_index, clear_data)

            if hasattr(model, "recalculate"):

                try:

                    model.recalculate(row_index)  # type: ignore[attr-defined]

                except Exception:

                    pass

        if not hasattr(model, "recalculate"):

            self._recalculate_menu_rows(key)



    def _on_context_menu(self, pos: QtCore.QPoint, key: str) -> None:

        table = self.tables.get(key)

        if not table:

            return



        index = table.indexAt(pos)
        selection_model = table.selectionModel()
        if selection_model is None or not selection_model.hasSelection():
            if index.isValid():
                table.selectRow(index.row())



        selected_rows = self._selected_rows_from_table(table)

        clipboard = self._clipboard_data()



        menu = QMenu(table)

        action_copy = menu.addAction(self._standard_icon("copy"), "Copiar dados da(s) linha(s)")

        action_copy.setEnabled(bool(selected_rows))



        action_paste = menu.addAction(self._standard_icon("paste"), "Colar dados da(s) linha(s)")

        action_paste.setEnabled(bool(clipboard.get("rows")) and clipboard.get("menu") == key)



        action_clear = menu.addAction(self._standard_icon("clear"), "Limpar dados da(s) linha(s)")

        action_clear.setEnabled(bool(selected_rows))








        action_select_mp = None

        if key in self._menus_select_mp:

            menu.addSeparator()

            action_select_mp = menu.addAction(self._standard_icon("select_mp"), "Selecionar Materia-Prima")



        selected_action = menu.exec(table.viewport().mapToGlobal(pos))

        if selected_action is None:

            return

        if selected_action == action_copy:

            self._copy_rows(key, selected_rows)

        elif selected_action == action_paste:

            self._paste_rows(key, table, selected_rows)

        elif selected_action == action_clear:

            self._clear_rows(key, selected_rows)


        elif action_select_mp and selected_action == action_select_mp:

            self.on_selecionar_mp(key)



    # ------------------------------------------------------------------ Data flow



    def load_orcamento(self, orcamento_id: int, *, item_id: Optional[int] = None) -> None:
        try:
            self.session.flush()
        except Exception:
            pass

        try:
            self.session.expire_all()
        except Exception:
            pass

        ctx = None

        if item_id is not None:
            try:
                ctx = self.svc.carregar_contexto(self.session, orcamento_id, item_id=item_id)
            except TypeError:
                ctx = None
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar contexto: {exc}")
                return

        if ctx is None:
            try:
                ctx = self.svc.carregar_contexto(self.session, orcamento_id)
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar contexto: {exc}")
                return

        self.context = ctx
        self._update_dimensions_labels(visible=False)
        self.lbl_title.setText(self.page_title)

        self._carregar_topo(orcamento_id)
        self._carregar_tipos_familias()

        try:
            data = self.svc.carregar_dados_gerais(self.session, ctx)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar dados: {exc}")
            data = {key: [] for key in self.tab_order}

        for key, model in self.models.items():
            rows = data.get(key, [])
            model.load_rows(rows)
            model._reindex()
        self._set_dirty(False)
    def _carregar_topo(self, orcamento_id: int) -> None:

        orc: Orcamento = self.session.get(Orcamento, orcamento_id)
        
        # Se não encontrou na sessão principal, tentar com nova sessão
        if not orc:
            try:
                from Martelo_Orcamentos_V2.app.db import SessionLocal
                with SessionLocal() as tmp_session:
                    orc = tmp_session.get(Orcamento, orcamento_id)
                    if orc:
                        # Copiar dados para evitar issues com session detached
                        orc_data = {
                            'id': orc.id,
                            'client_id': orc.client_id,
                            'ano': orc.ano,
                            'num_orcamento': orc.num_orcamento,
                            'versao': orc.versao,
                            'created_by': orc.created_by,
                        }
                        # Use os dados diretamente sem tentar reatachá-los
                        orc = type('obj', (object,), orc_data)()
            except Exception:
                pass

        cliente_nome = ""
        ano_text = ""
        numero_text = ""
        versao_text = ""
        username = getattr(self.current_user, "username", None) or ""

        if orc:
            if hasattr(self, 'session'):
                cliente: Optional[Client] = self.session.get(Client, orc.client_id) if orc.client_id else None
                user: Optional[User] = self.session.get(User, orc.created_by) if orc.created_by else None
            else:
                cliente = None
                user = None
            
            # Se cliente/user não encontrados na sessão principal, tentar nova sessão
            if not cliente and orc.client_id:
                try:
                    from Martelo_Orcamentos_V2.app.db import SessionLocal
                    with SessionLocal() as tmp_session:
                        cliente = tmp_session.get(Client, orc.client_id)
                except Exception:
                    pass
            
            if not user and orc.created_by:
                try:
                    from Martelo_Orcamentos_V2.app.db import SessionLocal
                    with SessionLocal() as tmp_session:
                        user = tmp_session.get(User, orc.created_by)
                except Exception:
                    pass

            cliente_nome = (getattr(cliente, "nome", "") or "").strip()
            ano_val = getattr(orc, "ano", "")
            ano_text = str(ano_val).strip() if ano_val is not None else ""
            numero_text = str(getattr(orc, "num_orcamento", "") or "")
            versao_raw = getattr(orc, "versao", "")
            try:
                versao_text = f"{int(versao_raw):02d}"
            except Exception:
                versao_text = str(versao_raw or "")
            username = getattr(user, "username", None) or username

        self.lbl_cliente.setText(cliente_nome or "-")
        self.lbl_ano.setText(ano_text or "-")
        self.lbl_num.setText(numero_text or "-")
        self.lbl_ver.setText(versao_text or "-")
        self.lbl_utilizador.setText(username or "-")

        if hasattr(self, "lbl_highlight"):
            apply_highlight_text(
                self.lbl_highlight,
                cliente=cliente_nome,
                numero=numero_text,
                versao=versao_text,
                ano=ano_text,
                utilizador=username,
            )


    def _carregar_tipos_familias(self) -> None:



        try:



            tipos = svc_mp.listar_tipos(self.session)



        except Exception:



            tipos = []
        self._tipos_cache = sorted(dict.fromkeys(tipos or []))


        try:



            mapping = svc_mp.mapear_tipos_por_familia(self.session)



        except Exception:
            mapping = {}
        normalised: Dict[str, Sequence[str]] = {}

        for familia, tipos_lista in mapping.items():

            key = str(familia or "").strip().upper()

            if not key:

                continue


            clean_tipos = [str(t).strip().upper() for t in tipos_lista if t]

            normalised[key] = clean_tipos
        defaults = [

                str(self.svc.MENU_DEFAULT_FAMILIA.get(menu, "PLACAS") or "").strip().upper()

               for menu in self.svc.MENU_FIXED_GROUPS

        ]



        for familia in defaults:

            if familia:

                normalised.setdefault(familia, tuple())

            self._tipos_por_familia = normalised

            familias_cache = [fam for fam in normalised.keys() if fam]

            familias_cache.extend(f for f in defaults if f)

            self._familias_cache = sorted(dict.fromkeys(familias_cache)) or ["PLACAS"]







    # ------------------------------------------------------------------ Actions



    def on_guardar(self):



        if not self.context:



            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum orcamento carregado.")



            return



        payload = {key: model.export_rows() for key, model in self.models.items()}



        try:



            self.svc.guardar_dados_gerais(self.session, self.context, payload)



            self.session.commit()



            QtWidgets.QMessageBox.information(self, "Sucesso", "Dados gerais guardados.")
            self._set_dirty(False)



        except Exception as exc:



            self.session.rollback()



            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao guardar: {exc}")







    def on_add_row(self, key: str):



        model = self.models[key]



        defaults = {"ordem": model.rowCount()}



        primary_field = self.svc.MENU_PRIMARY_FIELD.get(key)



        if primary_field:



            groups = self.svc.MENU_FIXED_GROUPS.get(key, ())



            if groups:



                defaults[primary_field] = groups[0]



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



            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum orcamento carregado.")



            return



        user_id = getattr(self.current_user, "id", None)



        if not user_id:



            QtWidgets.QMessageBox.warning(self, "Aviso", "Utilizador sem ID valido.")



            return



        linhas = self.models[key].export_rows()



        if not linhas:



            QtWidgets.QMessageBox.warning(self, "Aviso", "Nao ha linhas para guardar.")



            return



        dialog = GuardarModeloDialog(
            self.session,
            user_id=user_id,
            tipo_menu=key,
            linhas=linhas,
            parent=self,
            svc_module=self.svc,
            window_title=self.menu_save_button_text,
        )



        if dialog.exec() != QDialog.Accepted:



            return



        try:



            self.svc.guardar_modelo(



                self.session,



                user_id=user_id,



                tipo_menu=key,



                nome_modelo=dialog.model_name,



                linhas=linhas,



                replace_id=dialog.replace_model_id,
                is_global=getattr(dialog, "is_global", False),
                add_timestamp=getattr(dialog, "add_timestamp", False),



            )



            self.session.commit()



            QtWidgets.QMessageBox.information(self, "Sucesso", "Modelo guardado.")



        except Exception as exc:



            self.session.rollback()



            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao guardar modelo: {exc}")











    def on_importar_modelo(self, key: str):



        user_id = getattr(self.current_user, "id", None)



        if not user_id:



            QtWidgets.QMessageBox.warning(self, "Aviso", "Utilizador sem ID valido.")



            return



        modelos_existentes = self.svc.listar_modelos(self.session, user_id=user_id, tipo_menu=key)



        if not modelos_existentes:



            QtWidgets.QMessageBox.information(self, "Info", "Sem modelos guardados para este submenu.")



            return



        dialog = ImportarModeloDialog(self.session, user_id=user_id, tipo_menu=key, parent=self, svc_module=self.svc, window_title=self.import_button_text)



        if dialog.exec() != QDialog.Accepted:



            return



        if not dialog.selected_lines:



            return



        self._apply_imported_rows(key, dialog.selected_lines, replace=dialog.replace_existing)











    def _merge_with_materias_primas(self, rows: List[Dict[str, Any]], menu: str) -> List[Dict[str, Any]]:
        """
        Preenche campos faltantes a partir de materias_primas (match por ref_le) e resolve conflitos via dialogo.
        """
        fill_fields = {"desp", "orl_0_4", "orl_1_0", "comp_mp", "larg_mp", "esp_mp", "id_mp", "nao_stock"}
        compare_fields = ["ref_le", "descricao_material", "preco_tab", "preco_liq", "margem", "desconto", "und"]
        conflicts: Dict[int, Dict[str, Any]] = {}
        merged: List[Dict[str, Any]] = []
        mp_cache: Dict[int, Any] = {}

        label_field_map = {
            self.svc.MENU_MATERIAIS: "grupo_material",
            self.svc.MENU_FERRAGENS: "grupo_ferragem",
            self.svc.MENU_SIS_CORRER: "grupo_sistema",
            self.svc.MENU_ACABAMENTOS: "grupo_acabamento",
        }
        label_header_map = {
            self.svc.MENU_MATERIAIS: "Materiais",
            self.svc.MENU_FERRAGENS: "Ferragens",
            self.svc.MENU_SIS_CORRER: "Sistemas Correr",
            self.svc.MENU_ACABAMENTOS: "Acabamentos",
        }
        label_field = label_field_map.get(menu, "label")
        line_header = label_header_map.get(menu, "Linha")
        table_model_for_menu = None
        try:
            table_for_menu = self.tables.get(menu)
            table_model_for_menu = table_for_menu.model() if table_for_menu else None
        except Exception:
            table_model_for_menu = None

        try:
            current_rows = self.models.get(menu).export_rows()  # type: ignore[union-attr]
        except Exception:
            current_rows = []

        def _fmt_one_dec(val: Any):
            try:
                from decimal import Decimal
                return float(Decimal(str(val)).quantize(Decimal("0.1")))
            except Exception:
                try:
                    return round(float(val), 1)
                except Exception:
                    return val

        def _norm(val: Any) -> Any:
            if val is None:
                return None
            if isinstance(val, (int, float)):
                return float(val)
            return str(val).strip()

        def _is_close(a: Any, b: Any, field: str) -> bool:
            if a in (None, "") and b in (None, ""):
                return True
            try:
                fa = float(a)
                fb = float(b)
                if field in {"preco_tab", "preco_liq"}:
                    return abs(fa - fb) < 0.01
                if field in {"margem", "desconto"}:
                    return abs(fa - fb) < 0.0001
            except Exception:
                pass
            return _norm(a) == _norm(b)

        def _mp_value(mp_obj: Any, field: str) -> Any:
            alias_map = {
                "descricao_material": [
                    "descricao_material",
                    "descricao_no_orcamento",
                    "descricao_orcamento",
                    "DESCRICAO_no_ORCAMENTO",
                    "DESCRICAO_ORCAMENTO",
                ],
                "preco_tab": ["preco_tab", "preco_tabela", "PRECO_TABELA"],
                "preco_liq": ["preco_liq", "pliq", "PLIQ", "PRECO_LIQ"],
                "margem": ["margem", "MARGEM"],
                "desconto": ["desconto", "DESCONTO"],
                "ref_le": ["ref_le", "REF_LE", "Ref_LE"],
                "und": ["und", "UND"],
            }
            keys = alias_map.get(field, [field])
            for k in keys:
                try:
                    val = getattr(mp_obj, k)
                except Exception:
                    val = None
                if val not in (None, ""):
                    return val
            return None

        def _first_label(candidates: List[Any]) -> str:
            for cand in candidates:
                if cand is None:
                    continue
                if isinstance(cand, str):
                    val = cand.strip()
                    if val and not val.isdigit():
                        return val
                else:
                    try:
                        float(cand)
                        continue
                    except Exception:
                        pass
                    return str(cand)
            for cand in candidates:
                if cand not in (None, ""):
                    return str(cand).strip()
            return ""

        def _label_from_table(row_idx: int) -> Any:
            if table_model_for_menu is None:
                return None
            try:
                item = table_model_for_menu.item(row_idx, 0)  # type: ignore[attr-defined]
                if item:
                    return item.text()
            except Exception:
                pass
            try:
                idx_qt = table_model_for_menu.index(row_idx, 0)  # type: ignore[attr-defined]
                if idx_qt.isValid():
                    return idx_qt.data()
            except Exception:
                pass
            return None

        for idx, row in enumerate(rows):
            new_row = dict(row)
            ref_le = (new_row.get("ref_le") or "").strip()
            mp = svc_mp.get_materia_prima_by_ref_le(self.session, ref_le) if ref_le else None
            if mp:
                mp_cache[idx] = mp
                for field in fill_fields:
                    mp_val = getattr(mp, field, None)
                    if field in {"comp_mp", "larg_mp", "esp_mp"} and mp_val not in (None, ""):
                        mp_val = _fmt_one_dec(mp_val)
                    if mp_val is None:
                        continue
                    if new_row.get(field) in (None, ""):
                        new_row[field] = mp_val

                model_subset = {f: new_row.get(f) for f in compare_fields}
                mp_subset = {f: _mp_value(mp, f) for f in compare_fields}
                if any(not _is_close(model_subset.get(f), mp_subset.get(f), f) for f in compare_fields):
                    mp_full = {
                        "ref_le": getattr(mp, "ref_le", None),
                        "descricao_no_orcamento": getattr(mp, "descricao_no_orcamento", None)
                        or getattr(mp, "descricao_orcamento", None)
                        or getattr(mp, "DESCRICAO_no_ORCAMENTO", None)
                        or getattr(mp, "DESCRICAO_NO_ORCAMENTO", None)
                        or getattr(mp, "DESCRICAO_ORCAMENTO", None),
                        "descricao_material": getattr(mp, "descricao_material", None)
                        or getattr(mp, "DESCRICAO_MATERIAL", None),
                        "preco_tab": getattr(mp, "preco_tab", None) or getattr(mp, "PRECO_TAB", None),
                        "preco_tabela": getattr(mp, "preco_tabela", None) or getattr(mp, "PRECO_TABELA", None),
                        "preco_liq": getattr(mp, "preco_liq", None) or getattr(mp, "PRECO_LIQ", None),
                        "pliq": getattr(mp, "pliq", None) or getattr(mp, "PLIQ", None),
                        "margem": getattr(mp, "margem", None) or getattr(mp, "MARGEM", None),
                        "desconto": getattr(mp, "desconto", None) or getattr(mp, "DESCONTO", None),
                        "und": getattr(mp, "und", None) or getattr(mp, "UND", None),
                    }
                    label_candidates = [
                        _label_from_table(idx),
                        current_rows[idx].get(label_field) if idx < len(current_rows) else None,
                        new_row.get(label_field),
                        new_row.get("materiais"),
                        new_row.get("ferragens"),
                        new_row.get("sistemas_correr"),
                        new_row.get("acabamentos"),
                        new_row.get("linha"),
                        new_row.get("descricao"),
                        new_row.get("descricao_material"),
                        new_row.get("ref_le"),
                    ]
                    conflicts[idx] = {
                        "model": model_subset,
                        "mp": mp_subset,
                        "mp_full": mp_full,
                        "label": _first_label(label_candidates),
                        "line_header": line_header,
                    }
            merged.append(new_row)

        if conflicts:
            dialog = MateriaPrimaConflictDialogDG(conflicts, parent=self, line_header=line_header)
            if dialog.exec() == QtWidgets.QDialog.Accepted:
                choices = dialog.selected_sources()
                for row_idx, use_mp in choices.items():
                    if not (0 <= row_idx < len(merged)):
                        continue
                    mp = mp_cache.get(row_idx)
                    if not mp:
                        continue
                    mp_subset = conflicts[row_idx]["mp"]
                    if use_mp:
                        for field, val in mp_subset.items():
                            merged[row_idx][field] = val
                        for field in fill_fields:
                            mp_val = getattr(mp, field, merged[row_idx].get(field))
                            if field in {"comp_mp", "larg_mp", "esp_mp"} and mp_val not in (None, ""):
                                mp_val = _fmt_one_dec(mp_val)
                            merged[row_idx][field] = mp_val

        return merged

    def _apply_imported_rows(self, key: str, rows: Sequence[Mapping[str, Any]], *, replace: bool) -> None:
        """
        Importa linhas de modelo para o quadro atual.
        - Se replace=True: sobrepõe por chave (primary) nas linhas existentes, preservando tipo/familia e valores não enviados.
        - Se replace=False: mantém linhas atuais e acrescenta as que não encontrarem chave.
        """
        model = self.models[key]
        primary_field = self.svc.MENU_PRIMARY_FIELD.get(key)
        prepared_rows = [dict(r) for r in rows if isinstance(r, Mapping)]
        if not prepared_rows:
            return

        def _norm(val: Any) -> str:
            if val is None:
                return ""
            return str(val).strip().upper()

        existing_rows = model.export_rows()
        merged_rows: List[Dict[str, Any]] = list(existing_rows)
        primary_index: Dict[str, int] = {}
        if primary_field:
            for idx, row in enumerate(existing_rows):
                marker = _norm(row.get(primary_field))
                if marker and marker not in primary_index:
                    primary_index[marker] = idx

        for incoming in prepared_rows:
            marker = _norm(incoming.get(primary_field)) if primary_field else ""
            target_idx = primary_index.get(marker) if marker else None
            payload = {k: v for k, v in incoming.items() if k not in {"id", "ordem", "tipo", "familia"} and v not in (None, "")}

            if target_idx is not None:
                base = dict(merged_rows[target_idx] or {})
                base.update(payload)
                merged_rows[target_idx] = base
            else:
                # sem chave -> apenas adiciona se estamos em modo append/mesclar
                if replace:
                    continue
                merged_rows.append(payload)

        merged_rows = self._merge_with_materias_primas(merged_rows, key)
        model.load_rows(merged_rows)

        model._reindex()

        if hasattr(model, "recalculate"):
            for idx in range(model.rowCount()):
                try:
                    model.recalculate(idx)  # type: ignore[attr-defined]
                except Exception:
                    continue
        else:
            self._recalculate_menu_rows(key)
        self._set_dirty(True)


    def _recalculate_menu_rows(self, key: str) -> None:



        model = self.models[key]



        for idx in range(model.rowCount()):



            try:



                row = model.row_at(idx)



            except Exception:



                row = None



            if not row:



                continue



            preco_liq = self.svc.calcular_preco_liq(row.get("preco_tab"), row.get("margem"), row.get("desconto"))



            if preco_liq is not None:



                updated = dict(row)



                updated["preco_liq"] = preco_liq



                model.update_row(idx, updated)







    def on_importar_multi_modelos(self):



        user_id = getattr(self.current_user, "id", None)



        if not user_id:



            QtWidgets.QMessageBox.warning(self, "Aviso", "Utilizador sem ID valido.")



            return



        dialog = ImportarMultiModelosDialog(self.session, user_id=user_id, parent=self, svc_module=self.svc, window_title=self.import_multi_button_text)



        if dialog.exec() != QDialog.Accepted:



            return



        if not dialog.selections:



            return



        for menu, info in dialog.selections.items():



            modelo_id = info.get("modelo_id")



            if not modelo_id:



                continue



            try:



                data = self.svc.carregar_modelo(self.session, modelo_id, user_id=user_id)



            except Exception as exc:



                QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar modelo: {exc}")



                continue



            linhas = data.get("linhas", [])



            if not linhas:



                continue



            self._apply_imported_rows(menu, linhas, replace=info.get("replace", True))







    def on_selecionar_mp(self, key: str) -> None:



        table = self.tables.get(key)



        model = self.models.get(key)



        if not table or not model:



            return



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

            preco_liq = self.svc.calcular_preco_liq(materia.preco_tabela, margem, desconto)



        update_candidates = {



            "ref_le": materia.ref_le,



            "descricao_material": materia.descricao_orcamento,



            "preco_tab": materia.preco_tabela,



            "margem": margem,



            "desconto": desconto,



            "preco_liq": preco_liq,



            "und": materia.und,



            "desp": desp,



            "orl_0_4": getattr(materia, "orl_0_4", None),



            "orl_1_0": getattr(materia, "orl_1_0", None),



            "tipo": materia.tipo,



            "familia": materia.familia or current_row.get("familia"),



            "comp_mp": int(materia.comp_mp) if materia.comp_mp not in (None, "") else None,



            "larg_mp": int(materia.larg_mp) if materia.larg_mp not in (None, "") else None,



            "esp_mp": int(materia.esp_mp) if materia.esp_mp not in (None, "") else None,



            "id_mp": materia.id_mp,



            "nao_stock": bool(getattr(materia, "stock", 0)),



        }



        allowed_fields = {spec.field for spec in model.columns}



        update_data = {k: v for k, v in update_candidates.items() if k in allowed_fields}



        if not update_data:



            return



        model.update_row(idx.row(), update_data)



        if hasattr(model, "recalculate"):



            model.recalculate(idx.row())



    # ------------------------------------------------------------------ Cleanup



    def closeEvent(self, event):



        try:



            self.session.close()



        finally:



            super().closeEvent(event)































PREVIEW_COLUMNS = {



    "materiais": [



        ("Materiais", "grupo_material", "text"),



        ("Ref_LE", "ref_le", "text"),



        ("Descricao", "descricao_material", "text"),



        ("Preco Tab", "preco_tab", "money"),



        ("Preco Liq", "preco_liq", "money"),



        ("Margem", "margem", "percent"),



        ("Desconto", "desconto", "percent"),



        ("Und", "und", "text"),



    ],



    "ferragens": [



        ("Ferragens", "grupo_ferragem", "text"),



        ("Ref_LE", "ref_le", "text"),



        ("Descricao", "descricao_material", "text"),



        ("Preco Tab", "preco_tab", "money"),



        ("Preco Liq", "preco_liq", "money"),



        ("Margem", "margem", "percent"),



        ("Desconto", "desconto", "percent"),



        ("Und", "und", "text"),



    ],



    "sistemas_correr": [



        ("Sistemas Correr", "grupo_sistema", "text"),



        ("Ref_LE", "ref_le", "text"),



        ("Descricao", "descricao_material", "text"),



        ("Preco Tab", "preco_tab", "money"),



        ("Preco Liq", "preco_liq", "money"),



        ("Margem", "margem", "percent"),



        ("Desconto", "desconto", "percent"),



        ("Und", "und", "text"),



    ],



    "acabamentos": [



        ("Acabamentos", "grupo_acabamento", "text"),



        ("Ref_LE", "ref_le", "text"),



        ("Descricao", "descricao_material", "text"),



        ("Preco Tab", "preco_tab", "money"),



        ("Preco Liq", "preco_liq", "money"),



        ("Margem", "margem", "percent"),



        ("Desconto", "desconto", "percent"),



        ("Und", "und", "text"),



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
    def __init__(self, session, user_id: int, tipo_menu: str, linhas: Sequence[Mapping[str, Any]], parent=None, *, svc_module, window_title: Optional[str] = None):
        super().__init__(parent)
        self.session = session
        self.user_id = user_id
        self.tipo_menu = tipo_menu
        if svc_module is None:
            raise ValueError("GuardarModeloDialog requires svc_module")
        self.svc = svc_module
        self.global_prefix = getattr(self.svc, "GLOBAL_PREFIX", "__GLOBAL__|")
        self.window_title = window_title or "Guardar Modelo"
        self.setWindowTitle(self.window_title)

        self.linhas = [dict(row) for row in linhas]
        self.models = self.svc.listar_modelos(self.session, user_id=user_id, tipo_menu=tipo_menu)
        self.replace_model_id: Optional[int] = None
        self.model_name: str = ""
        self.is_global: bool = False
        self.add_timestamp: bool = True

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
        self.chk_timestamp = QCheckBox("Adicionar data/hora ao nome")
        self.chk_timestamp.setChecked(True)
        form.addRow("", self.chk_timestamp)
        self.chk_global = QCheckBox("Disponibilizar como Global (todos os utilizadores)")
        form.addRow("", self.chk_global)
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
        return [dict(row) for row in self.linhas]

    def _display_name(self, model) -> str:
        name = getattr(model, "nome_modelo", "") or ""
        is_global = name.startswith(self.global_prefix)
        clean = name[len(self.global_prefix):] if is_global else name
        label = f"[Global] {clean}" if is_global else clean
        created = getattr(model, "created_at", None)
        if created:
            label += f" ({created})"
        return label

    def _populate_models(self) -> None:
        self.models_list.clear()
        for model in self.models:
            item = QListWidgetItem(self._display_name(model))
            item.setData(Qt.UserRole, model.id)
            self.models_list.addItem(item)

    def _populate_preview(self) -> None:
        columns = PREVIEW_COLUMNS.get(self.tipo_menu, PREVIEW_COLUMNS["ferragens"])
        rows = self._filtered_lines()
        limit = min(len(rows), 12)
        self.preview_table.setColumnCount(len(columns))
        self.preview_table.setRowCount(limit)
        for col_idx, (header, _, _) in enumerate(columns):
            item = QtWidgets.QTableWidgetItem(header)
            f = item.font(); f.setBold(True); item.setFont(f)
            self.preview_table.setHorizontalHeaderItem(col_idx, item)
        for row_idx in range(limit):
            row_data = rows[row_idx]
            for col_idx, (_, key, kind) in enumerate(columns):
                item = QtWidgets.QTableWidgetItem(_format_preview_value(kind, row_data.get(key)))
                self.preview_table.setItem(row_idx, col_idx, item)
        self.preview_table.resizeColumnsToContents()

    def _on_model_selected(self) -> None:
        item = self.models_list.currentItem()
        if not item:
            self.preview_table.clearContents()
            self.preview_table.setRowCount(0)
            return
        model_id = item.data(Qt.UserRole)
        current_model = next((m for m in self.models if m.id == model_id), None)
        self.current_model = current_model
        if not current_model:
            return
        self.model_name = current_model.nome_modelo
        try:
            self.current_lines = self.svc.carregar_modelo(self.session, current_model.id)["linhas"]
        except Exception:
            self.current_lines = []
        self.preview_table.clearContents()
        self.preview_table.setRowCount(len(self.current_lines))
        columns = PREVIEW_COLUMNS.get(self.tipo_menu, PREVIEW_COLUMNS["ferragens"])
        for row_idx, row_data in enumerate(self.current_lines):
            for col_idx, (_, key, kind) in enumerate(columns):
                item = QtWidgets.QTableWidgetItem(_format_preview_value(kind, row_data.get(key)))
                self.preview_table.setItem(row_idx, col_idx, item)
        self.preview_table.resizeColumnsToContents()

    def accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Indique um nome para o modelo.")
            return
        self.add_timestamp = self.chk_timestamp.isChecked()
        self.is_global = self.chk_global.isChecked()

        replace_id: Optional[int] = None
        target_name = f"{self.global_prefix if self.is_global else ''}{name}".lower()
        for model in self.models:
            existing_name = (getattr(model, "nome_modelo", "") or "").lower()
            if existing_name == target_name:
                answer = QtWidgets.QMessageBox.question(
                    self,
                    "Substituir",
                    f"Ja existe um modelo chamado '{name}'. Deseja substituir?",
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



    def __init__(self, session, user_id: int, tipo_menu: str, parent=None, *, svc_module, window_title: Optional[str] = None):







        super().__init__(parent)







        self.session = session







        self.user_id = user_id







        self.tipo_menu = tipo_menu







        if svc_module is None:







            raise ValueError("ImportarModeloDialog requires svc_module")







        self.svc = svc_module







        self.window_title = window_title or "Importar Modelo"







        self.setWindowTitle(self.window_title)







        self.models = self.svc.listar_modelos(self.session, user_id=user_id, tipo_menu=tipo_menu)



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



        self.btn_clear_selection = QPushButton("Limpar Selecao")



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



        fields = self.svc.MENU_FIELDS.get(self.tipo_menu, ())



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



            data = self.svc.carregar_modelo(self.session, model_id, user_id=self.user_id)



        except Exception as exc:



            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar modelo: {exc}")



            return



        self.current_model = data.get("modelo")



        self.current_lines = [dict(row) for row in data.get("linhas", [])]



        self.display_lines = self._filtered_lines(self.current_lines)



        self._populate_lines_table()







    def _populate_lines_table(self) -> None:



        columns = PREVIEW_COLUMNS.get(self.tipo_menu, PREVIEW_COLUMNS["ferragens"])



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



            self.svc.eliminar_modelo(self.session, modelo_id=model_id, user_id=self.user_id)



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



            self.svc.renomear_modelo(self.session, modelo_id=model_id, user_id=self.user_id, novo_nome=new_name.strip())



            self.session.commit()



        except Exception as exc:



            self.session.rollback()



            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao renomear: {exc}")



            return



        self.models = self.svc.listar_modelos(self.session, user_id=self.user_id, tipo_menu=self.tipo_menu)



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



    def __init__(self, session, user_id: int, parent=None, *, svc_module, window_title: Optional[str] = None):







        super().__init__(parent)







        self.session = session







        self.user_id = user_id







        if svc_module is None:







            raise ValueError("ImportarMultiModelosDialog requires svc_module")







        self.svc = svc_module







        self.window_title = window_title or "Importar Multi Modelos"







        self.setWindowTitle(self.window_title)







        self.selections: Dict[str, Dict[str, Any]] = {}







        self.setWindowTitle("Importar Multi Modelos")



        self.resize(600, 420)







        layout = QVBoxLayout(self)



        self.sections: Dict[str, Dict[str, Any]] = {}



        for menu, titulo in (



            ("materiais", "Materiais"),



            ("ferragens", "Ferragens"),



            ("sistemas_correr", "Sistemas Correr"),



            ("acabamentos", "Acabamentos"),



        ):



            box = QGroupBox(titulo)



            box_layout = QVBoxLayout(box)



            combo = QComboBox()



            combo.addItem("(nenhum)", None)



            modelos = self.svc.listar_modelos(self.session, user_id=self.user_id, tipo_menu=menu)



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



            QtWidgets.QMessageBox.information(self, "Informacao", "Selecione pelo menos um modelo.")



            return



        self.selections = selections

        super().accept()


class MateriaPrimaConflictDialogDG(QtWidgets.QDialog):
    COLS_DISPLAY = [
        ("ref_le", "Ref_LE"),
        ("descricao_material", "Descrição Material"),
        ("preco_tab", "Preço Tabela"),
        ("preco_liq", "Preço Líquido"),
        ("margem", "Margem"),
        ("desconto", "Desconto"),
        ("und", "Und"),
    ]

    def __init__(self, conflicts: Mapping[int, Mapping[str, Any]], parent=None, line_header: str = "Linha") -> None:
        super().__init__(parent)
        self.setWindowTitle("Diferenças entre Dados do Modelo vs Matérias-Primas")
        self.resize(1900, 840)
        self._choices: Dict[int, bool] = {}  # row_idx -> use_mp
        self._conflicts = conflicts
        self._line_header = line_header

        layout = QtWidgets.QVBoxLayout(self)
        info = QtWidgets.QLabel(
            "Foram encontradas diferenças entre o modelo importado e a tabela de Matérias-Primas.\n"
            "Para cada linha, escolha se pretende aplicar os valores do Modelo ou da Matéria-Prima."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)

        self.table_model = QtWidgets.QTableWidget()
        self.COLS_MODEL = [("label", line_header)] + self.COLS_DISPLAY
        self.table_model.setColumnCount(len(self.COLS_MODEL) + 1)
        self.table_model.setHorizontalHeaderLabels(["Usar Modelo"] + [label for _, label in self.COLS_MODEL])
        self.table_model.setRowCount(len(conflicts))

        self.table_mp = QtWidgets.QTableWidget()
        self.table_mp.setColumnCount(len(self.COLS_DISPLAY) + 1)
        self.table_mp.setHorizontalHeaderLabels(["Usar MP"] + [label for _, label in self.COLS_DISPLAY])
        self.table_mp.setRowCount(len(conflicts))

        header_wrapper = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header_wrapper)
        lbl_model = QtWidgets.QLabel("<b>DADOS DO MODELO</b>")
        lbl_mp = QtWidgets.QLabel("<b>DADOS MATÉRIAS-PRIMAS</b>")
        header_layout.addWidget(lbl_model, 1)
        header_layout.addWidget(lbl_mp, 1)
        layout.addWidget(header_wrapper)

        def _format_value(field: str, val: Any) -> str:
            if val is None or val == "":
                return ""
            try:
                num = float(val)
            except Exception:
                return str(val)
            if field in {"preco_tab", "preco_liq"}:
                return f"{num:,.2f} \u20ac"
            if field in {"margem", "desconto"}:
                return f"{num*100:.2f} %"
            return str(val)

        sorted_conflicts = list(conflicts.items())
        self._row_keys = [row_idx for row_idx, _ in sorted_conflicts]
        for r_idx, (row_idx, data) in enumerate(sorted_conflicts):
            model_data = data.get("model", {})
            mp_data = data.get("mp_full") or data.get("mp", {})
            label_val = data.get("label", "")

            chk_model = QtWidgets.QTableWidgetItem()
            chk_model.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            chk_model.setCheckState(QtCore.Qt.Unchecked)
            self.table_model.setItem(r_idx, 0, chk_model)

            chk_mp = QtWidgets.QTableWidgetItem()
            chk_mp.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            chk_mp.setCheckState(QtCore.Qt.Checked)
            self.table_mp.setItem(r_idx, 0, chk_mp)
            self._choices[row_idx] = True

            for c_idx, (field, _) in enumerate(self.COLS_MODEL, start=1):
                val = label_val if field == "label" else model_data.get(field)
                item_model = QtWidgets.QTableWidgetItem(_format_value(field, val))
                self.table_model.setItem(r_idx, c_idx, item_model)

            def _mp_val(*keys: str):
                for k in keys:
                    if k in mp_data and mp_data.get(k) not in (None, ""):
                        return mp_data.get(k)
                    upper = k.upper()
                    if upper in mp_data and mp_data.get(upper) not in (None, ""):
                        return mp_data.get(upper)
                return mp_data.get(keys[0], None)

            mp_display = {
                "ref_le": _mp_val("ref_le"),
                "descricao_material": _mp_val(
                    "descricao_material",
                    "descricao_no_orcamento",
                    "descricao_orcamento",
                    "DESCRICAO_no_ORCAMENTO",
                    "DESCRICAO_ORCAMENTO",
                ),
                "preco_tab": _mp_val("preco_tab", "preco_tabela", "PRECO_TABELA"),
                "preco_liq": _mp_val("preco_liq", "pliq", "PLIQ"),
                "margem": _mp_val("margem", "MARGEM"),
                "desconto": _mp_val("desconto", "DESCONTO"),
                "und": _mp_val("und", "UND"),
            }

            for mp_c_idx, (field, _) in enumerate(self.COLS_DISPLAY, start=1):
                mp_val = mp_display.get(field)
                item_mp = QtWidgets.QTableWidgetItem(_format_value(field, mp_val))
                model_val = model_data.get(field)
                if str(model_val) != str(mp_val):
                    item_mp.setBackground(QtGui.QColor("#e0e0e0"))
                    model_item = self.table_model.item(r_idx, mp_c_idx + 1)
                    if model_item:
                        model_item.setBackground(QtGui.QColor("#e0e0e0"))
                self.table_mp.setItem(r_idx, mp_c_idx, item_mp)

        self.table_model.resizeColumnsToContents()
        self.table_mp.resizeColumnsToContents()
        splitter.addWidget(self.table_model)
        splitter.addWidget(self.table_mp)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.table_model.itemChanged.connect(self._on_model_item_changed)
        self.table_mp.itemChanged.connect(self._on_mp_item_changed)

    def selected_sources(self) -> Dict[int, bool]:
        return dict(self._choices)

    def _toggle_choice(self, row_key: int, use_mp: bool) -> None:
        self._choices[row_key] = use_mp
        row_idx = self._row_keys.index(row_key)
        m_item = self.table_model.item(row_idx, 0)
        p_item = self.table_mp.item(row_idx, 0)
        if not m_item or not p_item:
            return
        with QtCore.QSignalBlocker(self.table_model), QtCore.QSignalBlocker(self.table_mp):
            if use_mp:
                p_item.setCheckState(QtCore.Qt.Checked)
                m_item.setCheckState(QtCore.Qt.Unchecked)
            else:
                m_item.setCheckState(QtCore.Qt.Checked)
                p_item.setCheckState(QtCore.Qt.Unchecked)

    def _on_model_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        row_idx = item.row()
        if not (0 <= row_idx < len(self._row_keys)):
            return
        use_model = item.checkState() == QtCore.Qt.Checked
        self._toggle_choice(self._row_keys[row_idx], use_mp=not use_model)

    def _on_mp_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        row_idx = item.row()
        if not (0 <= row_idx < len(self._row_keys)):
            return
        use_mp = item.checkState() == QtCore.Qt.Checked
        self._toggle_choice(self._row_keys[row_idx], use_mp=use_mp)









