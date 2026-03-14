from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Sequence, Tuple
from pathlib import Path

import logging
from PySide6 import QtCore, QtWidgets, QtGui

logger = logging.getLogger(__name__)
import os
import sys
import datetime

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.settings import get_setting, set_setting
from Martelo_Orcamentos_V2.app.services.materias_primas import (
    DEFAULT_MATERIAS_BASE_PATH,
    KEY_MATERIAS_BASE_PATH,
)
from Martelo_Orcamentos_V2.app.services import custeio_items as svc_custeio
from Martelo_Orcamentos_V2.app.services import pesquisa_ia as svc_ia
from Martelo_Orcamentos_V2.app.services import producao as svc_producao
from Martelo_Orcamentos_V2.app.services import producao_processos as svc_producao_processos
from Martelo_Orcamentos_V2.app.services import producao_preparacao as svc_producao_preparacao
from Martelo_Orcamentos_V2.app.services import cutrite_automation as svc_cutrite
from Martelo_Orcamentos_V2.app.services import def_pecas as svc_def_pecas
from Martelo_Orcamentos_V2.app.services import margens as svc_margens
from Martelo_Orcamentos_V2.app.services import phc_sql as svc_phc
from Martelo_Orcamentos_V2.app.services import feature_flags as svc_features
from Martelo_Orcamentos_V2.app.models.user import User
from Martelo_Orcamentos_V2.ui.models.qt_table import SimpleTableModel


KEY_BASE_PATH = "base_path_orcamentos"
KEY_ORC_DB_BASE = "base_path_dados_orcamento"
KEY_PRODUCAO_BASE_PATH = "base_path_producao"
DEFAULT_BASE_PATH = r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2"
DEFAULT_BASE_DADOS_ORC = r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\Base_Dados_Orcamento"
DEFAULT_BASE_PRODUCAO = r"\\SERVER_LE_Lanca_Encanto\LancaEncanto\Dep_Producao"

AUTO_DIMS_HELP_TEXT = (
    "Quando ativo, o Martelo preenche automaticamente as colunas COMP e LARG "
    "para pecas padrao (COSTA, PORTA ABRIR, LATERAL, DIVISORIA, TETO, FUNDO, "
    "PRATELEIRA AMOVIVEL, PRAT. AMOV., PRATELEIRA FIXA, PRAT.FIXA) usando as "
    "dimensoes HM/LM/PM do item. Continua possivel editar manualmente os valores."
)


def _fmt_bool(value: object) -> str:
    return "Sim" if bool(value) else "Nao"


class AutoDimensionPiecesDialog(QtWidgets.QDialog):
    def __init__(
        self,
        parent: QtWidgets.QWidget,
        available_rules: Sequence[Tuple[str, str, str]],
        selected_prefixes: Sequence[str],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Selecionar peças para COMP/LARG automático")
        self.resize(520, 420)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        description = QtWidgets.QLabel(
            "Escolha as peças padrão em que o preenchimento automático de COMP/LARG "
            "deve ser aplicado quando a opção estiver ativa."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        layout.addWidget(self.list_widget, 1)

        selected = {str(prefix).upper() for prefix in selected_prefixes}
        for prefix, comp_expr, larg_expr in available_rules:
            item = QtWidgets.QListWidgetItem(prefix.title())
            item.setData(QtCore.Qt.UserRole, prefix)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked if prefix in selected else QtCore.Qt.Unchecked)
            item.setToolTip(f"COMP = {comp_expr} | LARG = {larg_expr}")
            self.list_widget.addItem(item)

        buttons_row = QtWidgets.QHBoxLayout()
        self.btn_select_all = QtWidgets.QPushButton("Selecionar tudo")
        self.btn_select_all.clicked.connect(lambda: self._set_all(QtCore.Qt.Checked))
        self.btn_clear_all = QtWidgets.QPushButton("Limpar seleção")
        self.btn_clear_all.clicked.connect(lambda: self._set_all(QtCore.Qt.Unchecked))
        buttons_row.addWidget(self.btn_select_all)
        buttons_row.addWidget(self.btn_clear_all)
        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _set_all(self, state: QtCore.Qt.CheckState) -> None:
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(state)

    def selected_prefixes(self) -> List[str]:
        prefixes: List[str] = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                prefixes.append(str(item.data(QtCore.Qt.UserRole)))
        return prefixes


class SettingsPage(QtWidgets.QWidget):
    margens_updated = QtCore.Signal()
    PRODUCAO_HEADERS = [
        "Descricao Equipamento",
        "Abreviatura",
        "Valor Producao STD",
        "Valor Producao Serie",
        "Resumo da Descricao",
    ]
    DEF_PECAS_HEADERS = [
        "ID",
        "Tipo_Peca_Principal",
        "Subgrupo_Peca",
        "Nome_da_Peca",
        "CP01_SEC",
        "CP02_ORL",
        "CP03_CNC",
        "CP04_ABD",
        "CP05_PRENSA",
        "CP06_ESQUAD",
        "CP07_EMBALAGEM",
        "CP08_MAO_DE_OBRA",
    ]
    DEF_PECAS_NUMERIC_COLUMNS = {4, 5, 6, 7, 8, 9, 10, 11}

    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self._current_user_id = getattr(current_user, "id", None) if current_user is not None else None
        self.db = SessionLocal()

        self._producao_ctx: Optional[svc_producao.ProducaoContext] = None
        self._producao_mode: str = "STD"
        self._loading_table: bool = False
        self._decimal_quant = Decimal("0.0001")
        self._default_lookup: Dict[str, Dict[str, Decimal]] = {}
        for entry in svc_producao.DEFAULT_PRODUCTION_VALUES:
            desc = str(entry["descricao_equipamento"])
            self._default_lookup[desc] = {
                "valor_std": Decimal(str(entry["valor_std"])).quantize(self._decimal_quant),
                "valor_serie": Decimal(str(entry["valor_serie"])).quantize(self._decimal_quant),
            }

        self._producao_dirty: bool = True
        self._def_pecas_dirty: bool = True
        self._def_pecas_loading: bool = False
        self._permissions_dirty: bool = False
        self._permissions_loading: bool = False

        main_layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tabs)

        self._init_login_tab()
        self._init_general_tab()
        self._init_phc_tab()
        self._init_producao_tab()
        self._init_def_pecas_tab()
        self._init_margens_tab()
        self._init_qt_rules_tab()
        if self._is_admin_user():
            self._init_permissions_tab()
        self._shortcut_save = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+G"), self)
        self._shortcut_save.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self._shortcut_save.activated.connect(self._on_shortcut_save)

    def _is_admin_user(self) -> bool:
        username = str(getattr(self.current_user, "username", "") or "").strip().lower()
        role = str(getattr(self.current_user, "role", "") or "").strip().lower()
        return username == "admin" or role == "admin"

    # ------------------------------------------------------------------ Login
    def _init_login_tab(self) -> None:
        tab = QtWidgets.QWidget()
        lay = QtWidgets.QFormLayout(tab)

        # Configuração global de pré-preenchimento automático
        self.chk_auto_fill_login = QtWidgets.QCheckBox("Ativar pré-preenchimento automático de utilizador")
        self.chk_auto_fill_login.setToolTip(
            "Quando ativo, o Martelo tenta identificar o utilizador do Windows "
            "e pré-preenche automaticamente o campo de utilizador no login."
        )
        lay.addRow(self.chk_auto_fill_login)

        # Grupo para mapeamentos de usuários
        group_mapping = QtWidgets.QGroupBox("Mapeamento Utilizadores Windows ↔ Martelo")
        mapping_layout = QtWidgets.QVBoxLayout(group_mapping)

        description = QtWidgets.QLabel(
            "Configure o mapeamento entre utilizadores do Windows e utilizadores do Martelo.\n"
            "Quando um utilizador do Windows faz login, o Martelo pode pré-preencher automaticamente "
            "o campo de utilizador correspondente."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666666; font-size: 11px;")
        mapping_layout.addWidget(description)

        # Lista de mapeamentos existentes
        self.list_user_mappings = QtWidgets.QListWidget()
        self.list_user_mappings.setAlternatingRowColors(True)
        self.list_user_mappings.setMaximumHeight(200)
        mapping_layout.addWidget(self.list_user_mappings)

        # Botões para gerir mapeamentos
        buttons_layout = QtWidgets.QHBoxLayout()
        
        self.btn_add_mapping = QtWidgets.QPushButton("Adicionar Mapeamento")
        self.btn_add_mapping.clicked.connect(self._on_add_user_mapping)
        buttons_layout.addWidget(self.btn_add_mapping)

        self.btn_remove_mapping = QtWidgets.QPushButton("Remover Selecionado")
        self.btn_remove_mapping.clicked.connect(self._on_remove_user_mapping)
        buttons_layout.addWidget(self.btn_remove_mapping)

        buttons_layout.addStretch(1)
        mapping_layout.addLayout(buttons_layout)

        lay.addRow(group_mapping)

        # Botão para gravar configurações
        self.btn_save_login = QtWidgets.QPushButton("Gravar Configurações Login")
        self.btn_save_login.setToolTip("Gravar configurações de login. Atalho: Ctrl+G.")
        self.btn_save_login.clicked.connect(self._on_save_login_settings)
        lay.addRow(self.btn_save_login)

        self.tabs.addTab(tab, "Login")

        # Carregar configurações existentes
        self._load_login_settings()

    # ------------------------------------------------------------------ Geral
    def _init_general_tab(self) -> None:
        tab = QtWidgets.QWidget()
        self.tab_producao = tab
        lay = QtWidgets.QFormLayout(tab)

        self.ed_base = QtWidgets.QLineEdit()
        btn_base_browse = QtWidgets.QPushButton("Procurar...")
        btn_base_browse.clicked.connect(lambda: self._choose_directory(self.ed_base))
        h_base = QtWidgets.QHBoxLayout()
        h_base.addWidget(self.ed_base, 1)
        h_base.addWidget(btn_base_browse)
        lay.addRow("Pasta base dos Orcamentos", h_base)

        self.ed_materias = QtWidgets.QLineEdit()
        btn_mp_browse = QtWidgets.QPushButton("Procurar...")
        btn_mp_browse.clicked.connect(lambda: self._choose_directory(self.ed_materias))
        h_mp = QtWidgets.QHBoxLayout()
        h_mp.addWidget(self.ed_materias, 1)
        h_mp.addWidget(btn_mp_browse)
        lay.addRow("Pasta Materias Primas", h_mp)

        self.ed_base_dados = QtWidgets.QLineEdit()
        btn_db_browse = QtWidgets.QPushButton("Procurar...")
        btn_db_browse.clicked.connect(lambda: self._choose_directory(self.ed_base_dados))
        h_db = QtWidgets.QHBoxLayout()
        h_db.addWidget(self.ed_base_dados, 1)
        h_db.addWidget(btn_db_browse)
        lay.addRow("Pasta Base Dados Orçamento", h_db)

        self.ed_base_producao = QtWidgets.QLineEdit()
        btn_base_producao = QtWidgets.QPushButton("Procurar...")
        btn_base_producao.clicked.connect(lambda: self._choose_directory(self.ed_base_producao))
        h_prod = QtWidgets.QHBoxLayout()
        h_prod.addWidget(self.ed_base_producao, 1)
        h_prod.addWidget(btn_base_producao)
        lay.addRow("Pasta base Produção", h_prod)

        self.ed_imorder_base = QtWidgets.QLineEdit()
        btn_imorder_base = QtWidgets.QPushButton("Procurar...")
        btn_imorder_base.clicked.connect(lambda: self._choose_directory(self.ed_imorder_base))
        h_imorder = QtWidgets.QHBoxLayout()
        h_imorder.addWidget(self.ed_imorder_base, 1)
        h_imorder.addWidget(btn_imorder_base)
        lay.addRow("Pasta Base Imorder (Imos IX)", h_imorder)

        self.ed_cutrite_exe = QtWidgets.QLineEdit()
        btn_cutrite_exe = QtWidgets.QPushButton("Procurar...")
        btn_cutrite_exe.clicked.connect(
            lambda: self._choose_existing_file(
                self.ed_cutrite_exe,
                "Selecionar executavel CUT-RITE",
                "Executaveis (*.exe);;Todos os ficheiros (*)",
            )
        )
        h_cutrite = QtWidgets.QHBoxLayout()
        h_cutrite.addWidget(self.ed_cutrite_exe, 1)
        h_cutrite.addWidget(btn_cutrite_exe)
        lay.addRow("Executavel CUT-RITE", h_cutrite)

        self.ed_cutrite_workdir = QtWidgets.QLineEdit()
        btn_cutrite_workdir = QtWidgets.QPushButton("Procurar...")
        btn_cutrite_workdir.clicked.connect(lambda: self._choose_directory(self.ed_cutrite_workdir))
        h_cutrite_workdir = QtWidgets.QHBoxLayout()
        h_cutrite_workdir.addWidget(self.ed_cutrite_workdir, 1)
        h_cutrite_workdir.addWidget(btn_cutrite_workdir)
        lay.addRow("Pasta Trabalho CUT-RITE", h_cutrite_workdir)

        self.ed_cutrite_data = QtWidgets.QLineEdit()
        btn_cutrite_data = QtWidgets.QPushButton("Procurar...")
        btn_cutrite_data.clicked.connect(lambda: self._choose_directory(self.ed_cutrite_data))
        h_cutrite_data = QtWidgets.QHBoxLayout()
        h_cutrite_data.addWidget(self.ed_cutrite_data, 1)
        h_cutrite_data.addWidget(btn_cutrite_data)
        lay.addRow("Pasta Dados CUT-RITE", h_cutrite_data)

        self.ed_cnc_source_root = QtWidgets.QLineEdit()
        btn_cnc_source_root = QtWidgets.QPushButton("Procurar...")
        btn_cnc_source_root.clicked.connect(lambda: self._choose_directory(self.ed_cnc_source_root))
        h_cnc_source_root = QtWidgets.QHBoxLayout()
        h_cnc_source_root.addWidget(self.ed_cnc_source_root, 1)
        h_cnc_source_root.addWidget(btn_cnc_source_root)
        lay.addRow("Pasta Origem Programas CNC", h_cnc_source_root)

        self.ed_mpr_root = QtWidgets.QLineEdit()
        btn_mpr_root = QtWidgets.QPushButton("Procurar...")
        btn_mpr_root.clicked.connect(lambda: self._choose_directory(self.ed_mpr_root))
        h_mpr_root = QtWidgets.QHBoxLayout()
        h_mpr_root.addWidget(self.ed_mpr_root, 1)
        h_mpr_root.addWidget(btn_mpr_root)
        lay.addRow("Pasta Destino Programas CNC", h_mpr_root)

        self.ed_ia_base = QtWidgets.QLineEdit()
        btn_ia_base = QtWidgets.QPushButton("Procurar...")
        btn_ia_base.clicked.connect(lambda: self._choose_directory(self.ed_ia_base))
        h_ia_base = QtWidgets.QHBoxLayout()
        h_ia_base.addWidget(self.ed_ia_base, 1)
        h_ia_base.addWidget(btn_ia_base)
        lay.addRow("Pasta Pesquisa Profunda IA", h_ia_base)

        self.ed_ia_emb = QtWidgets.QLineEdit()
        btn_ia_emb = QtWidgets.QPushButton("Procurar...")
        btn_ia_emb.clicked.connect(lambda: self._choose_directory(self.ed_ia_emb))
        h_ia_emb = QtWidgets.QHBoxLayout()
        h_ia_emb.addWidget(self.ed_ia_emb, 1)
        h_ia_emb.addWidget(btn_ia_emb)
        lay.addRow("Pasta Embeddings IA", h_ia_emb)

        self.ed_ia_model = QtWidgets.QLineEdit()
        btn_ia_model = QtWidgets.QPushButton("Procurar...")
        btn_ia_model.clicked.connect(lambda: self._choose_directory(self.ed_ia_model))
        h_ia_model = QtWidgets.QHBoxLayout()
        h_ia_model.addWidget(self.ed_ia_model, 1)
        h_ia_model.addWidget(btn_ia_model)
        lay.addRow("Pasta Modelo IA (texto)", h_ia_model)
        self.ed_log_path = QtWidgets.QLineEdit()
        self.ed_log_path.setReadOnly(True)
        self.ed_log_path.setToolTip("Caminho do ficheiro martelo_debug.log.")
        btn_log_open = QtWidgets.QPushButton("Abrir log")
        btn_log_open.clicked.connect(self._open_log_path)
        h_log = QtWidgets.QHBoxLayout()
        h_log.addWidget(self.ed_log_path, 1)
        h_log.addWidget(btn_log_open)
        lay.addRow("Ficheiro de log", h_log)

        self.cmb_ia_provider = QtWidgets.QComboBox()
        self.cmb_ia_provider.addItems(["auto", "local", "openai"])
        lay.addRow("Provedor resposta IA", self.cmb_ia_provider)

        self.ed_ia_openai_model = QtWidgets.QLineEdit()
        lay.addRow("Modelo OpenAI (texto)", self.ed_ia_openai_model)

        self.btn_auto_dims = QtWidgets.QPushButton()
        self.btn_auto_dims.setCheckable(True)
        self.btn_auto_dims.toggled.connect(self._update_auto_dims_label)
        if self._current_user_id is None:
            self.btn_auto_dims.setEnabled(False)
            self.btn_auto_dims.setToolTip("Disponivel apenas para utilizadores autenticados.")
            self.btn_auto_dims.setChecked(False)
        else:
            try:
                auto_enabled = svc_custeio.is_auto_dimension_enabled(self.db, self._current_user_id)
            except Exception:
                auto_enabled = False
            self.btn_auto_dims.setChecked(auto_enabled)
        self._update_auto_dims_label(self.btn_auto_dims.isChecked())

        self.btn_auto_dims_help = QtWidgets.QToolButton()
        self.btn_auto_dims_help.setText("?")
        self.btn_auto_dims_help.setAutoRaise(True)
        self.btn_auto_dims_help.setToolTip(AUTO_DIMS_HELP_TEXT)
        self.btn_auto_dims_help.clicked.connect(self._show_auto_dims_help)

        self.btn_auto_dims_config = QtWidgets.QPushButton("Selecionar peças…")
        self.btn_auto_dims_config.clicked.connect(self._on_config_auto_dims_clicked)
        if self._current_user_id is None:
            self.btn_auto_dims_config.setEnabled(False)

        auto_layout = QtWidgets.QHBoxLayout()
        auto_layout.addWidget(self.btn_auto_dims)
        auto_layout.addWidget(self.btn_auto_dims_config)
        auto_layout.addWidget(self.btn_auto_dims_help)
        auto_layout.addStretch(1)
        lay.addRow("Preencher COMP/LARG automaticamente", auto_layout)

        self.lbl_auto_dims_summary = QtWidgets.QLabel()
        self.lbl_auto_dims_summary.setWordWrap(True)
        self.lbl_auto_dims_summary.setStyleSheet("color: #555555; font-size: 11px;")
        lay.addRow("", self.lbl_auto_dims_summary)

        self.btn_save_general = QtWidgets.QPushButton("Gravar Configurações")
        self.btn_save_general.setToolTip("Gravar configurações gerais. Atalho: Ctrl+G.")
        self.btn_save_general.clicked.connect(self.on_save)
        lay.addRow(self.btn_save_general)

        self.tabs.addTab(tab, "Geral")

        # load defaults
        self.ed_base.setText(get_setting(self.db, KEY_BASE_PATH, DEFAULT_BASE_PATH))
        self.ed_materias.setText(get_setting(self.db, KEY_MATERIAS_BASE_PATH, DEFAULT_MATERIAS_BASE_PATH))
        self.ed_base_dados.setText(get_setting(self.db, KEY_ORC_DB_BASE, DEFAULT_BASE_DADOS_ORC))
        self.ed_base_producao.setText(get_setting(self.db, KEY_PRODUCAO_BASE_PATH, DEFAULT_BASE_PRODUCAO))
        self.ed_imorder_base.setText(
            get_setting(
                self.db,
                svc_producao_processos.KEY_IMORDER_BASE_PATH,
                svc_producao_processos.DEFAULT_IMORDER_BASE_PATH,
            )
        )
        self.ed_cutrite_exe.setText(svc_cutrite.resolve_cutrite_exe_path(self.db) or "")
        cutrite_workdir, cutrite_data_dir = svc_cutrite.resolve_configured_cutrite_paths(self.db)
        self.ed_cutrite_workdir.setText(str(cutrite_workdir or ""))
        self.ed_cutrite_data.setText(str(cutrite_data_dir or ""))
        self.ed_cnc_source_root.setText(
            get_setting(
                self.db,
                svc_producao_preparacao.KEY_PRODUCAO_CNC_SOURCE_ROOT,
                svc_producao_preparacao.DEFAULT_PRODUCAO_CNC_SOURCE_ROOT,
            )
        )
        self.ed_mpr_root.setText(
            get_setting(
                self.db,
                svc_producao_preparacao.KEY_PRODUCAO_MPR_ROOT,
                svc_producao_preparacao.DEFAULT_PRODUCAO_MPR_ROOT,
            )
        )
        self.ed_ia_base.setText(svc_ia.ia_base_path(self.db))
        self.ed_ia_emb.setText(svc_ia.ia_embeddings_path(self.db))
        self.ed_ia_model.setText(svc_ia.ia_model_path(self.db))
        self.ed_log_path.setText(str(self._resolve_log_path()))
        self.cmb_ia_provider.setCurrentText(get_setting(self.db, svc_ia.KEY_IA_GEN_PROVIDER, svc_ia.DEFAULT_IA_GEN_PROVIDER))
        self.ed_ia_openai_model.setText(get_setting(self.db, svc_ia.KEY_IA_OPENAI_MODEL, svc_ia.DEFAULT_IA_OPENAI_MODEL))
        self._refresh_auto_dims_summary()

    def _resolve_log_path(self) -> Path:
        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
            if base:
                candidates.append(Path(base) / "Martelo_Orcamentos_V2")
            try:
                candidates.append(Path(sys.executable).resolve().parent)
            except Exception:
                pass
        else:
            candidates.append(Path(__file__).resolve().parents[2])
        for log_dir in candidates:
            log_path = log_dir / "martelo_debug.log"
            if log_path.exists():
                return log_path
        return (candidates[0] / "martelo_debug.log") if candidates else Path("martelo_debug.log")

    def _open_log_path(self) -> None:
        if hasattr(self, "ed_log_path") and self.ed_log_path.text().strip():
            log_path = Path(self.ed_log_path.text().strip())
        else:
            log_path = self._resolve_log_path()
        if log_path.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(log_path)))
            return
        parent = log_path.parent
        if parent.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(parent)))
            QtWidgets.QMessageBox.information(
                self,
                "Log",
                "O ficheiro de log ainda nao existe. Foi aberta a pasta.",
            )
            return
        QtWidgets.QMessageBox.warning(
            self,
            "Log",
            "Nao foi possivel localizar a pasta de log.",
        )

    def _choose_directory(self, line_edit: QtWidgets.QLineEdit) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Escolher pasta")
        if directory:
            line_edit.setText(directory)

    def _choose_existing_file(self, line_edit: QtWidgets.QLineEdit, title: str, file_filter: str) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, title, line_edit.text().strip(), file_filter)
        if file_path:
            line_edit.setText(file_path)

    # ------------------------------------------------------------------ PHC
    def _init_phc_tab(self) -> None:
        tab = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(tab)

        info = QtWidgets.QLabel(
            "Ligação PHC (SQL Server).\n"
            "IMPORTANTE: o Martelo apenas faz consultas SELECT ao PHC (nunca escreve)."
        )
        info.setWordWrap(True)
        vbox.addWidget(info)

        gb = QtWidgets.QGroupBox("Ligação PHC (SQL Server)")
        form = QtWidgets.QFormLayout(gb)

        self.ed_phc_server = QtWidgets.QLineEdit()
        self.ed_phc_server.setToolTip("Servidor SQL do PHC (ex.: Server_le\\phc).")
        self.ed_phc_database = QtWidgets.QLineEdit()
        self.ed_phc_database.setToolTip("Base de dados do PHC (ex.: lancaencanto).")

        self.chk_phc_trusted = QtWidgets.QCheckBox("Autenticação Windows (Trusted_Connection)")
        self.chk_phc_trusted.setToolTip("Quando ativo usa autenticação Windows em vez de Utilizador/Password.")

        self.chk_phc_trust_cert = QtWidgets.QCheckBox("TrustServerCertificate=yes (recomendado em redes internas)")
        self.chk_phc_trust_cert.setToolTip("Evita problemas de certificado em redes internas.")

        self.ed_phc_user = QtWidgets.QLineEdit()
        self.ed_phc_user.setToolTip("Utilizador SQL do PHC (ex.: adriano.silva).")
        self.ed_phc_password = QtWidgets.QLineEdit()
        self.ed_phc_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.ed_phc_password.setToolTip("Password SQL do PHC.")

        form.addRow("Servidor:", self.ed_phc_server)
        form.addRow("Base de Dados:", self.ed_phc_database)
        form.addRow("", self.chk_phc_trust_cert)
        form.addRow("", self.chk_phc_trusted)
        form.addRow("Utilizador:", self.ed_phc_user)
        form.addRow("Password:", self.ed_phc_password)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_phc_save = QtWidgets.QPushButton("Guardar Configuração PHC")
        self.btn_phc_save.setToolTip(
            "Guarda a configuração da ligação ao PHC na base de dados do Martelo. Atalho: Ctrl+G."
        )
        self.btn_phc_test = QtWidgets.QPushButton("Testar Ligação")
        self.btn_phc_test.setToolTip("Testa a ligação ao PHC com uma query SELECT simples (read-only).")
        btn_row.addWidget(self.btn_phc_save)
        btn_row.addWidget(self.btn_phc_test)
        btn_row.addStretch(1)
        form.addRow(btn_row)

        self.lbl_phc_status = QtWidgets.QLabel("")
        self.lbl_phc_status.setStyleSheet("color:#555;")
        form.addRow(self.lbl_phc_status)

        self.btn_phc_save.clicked.connect(self._on_save_phc_settings)
        self.btn_phc_test.clicked.connect(self._on_test_phc_connection)
        self.chk_phc_trusted.toggled.connect(self._on_phc_trusted_toggled)

        vbox.addWidget(gb)
        vbox.addStretch(1)

        self.tabs.addTab(tab, "PHC (SQL Server)")

        cfg = svc_phc.load_phc_config(self.db)
        self.ed_phc_server.setText(cfg["server"])
        self.ed_phc_database.setText(cfg["database"])
        self.chk_phc_trusted.setChecked(bool(cfg["trusted"]))
        self.chk_phc_trust_cert.setChecked(bool(cfg["trust_server_certificate"]))
        self.ed_phc_user.setText(cfg["user"])
        self.ed_phc_password.setText(cfg["password"])
        self._on_phc_trusted_toggled(bool(cfg["trusted"]))

    def _on_phc_trusted_toggled(self, checked: bool) -> None:
        enabled = not bool(checked)
        self.ed_phc_user.setEnabled(enabled)
        self.ed_phc_password.setEnabled(enabled)

    def _on_save_phc_settings(self) -> None:
        self.lbl_phc_status.setText("")
        try:
            set_setting(self.db, svc_phc.KEY_PHC_SERVER, self.ed_phc_server.text().strip() or None)
            set_setting(self.db, svc_phc.KEY_PHC_DATABASE, self.ed_phc_database.text().strip() or None)
            set_setting(self.db, svc_phc.KEY_PHC_TRUSTED, "1" if self.chk_phc_trusted.isChecked() else "0")
            set_setting(self.db, svc_phc.KEY_PHC_TRUST_CERT, "1" if self.chk_phc_trust_cert.isChecked() else "0")
            set_setting(self.db, svc_phc.KEY_PHC_USER, self.ed_phc_user.text().strip() or None)
            password = self.ed_phc_password.text()
            if str(password).strip():
                set_setting(self.db, svc_phc.KEY_PHC_PASSWORD, password)
            self.db.commit()
            self.lbl_phc_status.setText("Configuração PHC gravada.")
            QtWidgets.QMessageBox.information(self, "OK", "Configuração PHC gravada.")
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar configuração PHC: {exc}")

    def _on_test_phc_connection(self) -> None:
        self.lbl_phc_status.setText("")
        try:
            cfg: svc_phc.PHCConfig = {
                "server": self.ed_phc_server.text().strip(),
                "database": self.ed_phc_database.text().strip(),
                "trusted": bool(self.chk_phc_trusted.isChecked()),
                "trust_server_certificate": bool(self.chk_phc_trust_cert.isChecked()),
                "user": self.ed_phc_user.text().strip(),
                "password": self.ed_phc_password.text(),
            }
            conn_str = svc_phc.build_connection_string(cfg)
            svc_phc.run_select(conn_str, "SELECT 1 AS OK;")
            self.lbl_phc_status.setText("Ligação OK.")
            QtWidgets.QMessageBox.information(self, "OK", "Ligação PHC OK.")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao testar ligação PHC:\n\n{exc}")

    def on_save(self) -> None:
        try:
            base_path = self.ed_base.text().strip() or DEFAULT_BASE_PATH
            materias_path = self.ed_materias.text().strip() or DEFAULT_MATERIAS_BASE_PATH
            base_dados = self.ed_base_dados.text().strip() or DEFAULT_BASE_DADOS_ORC
            base_producao = self.ed_base_producao.text().strip() or DEFAULT_BASE_PRODUCAO
            imorder_base = self.ed_imorder_base.text().strip() or svc_producao_processos.DEFAULT_IMORDER_BASE_PATH
            cutrite_exe = self.ed_cutrite_exe.text().strip()
            cutrite_workdir_input = self.ed_cutrite_workdir.text().strip()
            cutrite_data_input = self.ed_cutrite_data.text().strip()
            cnc_source_root = self.ed_cnc_source_root.text().strip() or svc_producao_preparacao.DEFAULT_PRODUCAO_CNC_SOURCE_ROOT
            mpr_root = self.ed_mpr_root.text().strip() or svc_producao_preparacao.DEFAULT_PRODUCAO_MPR_ROOT
            cutrite_workdir_path, cutrite_data_path, cutrite_paths_warning = svc_cutrite.normalize_cutrite_path_inputs(
                cutrite_workdir_input,
                cutrite_data_input,
            )
            if cutrite_workdir_input and cutrite_workdir_path is None:
                raise ValueError(
                    "A Pasta Trabalho CUT-RITE deve apontar para a pasta de perfil do utilizador.\n\n"
                    "Exemplo: \\\\SERVER_LE\\Homag_iX\\Cutrite\\V12-Data\\Paulo_Catarino"
                )
            if cutrite_data_input and cutrite_data_path is None:
                raise ValueError(
                    "A Pasta Dados CUT-RITE deve apontar para uma pasta de dados existente.\n\n"
                    "Exemplo: \\\\SERVER_LE\\Homag_iX\\Cutrite\\V12-Data\\Data"
                )
            ia_base = self.ed_ia_base.text().strip() or svc_ia.DEFAULT_IA_BASE_PATH
            ia_emb = self.ed_ia_emb.text().strip() or svc_ia.DEFAULT_IA_EMB_PATH
            ia_model = self.ed_ia_model.text().strip() or svc_ia.DEFAULT_IA_MODEL_PATH
            ia_provider = self.cmb_ia_provider.currentText().strip() or svc_ia.DEFAULT_IA_GEN_PROVIDER
            ia_openai_model = self.ed_ia_openai_model.text().strip() or svc_ia.DEFAULT_IA_OPENAI_MODEL
            set_setting(self.db, KEY_BASE_PATH, base_path)
            set_setting(self.db, KEY_MATERIAS_BASE_PATH, materias_path)
            set_setting(self.db, KEY_ORC_DB_BASE, base_dados)
            set_setting(self.db, KEY_PRODUCAO_BASE_PATH, base_producao)
            set_setting(self.db, svc_producao_processos.KEY_IMORDER_BASE_PATH, imorder_base)
            set_setting(self.db, svc_cutrite.KEY_CUTRITE_EXE_PATH, cutrite_exe or None)
            set_setting(self.db, svc_cutrite.KEY_CUTRITE_WORKDIR_PATH, str(cutrite_workdir_path) if cutrite_workdir_path else None)
            set_setting(self.db, svc_cutrite.KEY_CUTRITE_DATA_PATH, str(cutrite_data_path) if cutrite_data_path else None)
            set_setting(self.db, svc_producao_preparacao.KEY_PRODUCAO_CNC_SOURCE_ROOT, cnc_source_root)
            set_setting(self.db, svc_producao_preparacao.KEY_PRODUCAO_MPR_ROOT, mpr_root)
            set_setting(self.db, svc_ia.KEY_IA_BASE_PATH, ia_base)
            set_setting(self.db, svc_ia.KEY_IA_EMB_PATH, ia_emb)
            set_setting(self.db, svc_ia.KEY_IA_MODEL_PATH, ia_model)
            set_setting(self.db, svc_ia.KEY_IA_GEN_PROVIDER, ia_provider)
            set_setting(self.db, svc_ia.KEY_IA_OPENAI_MODEL, ia_openai_model)
            if self._current_user_id is not None:
                svc_custeio.set_auto_dimension_enabled(self.db, self._current_user_id, self.btn_auto_dims.isChecked())
            self.db.commit()
            self.ed_cutrite_workdir.setText(str(cutrite_workdir_path or ""))
            self.ed_cutrite_data.setText(str(cutrite_data_path or ""))
            self.ed_cnc_source_root.setText(cnc_source_root)
            self.ed_mpr_root.setText(mpr_root)
            message = "Configuracoes gravadas."
            if cutrite_paths_warning:
                message += f"\n\n{cutrite_paths_warning}"
            QtWidgets.QMessageBox.information(self, "OK", message)
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar: {exc}")

    def _open_rules_dialog(self) -> None:
        dlg = QtRulesDialog(self.db, self)
        dlg.exec()

    def _update_auto_dims_label(self, checked: bool) -> None:
        state = "ON" if checked else "OFF"
        self.btn_auto_dims.setText(f"Auto preenchimento: {state}")
        self.btn_auto_dims.setToolTip(f"{AUTO_DIMS_HELP_TEXT}\n\nEstado atual: {state}.")
        self._refresh_auto_dims_summary()

    def _refresh_auto_dims_summary(self) -> None:
        label = getattr(self, "lbl_auto_dims_summary", None)
        if label is None:
            return
        if self._current_user_id is None:
            label.setText("Disponível apenas após autenticação.")
            return
        try:
            available = svc_custeio.list_available_auto_dimension_rules()
            selected = svc_custeio.load_auto_dimension_prefixes(self.db, self._current_user_id)
        except Exception as exc:
            label.setText(f"Não foi possível carregar as peças: {exc}")
            return
        total = len(available)
        if selected is None or (total and len(selected) == total):
            resumo = "todas as peças padrão."
        elif not selected:
            resumo = "nenhuma peça selecionada."
        else:
            order = [prefix for prefix, _, _ in available if prefix in selected]
            preview = ", ".join(order[:6])
            if len(order) > 6:
                preview += f" … (+{len(order) - 6})"
            resumo = preview
        estado = "ativo" if self.btn_auto_dims.isChecked() else "inativo"
        label.setText(f"Estado atual: {estado}. Peças configuradas: {resumo}")

    def _on_config_auto_dims_clicked(self) -> None:
        if self._current_user_id is None:
            QtWidgets.QMessageBox.information(self, "Configuração", "Disponível apenas para utilizadores autenticados.")
            return
        try:
            available = svc_custeio.list_available_auto_dimension_rules()
            selected = svc_custeio.load_auto_dimension_prefixes(self.db, self._current_user_id)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Não foi possível carregar as peças: {exc}")
            return
        if selected is None:
            selected = [prefix for prefix, _, _ in available]

        dialog = AutoDimensionPiecesDialog(self, available, selected)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return

        novos = dialog.selected_prefixes()
        payload: Optional[Sequence[str]]
        if len(novos) == len(available):
            payload = None  # usa padrão
        else:
            payload = novos
        try:
            svc_custeio.save_auto_dimension_prefixes(self.db, self._current_user_id, payload)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(
                self,
                "Erro",
                f"Falha ao guardar as peças de preenchimento automático:\n{exc}",
            )
            return
        self._refresh_auto_dims_summary()

    def _show_auto_dims_help(self) -> None:
        QtWidgets.QMessageBox.information(self, "Ajuda", AUTO_DIMS_HELP_TEXT, QtWidgets.QMessageBox.Ok)

    def _load_margens_settings(self) -> None:
        if not hasattr(self, "_margem_inputs"):
            return
        try:
            valores = svc_margens.load_margens(self.db)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Aviso", f"Falha ao carregar margens: {exc}")
            valores = svc_margens.default_values()
        defaults = svc_margens.default_values()
        for key, widget in self._margem_inputs.items():
            value = valores.get(key, defaults.get(key))
            if widget is None or value is None:
                continue
            widget.blockSignals(True)
            widget.setValue(float(value))
            widget.blockSignals(False)

    def _collect_margens_inputs(self) -> Dict[str, Decimal]:
        valores: Dict[str, Decimal] = {}
        if not hasattr(self, "_margem_inputs"):
            return valores
        for key, widget in self._margem_inputs.items():
            valores[key] = Decimal(f"{widget.value():.4f}")
        return valores

    def _on_margens_save(self) -> None:
        valores = self._collect_margens_inputs()
        try:
            svc_margens.save_margens(self.db, valores)
            self.db.commit()
            QtWidgets.QMessageBox.information(self, "Sucesso", "Margens gravadas.")
            self.margens_updated.emit()
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar margens: {exc}")

    def _on_margens_reset(self) -> None:
        defaults = svc_margens.default_values()
        for key, widget in self._margem_inputs.items():
            value = defaults.get(key, Decimal("0"))
            widget.blockSignals(True)
            widget.setValue(float(value))
            widget.blockSignals(False)
        self._on_margens_save()

    def _init_margens_tab(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        label = QtWidgets.QLabel(
            "Configure os valores padrão das margens utilizadas no cálculo dos itens. "
            "Estas percentagens podem ser ajustadas posteriormente por orçamento."
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        container = QtWidgets.QWidget()
        container_layout = QtWidgets.QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(10)

        group = QtWidgets.QGroupBox("Margens e Ajustes padrão")
        group.setMaximumWidth(520)
        grid = QtWidgets.QGridLayout(group)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)

        self._margem_inputs = {}
        for idx, spec in enumerate(svc_margens.MARGEM_FIELDS):
            key = str(spec["key"])
            label_widget = QtWidgets.QLabel(str(spec["label"]))
            spin = QtWidgets.QDoubleSpinBox()
            spin.setDecimals(2)
            spin.setRange(0.0, 500.0)
            spin.setSingleStep(0.25)
            spin.setSuffix(" %")
            spin.setAlignment(QtCore.Qt.AlignRight)
            col = idx % 2
            row = idx // 2
            grid.addWidget(label_widget, row, col * 2)
            grid.addWidget(spin, row, col * 2 + 1)
            self._margem_inputs[key] = spin

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        container_layout.addWidget(group, alignment=QtCore.Qt.AlignHCenter)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_margens_save = QtWidgets.QPushButton("Guardar Margens")
        self.btn_margens_save.setToolTip("Guardar margens e ajustes. Atalho: Ctrl+G.")
        self.btn_margens_save.clicked.connect(self._on_margens_save)
        self.btn_margens_reset = QtWidgets.QPushButton("Repor Valores Padrão")
        self.btn_margens_reset.clicked.connect(self._on_margens_reset)
        btn_layout.addWidget(self.btn_margens_save)
        btn_layout.addWidget(self.btn_margens_reset)
        btn_layout.addStretch(1)
        container_layout.addLayout(btn_layout)

        layout.addWidget(container, alignment=QtCore.Qt.AlignHCenter)
        layout.addStretch(1)

        self.tabs.addTab(tab, "Margens & Ajustes")
        self._load_margens_settings()

    # ----------------------------------------------------- Regras de quantidade
    def _init_qt_rules_tab(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        intro = QtWidgets.QLabel(
            "Configure aqui as regras de quantidade (qt_und) aplicadas aos componentes filhos "
            "na tabela de custeio. Pode editar regras padrão ou definir regras específicas por "
            "orçamento/versão usando o editor dedicado."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        rules_box = QtWidgets.QGroupBox("Editor de Regras")
        rules_box.setToolTip(
            "Abra o editor para alterar expressoes/matches das regras de quantidade. "
            "Pode carregar regras por orçamento/versão ou repor os valores padrão."
        )
        rules_layout = QtWidgets.QVBoxLayout(rules_box)
        rules_layout.setSpacing(8)
        rules_box.setMinimumWidth(980)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_open_rules = QtWidgets.QPushButton("Abrir editor de regras")
        self.btn_open_rules.setToolTip(
            "Abre o editor de regras qt_und. Permite carregar/repor regras e gravar alteracoes."
        )
        self.btn_open_rules.clicked.connect(self._open_rules_dialog)
        btn_row.addWidget(self.btn_open_rules)

        self.btn_reset_rules = QtWidgets.QPushButton("Repor regras padrão")
        self.btn_reset_rules.setToolTip("Repor regras padrão (STD) para todos os orçamentos.")
        self.btn_reset_rules.clicked.connect(self._reset_qt_rules_default)
        btn_row.addWidget(self.btn_reset_rules)

        btn_row.addStretch(1)
        rules_layout.addLayout(btn_row)

        self.lbl_rules_summary = QtWidgets.QLabel()
        self.lbl_rules_summary.setStyleSheet("color: #555555;")
        rules_layout.addWidget(self.lbl_rules_summary)

        helper = QtWidgets.QLabel(
            "<b>Variáveis disponíveis:</b> COMP, LARG, ESP, COMP_MP, LARG_MP, ESP_MP, QT_PAI, QT_DIV, QT_MOD.<br>"
            "Use Python simples (if/else) nas expressões. Ex.: <code>2 * QT_PAI</code>."
        )
        helper.setWordWrap(True)
        rules_layout.addWidget(helper)

        layout.addWidget(rules_box)
        layout.addStretch(1)

        self.tabs.addTab(tab, "Regras Qt_und")
        self._refresh_rules_summary()

    def _on_shortcut_save(self) -> None:
        current = self.tabs.currentIndex() if hasattr(self, "tabs") else -1
        btn = None
        if current == 0:
            btn = getattr(self, "btn_save_login", None)
        elif current == 1:
            btn = getattr(self, "btn_save_general", None)
        elif current == 2:
            btn = getattr(self, "btn_phc_save", None)
        elif current == 3:
            btn = getattr(self, "btn_producao_save", None)
        elif current == 4:
            btn = getattr(self, "btn_def_pecas_save", None)
        elif current == 5:
            btn = getattr(self, "btn_margens_save", None)
        if btn is not None and btn.isEnabled():
            btn.click()

    def _refresh_rules_summary(self) -> None:
        if not hasattr(self, "lbl_rules_summary"):
            return
        try:
            regras = svc_custeio.load_qt_rules(self.db, None)
            total = len(regras)
            self.lbl_rules_summary.setText(f"Regras carregadas: {total}. Use o editor para ajustar ou duplicar regras.")
        except Exception as exc:
            self.lbl_rules_summary.setText(f"Não foi possível carregar as regras: {exc}")

    def _reset_qt_rules_default(self) -> None:
        if (
            QtWidgets.QMessageBox.question(
                self,
                "Confirmar",
                "Repor todas as regras de quantidade para o padrão (STD)? Esta ação é irreversível.",
            )
            != QtWidgets.QMessageBox.Yes
        ):
            return
        try:
            svc_custeio.reset_qt_rules(self.db, None, reset_default=True)
            self.db.commit()
            self._refresh_rules_summary()
            QtWidgets.QMessageBox.information(self, "OK", "Regras padrão repostas.")
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao repor regras: {exc}")

    # -------------------------------------------------------- Dados produtivos
    def _init_producao_tab(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        self.lbl_producao_info = QtWidgets.QLabel("Selecione um orçamento para editar os dados produtivos.")
        self.lbl_producao_info.setWordWrap(True)
        layout.addWidget(self.lbl_producao_info)

        buttons_layout = QtWidgets.QHBoxLayout()
        self.btn_producao_reset = QtWidgets.QPushButton("Repor Valores Padrão")
        self.btn_producao_reset.clicked.connect(self._on_producao_reset)
        buttons_layout.addWidget(self.btn_producao_reset)

        self.btn_producao_save = QtWidgets.QPushButton("Gravar Dados Produtivos")
        self.btn_producao_save.setToolTip("Gravar dados produtivos. Atalho: Ctrl+G.")
        self.btn_producao_save.clicked.connect(self._on_producao_save)
        buttons_layout.addWidget(self.btn_producao_save)

        self.btn_producao_refresh = QtWidgets.QPushButton("Atualizar")
        self.btn_producao_refresh.clicked.connect(lambda: self._load_producao_table(force=True))
        buttons_layout.addWidget(self.btn_producao_refresh)

        buttons_layout.addStretch(1)
        style = self.style() or QtWidgets.QApplication.style()
        self.btn_producao_reset.setIcon(style.standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        self.btn_producao_save.setIcon(style.standardIcon(QtWidgets.QStyle.SP_DialogSaveButton))
        self.btn_producao_refresh.setIcon(style.standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        layout.addLayout(buttons_layout)

        self.tbl_producao = QtWidgets.QTableWidget(0, len(self.PRODUCAO_HEADERS))
        self.tbl_producao.setHorizontalHeaderLabels(self.PRODUCAO_HEADERS)
        header = self.tbl_producao.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        header.setMinimumSectionSize(120)
        self.tbl_producao.verticalHeader().setVisible(False)
        self.tbl_producao.setAlternatingRowColors(True)
        self.tbl_producao.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        self.tbl_producao.itemChanged.connect(self._on_producao_item_changed)
        layout.addWidget(self.tbl_producao, 1)

        self.tabs.addTab(tab, "Dados Produtivos")
        self._set_producao_controls_enabled(False)

    def set_orcamento_context(self, orcamento_id: Optional[int], versao: Optional[str] = None) -> None:
        try:
            self.db.rollback()
        except Exception:
            pass
        if self._current_user_id is None or not orcamento_id:
            self._producao_ctx = None
            self._set_producao_controls_enabled(False)
            self._clear_producao_table()
            self._producao_mode = "--"
            self._producao_dirty = False
            self.lbl_producao_info.setText("Selecione um orçamento para editar os dados produtivos.")
            return
        try:
            try:
                self.db.expire_all()
            except Exception:
                pass
            ctx = svc_producao.build_context(self.db, orcamento_id, self._current_user_id, versao=versao)
        except Exception as exc:
            # registar diagnostico mais detalhado para facilitar debugging
            try:
                logger.exception("set_orcamento_context: falha ao carregar contexto para orcamento %s: %s", orcamento_id, exc)
            except Exception:
                pass
            # Fazer diagnóstico interativo: verificar na sessão actual, numa nova sessão e por SELECT raw
            try:
                from Martelo_Orcamentos_V2.app.models import Orcamento

                initial_found = False
                try:
                    initial_found = self.db.get(Orcamento, orcamento_id) is not None
                except Exception:
                    initial_found = False

                tmp_found = False
                raw_res = None
                try:
                    with SessionLocal() as tmp:
                        try:
                            tmp_found = tmp.get(Orcamento, orcamento_id) is not None
                        except Exception:
                            tmp_found = False
                        try:
                            raw_res = tmp.execute(
                                "SELECT id, ano, num_orcamento, versao FROM orcamento WHERE id = :id",
                                {"id": orcamento_id},
                            ).fetchone()
                        except Exception:
                            raw_res = None

                except Exception:
                    tmp_found = False
                    raw_res = None

                # mostrar popup com resultado diagnostico para o utilizador
                try:
                    msg = (
                        f"Erro ao carregar contexto para Orçamento ID={orcamento_id}\n\n"
                        f"Exceção: {exc}\n\n"
                        f"Sessão actual encontrou registo? {initial_found}\n"
                        f"Nova sessão encontrou registo? {tmp_found}\n"
                        f"Resultado raw SELECT: {raw_res}\n\n"
                        "Se tmp_found for True mas build_context falhar, veja permissões/transaction isolation/replicação."
                    )
                    QtWidgets.QMessageBox.critical(self, "Erro (diagnóstico)", msg)
                except Exception:
                    pass

                # gravar diagnostico em ficheiro temporario no directório do projecto
                try:
                    diag_path = os.path.join(os.getcwd(), "martelo_orc_diag.txt")
                    with open(diag_path, "a", encoding="utf-8") as f:
                        f.write("-----\n")
                        f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
                        f.write(f"Orcamento ID: {orcamento_id}\n")
                        f.write(f"Exception: {repr(exc)}\n")
                        f.write(f"Sessao actual encontrou registo: {initial_found}\n")
                        f.write(f"Nova sessao encontrou registo: {tmp_found}\n")
                        f.write(f"Resultado raw SELECT: {raw_res}\n")
                        f.write("-----\n\n")
                except Exception:
                    try:
                        logger.exception("Falha ao gravar ficheiro de diagnostico para orcamento %s", orcamento_id)
                    except Exception:
                        pass

                # Also print diagnostic to stdout and log it so it appears in the terminal
                try:
                    diag_msg = (
                        "-----\n"
                        f"Timestamp: {datetime.datetime.now().isoformat()}\n"
                        f"Orcamento ID: {orcamento_id}\n"
                        f"Exception: {repr(exc)}\n"
                        f"Sessao actual encontrou registo: {initial_found}\n"
                        f"Nova sessao encontrou registo: {tmp_found}\n"
                        f"Resultado raw SELECT: {raw_res}\n"
                        "-----\n"
                    )
                    # print to stdout (terminal)
                    try:
                        print(diag_msg, flush=True)
                    except Exception:
                        pass
                    # also log via logger at ERROR level
                    try:
                        logger.error("Diagnostico orcamento: %s", diag_msg)
                    except Exception:
                        pass
                except Exception:
                    pass

                # Se nova sessão encontrou o registo, substituimos a sessão local e tentamos novamente
                if tmp_found:
                    try:
                        try:
                            self.db.close()
                        except Exception:
                            pass
                        self.db = SessionLocal()
                        ctx = svc_producao.build_context(self.db, orcamento_id, self._current_user_id, versao=versao)
                    except Exception as exc2:
                        try:
                            logger.exception(
                                "set_orcamento_context: segunda tentativa falhou para orcamento %s: %s",
                                orcamento_id,
                                exc2,
                            )
                        except Exception:
                            pass
                        self.db.rollback()
                        self._producao_ctx = None
                        self._set_producao_controls_enabled(False)
                        self._clear_producao_table()
                        self.lbl_producao_info.setText(f"Falha ao carregar contexto: {exc2}")
                        return
                else:
                    # não encontrado em nenhuma sessão — sair com mensagem já mostrada
                    self.db.rollback()
                    self._producao_ctx = None
                    self._set_producao_controls_enabled(False)
                    self._clear_producao_table()
                    self.lbl_producao_info.setText(f"Falha ao carregar contexto: {exc}")
                    return
            except Exception:
                try:
                    self.db.rollback()
                except Exception:
                    pass
                self._producao_ctx = None
                self._set_producao_controls_enabled(False)
                self._clear_producao_table()
                self.lbl_producao_info.setText(f"Falha ao carregar contexto: {exc}")
                return
        self._producao_ctx = ctx
        self._producao_mode = "(pendente)"
        self._producao_dirty = True
        self._update_producao_info()
        if getattr(self, "tab_producao", None) is not None and self.tabs.currentWidget() is self.tab_producao:
            self._load_producao_table()

    def update_producao_mode_display(self, modo: str) -> None:
        if modo:
            self._producao_mode = modo.upper()
        self._producao_dirty = True
        self._update_producao_info()
        if self._producao_ctx and getattr(self, "tab_producao", None) is not None and self.tabs.currentWidget() is self.tab_producao:
            self._load_producao_table()

    def refresh_producao_mode(self) -> None:
        if not self._producao_ctx:
            return
        self._producao_dirty = True
        if getattr(self, "tab_producao", None) is not None and self.tabs.currentWidget() is self.tab_producao:
            self._load_producao_table()

    def _set_producao_controls_enabled(self, enabled: bool) -> None:
        self.tbl_producao.setEnabled(enabled)
        self.btn_producao_save.setEnabled(enabled)
        self.btn_producao_reset.setEnabled(enabled)
        self.btn_producao_refresh.setEnabled(enabled)

    def _init_def_pecas_tab(self) -> None:
        tab = QtWidgets.QWidget()
        self.tab_def_pecas = tab
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        self.lbl_def_pecas_info = QtWidgets.QLabel(
            "Tabela de referencia para o calculo das linhas do custeio. Altere ou acrescente pecas conforme necessario."
        )
        self.lbl_def_pecas_info.setWordWrap(True)
        layout.addWidget(self.lbl_def_pecas_info)

        search_layout = QtWidgets.QHBoxLayout()
        search_layout.addWidget(QtWidgets.QLabel("Pesquisar:"))
        self.ed_def_pecas_search = QtWidgets.QLineEdit()
        self.ed_def_pecas_search.setPlaceholderText("Filtrar nesta tabela (ID, nome, grupo, CPxx)...")
        self.ed_def_pecas_search.textChanged.connect(self._apply_def_pecas_search)
        search_layout.addWidget(self.ed_def_pecas_search, 1)
        layout.addLayout(search_layout)

        buttons_layout = QtWidgets.QHBoxLayout()
        self.btn_def_pecas_add = QtWidgets.QPushButton("Adicionar Linha")
        self.btn_def_pecas_add.clicked.connect(self._on_def_pecas_add_row)
        buttons_layout.addWidget(self.btn_def_pecas_add)

        self.btn_def_pecas_remove = QtWidgets.QPushButton("Remover Selecionadas")
        self.btn_def_pecas_remove.clicked.connect(self._on_def_pecas_remove_rows)
        buttons_layout.addWidget(self.btn_def_pecas_remove)

        self.btn_def_pecas_refresh = QtWidgets.QPushButton("Atualizar")
        self.btn_def_pecas_refresh.clicked.connect(lambda: self._load_def_pecas_table(force=True))
        buttons_layout.addWidget(self.btn_def_pecas_refresh)

        self.btn_def_pecas_save = QtWidgets.QPushButton("Gravar Definições")
        self.btn_def_pecas_save.setToolTip("Gravar definições de peças. Atalho: Ctrl+G.")
        self.btn_def_pecas_save.clicked.connect(self._on_def_pecas_save)
        buttons_layout.addWidget(self.btn_def_pecas_save)
        buttons_layout.addStretch(1)
        layout.addLayout(buttons_layout)

        self.tbl_def_pecas = QtWidgets.QTableWidget(0, len(self.DEF_PECAS_HEADERS))
        self.tbl_def_pecas.setHorizontalHeaderLabels(self.DEF_PECAS_HEADERS)
        header = self.tbl_def_pecas.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        header.setMinimumSectionSize(120)
        self.tbl_def_pecas.verticalHeader().setVisible(False)
        self.tbl_def_pecas.setAlternatingRowColors(True)
        self.tbl_def_pecas.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_def_pecas.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tbl_def_pecas.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        self.tbl_def_pecas.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tbl_def_pecas.customContextMenuRequested.connect(self._on_def_pecas_context_menu)
        self.tbl_def_pecas.itemChanged.connect(self._on_def_pecas_item_changed)
        layout.addWidget(self.tbl_def_pecas, 1)

        self.tabs.addTab(tab, "Definições Peças")
        self._set_def_pecas_controls_enabled(True)
        self._def_pecas_all: List[Dict[str, Optional[str]]] = []

    def _set_def_pecas_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            getattr(self, "tbl_def_pecas", None),
            getattr(self, "btn_def_pecas_add", None),
            getattr(self, "btn_def_pecas_remove", None),
            getattr(self, "btn_def_pecas_refresh", None),
            getattr(self, "btn_def_pecas_save", None),
        ):
            if widget is not None:
                widget.setEnabled(enabled)

    def _clear_def_pecas_table(self) -> None:
        if getattr(self, "tbl_def_pecas", None) is None:
            return
        self.tbl_def_pecas.blockSignals(True)
        self.tbl_def_pecas.setRowCount(0)
        self.tbl_def_pecas.blockSignals(False)

    def _load_def_pecas_table(self, force: bool = False) -> None:
        if self._def_pecas_loading:
            return
        if not force and not self._def_pecas_dirty:
            return
        try:
            self.db.rollback()
        except Exception:
            pass
        try:
            self._def_pecas_loading = True
            dados = svc_def_pecas.listar_definicoes(self.db)
        except Exception as exc:
            self._def_pecas_loading = False
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar definições de peças: {exc}")
            self._set_def_pecas_controls_enabled(False)
            return

        self._def_pecas_all = dados
        self._apply_def_pecas_search()
        self._def_pecas_loading = False
        self._def_pecas_dirty = False
        self._set_def_pecas_controls_enabled(True)

    def _populate_def_pecas_table(self, dados: List[Dict[str, Optional[str]]]) -> None:
        field_map = {
            "ID": "id",
            "Tipo_Peca_Principal": "tipo_peca_principal",
            "Subgrupo_Peca": "subgrupo_peca",
            "Nome_da_Peca": "nome_da_peca",
            "CP01_SEC": "cp01_sec",
            "CP02_ORL": "cp02_orl",
            "CP03_CNC": "cp03_cnc",
            "CP04_ABD": "cp04_abd",
            "CP05_PRENSA": "cp05_prensa",
            "CP06_ESQUAD": "cp06_esquad",
            "CP07_EMBALAGEM": "cp07_embalagem",
            "CP08_MAO_DE_OBRA": "cp08_mao_de_obra",
        }
        self.tbl_def_pecas.blockSignals(True)
        self.tbl_def_pecas.setRowCount(len(dados))
        for row_idx, reg in enumerate(dados):
            for col_idx, header in enumerate(self.DEF_PECAS_HEADERS):
                key = field_map[header]
                valor = reg.get(key)
                if header == "ID":
                    texto = str(int(valor)) if valor not in (None, "") else ""
                elif col_idx in self.DEF_PECAS_NUMERIC_COLUMNS and valor not in (None, ""):
                    texto = f"{float(valor):.4f}".rstrip("0").rstrip(".")
                    if not texto:
                        texto = "0"
                else:
                    texto = str(valor) if valor not in (None, "") else ""
                item = QtWidgets.QTableWidgetItem(texto)
                if header == "ID":
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                elif col_idx in self.DEF_PECAS_NUMERIC_COLUMNS:
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                else:
                    item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                self.tbl_def_pecas.setItem(row_idx, col_idx, item)
        self.tbl_def_pecas.blockSignals(False)

    def _apply_def_pecas_search(self) -> None:
        dados = getattr(self, "_def_pecas_all", [])
        termo = ""
        if hasattr(self, "ed_def_pecas_search"):
            try:
                termo = self.ed_def_pecas_search.text().strip().casefold()
            except Exception:
                termo = ""
        if not termo:
            filtrado = dados
        else:
            filtrado = []
            for linha in dados:
                if any(termo in str(val).casefold() for val in linha.values() if val not in (None, "")):
                    filtrado.append(linha)
        self._populate_def_pecas_table(filtrado)

    def _insert_def_pecas_row(self, values: Optional[List[str]] = None, position: Optional[int] = None) -> None:
        if position is None or position < 0:
            position = self.tbl_def_pecas.rowCount()
        self.tbl_def_pecas.insertRow(position)
        for col_idx in range(len(self.DEF_PECAS_HEADERS)):
            text_val = ""
            if values and col_idx < len(values):
                text_val = values[col_idx] or ""
            if col_idx == 0:
                item = QtWidgets.QTableWidgetItem(text_val)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                item.setTextAlignment(QtCore.Qt.AlignCenter)
            else:
                if not text_val:
                    text_val = "0" if col_idx in self.DEF_PECAS_NUMERIC_COLUMNS else ""
                item = QtWidgets.QTableWidgetItem(text_val)
                if col_idx in self.DEF_PECAS_NUMERIC_COLUMNS:
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                else:
                    item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self.tbl_def_pecas.setItem(position, col_idx, item)
        self._def_pecas_dirty = True

    def _on_def_pecas_context_menu(self, pos: QtCore.QPoint) -> None:
        if not getattr(self, "tbl_def_pecas", None):
            return
        style = self.style() or QtWidgets.QApplication.style()
        menu = QtWidgets.QMenu(self)
        act_copy = menu.addAction(style.standardIcon(QtWidgets.QStyle.SP_FileIcon), "Copiar linha")
        act_insert = menu.addAction(style.standardIcon(QtWidgets.QStyle.SP_FileDialogNewFolder), "Inserir linha")
        act_remove = menu.addAction(style.standardIcon(QtWidgets.QStyle.SP_TrashIcon), "Remover linha")
        menu.addSeparator()
        act_up = menu.addAction(style.standardIcon(QtWidgets.QStyle.SP_ArrowUp), "Mover para cima")
        act_down = menu.addAction(style.standardIcon(QtWidgets.QStyle.SP_ArrowDown), "Mover para baixo")
        action = menu.exec(self.tbl_def_pecas.viewport().mapToGlobal(pos))
        if action == act_copy:
            self._on_def_pecas_copy_rows()
        elif action == act_insert:
            self._on_def_pecas_insert_empty()
        elif action == act_remove:
            self._on_def_pecas_remove_rows()
        elif action == act_up:
            self._on_def_pecas_move_up()
        elif action == act_down:
            self._on_def_pecas_move_down()

    def _on_def_pecas_copy_rows(self) -> None:
        selection = self.tbl_def_pecas.selectionModel()
        if not selection:
            return
        rows = sorted({idx.row() for idx in selection.selectedRows()})
        if not rows:
            return
        insert_at = max(rows) + 1
        collected: List[List[str]] = []
        for row in rows:
            values: List[str] = []
            for col_idx in range(len(self.DEF_PECAS_HEADERS)):
                item = self.tbl_def_pecas.item(row, col_idx)
                values.append(item.text() if item else "")
            if values:
                values[0] = ""  # clear ID for new line
                collected.append(values)
        for offset, vals in enumerate(collected):
            self._insert_def_pecas_row(vals, insert_at + offset)
        self._def_pecas_dirty = True

    def _on_def_pecas_insert_empty(self) -> None:
        selection = self.tbl_def_pecas.selectionModel()
        insert_at = self.tbl_def_pecas.rowCount()
        if selection and selection.selectedRows():
            insert_at = max(idx.row() for idx in selection.selectedRows()) + 1
        self._insert_def_pecas_row(None, insert_at)

    def _selected_def_pecas_rows(self) -> List[int]:
        selection = self.tbl_def_pecas.selectionModel()
        if not selection:
            return []
        return sorted({idx.row() for idx in selection.selectedRows()})

    def _swap_def_pecas_rows(self, row_a: int, row_b: int) -> None:
        if row_a == row_b:
            return
        if row_a < 0 or row_b < 0:
            return
        if row_a >= self.tbl_def_pecas.rowCount() or row_b >= self.tbl_def_pecas.rowCount():
            return
        for col in range(self.tbl_def_pecas.columnCount()):
            item_a = self.tbl_def_pecas.takeItem(row_a, col)
            item_b = self.tbl_def_pecas.takeItem(row_b, col)
            if item_b is not None:
                self.tbl_def_pecas.setItem(row_a, col, item_b)
            if item_a is not None:
                self.tbl_def_pecas.setItem(row_b, col, item_a)

    def _on_def_pecas_move_up(self) -> None:
        rows = self._selected_def_pecas_rows()
        if not rows:
            return
        selected = set(rows)
        moved_rows: List[int] = []
        self.tbl_def_pecas.blockSignals(True)
        for row in rows:
            if row <= 0:
                moved_rows.append(row)
                continue
            if (row - 1) in selected:
                moved_rows.append(row)
                continue
            self._swap_def_pecas_rows(row, row - 1)
            moved_rows.append(row - 1)
        self.tbl_def_pecas.blockSignals(False)
        self._def_pecas_dirty = True

        sel_model = self.tbl_def_pecas.selectionModel()
        if sel_model:
            sel_model.clearSelection()
            for row in sorted(set(moved_rows)):
                index = self.tbl_def_pecas.model().index(row, 0)
                sel_model.select(index, QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)

    def _on_def_pecas_move_down(self) -> None:
        rows = self._selected_def_pecas_rows()
        if not rows:
            return
        selected = set(rows)
        moved_rows: List[int] = []
        max_row = self.tbl_def_pecas.rowCount() - 1
        self.tbl_def_pecas.blockSignals(True)
        for row in sorted(rows, reverse=True):
            if row >= max_row:
                moved_rows.append(row)
                continue
            if (row + 1) in selected:
                moved_rows.append(row)
                continue
            self._swap_def_pecas_rows(row, row + 1)
            moved_rows.append(row + 1)
        self.tbl_def_pecas.blockSignals(False)
        self._def_pecas_dirty = True

        sel_model = self.tbl_def_pecas.selectionModel()
        if sel_model:
            sel_model.clearSelection()
            for row in sorted(set(moved_rows)):
                index = self.tbl_def_pecas.model().index(row, 0)
                sel_model.select(index, QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)

    def _collect_def_pecas_rows(self) -> List[Dict[str, Optional[str]]]:
        field_map = {
            "ID": "id",
            "Tipo_Peca_Principal": "tipo_peca_principal",
            "Subgrupo_Peca": "subgrupo_peca",
            "Nome_da_Peca": "nome_da_peca",
            "CP01_SEC": "cp01_sec",
            "CP02_ORL": "cp02_orl",
            "CP03_CNC": "cp03_cnc",
            "CP04_ABD": "cp04_abd",
            "CP05_PRENSA": "cp05_prensa",
            "CP06_ESQUAD": "cp06_esquad",
            "CP07_EMBALAGEM": "cp07_embalagem",
            "CP08_MAO_DE_OBRA": "cp08_mao_de_obra",
        }
        linhas: List[Dict[str, Optional[str]]] = []
        for row in range(self.tbl_def_pecas.rowCount()):
            linha: Dict[str, Optional[str]] = {}
            nome = ""
            for col_idx, header in enumerate(self.DEF_PECAS_HEADERS):
                item = self.tbl_def_pecas.item(row, col_idx)
                texto = item.text().strip() if item else ""
                chave = field_map[header]
                linha[chave] = texto or None
                if chave == "nome_da_peca":
                    nome = texto
            if nome:
                linhas.append(linha)
        return linhas

    def _on_def_pecas_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if self._def_pecas_loading:
            return
        self._def_pecas_dirty = True
        if item.column() in self.DEF_PECAS_NUMERIC_COLUMNS:
            texto = item.text().strip()
            if texto:
                try:
                    valor = float(texto.replace(",", "."))
                except ValueError:
                    valor = 0.0
                item.setText(f"{valor:.4f}".rstrip("0").rstrip(".") or "0")
            else:
                item.setText("0")

    def _on_def_pecas_add_row(self) -> None:
        row = self.tbl_def_pecas.rowCount()
        self.tbl_def_pecas.insertRow(row)
        for col_idx in range(len(self.DEF_PECAS_HEADERS)):
            if col_idx == 0:
                item = QtWidgets.QTableWidgetItem("")
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                item.setTextAlignment(QtCore.Qt.AlignCenter)
            else:
                default_text = "0" if col_idx in self.DEF_PECAS_NUMERIC_COLUMNS else ""
                item = QtWidgets.QTableWidgetItem(default_text)
                if col_idx in self.DEF_PECAS_NUMERIC_COLUMNS:
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                else:
                    item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self.tbl_def_pecas.setItem(row, col_idx, item)
        self._def_pecas_dirty = True

    def _on_def_pecas_remove_rows(self) -> None:
        selection = self.tbl_def_pecas.selectionModel()
        if not selection:
            return
        rows = sorted({index.row() for index in selection.selectedRows()}, reverse=True)
        if not rows:
            return
        for row in rows:
            self.tbl_def_pecas.removeRow(row)
        self._def_pecas_dirty = True

    def _on_def_pecas_save(self) -> None:
        try:
            linhas = self._collect_def_pecas_rows()
            svc_def_pecas.guardar_definicoes(self.db, linhas)
            self._def_pecas_dirty = False
            self._load_def_pecas_table(force=True)
            QtWidgets.QMessageBox.information(self, "Sucesso", "Definições de peças gravadas.")
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar definições de peças: {exc}")

    # ------------------------------------------------------------------ Permissoes
    def _init_permissions_tab(self) -> None:
        tab = QtWidgets.QWidget()
        self.tab_permissions = tab
        layout = QtWidgets.QVBoxLayout(tab)

        info = QtWidgets.QLabel(
            "Permissoes por utilizador. Apenas o administrador pode alterar estas opcoes."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        buttons = QtWidgets.QHBoxLayout()
        self.btn_permissions_reload = QtWidgets.QPushButton("Recarregar")
        self.btn_permissions_reload.clicked.connect(lambda: self._load_permissions_table(force=True))
        self.btn_permissions_save = QtWidgets.QPushButton("Gravar Permissoes")
        self.btn_permissions_save.setEnabled(False)
        self.btn_permissions_save.clicked.connect(self._on_permissions_save)
        buttons.addWidget(self.btn_permissions_reload)
        buttons.addWidget(self.btn_permissions_save)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.tbl_permissions = QtWidgets.QTableView(tab)
        self.tbl_permissions.setAlternatingRowColors(True)
        self.tbl_permissions.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_permissions.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tbl_permissions.setSortingEnabled(True)

        self.permissions_model = SimpleTableModel(
            columns=[
                {"header": "Utilizador", "attr": "username", "editable": False},
                {"header": "Role", "attr": "role", "editable": False},
                {"header": "Ativo", "attr": "is_active", "editable": False, "formatter": _fmt_bool},
                {"header": "PDF Manager", "attr": "feature_pdf_manager", "type": "bool", "editable": True},
                {"header": "Preparacao", "attr": "feature_producao_preparacao", "type": "bool", "editable": True},
            ]
        )
        self.tbl_permissions.setModel(self.permissions_model)
        self.permissions_model.dataChanged.connect(self._on_permissions_data_changed)
        layout.addWidget(self.tbl_permissions, 1)

        self.tabs.addTab(tab, "Permissoes")
        self._permissions_dirty = True
        self._load_permissions_table(force=True)

    def _load_permissions_table(self, *, force: bool = False) -> None:
        if self._permissions_loading:
            return
        if not force and not self._permissions_dirty:
            return
        self._permissions_loading = True
        try:
            self.db.rollback()
        except Exception:
            pass
        try:
            users = self.db.query(User).order_by(User.username).all()
            pdf_flags = svc_features.list_feature_flags(self.db, svc_features.FEATURE_PDF_MANAGER)
            preparacao_flags = svc_features.list_feature_flags(
                self.db,
                svc_features.FEATURE_PRODUCAO_PREPARACAO,
            )
            rows = []
            for user in users:
                user_id = int(getattr(user, "id"))
                rows.append(
                    {
                        "user_id": user_id,
                        "username": getattr(user, "username", "") or "",
                        "role": getattr(user, "role", "") or "",
                        "is_active": bool(getattr(user, "is_active", False)),
                        "feature_pdf_manager": bool(
                            pdf_flags.get(
                                user_id,
                                svc_features.feature_default_enabled(svc_features.FEATURE_PDF_MANAGER),
                            )
                        ),
                        "feature_producao_preparacao": bool(
                            preparacao_flags.get(
                                user_id,
                                svc_features.feature_default_enabled(svc_features.FEATURE_PRODUCAO_PREPARACAO),
                            )
                        ),
                    }
                )
            self.permissions_model.set_rows(rows)
            self.tbl_permissions.resizeColumnsToContents()
            self._permissions_dirty = False
            self.btn_permissions_save.setEnabled(False)
        finally:
            self._permissions_loading = False

    def _on_permissions_data_changed(self, *args) -> None:
        if self._permissions_loading:
            return
        self._permissions_dirty = True
        if hasattr(self, "btn_permissions_save"):
            self.btn_permissions_save.setEnabled(True)

    def _on_permissions_save(self) -> None:
        rows = list(getattr(self.permissions_model, "_rows", []))
        if not rows:
            return
        try:
            for row in rows:
                user_id = row.get("user_id")
                if not user_id:
                    continue
                enabled = bool(row.get("feature_pdf_manager"))
                svc_features.set_feature(
                    self.db,
                    int(user_id),
                    svc_features.FEATURE_PDF_MANAGER,
                    enabled,
                )
                preparacao_enabled = bool(row.get("feature_producao_preparacao"))
                svc_features.set_feature(
                    self.db,
                    int(user_id),
                    svc_features.FEATURE_PRODUCAO_PREPARACAO,
                    preparacao_enabled,
                )
            self.db.commit()
            self._permissions_dirty = False
            self.btn_permissions_save.setEnabled(False)
            QtWidgets.QMessageBox.information(self, "Permissoes", "Permissoes gravadas.")
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Permissoes", f"Falha ao gravar permissoes: {exc}")

    def _on_tab_changed(self, index: int) -> None:
        widget = self.tabs.widget(index)
        if getattr(self, "tab_producao", None) is not None and widget is self.tab_producao and self._producao_ctx and self._producao_dirty:
            self._load_producao_table()
        if getattr(self, "tab_def_pecas", None) is not None and widget is self.tab_def_pecas and self._def_pecas_dirty:
            self._load_def_pecas_table(force=True)
        if getattr(self, "tab_permissions", None) is not None and widget is self.tab_permissions and self._permissions_dirty:
            self._load_permissions_table(force=True)

    def _clear_producao_table(self) -> None:
        self.tbl_producao.setRowCount(0)

    def _load_producao_table(self, force: bool = False) -> None:
        if not self._producao_ctx:
            self._set_producao_controls_enabled(False)
            self._clear_producao_table()
            return
        if not force and not self._producao_dirty:
            self._update_producao_info()
            return
        try:
            self.db.rollback()
        except Exception:
            pass
        try:
            self._loading_table = True
            valores = svc_producao.load_values(self.db, self._producao_ctx)
            self._producao_mode = svc_producao.get_mode(self.db, self._producao_ctx)
            self.db.commit()
        except Exception as exc:
            self._loading_table = False
            self.db.rollback()
            self._set_producao_controls_enabled(False)
            self._clear_producao_table()
            self.lbl_producao_info.setText(f"Falha ao carregar dados produtivos: {exc}")
            return

        self.tbl_producao.setRowCount(len(valores))
        for row_idx, entrada in enumerate(valores):
            desc_item = QtWidgets.QTableWidgetItem(str(entrada.get("descricao_equipamento", "")))
            desc_item.setFlags(desc_item.flags() & ~QtCore.Qt.ItemIsEditable)
            abrev_item = QtWidgets.QTableWidgetItem(str(entrada.get("abreviatura", "")))
            abrev_item.setFlags(abrev_item.flags() & ~QtCore.Qt.ItemIsEditable)
            std_item = QtWidgets.QTableWidgetItem(self._format_decimal(entrada.get("valor_std")))
            serie_item = QtWidgets.QTableWidgetItem(self._format_decimal(entrada.get("valor_serie")))
            resumo_item = QtWidgets.QTableWidgetItem(str(entrada.get("resumo", "")))
            for col, item in enumerate([desc_item, abrev_item, std_item, serie_item, resumo_item]):
                item.setData(QtCore.Qt.UserRole, entrada.get("ordem", row_idx + 1))
                self.tbl_producao.setItem(row_idx, col, item)
                self._apply_item_style(row_idx, col, item)

        self._loading_table = False
        self._producao_dirty = False
        self._set_producao_controls_enabled(True)
        self._update_producao_info()

    def _update_producao_info(self) -> None:
        if not self._producao_ctx:
            self.lbl_producao_info.setText(
                f"Selecione um orçamento para editar os dados produtivos. Modo atual: {self._producao_mode}"
            )
            return
        ctx = self._producao_ctx
        info = (
            f"Ano {ctx.ano} | N.º Orçamento {ctx.num_orcamento} | Versão {ctx.versao} | Modo atual: {self._producao_mode}"
        )
        self.lbl_producao_info.setText(info)

    def _format_decimal(self, value: Optional[float]) -> str:
        if value is None:
            return ""
        text = f"{value:.4f}"
        text = text.rstrip("0").rstrip(".")
        return text or "0"

    def _collect_producao_values(self) -> List[Dict[str, str]]:
        valores: List[Dict[str, str]] = []
        for row in range(self.tbl_producao.rowCount()):
            desc = self._item_text(row, 0)
            abrev = self._item_text(row, 1)
            std = self._item_text(row, 2)
            serie = self._item_text(row, 3)
            resumo = self._item_text(row, 4)
            if not desc:
                continue
            valores.append(
                {
                    "descricao_equipamento": desc,
                    "abreviatura": abrev,
                    "valor_std": std,
                    "valor_serie": serie,
                    "resumo": resumo,
                }
            )
        return valores

    def _item_text(self, row: int, column: int) -> str:
        item = self.tbl_producao.item(row, column)
        return item.text().strip() if item else ""

    def _safe_decimal(self, text: str) -> Optional[Decimal]:
        cleaned = (text or "").strip().replace(",", ".")
        if not cleaned:
            return None
        try:
            return Decimal(cleaned).quantize(self._decimal_quant)
        except (InvalidOperation, ValueError):
            return None

    def _apply_item_style(self, row: int, column: int, item: Optional[QtWidgets.QTableWidgetItem]) -> None:
        if item is None:
            return
        if column in (1, 2, 3):
            item.setTextAlignment(QtCore.Qt.AlignCenter)
        else:
            item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        font = item.font()
        if column in (2, 3):
            desc = self._item_text(row, 0)
            default_entry = self._default_lookup.get(desc)
            value = self._safe_decimal(item.text())
            is_diff = False
            if default_entry:
                default_value = default_entry["valor_std" if column == 2 else "valor_serie"]
                if value is None:
                    is_diff = True
                else:
                    is_diff = value != default_value
            else:
                is_diff = bool(item.text().strip())
            font.setBold(is_diff)
            font.setItalic(is_diff)
        else:
            font.setBold(False)
            font.setItalic(False)
        item.setFont(font)

    def _on_producao_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if self._loading_table:
            return
        self._apply_item_style(item.row(), item.column(), item)

    def _on_producao_save(self) -> None:
        if not self._producao_ctx:
            QtWidgets.QMessageBox.information(self, "Aviso", "Nenhum orçamento selecionado.")
            return
        try:
            valores = self._collect_producao_values()
            svc_producao.save_values(self.db, self._producao_ctx, valores)
            self.db.commit()
            QtWidgets.QMessageBox.information(self, "Sucesso", "Dados produtivos gravados.")
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar dados produtivos: {exc}")
            return
        self._load_producao_table()

    def _on_producao_reset(self) -> None:
        if not self._producao_ctx:
            return
        if (
            QtWidgets.QMessageBox.question(
                self,
                "Confirmar",
                "Repor os valores padrão (STD) para este orçamento?",
            )
            != QtWidgets.QMessageBox.Yes
        ):
            return
        try:
            svc_producao.reset_values(self.db, self._producao_ctx)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao repor valores: {exc}")
            return
        self._load_producao_table()

    # ------------------------------------------------------------------ Login Settings
    def _load_login_settings(self) -> None:
        """Carrega as configurações de login existentes."""
        try:
            # Carregar configuração global de pré-preenchimento
            auto_fill_enabled = get_setting(self.db, "auto_fill_login", "true").lower() == "true"
            self.chk_auto_fill_login.setChecked(auto_fill_enabled)

            # Carregar mapeamentos de usuários
            self.list_user_mappings.clear()
            
            # Buscar todas as configurações que começam com "user_mapping_"
            from Martelo_Orcamentos_V2.app.models.app_setting import AppSetting
            mappings = self.db.query(AppSetting).filter(AppSetting.key.like("user_mapping_%")).all()
            
            for mapping in mappings:
                # Extrair o nome do usuário Windows da chave
                windows_user = mapping.key.replace("user_mapping_", "")
                martelo_user = mapping.value
                
                item_text = f"Windows: {windows_user} → Martelo: {martelo_user}"
                item = QtWidgets.QListWidgetItem(item_text)
                item.setData(QtCore.Qt.UserRole, (windows_user, martelo_user))
                self.list_user_mappings.addItem(item)
                
        except Exception as exc:
            logger.exception("Erro ao carregar configurações de login: %s", exc)
            QtWidgets.QMessageBox.warning(self, "Erro", f"Erro ao carregar configurações de login: {exc}")

    def _on_add_user_mapping(self) -> None:
        """Adiciona um novo mapeamento de usuário."""
        dialog = UserMappingDialog(self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            windows_user, martelo_user = dialog.get_mapping()
            if windows_user and martelo_user:
                # Verificar se o mapeamento já existe
                for i in range(self.list_user_mappings.count()):
                    item = self.list_user_mappings.item(i)
                    existing_windows, existing_martelo = item.data(QtCore.Qt.UserRole)
                    if existing_windows == windows_user:
                        QtWidgets.QMessageBox.warning(
                            self, "Aviso", 
                            f"Já existe um mapeamento para o usuário Windows '{windows_user}'."
                        )
                        return
                
                # Verificar se o usuário do Martelo existe
                from Martelo_Orcamentos_V2.app.models import User
                user_exists = self.db.query(User).filter(
                    User.username == martelo_user, User.is_active == True
                ).first() is not None
                
                if not user_exists:
                    QtWidgets.QMessageBox.warning(
                        self, "Aviso", 
                        f"O usuário '{martelo_user}' não existe no Martelo ou não está ativo."
                    )
                    return
                
                # Adicionar à lista
                item_text = f"Windows: {windows_user} → Martelo: {martelo_user}"
                item = QtWidgets.QListWidgetItem(item_text)
                item.setData(QtCore.Qt.UserRole, (windows_user, martelo_user))
                self.list_user_mappings.addItem(item)

    def _on_remove_user_mapping(self) -> None:
        """Remove o mapeamento selecionado."""
        current_item = self.list_user_mappings.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um mapeamento para remover.")
            return
        
        windows_user, martelo_user = current_item.data(QtCore.Qt.UserRole)
        confirm = QtWidgets.QMessageBox.question(
            self, "Confirmar",
            f"Remover mapeamento: Windows '{windows_user}' → Martelo '{martelo_user}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if confirm == QtWidgets.QMessageBox.Yes:
            row = self.list_user_mappings.row(current_item)
            self.list_user_mappings.takeItem(row)

    def _on_save_login_settings(self) -> None:
        """Grava as configurações de login."""
        try:
            # Salvar configuração global de pré-preenchimento
            auto_fill_value = "true" if self.chk_auto_fill_login.isChecked() else "false"
            set_setting(self.db, "auto_fill_login", auto_fill_value)
            
            # Primeiro, remover todos os mapeamentos existentes
            from Martelo_Orcamentos_V2.app.models.app_setting import AppSetting
            self.db.query(AppSetting).filter(AppSetting.key.like("user_mapping_%")).delete()
            
            # Salvar novos mapeamentos
            for i in range(self.list_user_mappings.count()):
                item = self.list_user_mappings.item(i)
                windows_user, martelo_user = item.data(QtCore.Qt.UserRole)
                key = f"user_mapping_{windows_user}"
                set_setting(self.db, key, martelo_user)
            
            self.db.commit()
            QtWidgets.QMessageBox.information(self, "OK", "Configurações de login gravadas com sucesso.")
            
        except Exception as exc:
            self.db.rollback()
            logger.exception("Erro ao gravar configurações de login: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao gravar configurações de login: {exc}")

    # ----------------------------------------------------------------- Helpers
    def closeEvent(self, event: QtCore.QEvent) -> None:  # type: ignore[override]
        try:
            self.db.close()
        finally:
            super().closeEvent(event)


class QtRulesDialog(QtWidgets.QDialog):
    HEADERS = ["Regra", "Matches", "Expressão", "Tooltip"]

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Regras de Quantidade (qt_und)")
        self.resize(1550, 720)

        layout = QtWidgets.QVBoxLayout(self)

        intro = QtWidgets.QLabel(
            "Edite ou personalize as regras de quantidade. Use o ID/versão do orçamento para carregar regras específicas; "
            "deixe em branco para editar as regras padrão."
        )
        intro.setWordWrap(True)
        intro.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        layout.addWidget(intro)

        target_layout = QtWidgets.QHBoxLayout()
        target_layout.addWidget(QtWidgets.QLabel("Orçamento ID:"))
        self.ed_orcamento = QtWidgets.QLineEdit()
        self.ed_orcamento.setPlaceholderText("Deixe vazio para regras padrão")
        self.ed_orcamento.setToolTip("Opcional. Se preenchido, carrega/guarda regras apenas para este orçamento.")
        target_layout.addWidget(self.ed_orcamento)

        target_layout.addWidget(QtWidgets.QLabel("Versão:"))
        self.ed_versao = QtWidgets.QLineEdit()
        self.ed_versao.setPlaceholderText("01")
        self.ed_versao.setToolTip("Opcional. Usado em conjunto com o ID do orçamento.")
        target_layout.addWidget(self.ed_versao)

        btn_load = QtWidgets.QPushButton("Carregar")
        btn_load.setToolTip("Carrega regras a partir do ID/versão informados ou as regras padrão.")
        btn_load.clicked.connect(self._on_load)
        target_layout.addWidget(btn_load)

        btn_reset = QtWidgets.QPushButton("Repor")
        btn_reset.setToolTip("Repor regras padrão para o alvo atual (ou padrão global se vazio).")
        btn_reset.clicked.connect(self._on_reset)
        target_layout.addWidget(btn_reset)

        target_layout.addStretch(1)
        layout.addLayout(target_layout)

        self.table = QtWidgets.QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(120)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Interactive)
        header.resizeSection(3, 520)
        self.table.setAlternatingRowColors(True)
        self.table.setToolTip(
            "Edite as regras diretamente. Colunas:\n"
            "- Regra: nome único.\n- Matches: etiquetas/peças que ativam a regra (separadas por vírgula).\n"
            "- Expressão: fórmula Python simples usando COMP, LARG, QT_PAI, etc.\n"
            "- Tooltip: descrição exibida no custeio."
        )
        for idx, header in enumerate(self.HEADERS):
            item = self.table.horizontalHeaderItem(idx)
            if item:
                item.setToolTip(self.HEADERS[idx])
        layout.addWidget(self.table, 1)

        actions_layout = QtWidgets.QHBoxLayout()
        btn_add = QtWidgets.QPushButton("Adicionar Regra")
        btn_add.setToolTip("Cria uma nova linha em branco para definir uma regra personalizada.")
        btn_add.clicked.connect(self._on_add_rule)
        actions_layout.addWidget(btn_add)

        btn_remove = QtWidgets.QPushButton("Remover Selecionada")
        btn_remove.setToolTip("Remove as linhas atualmente selecionadas na tabela.")
        btn_remove.clicked.connect(self._on_remove_rule)
        actions_layout.addWidget(btn_remove)

        actions_layout.addStretch(1)

        btn_save = QtWidgets.QPushButton("Guardar")
        btn_save.setToolTip("Guarda as regras na base de dados (para o alvo definido ou padrão).")
        btn_save.clicked.connect(self._on_save)
        actions_layout.addWidget(btn_save)

        layout.addLayout(actions_layout)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._current_rules: Dict[str, Dict[str, Any]] = {}
        self._load_rules()

    def _current_target(self) -> tuple[Optional[int], Optional[str]]:
        orc_text = self.ed_orcamento.text().strip()
        versao_text = self.ed_versao.text().strip() or None
        if not orc_text:
            return None, None
        try:
            orc_id = int(orc_text)
        except ValueError as exc:
            raise ValueError("Orçamento deve ser numérico.") from exc
        return orc_id, versao_text

    def _populate_table(self, rules: Dict[str, Dict[str, Any]]) -> None:
        self.table.setRowCount(0)
        for row_idx, (name, data) in enumerate(sorted(rules.items(), key=lambda item: item[0])):
            self.table.insertRow(row_idx)
            matches = ", ".join(data.get("matches", []))
            expression = data.get("expression") or ""
            tooltip = data.get("tooltip") or ""
            items = [
                QtWidgets.QTableWidgetItem(name),
                QtWidgets.QTableWidgetItem(matches),
                QtWidgets.QTableWidgetItem(expression),
                QtWidgets.QTableWidgetItem(tooltip),
            ]
            for col, item in enumerate(items):
                self.table.setItem(row_idx, col, item)
        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)

    def _collect_rules(self) -> Dict[str, Dict[str, Any]]:
        rules: Dict[str, Dict[str, Any]] = {}
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            if not name_item:
                continue
            name = name_item.text().strip()
            if not name:
                continue
            matches_text = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
            expression_text = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
            tooltip_text = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
            matches = [m.strip() for m in matches_text.split(",") if m.strip()]
            rules[name] = {
                "matches": matches,
                "expression": expression_text.strip() or None,
                "tooltip": tooltip_text.strip() or None,
            }
        return rules

    def _load_rules(self, *, orcamento_id: Optional[int] = None, versao: Optional[str] = None) -> None:
        rules = svc_custeio.load_qt_rules(self.session, None, orcamento_id=orcamento_id, versao=versao)
        self._current_rules = rules
        self._populate_table(rules)

    def _on_load(self) -> None:
        try:
            orcamento_id, versao = self._current_target()
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Aviso", str(exc))
            return
        self._load_rules(orcamento_id=orcamento_id, versao=versao)

    def _on_reset(self) -> None:
        try:
            orcamento_id, versao = self._current_target()
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Aviso", str(exc))
            return
        if orcamento_id is None:
            svc_custeio.reset_qt_rules(self.session, None, reset_default=True)
        else:
            svc_custeio.reset_qt_rules(self.session, None, orcamento_id=orcamento_id, versao=versao)
        self._load_rules(orcamento_id=orcamento_id, versao=versao)
        QtWidgets.QMessageBox.information(self, "OK", "Regras repostas.")

    def _on_add_rule(self) -> None:
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)
        for col in range(len(self.HEADERS)):
            self.table.setItem(row_idx, col, QtWidgets.QTableWidgetItem(""))

    def _on_remove_rule(self) -> None:
        selected = self.table.selectionModel().selectedRows()
        for index in sorted(selected, key=lambda i: i.row(), reverse=True):
            self.table.removeRow(index.row())

    def _on_save(self) -> None:
        try:
            orcamento_id, versao = self._current_target()
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Aviso", str(exc))
            return
        rules = self._collect_rules()
        if not rules:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhuma regra definida.")
            return
        svc_custeio.save_qt_rules(self.session, None, rules, orcamento_id=orcamento_id, versao=versao)
        QtWidgets.QMessageBox.information(self, "OK", "Regras gravadas com sucesso.")

class UserMappingDialog(QtWidgets.QDialog):
    """Diálogo para adicionar/editar mapeamento de usuário."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adicionar Mapeamento Utilizador")
        self.setModal(True)
        
        layout = QtWidgets.QFormLayout(self)
        
        self.ed_windows_user = QtWidgets.QLineEdit(self)
        self.ed_windows_user.setPlaceholderText("ex.: joao.silva")
        layout.addRow("Utilizador Windows", self.ed_windows_user)
        
        self.ed_martelo_user = QtWidgets.QLineEdit(self)
        self.ed_martelo_user.setPlaceholderText("ex.: João Silva")
        layout.addRow("Utilizador Martelo", self.ed_martelo_user)
        
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        # Focar no primeiro campo
        self.ed_windows_user.setFocus()
    
    def get_mapping(self) -> tuple[str, str]:
        """Retorna o mapeamento (windows_user, martelo_user)."""
        return (
            self.ed_windows_user.text().strip().lower(),
            self.ed_martelo_user.text().strip()
        )
