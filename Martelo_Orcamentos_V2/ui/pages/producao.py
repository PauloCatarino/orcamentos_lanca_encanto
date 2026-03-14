import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import QStyle, QFileDialog

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.config import settings as app_settings
from Martelo_Orcamentos_V2.app.utils.display import format_currency_pt, parse_currency_pt
from Martelo_Orcamentos_V2.app.utils.date_utils import format_date_storage, parse_date_value
from Martelo_Orcamentos_V2.app.services import producao_processos as svc_producao
from Martelo_Orcamentos_V2.app.services import producao_workflow as svc_producao_workflow
from Martelo_Orcamentos_V2.app.services import producao_preparacao as svc_producao_preparacao
from Martelo_Orcamentos_V2.app.services import cutrite_automation as svc_cutrite
from Martelo_Orcamentos_V2.app.services.modulos import pasta_imagens_base
from Martelo_Orcamentos_V2.app.services.settings import get_setting
from Martelo_Orcamentos_V2.app.services import feature_flags as svc_features
from Martelo_Orcamentos_V2.app.models.user import User
from Martelo_Orcamentos_V2.ui.dialogs.orcamento_picker import OrcamentoPicker
from Martelo_Orcamentos_V2.ui.dialogs.cutrite_progress import CutRiteProgressDialog
from Martelo_Orcamentos_V2.ui.dialogs.producao_new_process import NovoProcessoDialog
from Martelo_Orcamentos_V2.ui.dialogs.producao_preparacao import ProducaoPreparacaoDialog
from Martelo_Orcamentos_V2.ui.dialogs.producao_versioning import NovaVersaoProcessoDialog, PastasExistentesDialog
from Martelo_Orcamentos_V2.ui.models.qt_table import SimpleTableModel
from Martelo_Orcamentos_V2.ui.pages.producao_table_support import (
    ProcessoExpandDelegate,
    build_producao_table_rows,
    build_search_status_text,
    normalize_filter_text,
    sync_filter_combo,
)
from Martelo_Orcamentos_V2.ui.pages.producao_media_support import (
    build_external_names,
    build_folder_preview_text,
    find_imos_ix_image_path,
    load_scaled_pixmap,
    render_pdf_preview_image,
)
from Martelo_Orcamentos_V2.ui.pages.producao_form_support import (
    build_empty_form_state,
    build_form_state_from_processo,
    build_processo_form_payload,
)
from Martelo_Orcamentos_V2.ui.pages.producao_actions_support import (
    build_lista_material_imos_values,
    build_processo_delete_ui_plan,
    normalize_tipo_pasta_text,
)
from Martelo_Orcamentos_V2.ui.pages.producao_pdf_manager import ProducaoPDFManagerDialog

logger = logging.getLogger(__name__)


def _parse_date_edit(edit: QtWidgets.QDateEdit) -> str:
    try:
        return format_date_storage(edit.date().toPython())
    except Exception:
        return ""


def _set_date_edit(edit: QtWidgets.QDateEdit, text: Optional[str]) -> None:
    if not text:
        edit.setDate(QDate.currentDate())
        return
    parsed = parse_date_value(text)
    if parsed is not None:
        edit.setDate(QDate(parsed.year, parsed.month, parsed.day))
    else:
        edit.setDate(QDate.currentDate())


def _parse_float(text: str) -> Optional[float]:
    return parse_currency_pt(text)

def _format_currency(val: Optional[float]) -> str:
    return format_currency_pt(val)


class ProducaoPage(QtWidgets.QWidget):
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.db = SessionLocal()
        self._current_id: Optional[int] = None
        self._image_path: Optional[str] = None
        self._pdf_doc = None
        self._last_no_results_prompt_key: Optional[tuple] = None
        self._dirty: bool = False
        self._loading_form: bool = False
        self._loaded_estado: str = ""
        self._last_valid_dates: dict[int, QDate] = {}
        self._base_save_button_text: str = "Salvar"
        self._pdf_manager_enabled = svc_features.has_feature(
            self.db, self._current_user_id(), svc_features.FEATURE_PDF_MANAGER
        )
        self._preparacao_enabled = svc_features.has_feature(
            self.db, self._current_user_id(), svc_features.FEATURE_PRODUCAO_PREPARACAO
        )

        self._responsaveis_fallback = [
            "Paulo",
            "Pedro",
            "Bruno",
            "Dario",
            "Angela",
            "Andreia",
            "Elizabete",
            "Manuel",
            "Catia",
        ]
        self._responsaveis_default = self._load_responsaveis()
        self._responsavel_default = self._get_responsavel_default()
        self._estados_default = ["Planeamento", "Producao", "Finalizado", "Arquivado"]
        default_base = getattr(app_settings, "PRODUCAO_BASE_PATH", None) or svc_producao.DEFAULT_BASE_PATH
        self._base_producao = get_setting(self.db, getattr(svc_producao, "KEY_PRODUCAO_BASE_PATH", "base_path_producao"), default_base)
        self._imorder_base = get_setting(
            self.db,
            getattr(svc_producao, "KEY_IMORDER_BASE_PATH", "base_path_imorder_imos_ix"),
            getattr(svc_producao, "DEFAULT_IMORDER_BASE_PATH", r"I:\Factory\Imorder"),
        )

        self._build_ui()
        self._load_table()

    def _current_username(self) -> str:
        return (
            str(getattr(self.current_user, "username", None) or getattr(self.current_user, "name", None) or "").strip()
        )

    def _current_user_id(self) -> Optional[int]:
        return getattr(self.current_user, "id", None)

    def _load_responsaveis(self) -> list[str]:
        names: list[str] = []
        try:
            users = (
                self.db.query(User)
                .filter(User.is_active == True)  # noqa: E712
                .order_by(User.username)
                .all()
            )
            for user in users:
                username = str(getattr(user, "username", "") or "").strip()
                if username:
                    names.append(username)
        except Exception:
            names = []

        if not names:
            names = list(self._responsaveis_fallback)

        current = self._current_username()
        if current and current not in names:
            names.insert(0, current)
        return names

    def _get_responsavel_default(self) -> str:
        current = self._current_username()
        if current:
            return current
        if self._responsaveis_default:
            return self._responsaveis_default[0]
        return ""

    def _apply_responsavel_default(self) -> None:
        if not hasattr(self, "cb_responsavel"):
            return
        default_resp = (self._responsavel_default or "").strip()
        if default_resp:
            items = [self.cb_responsavel.itemText(i) for i in range(self.cb_responsavel.count())]
            if default_resp not in items:
                self.cb_responsavel.addItem(default_resp, default_resp)
            self.cb_responsavel.setCurrentText(default_resp)
        elif self.cb_responsavel.count() > 0:
            self._apply_responsavel_default()

    # -------------------------
    # UI
    # -------------------------

    def _build_ui(self) -> None:
        s = self.style()
        layout = QtWidgets.QVBoxLayout(self)

        # Barra de botoes topo
        btn_row = QtWidgets.QHBoxLayout()
        def _style_primary_button(btn: QtWidgets.QPushButton, color: str):
            btn.setStyleSheet(
                f"background-color:{color}; color:white; font-weight:bold; padding:8px 12px; border-radius:4px;"
            )
            btn.setCursor(Qt.PointingHandCursor)
        def _style_secondary(btn: QtWidgets.QPushButton):
            btn.setStyleSheet("font-weight:bold; padding:6px 10px;")
            btn.setCursor(Qt.PointingHandCursor)
        def _excel_icon(size: int = 16) -> QtGui.QIcon:
            pix = QtGui.QPixmap(size, size)
            pix.fill(Qt.transparent)
            painter = QtGui.QPainter(pix)
            try:
                painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                rect = pix.rect().adjusted(0, 0, -1, -1)
                painter.setBrush(QtGui.QColor("#217346"))
                painter.setPen(QtGui.QPen(QtGui.QColor("#1e623d"), 1))
                painter.drawRoundedRect(rect, 3, 3)
                painter.setPen(Qt.white)
                font = painter.font()
                font.setBold(True)
                font.setPointSize(max(7, int(size * 0.65)))
                painter.setFont(font)
                painter.drawText(rect, Qt.AlignCenter, "X")
            finally:
                painter.end()
            return QtGui.QIcon(pix)
        def _cutrite_icon(size: int = 16) -> QtGui.QIcon:
            pix = QtGui.QPixmap(size, size)
            pix.fill(Qt.transparent)
            painter = QtGui.QPainter(pix)
            try:
                painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                rect = pix.rect().adjusted(0, 0, -1, -1)
                painter.setPen(QtGui.QPen(QtGui.QColor("#9E6A21"), 1))
                painter.setBrush(QtGui.QColor("#F4E2BF"))
                painter.drawRoundedRect(rect, 3, 3)

                half_w = rect.width() // 2
                half_h = rect.height() // 2
                painter.fillRect(QtCore.QRect(rect.left() + 1, rect.top() + 1, half_w - 1, half_h - 1), QtGui.QColor("#B6581A"))
                painter.fillRect(QtCore.QRect(rect.left() + half_w, rect.top() + 1, rect.width() - half_w, half_h - 1), QtGui.QColor("#E3A73A"))
                painter.fillRect(QtCore.QRect(rect.left() + 1, rect.top() + half_h, half_w - 1, rect.height() - half_h), QtGui.QColor("#7DA9A6"))
                painter.fillRect(QtCore.QRect(rect.left() + half_w, rect.top() + half_h, rect.width() - half_w, rect.height() - half_h), QtGui.QColor("#4D7653"))

                painter.setPen(Qt.white)
                font = painter.font()
                font.setBold(True)
                font.setPointSize(max(6, int(size * 0.6)))
                painter.setFont(font)
                painter.drawText(rect.adjusted(0, 0, 0, 1), Qt.AlignCenter, "12")
            finally:
                painter.end()
            return QtGui.QIcon(pix)
        def _printer_icon(size: int = 16) -> QtGui.QIcon:
            pix = QtGui.QPixmap(size, size)
            pix.fill(Qt.transparent)
            painter = QtGui.QPainter(pix)
            try:
                painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                body = QtCore.QRect(2, 6, size - 4, size - 7)
                top = QtCore.QRect(4, 1, size - 8, 6)
                paper = QtCore.QRect(4, 0, size - 8, size - 6)

                painter.setPen(QtGui.QPen(QtGui.QColor("#5A5A5A"), 1))
                painter.setBrush(QtGui.QColor("#FFFFFF"))
                painter.drawRect(paper)

                painter.setBrush(QtGui.QColor("#BFC5CC"))
                painter.drawRoundedRect(top, 2, 2)

                painter.setBrush(QtGui.QColor("#D7DBE0"))
                painter.drawRoundedRect(body, 2, 2)

                painter.setPen(QtGui.QPen(QtGui.QColor("#8A8A8A"), 1))
                painter.drawLine(5, 4, size - 5, 4)
                painter.drawLine(5, 10, size - 5, 10)
                painter.drawLine(5, 12, size - 5, 12)
            finally:
                painter.end()
            return QtGui.QIcon(pix)
        self.btn_novo = QtWidgets.QPushButton("Novo Processo")
        self.btn_novo.setIcon(s.standardIcon(QStyle.SP_FileIcon))
        self.btn_novo.setToolTip("Criar novo processo a partir de uma Encomenda (PHC) ou Cliente Final (Streamlit).")
        _style_primary_button(self.btn_novo, "#4CAF50")
        self.btn_novo.clicked.connect(self.on_novo)

        self.btn_nova_versao = QtWidgets.QPushButton("Nova Versao Processo")
        self.btn_nova_versao.setIcon(s.standardIcon(QStyle.SP_BrowserReload))
        self.btn_nova_versao.setToolTip("Criar uma nova versao do processo selecionado.")
        _style_secondary(self.btn_nova_versao)
        self.btn_nova_versao.clicked.connect(self.on_nova_versao)

        self.btn_conv = QtWidgets.QPushButton("Converter Orcamento")
        self.btn_conv.setIcon(s.standardIcon(QStyle.SP_ArrowRight))
        self.btn_conv.setToolTip("Converter um orcamento num processo de Producao.")
        _style_primary_button(self.btn_conv, "#FF9800")
        self.btn_conv.clicked.connect(self.on_converter)

        self.btn_save = QtWidgets.QPushButton("Salvar")
        self.btn_save.setIcon(s.standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_save.setToolTip("Gravar alteracoes do processo. Atalho: Ctrl+G.")
        _style_primary_button(self.btn_save, "#2196F3")
        self.btn_save.clicked.connect(self.on_save)
        self._shortcut_save = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+G"), self)
        self._shortcut_save.setContext(Qt.WidgetWithChildrenShortcut)
        self._shortcut_save.activated.connect(self.on_save)
        self._base_save_button_text = self.btn_save.text() or "Salvar"

        self.btn_criar_pasta = QtWidgets.QPushButton("Criar Pasta")
        self.btn_criar_pasta.setIcon(s.standardIcon(QStyle.SP_DirIcon))
        self.btn_criar_pasta.setToolTip("Criar/atualizar a pasta da obra no servidor (Pasta Servidor).")
        _style_secondary(self.btn_criar_pasta)
        self.btn_criar_pasta.clicked.connect(self.on_criar_pasta)

        self.btn_abrir_pasta = QtWidgets.QPushButton("Abrir Pasta")
        self.btn_abrir_pasta.setIcon(s.standardIcon(QStyle.SP_DialogOpenButton))
        self.btn_abrir_pasta.setToolTip("Abrir a Pasta Servidor no Explorador.")
        _style_secondary(self.btn_abrir_pasta)
        self.btn_abrir_pasta.clicked.connect(self.on_abrir_pasta)

        self.btn_lista_material_imos = QtWidgets.QPushButton("Lista Material_IMOS")
        self.btn_lista_material_imos.setIcon(_excel_icon())
        self.btn_lista_material_imos.setToolTip(
            "Criar o Excel 'Lista_Material_<Nome Enc IMOS IX>.xlsm' na Pasta Servidor (a partir do modelo) e preencher os dados."
        )
        _style_secondary(self.btn_lista_material_imos)
        self.btn_lista_material_imos.clicked.connect(self.on_lista_material_imos)

        self.btn_cutrite_import = QtWidgets.QPushButton("Enviar CUT-RITE")
        self.btn_cutrite_import.setIcon(_cutrite_icon())
        self.btn_cutrite_import.setToolTip(
            "Abrir a 'Lista de pecas' no CUT-RITE, usar a listagem preparada pelo Excel "
            "'Lista_Material_*' (macro Copia_Listagem_Software_Cut_Rite), colar os dados "
            "e guardar o plano automaticamente."
        )
        _style_secondary(self.btn_cutrite_import)
        self.btn_cutrite_import.clicked.connect(self.on_cutrite_import)

        self.btn_preparacao = QtWidgets.QPushButton("Preparacao")
        self.btn_preparacao.setIcon(s.standardIcon(QStyle.SP_FileDialogDetailedView))
        self.btn_preparacao.setToolTip(
            "Abrir o painel de preparacao da obra: gerar 2_Projeto_Producao.pdf e gerir programas CNC."
        )
        _style_secondary(self.btn_preparacao)
        self.btn_preparacao.clicked.connect(self.on_preparacao_producao)

        self.btn_delete = QtWidgets.QPushButton("Eliminar")
        self.btn_delete.setIcon(s.standardIcon(QStyle.SP_TrashIcon))
        self.btn_delete.setToolTip("Eliminar o processo selecionado (e opcionalmente a pasta).")
        _style_secondary(self.btn_delete)
        self.btn_delete.clicked.connect(self.on_delete)

        self.btn_refresh = QtWidgets.QPushButton("Atualizar")
        self.btn_refresh.setIcon(s.standardIcon(QStyle.SP_BrowserReload))
        self.btn_refresh.setToolTip("Atualizar a lista de processos.")
        _style_secondary(self.btn_refresh)
        self.btn_refresh.clicked.connect(self._load_table)

        if self._pdf_manager_enabled:
            self.btn_pdf_manager = QtWidgets.QPushButton("Imprimir PDFs")
            self.btn_pdf_manager.setIcon(_printer_icon())
            self.btn_pdf_manager.setToolTip("Abrir gestor de impressao de PDFs do processo.")
            _style_secondary(self.btn_pdf_manager)
            self.btn_pdf_manager.clicked.connect(self.on_pdf_manager)

        for b in (
            self.btn_novo,
            self.btn_save,
            self.btn_conv,
            self.btn_nova_versao,
            self.btn_delete,
            self.btn_criar_pasta,
            self.btn_abrir_pasta,
            self.btn_lista_material_imos,
            self.btn_cutrite_import,
            self.btn_refresh,
        ):
            btn_row.addWidget(b)
        if self._preparacao_enabled:
            btn_row.addWidget(self.btn_preparacao)
        if self._pdf_manager_enabled and hasattr(self, "btn_pdf_manager"):
            btn_row.addWidget(self.btn_pdf_manager)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        # Filtros
        filter_row = QtWidgets.QHBoxLayout()
        self.ed_search = QtWidgets.QLineEdit()
        self.ed_search.setPlaceholderText("Pesquisar (todos os campos; use % ou espaco para multi-termos)")
        self._search_timer = QtCore.QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._load_table)
        self.ed_search.textChanged.connect(self._on_search_text_changed)
        self.ed_search.returnPressed.connect(self._load_table)
        self.btn_clear_search = QtWidgets.QToolButton()
        self.btn_clear_search.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogResetButton))
        self.btn_clear_search.setToolTip("Limpar pesquisa")
        self.btn_clear_search.setEnabled(False)
        self.btn_clear_search.clicked.connect(lambda: self.ed_search.setText(""))
        self.cb_estado_filter = QtWidgets.QComboBox()
        self.cb_estado_filter.setEditable(True)
        self.cb_estado_filter.addItem("Todos", "")
        for est in self._estados_default:
            self.cb_estado_filter.addItem(est, est)
        self.cb_estado_filter.currentIndexChanged.connect(self._load_table)

        self.cb_cliente_filter = QtWidgets.QComboBox()
        self.cb_cliente_filter.setEditable(True)
        self.cb_cliente_filter.setInsertPolicy(QtWidgets.QComboBox.InsertAtTop)
        self.cb_cliente_filter.addItem("Todos", "")
        self.cb_cliente_filter.currentTextChanged.connect(self._load_table)

        self.cb_resp_filter = QtWidgets.QComboBox()
        self.cb_resp_filter.setEditable(True)
        self.cb_resp_filter.setInsertPolicy(QtWidgets.QComboBox.InsertAtTop)
        self.cb_resp_filter.addItem("Todos", "")
        self.cb_resp_filter.currentTextChanged.connect(self._load_table)
        filter_row.addWidget(QtWidgets.QLabel("Pesquisa:"))
        filter_row.addWidget(self.ed_search, 1)
        filter_row.addWidget(self.btn_clear_search)
        filter_row.addWidget(QtWidgets.QLabel("Estado:"))
        filter_row.addWidget(self.cb_estado_filter)
        filter_row.addWidget(QtWidgets.QLabel("Cliente:"))
        filter_row.addWidget(self.cb_cliente_filter)
        filter_row.addWidget(QtWidgets.QLabel("Responsavel:"))
        filter_row.addWidget(self.cb_resp_filter)
        layout.addLayout(filter_row)
        self.lbl_search_status = QtWidgets.QLabel("")
        self.lbl_search_status.setStyleSheet("color:#b00020;")
        self.lbl_search_status.setVisible(False)
        layout.addWidget(self.lbl_search_status)

        # Formulario + imagem compactos
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setSpacing(12)

        form_container = QtWidgets.QWidget()
        form_grid = QtWidgets.QGridLayout(form_container)
        form_grid.setContentsMargins(6, 6, 6, 6)
        form_grid.setHorizontalSpacing(8)
        form_grid.setVerticalSpacing(6)
        form_grid.setColumnStretch(1, 1)
        form_grid.setColumnStretch(3, 1)

        def add_pair(row: int, left_label: str, left_widget: QtWidgets.QWidget, right_label: str, right_widget: QtWidgets.QWidget):
            form_grid.addWidget(QtWidgets.QLabel(left_label), row, 0)
            form_grid.addWidget(left_widget, row, 1)
            form_grid.addWidget(QtWidgets.QLabel(right_label), row, 2)
            form_grid.addWidget(right_widget, row, 3)

        self.lbl_codigo = QtWidgets.QLabel("-")
        self.lbl_codigo.setFrameShape(QtWidgets.QFrame.Box)
        self.lbl_codigo.setStyleSheet("padding:4px;")
        self.ed_ano = QtWidgets.QLineEdit(datetime.now().strftime("%Y"))

        self.ed_num_enc = QtWidgets.QLineEdit()
        self.ed_ver_obra = QtWidgets.QLineEdit("01")
        self.ed_ver_plano = QtWidgets.QLineEdit("01")
        self.cb_responsavel = QtWidgets.QComboBox()
        self.cb_responsavel.setEditable(True)
        self.cb_responsavel.addItems(self._responsaveis_default)
        self.cb_responsavel.setInsertPolicy(QtWidgets.QComboBox.InsertAtBottom)
        self._apply_responsavel_default()

        self.cb_estado = QtWidgets.QComboBox()
        self.cb_estado.setEditable(True)
        self.cb_estado.addItems(self._estados_default)
        self.cb_estado.setInsertPolicy(QtWidgets.QComboBox.InsertAtBottom)

        self.cb_tipo_pasta = QtWidgets.QComboBox()
        self.cb_tipo_pasta.addItems([svc_producao.DEFAULT_PASTA_ENCOMENDA, svc_producao.DEFAULT_PASTA_ENCOMENDA_FINAL])

        self.ed_num_orc = QtWidgets.QLineEdit()
        self.ed_ver_orc = QtWidgets.QLineEdit()
        self.ed_nome_cliente = QtWidgets.QLineEdit()
        self.ed_nome_simplex = QtWidgets.QLineEdit()
        self.ed_ref_cliente = QtWidgets.QLineEdit()
        self.ed_num_cliente_phc = QtWidgets.QLineEdit()
        self.ed_obra = QtWidgets.QLineEdit()
        self.ed_local = QtWidgets.QLineEdit()
        self.ed_data_inicio = QtWidgets.QDateEdit()
        self.ed_data_inicio.setDisplayFormat("dd-MM-yyyy")
        self.ed_data_inicio.setCalendarPopup(True)
        self.ed_data_inicio.setDate(QDate.currentDate())
        self._last_valid_dates[id(self.ed_data_inicio)] = self.ed_data_inicio.date()

        self.ed_data_entrega = QtWidgets.QDateEdit()
        self.ed_data_entrega.setDisplayFormat("dd-MM-yyyy")
        self.ed_data_entrega.setCalendarPopup(True)
        self.ed_data_entrega.setDate(QDate.currentDate())
        self._last_valid_dates[id(self.ed_data_entrega)] = self.ed_data_entrega.date()

        self.ed_preco = QtWidgets.QLineEdit()
        self.ed_qt_artigos = QtWidgets.QLineEdit()
        self.ed_pasta = QtWidgets.QLineEdit()
        self.ed_pasta.setReadOnly(True)

        self.ed_nome_plano_cut_rite = QtWidgets.QLineEdit()
        self.ed_nome_plano_cut_rite.setReadOnly(True)
        self.ed_nome_plano_cut_rite.setPlaceholderText("Gerado automaticamente")
        self.ed_nome_plano_cut_rite.setToolTip("Formato: NNNN_VV_PP_AA_CLIENTE (ex.: 1956_01_01_25_CICOMOL)")

        self.ed_nome_enc_imos_ix = QtWidgets.QLineEdit()
        self.ed_nome_enc_imos_ix.setReadOnly(True)
        self.ed_nome_enc_imos_ix.setPlaceholderText("Gerado automaticamente")
        self.ed_nome_enc_imos_ix.setToolTip("Formato: NNNN_VV_AA_CLIENTE (ex.: 1956_01_25_CICOMOL)")

        add_pair(0, "Processo:", self.lbl_codigo, "Ano:", self.ed_ano)

        icons_base = Path(pasta_imagens_base(self.db) or "")
        icon_cut_rite_path = icons_base / "icon_cut_rite.png"
        icon_imos_ix_path = icons_base / "icon_imos_ix.png"
        icon_size = 18

        def icon_label(text: str, icon_path: Path, tooltip: str) -> QtWidgets.QWidget:
            container = QtWidgets.QWidget()
            h = QtWidgets.QHBoxLayout(container)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            icon = QtWidgets.QLabel()
            icon.setFixedSize(icon_size, icon_size)
            if icon_path.is_file():
                pix = QtGui.QPixmap(str(icon_path))
                if not pix.isNull():
                    icon.setPixmap(pix.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            h.addWidget(icon)
            lbl = QtWidgets.QLabel(text)
            h.addWidget(lbl)
            container.setToolTip(tooltip)
            return container

        form_grid.addWidget(
            icon_label(
                "Nome Plano CUT-RITE:",
                icon_cut_rite_path,
                "Formato: NNNN_VV_PP_AA_CLIENTE (ex.: 1956_01_01_25_CICOMOL)",
            ),
            1,
            0,
        )
        form_grid.addWidget(self.ed_nome_plano_cut_rite, 1, 1)
        form_grid.addWidget(
            icon_label(
                "Nome Enc IMOS IX:",
                icon_imos_ix_path,
                "Formato: NNNN_VV_AA_CLIENTE (ex.: 1956_01_25_CICOMOL)",
            ),
            1,
            2,
        )
        form_grid.addWidget(self.ed_nome_enc_imos_ix, 1, 3)

        add_pair(2, "Num Enc PHC:", self.ed_num_enc, "Responsavel:", self.cb_responsavel)
        add_pair(3, "Versao Obra:", self.ed_ver_obra, "Estado:", self.cb_estado)
        add_pair(4, "Versao CutRite:", self.ed_ver_plano, "Tipo Pasta:", self.cb_tipo_pasta)
        add_pair(5, "Nome Cliente Simplex:", self.ed_nome_simplex, "Num Orcamento:", self.ed_num_orc)
        add_pair(6, "Nome Cliente:", self.ed_nome_cliente, "Versao Orc:", self.ed_ver_orc)
        add_pair(7, "Ref Cliente:", self.ed_ref_cliente, "Obra:", self.ed_obra)
        add_pair(8, "Num Cliente PHC:", self.ed_num_cliente_phc, "Localizacao:", self.ed_local)
        add_pair(9, "Qt Artigos:", self.ed_qt_artigos, "Preco:", self.ed_preco)
        add_pair(10, "Data Inicio:", self.ed_data_inicio, "Data Entrega:", self.ed_data_entrega)
        form_grid.addWidget(QtWidgets.QLabel("Pasta Servidor:"), 11, 0)
        form_grid.addWidget(self.ed_pasta, 11, 1, 1, 3)

        for w in (
            self.ed_ano,
            self.ed_num_enc,
            self.ed_ver_obra,
            self.ed_ver_plano,
            self.ed_nome_simplex,
            self.ed_nome_cliente,
            self.ed_ref_cliente,
        ):
            w.textChanged.connect(self._update_external_names)
        self._update_external_names()

        form_vbox = QtWidgets.QVBoxLayout()
        form_vbox.setContentsMargins(0, 0, 0, 0)
        form_vbox.setSpacing(4)
        form_vbox.addWidget(form_container)

        # Coluna de imagem
        image_container = QtWidgets.QWidget()
        image_layout = QtWidgets.QVBoxLayout(image_container)
        image_layout.setContentsMargins(6, 6, 6, 6)
        image_layout.setSpacing(8)

        self.image_preview = QtWidgets.QLabel("IMOS IX - Preview\n(Reservado)")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setMinimumSize(320, 260)
        self.image_preview.setFrameShape(QtWidgets.QFrame.Box)
        self.image_preview.setStyleSheet("background:#f5f5f5; color:#555;")
        self.image_preview.setWordWrap(True)
        self.lbl_image_path = QtWidgets.QLabel("")
        self.lbl_image_path.setWordWrap(True)
        self.lbl_image_path.setStyleSheet("color:#555;")

        btn_img_row = QtWidgets.QHBoxLayout()
        self.btn_image_choose = QtWidgets.QPushButton("Escolher Imagem/PDF...")
        self.btn_image_choose.setIcon(s.standardIcon(QStyle.SP_DialogOpenButton))
        self.btn_image_choose.setCursor(Qt.PointingHandCursor)
        self.btn_image_clear = QtWidgets.QPushButton("Limpar Imagem")
        self.btn_image_clear.setIcon(s.standardIcon(QStyle.SP_TrashIcon))
        self.btn_image_clear.setCursor(Qt.PointingHandCursor)
        self.btn_image_choose.clicked.connect(self._choose_image)
        self.btn_image_clear.clicked.connect(self._clear_image)
        btn_img_row.addWidget(self.btn_image_choose)
        btn_img_row.addWidget(self.btn_image_clear)

        image_layout.addWidget(self.image_preview)
        image_layout.addWidget(self.lbl_image_path)
        image_layout.addLayout(btn_img_row)
        image_layout.addStretch(1)

        top_layout.addLayout(form_vbox, 2)
        top_layout.addWidget(image_container, 1)
        top_group = QtWidgets.QGroupBox()
        top_group.setLayout(top_layout)
        layout.addWidget(top_group)

        # Campos de texto amplos (sob form e imagem)
        # --- Campos de texto amplos (sob form e imagem) ---
        self.ed_desc_orc = QtWidgets.QTextEdit()
        self.ed_desc_orc.setMinimumHeight(40)

        # Artigos / Materiais / Producao
        self.ed_desc_artigos = QtWidgets.QTextEdit()
        self.ed_desc_artigos.setMinimumHeight(60)
        self.ed_desc_artigos.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.MinimumExpanding)

        self.ed_materias = QtWidgets.QTextEdit()
        self.ed_materias.setMinimumHeight(60)
        self.ed_materias.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.MinimumExpanding)

        self.ed_desc_prod = QtWidgets.QTextEdit()
        self.ed_desc_prod.setMinimumHeight(60)
        self.ed_desc_prod.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.MinimumExpanding)

        # Notas: aumentar para 80px de minimo
        self.ed_notas1 = QtWidgets.QTextEdit()
        self.ed_notas2 = QtWidgets.QTextEdit()
        self.ed_notas3 = QtWidgets.QTextEdit()
        for ed in (self.ed_notas1, self.ed_notas2, self.ed_notas3):
            ed.setMinimumHeight(40)
            ed.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.MinimumExpanding)

        # === CRIAR O GRID (isto estava em falta no teu ficheiro) ===
        text_grid = QtWidgets.QGridLayout()
        text_grid.setHorizontalSpacing(6)
        text_grid.setVerticalSpacing(2)
        text_grid.setContentsMargins(4, 2, 4, 2)
        text_grid.setColumnStretch(0, 1)
        text_grid.setColumnStretch(1, 1)
        text_grid.setColumnStretch(2, 1)
        # Ajuste de proporcao para nao roubar area da tabela
        text_grid.setRowStretch(1, 1)  # Linha Artigos/Materiais/Producao
        text_grid.setRowStretch(3, 1)  # Linha Notas


        # Toggle descricao orcamento
        self.btn_toggle_desc_orc = QtWidgets.QToolButton()
        self.btn_toggle_desc_orc.setText("-")
        self.btn_toggle_desc_orc.setCheckable(True)
        self.btn_toggle_desc_orc.setChecked(True)
        self.btn_toggle_desc_orc.clicked.connect(self._toggle_desc_orc)
        # Descricao Orcamento removida (liberta espaco)

        # Linha unica: artigos, materias, producao
        text_grid.addWidget(QtWidgets.QLabel("Descricao Artigos"), 0, 0)
        text_grid.addWidget(QtWidgets.QLabel("Materiais Usados"), 0, 1)
        text_grid.addWidget(QtWidgets.QLabel("Descricao Producao"), 0, 2)
        text_grid.addWidget(self.ed_desc_artigos, 1, 0)
        text_grid.addWidget(self.ed_materias, 1, 1)
        text_grid.addWidget(self.ed_desc_prod, 1, 2)

        # Linha unica: notas
        text_grid.addWidget(QtWidgets.QLabel("Notas 1"), 2, 0)
        text_grid.addWidget(QtWidgets.QLabel("Notas 2"), 2, 1)
        text_grid.addWidget(QtWidgets.QLabel("Notas 3"), 2, 2)
        text_grid.addWidget(self.ed_notas1, 3, 0)
        text_grid.addWidget(self.ed_notas2, 3, 1)
        text_grid.addWidget(self.ed_notas3, 3, 2)

        text_group = QtWidgets.QGroupBox()
        text_group.setLayout(text_grid)
        layout.addWidget(text_group)

        # Tabela (bottom)
        self.table = QtWidgets.QTableView(self)
        self.model = SimpleTableModel(
            columns=[
                ("ID", "id"),
                ("Ano", "ano"),
                ("Estado", "estado"),
                ("Responsavel", "responsavel"),
                ("Processo", "codigo_processo"),
                ("Enc PHC", "num_enc_phc"),
                ("Versao Obra", "versao_obra"),
                ("Versao CutRite", "versao_plano"),
                ("Cliente", "nome_cliente"),
                ("Ref Cliente", "ref_cliente"),
                ("Obra", "obra"),
                ("Data Inicio", "data_inicio"),
                ("Data Entrega", "data_entrega"),
                ("Qt Artigos", "qt_artigos"),
                ("Preco", "preco_total", _format_currency),
                ("Descricao Producao", "descricao_producao"),
            ]
        )
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self._apply_table_column_widths()
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.DescendingOrder)
        self.table.selectionModel().selectionChanged.connect(self._on_select_row)
        self._setup_processo_expand()
        layout.addWidget(self.table, 1)
        # dar mais espaco a tabela
        layout.setStretch(0, 0)
        layout.setStretch(1, 0)
        layout.setStretch(2, 0)
        layout.setStretch(3, 1)
        self._setup_dirty_tracking()
        self._set_dirty(False)

    def _apply_table_column_widths(self) -> None:
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(40)
        width_map = {
            "ID": 44,
            "Ano": 50,
            "Estado": 95,
            "Responsavel": 90,
            "Processo": 250,
            "Enc PHC": 50,
            "Versao Obra": 70,
            "Versao CutRite": 70,
            "Cliente": 280,
            "Ref Cliente": 110,
            "Obra": 120,
            "Data Inicio": 85,
            "Data Entrega": 85,
            "Qt Artigos": 70,
            "Preco": 70,
            "Descricao Producao": 390,
        }
        stretch_cols = {"Descricao Producao"}
        for idx, col in enumerate(self.model.columns):
            spec = self.model._col_spec(col)
            label = spec.get("header", "")
            if label in stretch_cols:
                header.setSectionResizeMode(idx, QtWidgets.QHeaderView.Stretch)
                continue
            header.setSectionResizeMode(idx, QtWidgets.QHeaderView.Interactive)
            if label in width_map:
                header.resizeSection(idx, width_map[label])

    def _set_dirty(self, dirty: bool) -> None:
        dirty = bool(dirty)
        if getattr(self, "_dirty", False) == dirty:
            return
        self._dirty = dirty
        self._update_save_button_text()

    def _update_save_button_text(self) -> None:
        btn = getattr(self, "btn_save", None)
        if not isinstance(btn, QtWidgets.QPushButton):
            return
        base = getattr(self, "_base_save_button_text", btn.text() or "Salvar")
        text = f"{base}*" if getattr(self, "_dirty", False) else base
        if btn.text() != text:
            btn.setText(text)

    def _on_user_edit(self, *_args) -> None:
        self._set_dirty(True)

    def _on_form_change(self, *_args) -> None:
        if getattr(self, "_loading_form", False):
            return
        self._set_dirty(True)

    def _show_toast(self, widget: Optional[QtWidgets.QWidget], text: str, timeout_ms: int = 4000) -> None:
        if not text:
            return
        try:
            if widget is not None:
                rect = widget.rect()
                center = rect.center()
                global_pos = widget.mapToGlobal(center)
                QtWidgets.QToolTip.showText(global_pos, text, widget, rect, timeout_ms)
                return
        except Exception:
            pass
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), text)

    def _on_date_changed(self, edit: QtWidgets.QDateEdit, label: str, date: QDate) -> None:
        if getattr(self, "_loading_form", False):
            self._last_valid_dates[id(edit)] = date
            return
        today = QDate.currentDate()
        if date < today:
            prev = self._last_valid_dates.get(id(edit)) or today
            self._show_toast(edit, f"{label}: nao pode ser anterior ao dia atual.", timeout_ms=4000)
            try:
                edit.blockSignals(True)
                edit.setDate(prev)
            finally:
                edit.blockSignals(False)
            return
        self._last_valid_dates[id(edit)] = date
        self._set_dirty(True)

    def _setup_dirty_tracking(self) -> None:
        line_edits = (
            getattr(self, "ed_ano", None),
            getattr(self, "ed_num_enc", None),
            getattr(self, "ed_ver_obra", None),
            getattr(self, "ed_ver_plano", None),
            getattr(self, "ed_nome_cliente", None),
            getattr(self, "ed_nome_simplex", None),
            getattr(self, "ed_num_cliente_phc", None),
            getattr(self, "ed_ref_cliente", None),
            getattr(self, "ed_num_orc", None),
            getattr(self, "ed_ver_orc", None),
            getattr(self, "ed_obra", None),
            getattr(self, "ed_local", None),
            getattr(self, "ed_preco", None),
            getattr(self, "ed_qt_artigos", None),
            getattr(self, "ed_pasta", None),
        )
        for w in line_edits:
            if hasattr(w, "textEdited"):
                w.textEdited.connect(self._on_user_edit)

        combos = (
            getattr(self, "cb_responsavel", None),
            getattr(self, "cb_estado", None),
            getattr(self, "cb_tipo_pasta", None),
        )
        for cb in combos:
            if hasattr(cb, "activated"):
                cb.activated.connect(self._on_user_edit)
            try:
                le = cb.lineEdit() if cb is not None else None
                if le is not None and hasattr(le, "textEdited"):
                    le.textEdited.connect(self._on_user_edit)
            except Exception:
                continue

        for edit, label in (
            (getattr(self, "ed_data_inicio", None), "Data Inicio"),
            (getattr(self, "ed_data_entrega", None), "Data Entrega"),
        ):
            if edit is None or not hasattr(edit, "dateChanged"):
                continue
            if id(edit) not in self._last_valid_dates:
                self._last_valid_dates[id(edit)] = edit.date()
            edit.dateChanged.connect(lambda d, e=edit, l=label: self._on_date_changed(e, l, d))

        text_edits = (
            getattr(self, "ed_desc_artigos", None),
            getattr(self, "ed_materias", None),
            getattr(self, "ed_desc_prod", None),
            getattr(self, "ed_notas1", None),
            getattr(self, "ed_notas2", None),
            getattr(self, "ed_notas3", None),
        )
        for w in text_edits:
            if hasattr(w, "textChanged"):
                w.textChanged.connect(self._on_form_change)

    def _on_search_text_changed(self, _text: str) -> None:
        """
        Evita reload a cada tecla e fecha popups vazios (completers/menus) que possam ficar abertos.
        """
        try:
            popup = QtWidgets.QApplication.activePopupWidget()
            if popup is not None:
                popup.hide()
        except Exception:
            pass
        btn_clear = getattr(self, "btn_clear_search", None)
        if isinstance(btn_clear, QtWidgets.QToolButton):
            btn_clear.setEnabled(bool(self.ed_search.text().strip()))
        try:
            self._search_timer.start(280)
        except Exception:
            self._load_table()

    # -------------------------
    # Data helpers
    # -------------------------

    def _set_filters_todos(self) -> None:
        combos = (self.cb_estado_filter, self.cb_cliente_filter, self.cb_resp_filter)
        for cb in combos:
            try:
                cb.blockSignals(True)
            except Exception:
                pass
        try:
            self.cb_estado_filter.setCurrentIndex(0)
            self.cb_cliente_filter.setCurrentIndex(0)
            self.cb_resp_filter.setCurrentIndex(0)
        finally:
            for cb in combos:
                try:
                    cb.blockSignals(False)
                except Exception:
                    pass

    def _update_search_status(self, *, search: str, has_rows: bool) -> None:
        label = getattr(self, "lbl_search_status", None)
        if not isinstance(label, QtWidgets.QLabel):
            return
        text = build_search_status_text(search=search, has_rows=has_rows)
        label.setText(text)
        label.setVisible(bool(text))

    def _maybe_prompt_search_without_filters(self, *, search: str, estado: Optional[str], cliente: str, responsavel: str) -> bool:
        """
        Quando a pesquisa nao devolve resultados por causa dos filtros ativos,
        pergunta ao utilizador se quer pesquisar em "Todos" (limpar filtros).
        Retorna True se alterou filtros e fez reload.
        """
        term = (search or "").strip()
        if not term or len(term) < 2:
            return False

        active_filters = []
        if estado:
            active_filters.append(f"Estado: {estado}")
        if cliente:
            active_filters.append(f"Cliente: {cliente}")
        if responsavel:
            active_filters.append(f"Responsovel: {responsavel}")
        if not active_filters:
            return False

        prompt_key = (term.casefold(), (estado or "").casefold(), cliente.casefold(), responsavel.casefold())
        if prompt_key == getattr(self, "_last_no_results_prompt_key", None):
            return False

        try:
            any_rows_all = svc_producao.listar_processos(self.db, search=term, limit=1, approx=False)
        except Exception:
            return False
        if not any_rows_all:
            return False

        self._last_no_results_prompt_key = prompt_key
        filtros_txt = ", ".join(active_filters)
        msg = (
            f"Nao foram encontrados resultados para a pesquisa: {term!r}\n\n"
            f"Filtros ativos: {filtros_txt}\n\n"
            "Pretende fazer a pesquisa em 'Todos' (limpar filtros)?"
        )
        res = QtWidgets.QMessageBox.question(
            self,
            "Pesquisa sem resultados",
            msg,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if res != QtWidgets.QMessageBox.Yes:
            return False

        self._set_filters_todos()
        self._load_table()
        return True

    def _load_table(self, *args, select_id: Optional[int] = None):
        try:
            if getattr(self, "ed_search", None) is not None and self.ed_search.hasFocus():
                popup = QtWidgets.QApplication.activePopupWidget()
                if popup is not None:
                    popup.hide()
        except Exception:
            pass
        search = self.ed_search.text().strip()
        estado = self.cb_estado_filter.currentData()
        prev_id = select_id
        try:
            if prev_id is None:
                idxs = self.table.selectionModel().selectedRows()
                if idxs:
                    row = idxs[0].row()
                    current = self.model.row(row)
                    prev_id = current.get("id") if current else None
        except Exception:
            prev_id = self._current_id
        try:
            cliente = normalize_filter_text(self.cb_cliente_filter.currentText())
            resp = normalize_filter_text(self.cb_resp_filter.currentText())
            rows = svc_producao.listar_processos(
                self.db,
                search=search or None,
                estado=estado or None,
                limit=300,
                cliente=cliente or None,
                responsavel=resp or None,
            )
        except Exception as exc:
            logger.exception("Falha ao listar producao: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar lista: {exc}")
            return

        if not rows and search and self._maybe_prompt_search_without_filters(search=search, estado=estado or None, cliente=cliente, responsavel=resp):
            return
        self._update_search_status(search=search, has_rows=bool(rows))
        data, client_names, resp_names = build_producao_table_rows(rows)
        # SimpleTableModel usa set_rows
        self.model.set_rows(data)
        if client_names:
            current = (self.cb_cliente_filter.currentText() or "").strip()
            sync_filter_combo(self.cb_cliente_filter, client_names, current)
        if resp_names:
            current_r = (self.cb_resp_filter.currentText() or "").strip()
            sync_filter_combo(self.cb_resp_filter, resp_names, current_r)
        target_row = 0
        if prev_id is not None:
            for idx, row_data in enumerate(data):
                if row_data.get("id") == prev_id:
                    target_row = idx
                    break
        self._current_id = data[target_row]["id"] if data else None
        if data:
            self.table.selectRow(target_row)
            self._on_select_row()
        else:
            self._clear_form()

    def _clear_form(self):
        self._loading_form = True
        try:
            state = build_empty_form_state(
                current_year=datetime.now().strftime("%Y"),
                default_tipo_pasta=self.cb_tipo_pasta.itemText(0) if self.cb_tipo_pasta.count() else "",
                default_estado=self.cb_estado.itemText(0) if self.cb_estado.count() else "",
            )
            self._current_id = None
            self._apply_form_state(state, is_new=True)
            self.ed_nome_plano_cut_rite.setText("")
            self.ed_nome_enc_imos_ix.setText("")
            self._loaded_estado = str(state.estado or "")
            self._update_image_preview(None)
            self._update_external_names()
            if hasattr(self, "btn_toggle_desc_orc"):
                self.btn_toggle_desc_orc.setChecked(True)
                self._toggle_desc_orc()
        finally:
            self._loading_form = False
        self._set_dirty(False)

    def _fill_form(self, proc):
        self._loading_form = True
        try:
            state = build_form_state_from_processo(
                proc,
                default_tipo_pasta=svc_producao.DEFAULT_PASTA_ENCOMENDA,
            )
            self._current_id = proc.id
            self._apply_form_state(state, is_new=False)
            self._loaded_estado = str(state.estado or "")
            self._update_image_preview(self._image_path)
            self._update_external_names()
        finally:
            self._loading_form = False
        self._set_dirty(False)

    def _apply_form_state(self, state, *, is_new: bool) -> None:
        self.lbl_codigo.setText(state.codigo_display)
        self.ed_ano.setText(state.ano)
        self.ed_num_enc.setText(state.num_enc_phc)
        self.ed_ver_obra.setText(state.versao_obra)
        self.ed_ver_plano.setText(state.versao_plano)
        if is_new:
            self.cb_responsavel.setCurrentIndex(0)
            self.cb_estado.setCurrentIndex(0)
        else:
            resp = state.responsavel
            if resp:
                items = [self.cb_responsavel.itemText(i) for i in range(self.cb_responsavel.count())]
                if resp not in items:
                    self.cb_responsavel.addItem(resp, resp)
            self.cb_responsavel.setCurrentText(state.responsavel)
            self.cb_estado.setCurrentText(state.estado)
        self.ed_nome_cliente.setText(state.nome_cliente)
        self.ed_nome_simplex.setText(state.nome_cliente_simplex)
        self.ed_num_cliente_phc.setText(state.num_cliente_phc)
        self.ed_ref_cliente.setText(state.ref_cliente)
        self.ed_num_orc.setText(state.num_orcamento)
        self.ed_ver_orc.setText(state.versao_orc)
        self.ed_obra.setText(state.obra)
        self.ed_local.setText(state.localizacao)
        self.ed_desc_orc.setText(state.descricao_orcamento)
        if is_new:
            self.ed_data_inicio.setDate(QDate.currentDate())
            self.ed_data_entrega.setDate(QDate.currentDate())
        else:
            _set_date_edit(self.ed_data_inicio, state.data_inicio)
            _set_date_edit(self.ed_data_entrega, state.data_entrega)
        self.ed_preco.setText(state.preco_total_text)
        self.ed_qt_artigos.setText(state.qt_artigos_text)
        self.ed_desc_artigos.setText(state.descricao_artigos)
        self.ed_desc_prod.setText(state.descricao_producao)
        self.ed_materias.setText(state.materias_usados)
        self.ed_notas1.setPlainText(state.notas1)
        self.ed_notas2.setPlainText(state.notas2)
        self.ed_notas3.setPlainText(state.notas3)
        self.ed_pasta.setText(state.pasta_servidor)
        if is_new:
            self.cb_tipo_pasta.setCurrentIndex(0)
        else:
            self.cb_tipo_pasta.setCurrentText(state.tipo_pasta)
        self._image_path = state.imagem_path
        self.lbl_image_path.setText(state.imagem_path or "")

    def _update_external_names(self) -> None:
        if not hasattr(self, "ed_nome_plano_cut_rite") or not hasattr(self, "ed_nome_enc_imos_ix"):
            return
        ano = self.ed_ano.text().strip()
        num_enc = self.ed_num_enc.text().strip()
        versao_obra = self.ed_ver_obra.text().strip() or "01"
        versao_plano = self.ed_ver_plano.text().strip() or "01"
        nome_simplex = self.ed_nome_simplex.text().strip() or None
        nome_cliente = self.ed_nome_cliente.text().strip() or None
        ref_cliente = self.ed_ref_cliente.text().strip() or None

        if not ano or not num_enc:
            self.ed_nome_plano_cut_rite.setText("")
            self.ed_nome_enc_imos_ix.setText("")
            if hasattr(self, "image_preview"):
                self._update_image_preview(self._image_path)
            return

        plano_name, imos_name = build_external_names(
            ano=ano,
            num_enc=num_enc,
            versao_obra=versao_obra,
            versao_plano=versao_plano,
            nome_simplex=nome_simplex,
            nome_cliente=nome_cliente,
            ref_cliente=ref_cliente,
            plano_builder=svc_producao.gerar_nome_plano_cut_rite,
            imos_builder=svc_producao.gerar_nome_enc_imos_ix,
        )
        self.ed_nome_plano_cut_rite.setText(plano_name)
        self.ed_nome_enc_imos_ix.setText(imos_name)

        if hasattr(self, "image_preview"):
            self._update_image_preview(self._image_path)

    def _start_blink_versions(self, *, duration_ms: int = 2800, interval_ms: int = 280) -> None:
        if not hasattr(self, "ed_ver_obra") or not hasattr(self, "ed_ver_plano"):
            return
        if getattr(self, "_blink_timer_versions", None) is None:
            self._blink_timer_versions = QtCore.QTimer(self)
            self._blink_timer_versions.timeout.connect(self._blink_versions_tick)
        self._blink_versions_remaining = max(1, int(duration_ms / max(1, interval_ms)))
        self._blink_versions_state = False
        self._blink_versions_original = (
            self.ed_ver_obra.styleSheet(),
            self.ed_ver_plano.styleSheet(),
        )
        self._blink_timer_versions.start(interval_ms)

    def _blink_versions_tick(self) -> None:
        if getattr(self, "_blink_versions_remaining", 0) <= 0:
            try:
                self._blink_timer_versions.stop()
            except Exception:
                pass
            try:
                orig_obra, orig_plano = getattr(self, "_blink_versions_original", ("", ""))
                self.ed_ver_obra.setStyleSheet(orig_obra or "")
                self.ed_ver_plano.setStyleSheet(orig_plano or "")
            except Exception:
                pass
            return
        self._blink_versions_remaining -= 1
        self._blink_versions_state = not getattr(self, "_blink_versions_state", False)
        style = "background:#fff3cd; border:1px solid #f0ad4e;" if self._blink_versions_state else ""
        self.ed_ver_obra.setStyleSheet(style)
        self.ed_ver_plano.setStyleSheet(style)

    def _update_image_preview(self, path: Optional[str]) -> None:
        if path and Path(path).is_file():
            suffix = Path(path).suffix.lower()
            if suffix == ".pdf":
                try:
                    from PySide6.QtPdf import QPdfDocument
                except Exception:
                    self.image_preview.setPixmap(QtGui.QPixmap())
                    self.image_preview.setText(f"PDF selecionado:\n{Path(path).name}")
                    self.lbl_image_path.setText(path)
                    return
                if self._pdf_doc is None:
                    self._pdf_doc = QPdfDocument(self)
                image = render_pdf_preview_image(self._pdf_doc, path, self.image_preview.size())
                if isinstance(image, QtGui.QImage) and not image.isNull():
                    self.image_preview.setPixmap(QtGui.QPixmap.fromImage(image))
                    self.image_preview.setText("")
                    self.lbl_image_path.setText(path)
                    return
                self.image_preview.setPixmap(QtGui.QPixmap())
                self.image_preview.setText(f"PDF selecionado:\n{Path(path).name}")
                self.lbl_image_path.setText(path)
                return
            pix = load_scaled_pixmap(path, self.image_preview.size())
            if pix is not None:
                self.image_preview.setPixmap(pix)
                self.image_preview.setText("")
                self.lbl_image_path.setText(path)
                return

        # 1a prioridade: imagem do IMOS IX (Imorder)
        imos_path = self._imos_ix_image_path()
        if imos_path is not None and imos_path.is_file():
            pix = QtGui.QPixmap(str(imos_path))
            if not pix.isNull():
                self.image_preview.setPixmap(
                    pix.scaled(self.image_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.image_preview.setText("")
                self.lbl_image_path.setText(str(imos_path))
                return

        # Fallback: mostrar conteudo da pasta do processo
        folder_path = self.ed_pasta.text().strip()
        folder_text = build_folder_preview_text(folder_path)
        self.image_preview.setPixmap(QtGui.QPixmap())
        self.image_preview.setText(folder_text or "IMOS IX - Preview\n(Reservado)")
        self.lbl_image_path.setText(path or folder_path or "")

    def _imos_ix_image_path(self) -> Optional[Path]:
        """
        Procura imagem no IMOS IX (Imorder) com o nome:
          <base_imorder>/<Nome Enc IMOS IX>/<Nome Enc IMOS IX>.png
        """
        try:
            self._imorder_base = get_setting(
                self.db,
                getattr(svc_producao, "KEY_IMORDER_BASE_PATH", "base_path_imorder_imos_ix"),
                getattr(svc_producao, "DEFAULT_IMORDER_BASE_PATH", r"I:\Factory\Imorder"),
            ) or self._imorder_base
        except Exception:
            pass
        base = str(getattr(self, "_imorder_base", "") or "").strip()
        nome_enc = self.ed_nome_enc_imos_ix.text().strip() if hasattr(self, "ed_nome_enc_imos_ix") else ""
        return find_imos_ix_image_path(base, nome_enc)

    def _toggle_desc_orc(self):
        if self.ed_desc_orc.parent() is None:
            self.ed_desc_orc.hide()
            self.btn_toggle_desc_orc.setChecked(False)
            self.btn_toggle_desc_orc.setText("+")
            return
        visible = self.btn_toggle_desc_orc.isChecked()
        self.ed_desc_orc.setVisible(visible)
        self.btn_toggle_desc_orc.setText("-" if visible else "+")

    def _choose_image(self):
        start_dir = self.ed_pasta.text().strip() or str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Escolher imagem ou PDF",
            start_dir,
            "Imagens ou PDF (*.png *.jpg *.jpeg *.bmp *.pdf);;Todos os ficheiros (*.*)",
        )
        if not file_path:
            return
        self._image_path = file_path
        self._update_image_preview(self._image_path)
        self._set_dirty(True)

    def _clear_image(self):
        self._image_path = None
        self._update_image_preview(None)
        self._set_dirty(True)

    def _collect_form(self) -> dict:
        return build_processo_form_payload(**self._collect_form_payload_inputs())

    def _collect_form_payload_inputs(self) -> dict:
        return {
            "ano": self.ed_ano.text(),
            "num_enc_phc": self.ed_num_enc.text(),
            "versao_obra": self.ed_ver_obra.text(),
            "versao_plano": self.ed_ver_plano.text(),
            "responsavel": self.cb_responsavel.currentText(),
            "estado": self.cb_estado.currentText(),
            "nome_cliente": self.ed_nome_cliente.text(),
            "nome_cliente_simplex": self.ed_nome_simplex.text(),
            "num_cliente_phc": self.ed_num_cliente_phc.text(),
            "ref_cliente": self.ed_ref_cliente.text(),
            "num_orcamento": self.ed_num_orc.text(),
            "versao_orc": self.ed_ver_orc.text(),
            "obra": self.ed_obra.text(),
            "localizacao": self.ed_local.text(),
            "data_inicio": _parse_date_edit(self.ed_data_inicio),
            "data_entrega": _parse_date_edit(self.ed_data_entrega),
            "preco_total": _parse_float(self.ed_preco.text()),
            "qt_artigos_text": self.ed_qt_artigos.text(),
            "descricao_artigos": self.ed_desc_artigos.toPlainText(),
            "materias_usados": self.ed_materias.toPlainText(),
            "descricao_producao": self.ed_desc_prod.toPlainText(),
            "notas1": self.ed_notas1.toPlainText(),
            "notas2": self.ed_notas2.toPlainText(),
            "notas3": self.ed_notas3.toPlainText(),
            "pasta_servidor": self.ed_pasta.text(),
            "tipo_pasta": self.cb_tipo_pasta.currentText(),
            "imagem_path": self._image_path,
        }

    def _folder_preview_text(self, folder: Path, limit: int = 25) -> str:
        if not folder.exists():
            return "(pasta inexistente)"
        items = []
        count = 0
        for entry in folder.rglob("*"):
            count += 1
            if count > limit:
                continue
            rel = entry.relative_to(folder)
            items.append(str(rel))
        if count > limit:
            items.append(f"... (+{count - limit} itens)")
        if not items:
            return "(pasta vazia)"
        return "\n".join(items)

    def _setup_processo_expand(self) -> None:
        try:
            columns = getattr(self.model, "columns", []) or []
            processo_col = None
            for idx, col in enumerate(columns):
                if isinstance(col, (tuple, list)) and len(col) > 1 and col[1] == "codigo_processo":
                    processo_col = idx
                    break
            if processo_col is None:
                return
            self._processo_expand_delegate = ProcessoExpandDelegate(parent=self.table, on_expand=self._on_expand_processo)  # type: ignore[attr-defined]
            self.table.setItemDelegateForColumn(processo_col, self._processo_expand_delegate)  # type: ignore[arg-type]
        except Exception:
            return

    def _on_expand_processo(self, index: QtCore.QModelIndex) -> None:
        try:
            self.table.selectRow(index.row())
        except Exception:
            pass

        data = self.model.row(index.row())
        proc_id = data.get("id") if isinstance(data, dict) else None
        if not proc_id:
            return

        try:
            context = svc_producao_workflow.build_processo_folders_context(
                self.db,
                current_id=proc_id,
            )
        except Exception as exc:
            logger.exception("Falha ao listar pastas existentes: %s", exc)
            QtWidgets.QMessageBox.warning(self, "Pastas", f"Falha ao listar pastas existentes:\n{exc}")
            return

        dlg = PastasExistentesDialog(
            parent=self,
            folder_root=context.folder_root,
            folder_tree=context.folder_tree,
            title_suffix=context.title_suffix,
        )
        dlg.exec()

    # -------------------------
    # Slots
    # -------------------------

    def _on_select_row(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return
        row = indexes[0].row()
        data = self.model.row(row)
        if not data:
            return
        proc_id = data.get("id")
        proc = svc_producao.obter_processo(self.db, proc_id)
        if proc:
            self._fill_form(proc)

    def on_novo(self):
        dlg = NovoProcessoDialog(parent=self, db=self.db)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        try:
            preparation = svc_producao_workflow.prepare_external_process_creation(
                self.db,
                result_data=dlg.result_data() or {},
                responsavel_default=self._responsavel_default,
            )
        except ValueError as exc:
            if "origem selecionada" in str(exc):
                QtWidgets.QMessageBox.information(self, "Em desenvolvimento", str(exc))
            else:
                QtWidgets.QMessageBox.warning(self, "Dados incompletos", str(exc))
            return

        versao_obra = preparation.versao_obra_next
        versao_plano = preparation.versao_plano_next

        try:
            if preparation.should_prompt_versions:
                dlg = NovaVersaoProcessoDialog(
                    parent=self,
                    versao_obra_sug_cutrite=preparation.reuse_versao_obra,
                    versao_plano_sug_cutrite=preparation.reuse_versao_plano,
                    versao_obra_sug_obra=preparation.versao_obra_next,
                    versao_plano_sug_obra=preparation.versao_plano_next,
                    existing_keys=preparation.existing_keys,
                    folder_root=preparation.folder_root,
                    folder_tree=preparation.folder_tree,
                    window_title="Novo Processo - Versoes",
                    intro_text=(
                        "Foram detetadas pastas existentes no servidor para esta encomenda.\n"
                        "Escolha as versoes para reutilizar a pasta existente ou criar uma nova."
                    ),
                    label_sug_cutrite="Usar Pasta Existente",
                    tooltip_sug_cutrite="Usa a versao encontrada nas pastas (se aplicavel).",
                    label_sug_obra="Criar Nova Versao",
                    tooltip_sug_obra="Sugere uma nova combinacao de Versao Obra e Versao CutRite.",
                )
                if dlg.exec() != QtWidgets.QDialog.Accepted:
                    return
                versao_obra, versao_plano = dlg.values()

            proc = svc_producao_workflow.create_external_process(
                self.db,
                preparation=preparation,
                versao_obra=versao_obra,
                versao_plano=versao_plano,
                current_user_id=getattr(self.current_user, "id", None),
            )

            self.db.commit()
            QtWidgets.QMessageBox.information(self, "Criado", f"Processo criado: {proc.codigo_processo}")
            self._load_table(select_id=proc.id)
        except Exception as exc:
            self.db.rollback()
            logger.exception("Falha ao criar processo via %s: %s", preparation.source, exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao criar processo: {exc}")

    def on_nova_versao(self):
        try:
            preparation = svc_producao_workflow.prepare_nova_versao(
                self.db,
                current_id=self._current_id,
                data=self._collect_form(),
            )
        except ValueError as exc:
            title = "Campos obrigatorios" if "obrigatorios" in str(exc) else "Aviso"
            QtWidgets.QMessageBox.warning(self, title, str(exc))
            return

        dlg = NovaVersaoProcessoDialog(
            parent=self,
            versao_obra_sug_cutrite=preparation.sug_obra_cutrite,
            versao_plano_sug_cutrite=preparation.sug_plano_cutrite,
            versao_obra_sug_obra=preparation.sug_obra_obra,
            versao_plano_sug_obra=preparation.sug_plano_obra,
            existing_keys=preparation.existing_keys,
            folder_root=preparation.folder_root,
            folder_tree=preparation.folder_tree,
        )
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        new_ver_obra, new_ver_plano = dlg.values()

        try:
            proc = svc_producao_workflow.create_nova_versao(
                self.db,
                preparation=preparation,
                versao_obra=new_ver_obra,
                versao_plano=new_ver_plano,
                current_user_id=getattr(self.current_user, "id", None),
            )
            self.db.commit()
            QtWidgets.QMessageBox.information(self, "Criado", f"Nova versao criada: {proc.codigo_processo}")
            self._load_table(select_id=proc.id)
            self._start_blink_versions()
        except Exception as exc:
            self.db.rollback()
            logger.exception("Falha ao criar nova versao: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao criar nova versao: {exc}")

    def on_converter(self):
        picker = OrcamentoPicker(self.db, self)
        if picker.exec() != QtWidgets.QDialog.Accepted:
            return
        orc_id = picker.selected_id()
        if not orc_id:
            return

        try:
            preparation = svc_producao_workflow.prepare_orcamento_conversion(
                self.db,
                orcamento_id=int(orc_id),
                responsavel_default=self._responsavel_default,
            )
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Aviso", str(exc))
            return

        versao_plano, ok2 = QtWidgets.QInputDialog.getText(
            self,
            "Versao CutRite",
            "Versao CutRite (PP):",
            text=str(preparation.suggested_plano_default or "01"),
        )
        if not ok2:
            return
        try:
            proc = svc_producao_workflow.create_process_from_orcamento_conversion(
                self.db,
                preparation=preparation,
                versao_plano=versao_plano,
                current_user_id=getattr(self.current_user, "id", None),
            )

            self.db.commit()
            QtWidgets.QMessageBox.information(self, "Sucesso", f"Processo criado: {proc.codigo_processo}")
            self._load_table()
            self._fill_form(proc)
        except ValueError as exc:
            self.db.rollback()
            logger.warning("Falha converter orcamento: %s", exc)
            QtWidgets.QMessageBox.warning(self, "Aviso", str(exc))
        except Exception as exc:
            self.db.rollback()
            logger.exception("Falha converter orcamento: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao converter: {exc}")

    def on_save(self):
        data = self._collect_form()
        previous_estado = str(getattr(self, "_loaded_estado", "") or "").strip()
        saved_estado = str(data.get("estado") or "").strip()
        try:
            result = svc_producao_workflow.save_processo(
                self.db,
                current_id=self._current_id,
                data=data,
                current_user_id=getattr(self.current_user, "id", None),
            )
            self.db.commit()
            self._current_id = getattr(result.processo, "id", None)
            self._load_table(select_id=self._current_id)
            self._set_dirty(False)
            QtWidgets.QMessageBox.information(self, result.message_title, result.message_text)
            self._maybe_prompt_producao_preparacao(
                previous_estado=previous_estado,
                saved_estado=saved_estado,
            )
        except ValueError as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.warning(self, "Campos obrigatorios", str(exc))
        except Exception as exc:
            self.db.rollback()
            logger.exception("Falha ao gravar processo: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar: {exc}")

    def on_delete(self):
        if self._current_id is None:
            return
        try:
            context = svc_producao_workflow.build_processo_action_context(self.db, self._current_id)
        except ValueError:
            return
        box = QtWidgets.QMessageBox(self)
        box.setIcon(QtWidgets.QMessageBox.Question)
        box.setWindowTitle("Confirmar")
        box.setText(f"Eliminar processo:\n{context.info_text}")
        btn_registo = box.addButton("So registo (BD)", QtWidgets.QMessageBox.YesRole)
        btn_pasta = box.addButton("Apagar pasta e registo", QtWidgets.QMessageBox.DestructiveRole)
        box.addButton(QtWidgets.QMessageBox.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is None or clicked == box.button(QtWidgets.QMessageBox.Cancel):
            return
        delete_folder = clicked == btn_pasta
        try:
            folder = context.folder_path if delete_folder else None
            plan = build_processo_delete_ui_plan(
                info_text=context.info_text,
                folder=folder,
                delete_folder=delete_folder,
                folder_preview_text=self._folder_preview_text(folder) if delete_folder and folder else "",
            )
            if plan.folder_confirmation_text:
                confirm = QtWidgets.QMessageBox.question(
                    self,
                    "Confirmar remocao de pasta",
                    plan.folder_confirmation_text,
                )
                if confirm != QtWidgets.QMessageBox.Yes:
                    return

            confirm_db = QtWidgets.QMessageBox.question(
                self,
                "Confirmar eliminacao definitiva",
                plan.db_confirmation_text,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if confirm_db != QtWidgets.QMessageBox.Yes:
                return

            try:
                svc_producao_workflow.delete_processo(
                    self.db,
                    self._current_id,
                    delete_folder=delete_folder,
                )
            except PermissionError as exc:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Aviso",
                    f"Nao foi possivel apagar a pasta (ficheiro em uso?):\n{folder}\n{exc}\n\nO registo nao foi eliminado.",
                )
                return
            except Exception as exc:
                if delete_folder and folder:
                    QtWidgets.QMessageBox.warning(
                        self, "Aviso", f"Falha ao apagar pasta:\n{folder}\n{exc}\n\nO registo nao foi eliminado."
                    )
                    return
                raise
            self.db.commit()
            self._load_table()
        except Exception as exc:
            self.db.rollback()
            logger.exception("Falha ao eliminar: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar: {exc}")

    def on_criar_pasta(self):
        try:
            result = svc_producao_workflow.create_processo_folder(
                self.db,
                self._current_id,
                current_base_dir=self._base_producao,
                tipo_pasta=normalize_tipo_pasta_text(self.cb_tipo_pasta.currentText()),
            )
            self._base_producao = result.base_dir
            self.db.commit()
            self.ed_pasta.setText(str(result.path))
            QtWidgets.QMessageBox.information(self, "Pasta", f"Pasta criada/atualizada:\n{result.path}")
            self._load_table()
        except ValueError as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.warning(self, "Aviso", str(exc))
        except Exception as exc:
            self.db.rollback()
            logger.exception("Falha ao criar pasta: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao criar pasta: {exc}")

    def on_abrir_pasta(self):
        if not self._current_id:
            return
        try:
            result = svc_producao_workflow.open_processo_folder(
                self.db,
                self._current_id,
                current_base_dir=self._base_producao,
                tipo_pasta=normalize_tipo_pasta_text(self.cb_tipo_pasta.currentText()),
            )
            self._base_producao = result.base_dir
            self.db.commit()
            self.ed_pasta.setText(str(result.path))
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao abrir pasta: {exc}")

    def on_pdf_manager(self) -> None:
        try:
            proc = svc_producao_workflow.resolve_pdf_manager_target(self.db, self._current_id)
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Imprimir PDFs", str(exc))
            return
        dlg = ProducaoPDFManagerDialog(session=self.db, producao=proc, parent=self)
        dlg.exec()

    def on_lista_material_imos(self) -> None:
        values = build_lista_material_imos_values(
            responsavel=self.cb_responsavel.currentText(),
            ref_cliente=self.ed_ref_cliente.text(),
            obra=self.ed_obra.text(),
            nome_enc_imos_ix=self.ed_nome_enc_imos_ix.text(),
            num_cliente_phc=self.ed_num_cliente_phc.text(),
            nome_cliente=self.ed_nome_cliente.text(),
            nome_cliente_simplex=self.ed_nome_simplex.text(),
            localizacao=self.ed_local.text(),
            descricao_producao=self.ed_desc_prod.toPlainText(),
            descricao_artigos=self.ed_desc_artigos.toPlainText(),
            materias=self.ed_materias.toPlainText(),
            qtd=self.ed_qt_artigos.text(),
            plano_corte=self.ed_nome_plano_cut_rite.text(),
            data_conclusao=_parse_date_edit(self.ed_data_entrega),
            data_inicio=_parse_date_edit(self.ed_data_inicio),
            enc_phc=self.ed_num_enc.text(),
        )

        try:
            context = svc_producao_workflow.prepare_lista_material_imos(
                self.db,
                current_id=self._current_id,
                pasta_servidor=self.ed_pasta.text().strip(),
                nome_enc_imos=self.ed_nome_enc_imos_ix.text().strip(),
                values=values,
            )
        except ValueError as exc:
            title = "Erro" if str(exc).startswith("Modelo Excel nao encontrado") else "Aviso"
            if title == "Erro":
                QtWidgets.QMessageBox.critical(self, title, str(exc))
            else:
                QtWidgets.QMessageBox.warning(self, title, str(exc))
            return

        if context.output_path.exists():
            confirm = QtWidgets.QMessageBox.question(
                self,
                "Confirmar",
                f"O ficheiro ja existe:\n{context.output_path}\n\nPretende substituir?",
            )
            if confirm != QtWidgets.QMessageBox.Yes:
                return
        try:
            output_path = svc_producao_workflow.execute_lista_material_imos(context)
        except Exception as exc:
            logger.exception("Falha ao criar Lista Material IMOS (Excel COM): %s", exc)
            QtWidgets.QMessageBox.critical(
                self,
                "Erro",
                "Nao foi possivel criar o Excel 'Lista Material_IMOS'.\n\n"
                f"Detalhe: {exc}",
            )
            return

        self._update_image_preview(self._image_path)
        QtWidgets.QMessageBox.information(self, "OK", f"Ficheiro criado:\n{output_path}")

    def on_cutrite_import(self) -> None:
        progress_dialog = CutRiteProgressDialog(self)
        progress_dialog.add_step("A iniciar o envio para o CUT-RITE.")
        progress_dialog.show()
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents, 50)
        try:
            context = svc_cutrite.prepare_cutrite_import(
                self.db,
                current_id=self._current_id,
                pasta_servidor=self.ed_pasta.text().strip(),
                nome_plano_cut_rite=self.ed_nome_plano_cut_rite.text().strip(),
                nome_enc_imos=self.ed_nome_enc_imos_ix.text().strip(),
            )
        except ValueError as exc:
            message = str(exc)
            title = "Erro" if "Executavel CUT-RITE" in message or "Import.exe" in message else "Aviso"
            if title == "Erro":
                QtWidgets.QMessageBox.critical(self, title, message)
            else:
                QtWidgets.QMessageBox.warning(self, title, message)
            progress_dialog.finish(success=False)
            return
        except Exception as exc:
            progress_dialog.add_step(f"Erro ao preparar o envio: {exc}")
            progress_dialog.finish(success=False)
            logger.exception("Falha ao preparar envio CUT-RITE: %s", exc)
            QtWidgets.QMessageBox.critical(
                self,
                "Erro",
                "Nao foi possivel preparar o envio para o CUT-RITE.\n\n"
                f"Detalhe: {exc}",
            )
            return

        try:
            result = svc_cutrite.execute_cutrite_import(
                context,
                progress_callback=progress_dialog.add_step,
            )
        except Exception as exc:
            progress_dialog.add_step(f"Erro durante a automacao CUT-RITE: {exc}")
            progress_dialog.finish(success=False)
            logger.exception("Falha ao enviar lista para CUT-RITE: %s", exc)
            QtWidgets.QMessageBox.critical(
                self,
                "Erro",
                "Nao foi possivel enviar a lista para o CUT-RITE.\n\n"
                f"Detalhe: {exc}",
            )
            return

        progress_dialog.finish(success=True)

        message = (
            "Lista enviada para o CUT-RITE.\n\n"
            f"Origem: {result.source_workbook_path}\n"
            f"Perfil CUT-RITE: {result.cutrite_profile_dir}\n"
            f"Execucao CUT-RITE: {result.cutrite_workdir}\n"
            f"Dados origem: {result.cutrite_data_dir}\n"
            f"Dados destino: {result.cutrite_target_data_dir}\n"
        )
        if result.generated_data_paths:
            message += "\nFicheiros gerados/copiados:\n" + "\n".join(str(path) for path in result.generated_data_paths[:8])
        if result.launched_cutrite:
            message += "\nO CUT-RITE foi iniciado automaticamente."
        elif result.cutrite_was_running:
            message += "\nO CUT-RITE ja estava em execucao."
        QtWidgets.QMessageBox.information(self, "CUT-RITE", message)

    def _resolve_preparacao_context(self):
        return svc_producao_preparacao.resolve_preparacao_context(
            self.db,
            current_id=self._current_id,
            pasta_servidor=self.ed_pasta.text().strip(),
            nome_enc_imos=self.ed_nome_enc_imos_ix.text().strip(),
            nome_plano_cut_rite=self.ed_nome_plano_cut_rite.text().strip(),
        )

    def on_preparacao_producao(self) -> None:
        if not self._preparacao_enabled:
            QtWidgets.QMessageBox.warning(
                self,
                "Preparacao",
                "O utilizador atual nao tem permissao para usar o painel de Preparacao de Producao.",
            )
            return
        try:
            dialog = ProducaoPreparacaoDialog(
                db_session=self.db,
                current_id=self._current_id,
                pasta_servidor=self.ed_pasta.text().strip(),
                nome_enc_imos=self.ed_nome_enc_imos_ix.text().strip(),
                nome_plano_cut_rite=self.ed_nome_plano_cut_rite.text().strip(),
                current_user_id=self._current_user_id(),
                parent=self,
            )
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Preparacao", str(exc))
            return
        except Exception as exc:
            logger.exception("Falha ao abrir painel de preparacao: %s", exc)
            QtWidgets.QMessageBox.critical(
                self,
                "Preparacao",
                f"Nao foi possivel abrir o painel de preparacao.\n\nDetalhe: {exc}",
            )
            return
        dialog.exec()

    def _maybe_prompt_producao_preparacao(self, *, previous_estado: str, saved_estado: str) -> None:
        if not self._preparacao_enabled:
            return
        if str(saved_estado or "").strip().lower() != "producao":
            return
        if str(previous_estado or "").strip().lower() == "producao":
            return

        try:
            context = self._resolve_preparacao_context()
            required_keys = svc_producao_preparacao.get_required_preparacao_keys(
                self.db,
                self._current_user_id(),
            )
            pending = svc_producao_preparacao.build_pending_preparacao_labels(
                context,
                required_keys=required_keys,
                critical_only=True,
            )
        except Exception as exc:
            logger.warning("Falha ao validar painel de preparacao apos gravacao: %s", exc)
            QtWidgets.QMessageBox.warning(
                self,
                "Preparacao de Producao",
                "O estado do processo foi alterado para 'Producao', mas nao foi possivel validar a preparacao da obra.\n\n"
                f"Detalhe: {exc}\n\n"
                "O painel de preparacao vai ser aberto para verificacao manual.",
            )
            self.on_preparacao_producao()
            return

        if not pending:
            return

        detail = "Pendencias criticas detetadas:\n- " + "\n- ".join(pending)
        QtWidgets.QMessageBox.warning(
            self,
            "Preparacao de Producao",
            "O estado do processo foi alterado para 'Producao'.\n\n"
            f"{detail}\n\n"
            "O painel de preparacao vai ser aberto para validacao.",
        )
        self.on_preparacao_producao()
