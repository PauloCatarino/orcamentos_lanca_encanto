import logging
import os
import re
from typing import Optional
from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Qt, Signal, QDate, QTimer
from PySide6.QtWidgets import QStyle, QCompleter, QToolButton, QAbstractSpinBox
from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.utils.display import format_currency_pt, parse_currency_pt, repair_mojibake
from Martelo_Orcamentos_V2.app.utils.date_utils import format_date_storage, parse_date_value
from Martelo_Orcamentos_V2.app.services.orcamentos import (
    list_orcamentos,
    next_seq_for_year,
    search_orcamentos,
    PRECO_MANUAL_KEY,
    TEMP_CLIENT_ID_KEY,
    TEMP_CLIENT_NAME_KEY,
)
from Martelo_Orcamentos_V2.app.services.clientes_temporarios import (
    get_cliente_temporario,
)
from Martelo_Orcamentos_V2.app.services.settings import get_setting
from Martelo_Orcamentos_V2.app.services import orcamento_lembretes as svc_lembretes
from Martelo_Orcamentos_V2.app.services import orcamento_tasks as svc_orc_tasks
from Martelo_Orcamentos_V2.app.services import orcamentos_client_workflow as svc_orc_client_workflow
from Martelo_Orcamentos_V2.app.services import orcamentos_workflow as svc_orc_workflow
from Martelo_Orcamentos_V2.app.models.user import User
from Martelo_Orcamentos_V2.ui.dialogs.cliente_info import ClienteInfoDialog
from Martelo_Orcamentos_V2.ui.dialogs.orcamento_duplicate_dialog import confirm_ref_cliente_duplicate
from Martelo_Orcamentos_V2.ui.dialogs.orcamento_lembretes import DailyOrcamentoReminderDialog
from Martelo_Orcamentos_V2.ui.dialogs.orcamento_tasks import OrcamentoTasksDialog
from Martelo_Orcamentos_V2.ui.dialogs.temp_client import TempClientDialog
from Martelo_Orcamentos_V2.ui.pages.orcamentos_form_support import (
    build_existing_orcamento_folder_path,
    build_new_orcamento_form_state,
    extract_temp_simplex_from_extras,
    normalize_simplex,
    prepare_loaded_orcamento_selection,
    resolve_orcamento_simplex,
)
from Martelo_Orcamentos_V2.ui.pages.orcamentos_persistence_support import (
    build_duplicate_success_message,
    find_row_index_by_id,
)
from Martelo_Orcamentos_V2.ui.pages.orcamentos_support import (
    ClienteComboItem,
    build_auto_refresh_state,
    build_cliente_change_plan,
    build_focus_request,
    build_post_save_plan,
    build_orcamento_table_state,
    plan_table_selection,
)
from ..models.qt_table import SimpleTableModel


logger = logging.getLogger(__name__)
CONSUMIDOR_FINAL_LABEL = "CONSUMIDOR FINAL"


class OrcamentosPage(QtWidgets.QWidget):
    orcamento_aberto = Signal(int)  # id_orcamento

    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.db = SessionLocal()
        self._current_id: Optional[int] = None
        self._dirty: bool = False
        self._loading_form: bool = False
        self._base_save_button_text: str = "Salvar"
        self._preco_manual_active: bool = False
        self._preco_manual_changed: bool = False
        self._consumidor_final_id: Optional[int] = None
        self._ignore_cliente_change: bool = False
        self._last_cliente_text: str = ""
        self._phc_name_set: set[str] = set()
        self._temp_dialog_open: bool = False
        self._orcamento_user_choices = []

        # Auto-refresh da lista de orcamentos (para multi-user)
        self._auto_refresh_timer = QTimer()
        self._auto_refresh_timer.timeout.connect(self._auto_refresh_table)
        self._auto_refresh_interval_ms = 10000  # 10 segundos
        self._auto_refresh_timer.start(self._auto_refresh_interval_ms)
        
        # Timer para resetar flag de navegacao tabela apos 2 segundos
        self._table_scroll_reset_timer = QTimer()
        self._table_scroll_reset_timer.setSingleShot(True)
        self._table_scroll_reset_timer.timeout.connect(lambda: setattr(self, '_table_user_scrolling', False))
        
        # Flags para controlar quando auto-refresh deve estar ativo
        self._search_text: str = ""  # Texto da pesquisa ativa
        self._table_user_scrolling: bool = False  # Utilizador a fazer scroll
        self._creating_new_orcamento: bool = False  # Em modo novo orcamento
        self._last_row_count: int = 0  # Para detectar novos orcamentos
        self._refresh_scroll_position: int = 0  # Guardar posicao de scroll

        # Campos base
        self.cb_cliente = QtWidgets.QComboBox()
        self.cb_cliente.setEditable(True)
        self._clients = []
        self._load_clients()
        try:
            self.cb_cliente.activated.connect(self._on_cliente_selected)
            le = self.cb_cliente.lineEdit()
            if le is not None:
                le.editingFinished.connect(self._on_cliente_edit_finished)
        except Exception:
            pass

        self.cb_ano = QtWidgets.QComboBox()
        self.cb_ano.setEditable(True)
        try:
            self.cb_ano.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        except Exception:
            pass
        try:
            ano_edit = self.cb_ano.lineEdit()
            if ano_edit is not None:
                ano_edit.setMaxLength(4)
                ano_edit.setValidator(QtGui.QIntValidator(1900, 2200, self))
                ano_edit.setPlaceholderText("AAAA")
                ano_edit.editingFinished.connect(self._on_ano_editing_finished)
        except Exception:
            pass
        self.cb_ano.currentTextChanged.connect(self._on_ano_changed)
        self.ed_num = QtWidgets.QLineEdit()
        self.ed_num.setReadOnly(True)
        self.ed_ver = QtWidgets.QLineEdit("01")
        self.ed_data = QtWidgets.QDateEdit()
        self.ed_data.setDisplayFormat("dd-MM-yyyy")
        self.ed_data.setCalendarPopup(True)
        self.ed_data.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.ed_data.setDate(QDate.currentDate())
        self._last_valid_date = self.ed_data.date()
        self.cb_owner_user = QtWidgets.QComboBox()
        self.cb_owner_user.setFixedWidth(140)
        self.cb_owner_user.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContentsOnFirstShow)
        self.cb_owner_user.setToolTip(
            "Utilizador associado ao orcamento. Por defeito fica o utilizador do login, "
            "mas pode ser alterado para outro responsavel."
        )
        self._load_orcamento_user_choices(preserve_current=False)
        # Pasta do orcamento (mostra apenas se existir)
        self.lbl_pasta_orc = QtWidgets.QLabel("Pasta:")
        self.ed_pasta_orc = QtWidgets.QLineEdit()
        self.ed_pasta_orc.setReadOnly(True)
        self.ed_pasta_orc.setMinimumWidth(320)
        self.ed_pasta_orc.setPlaceholderText("Pasta do orcamento no servidor")
        self.lbl_pasta_orc.setVisible(False)
        self.ed_pasta_orc.setVisible(False)
        self.pasta_container = QtWidgets.QWidget()
        pasta_layout = QtWidgets.QHBoxLayout(self.pasta_container)
        pasta_layout.setContentsMargins(0, 0, 0, 0)
        pasta_layout.setSpacing(6)
        pasta_layout.addWidget(self.lbl_pasta_orc)
        pasta_layout.addWidget(self.ed_pasta_orc, 1)
        self.cb_status = QtWidgets.QComboBox()
        self.cb_status.addItems(["Falta Orcamentar", "Enviado", "Nao Enviado", "Adjudicado", "Sem Interesse", "Nao Adjudicado"])
        self.ed_enc_phc = QtWidgets.QLineEdit()
        self.ed_ref_cliente = QtWidgets.QLineEdit()
        self.ed_obra = QtWidgets.QLineEdit()
        self.ed_preco = QtWidgets.QLineEdit()
        self.ed_desc = QtWidgets.QTextEdit()
        # ocupa 2 linhas (ver layout em "Campos do Orcamento")
        self.ed_desc.setFixedHeight(120)
        self.ed_desc.setPlaceholderText("Descricao curta...")
        self.ed_loc = QtWidgets.QLineEdit()
        self.ed_info1 = QtWidgets.QTextEdit()
        self.ed_info1.setFixedHeight(60)
        self.ed_info2 = QtWidgets.QTextEdit()
        self.ed_info2.setFixedHeight(60)

        # Pesquisa
        search_bar = QtWidgets.QHBoxLayout()
        search_bar.setSpacing(6)
        lbl_search = QtWidgets.QLabel("Pesquisa:")
        self.ed_search = QtWidgets.QLineEdit()
        self.ed_search.setMinimumWidth(320)
        self.ed_search.setPlaceholderText("Pesquisar orcamentos - use % para multi-termos")
        self.ed_search.textChanged.connect(self.on_search)
        self.ed_search.textChanged.connect(self._update_clear_search_button)
        self.btn_clear_search = QToolButton()
        self.btn_clear_search.setIcon(self.style().standardIcon(QStyle.SP_DialogResetButton))
        self.btn_clear_search.setToolTip("Limpar pesquisa")
        self.btn_clear_search.setEnabled(False)
        self.btn_clear_search.clicked.connect(self._clear_search)

        # Filtros adicionais
        self.cb_estado_filter = QtWidgets.QComboBox()
        self.cb_estado_filter.setEditable(True)
        self.cb_estado_filter.addItem("Todos", "")
        self.cb_estado_filter.currentIndexChanged.connect(lambda: self.refresh(select_first=False))

        self.cb_cliente_filter = QtWidgets.QComboBox()
        self.cb_cliente_filter.setEditable(True)
        self.cb_cliente_filter.addItem("Todos", "")
        self.cb_cliente_filter.currentIndexChanged.connect(lambda: self.refresh(select_first=False))

        self.cb_user_filter = QtWidgets.QComboBox()
        self.cb_user_filter.setEditable(True)
        self.cb_user_filter.addItem("Todos", "")
        self.cb_user_filter.currentIndexChanged.connect(lambda: self.refresh(select_first=False))

        search_bar.addWidget(lbl_search)
        search_bar.addWidget(self.ed_search, 3)
        search_bar.addWidget(self.btn_clear_search)
        search_bar.addSpacing(8)
        search_bar.addWidget(QtWidgets.QLabel("Estado:"))
        search_bar.addWidget(self.cb_estado_filter)
        search_bar.addSpacing(8)
        search_bar.addWidget(QtWidgets.QLabel("Cliente:"))
        search_bar.addWidget(self.cb_cliente_filter)
        search_bar.addSpacing(8)
        search_bar.addWidget(QtWidgets.QLabel("Utilizador:"))
        search_bar.addWidget(self.cb_user_filter)

        # Tabela
        self.table = QtWidgets.QTableView(self)
        self.model = SimpleTableModel(
            columns=[
                {"header": "Ano", "attr": "ano", "editable": False},
                {"header": "Num Orcamento", "attr": "num_orcamento", "editable": False},
                {"header": "Versao", "attr": "versao", "editable": False},
                {"header": "Enc PHC", "attr": "enc_phc", "formatter": self._format_enc_phc, "editable": False},
                {"header": "Cliente", "attr": "cliente", "editable": False},
                {"header": "Ref. Cliente", "attr": "ref_cliente", "editable": False},
                {"header": "Data", "attr": "data", "editable": False},
                {
                    "header": "Preco",
                    "attr": "preco",
                    "formatter": lambda v: self._format_currency(v),
                    "tooltip": self._preco_tooltip,
                    "editable": False,
                },
                {"header": "Utilizador", "attr": "utilizador", "editable": False},
                {"header": "Estado", "attr": "estado", "editable": False},
                {"header": "Obra", "attr": "obra", "editable": False},
                {"header": "Localizacao", "attr": "localizacao", "editable": False},
                {"header": "Descricao", "attr": "descricao", "editable": False},
                {"header": "Info 1", "attr": "info_1", "editable": False},
                {"header": "Info 2", "attr": "info_2", "editable": False},
                {"header": "ID", "attr": "id", "editable": False},
            ]
        )
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet(
            "QTableView::item:selected { background: #555555; color: white; }"
            "QTableView::item:selected:!active { background: #666666; color: white; }"
        )
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.setStretchLastSection(False)
        self.table.setSortingEnabled(True)
        # Largura das colunas Lista Orcamentos
        width_map = {
            "ID": 30,
            "Ano": 50,
            "Num Orcamento": 100,
            "Versao": 60,
            "Enc PHC": 80,
            "Cliente": 170,
            "Ref. Cliente": 80,
            "Data": 80,
            "Preco": 80,
            "Utilizador": 90,
            "Estado": 110,
            "Obra": 180,
            "Localizacao": 140,
            "Descricao": 220,
            "Info 1": 220,
            "Info 2": 220,
        }
        stretch_cols = {"Descricao", "Info 1", "Info 2"}
        for idx, col in enumerate(self.model.columns):
            spec = self.model._col_spec(col)
            label = spec.get("header", "")
            if label in stretch_cols:
                header.setSectionResizeMode(idx, QtWidgets.QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(idx, QtWidgets.QHeaderView.Interactive)
                if label in width_map:
                    header.resizeSection(idx, width_map[label])
        self.table.selectionModel().selectionChanged.connect(self.load_selected)
        self.table.doubleClicked.connect(self._open_cliente_info)
        
        # Detectar interacao com tabela (scroll, navegacao com arrow keys)
        self.table.installEventFilter(self)

        # Botoes
        def _style_primary_button(btn: QtWidgets.QPushButton, color: str):
            btn.setStyleSheet(
                f"background-color:{color}; color:white; font-weight:bold; padding:8px 12px; border-radius:4px;"
            )
            btn.setCursor(Qt.PointingHandCursor)

        s = self.style()
        btn_novo = QtWidgets.QPushButton("Novo Orcamento")
        btn_novo.setIcon(s.standardIcon(QStyle.SP_FileIcon))
        btn_novo.setToolTip(
            "Cria um novo orcamento no formulario.\n"
            "- Mantem o ano atual/selecionado e calcula o proximo numero sequencial.\n"
            "- Limpa os campos para comecar um registo novo.\n"
            "- Nota: so grava na base de dados quando clicar em 'Salvar'."
        )
        _style_primary_button(btn_novo, "#4CAF50")
        btn_novo.clicked.connect(self.on_novo)

        self.btn_save = QtWidgets.QPushButton("Salvar")
        self.btn_save.setIcon(s.standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_save.setToolTip(
            "Grava o orcamento atual na base de dados.\n"
            "- Cria novo registo (se ainda nao existir) ou atualiza o selecionado.\n"
            "- Requer: Cliente selecionado e Ano valido (AAAA).\n"
            "- Dica: o campo 'Preco Orcamento' aceita virgula ou ponto.\n"
            "- Atalho: Ctrl+G."
        )
        _style_primary_button(self.btn_save, "#2196F3")
        self.btn_save.clicked.connect(self.on_save)
        self._base_save_button_text = self.btn_save.text() or "Salvar"
        self._shortcut_save = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+G"), self)
        self._shortcut_save.setContext(Qt.WidgetWithChildrenShortcut)
        self._shortcut_save.activated.connect(self.on_save)

        btn_open = QtWidgets.QPushButton("Abrir Itens")
        btn_open.setIcon(s.standardIcon(QStyle.SP_ArrowRight))
        btn_open.setToolTip(
            "Abre o menu 'Itens' para o orcamento selecionado.\n"
            "- Use para inserir/editar os itens do orcamento.\n"
            "- Requer: selecionar uma linha na lista de orcamentos."
        )
        _style_primary_button(btn_open, "#FF9800")
        btn_open.clicked.connect(self.on_open)

        btn_dup = QtWidgets.QPushButton("Duplicar p/ Versao")
        btn_dup.setIcon(s.standardIcon(QStyle.SP_BrowserReload))
        btn_dup.setToolTip(
            "Cria uma nova versao do orcamento selecionado.\n"
            "- Incrementa a versao (ex.: 01 -> 02) e duplica os dados principais.\n"
            "- Importante: nesta fase, nao duplica os itens automaticamente."
        )
        btn_dup.setStyleSheet("font-weight:bold; padding:6px 10px;")
        btn_dup.setCursor(Qt.PointingHandCursor)
        btn_dup.clicked.connect(self.on_duplicate)

        btn_del = QtWidgets.QPushButton("Eliminar Orcamento")
        btn_del.setIcon(s.standardIcon(QStyle.SP_TrashIcon))
        btn_del.setToolTip(
            "Elimina o orcamento selecionado.\n"
            "- Pode escolher: apagar na Base de Dados ou apagar as pastas no servidor.\n"
            "- Atencao: eliminar na Base de Dados e irreversivel."
        )
        btn_del.setStyleSheet("font-weight:bold; padding:6px 10px;")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.clicked.connect(self.on_delete)

        btn_folder = QtWidgets.QPushButton("Criar Pasta do Orcamento")
        btn_folder.setIcon(s.standardIcon(QStyle.SP_DirIcon))
        btn_folder.setToolTip(
            "Cria a pasta do orcamento no caminho configurado.\n"
            "- Estrutura tipica: <base>\\<Ano>\\<Num_Orcamento>_<Cliente>\\<Versao>.\n"
            "- Se ja existir, nao altera conteudos."
        )
        btn_folder.setStyleSheet("font-weight:bold; padding:6px 10px;")
        btn_folder.setCursor(Qt.PointingHandCursor)
        btn_folder.clicked.connect(self.on_create_folder)

        btn_open_folder = QtWidgets.QPushButton("Abrir Pasta Orcamento")
        btn_open_folder.setIcon(s.standardIcon(QStyle.SP_DialogOpenButton))
        btn_open_folder.setToolTip(
            "Abre no Explorador a pasta do orcamento.\n"
            "- Se a pasta da versao nao existir, abre a pasta base do orcamento.\n"
            "- Dica: use 'Criar Pasta do Orcamento' se ainda nao existir."
        )
        btn_open_folder.setStyleSheet("font-weight:bold; padding:6px 10px;")
        btn_open_folder.setCursor(Qt.PointingHandCursor)
        btn_open_folder.clicked.connect(self.on_open_folder)

        btn_refresh = QtWidgets.QPushButton("Atualizar")
        btn_refresh.setIcon(s.standardIcon(QStyle.SP_BrowserReload))
        btn_refresh.setToolTip(
            "Atualiza a lista de orcamentos e os filtros.\n"
            "- Recarrega tambem a lista de clientes.\n"
            "- Dica: se tiver alteracoes por gravar, clique primeiro em 'Salvar'."
        )
        btn_refresh.setStyleSheet("font-weight:bold; padding:6px 10px;")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(lambda: (self.refresh(), self._load_clients()))

        self.btn_daily_summary = QtWidgets.QPushButton("Resumo Diario")
        self.btn_daily_summary.setIcon(s.standardIcon(QStyle.SP_FileDialogInfoView))
        self.btn_daily_summary.setToolTip(
            "Mostra um resumo das tarefas formais do utilizador atual.\n"
            "- Usa tarefas formais por orcamento.\n"
            "- Se ainda nao existirem tarefas formais, usa Info 1, Info 2 e Notas como fallback.\n"
            "- Abre diretamente o orcamento ou os itens a partir da lista."
        )
        self.btn_daily_summary.setStyleSheet("font-weight:bold; padding:6px 10px;")
        self.btn_daily_summary.setCursor(Qt.PointingHandCursor)
        self.btn_daily_summary.clicked.connect(lambda: self.show_daily_summary_dialog(force=True))

        self.btn_tasks = QtWidgets.QPushButton("Tarefas")
        self.btn_tasks.setIcon(s.standardIcon(QStyle.SP_FileDialogDetailedView))
        self.btn_tasks.setToolTip(
            "Gere tarefas formais do orcamento selecionado.\n"
            "- Cada tarefa tem texto, utilizador, data limite e estado.\n"
            "- O Resumo Diario passa a usar estas tarefas como fonte principal."
        )
        self.btn_tasks.setStyleSheet("font-weight:bold; padding:6px 10px;")
        self.btn_tasks.setCursor(Qt.PointingHandCursor)
        self.btn_tasks.clicked.connect(self.on_tasks)

        # Header (Campos do Orcamento)
        def _lbl(text: str, width: Optional[int] = None) -> QtWidgets.QLabel:
            w = QtWidgets.QLabel(repair_mojibake(text))
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if width is not None and width > 0:
                w.setFixedWidth(width)
            return w

        header_box = QtWidgets.QGroupBox("Campos do Orcamento")
        header_v = QtWidgets.QVBoxLayout(header_box)
        header_v.setContentsMargins(10, 8, 10, 8)
        header_v.setSpacing(8)

        # widths (mantem campos curtos controlados) + layout compacto (2 linhas + 2 linhas de texto)
        self.cb_cliente.setFixedWidth(320)
        self.cb_ano.setFixedWidth(80)
        self.ed_data.setFixedWidth(120)
        self.cb_status.setFixedWidth(120)
        self.ed_preco.setFixedWidth(130)
        self.ed_enc_phc.setFixedWidth(110)
        self.ed_num.setFixedWidth(110)
        self.ed_ver.setFixedWidth(60)
        self.ed_ref_cliente.setFixedWidth(160)

        # 1a linha: Cliente + Ano + Data + Estado + Preco + Enc PHC
        r1 = QtWidgets.QHBoxLayout()
        r1.setSpacing(10)
        r1.addWidget(_lbl("Cliente:"))
        r1.addWidget(self.cb_cliente)
        r1.addWidget(_lbl("Ano:"))
        r1.addWidget(self.cb_ano)
        r1.addWidget(_lbl("Data:"))
        r1.addWidget(self.ed_data)
        r1.addWidget(_lbl("Estado:"))
        r1.addWidget(self.cb_status)
        r1.addWidget(_lbl("Preco Orcamento:"))
        r1.addWidget(self.ed_preco)
        r1.addWidget(_lbl("Enc PHC:"))
        r1.addWidget(self.ed_enc_phc)
        r1.addStretch(1)
        header_v.addLayout(r1)

        # 2a linha: Num Orcamento + Versao + Utilizador + Ref. Cliente + Obra + Localizacao
        r2 = QtWidgets.QHBoxLayout()
        r2.setSpacing(10)
        r2.addWidget(_lbl("Num Orcamento (seq):"))
        r2.addWidget(self.ed_num)
        r2.addWidget(_lbl("Versao:"))
        r2.addWidget(self.ed_ver)
        r2.addWidget(_lbl("Utilizador:"))
        r2.addWidget(self.cb_owner_user)
        r2.addWidget(_lbl("Ref. Cliente:"))
        r2.addWidget(self.ed_ref_cliente)
        r2.addWidget(_lbl("Obra:"))
        r2.addWidget(self.ed_obra, 1)
        r2.addWidget(_lbl("Localizacao:"))
        r2.addWidget(self.ed_loc, 1)
        header_v.addLayout(r2)

        # 3a + 4a linhas: Descricao (2 linhas a esquerda) + Info 1/2 (direita)
        grid_text = QtWidgets.QGridLayout()
        grid_text.setContentsMargins(0, 0, 0, 0)
        grid_text.setHorizontalSpacing(10)
        grid_text.setVerticalSpacing(8)

        grid_text.addWidget(_lbl("Descricao Orcamento:", 130), 0, 0)
        grid_text.addWidget(self.ed_desc, 0, 1, 2, 1)
        grid_text.addWidget(_lbl("Info 1:", 70), 0, 2)
        grid_text.addWidget(self.ed_info1, 0, 3)
        grid_text.addWidget(_lbl("Info 2:", 70), 1, 2)
        grid_text.addWidget(self.ed_info2, 1, 3)

        grid_text.setColumnStretch(1, 1)
        grid_text.setColumnStretch(3, 1)
        header_v.addLayout(grid_text)

        header_box.setStyleSheet("QGroupBox { padding-top: 10px; }")
        header_box.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
        header_box.setMaximumHeight(360)

        primary_actions = QtWidgets.QHBoxLayout()
        primary_actions.setSpacing(10)
        primary_actions.addWidget(btn_novo)
        primary_actions.addWidget(self.btn_save)
        primary_actions.addWidget(btn_open)
        for b in [btn_dup, btn_del, btn_folder, btn_open_folder, self.btn_tasks, self.btn_daily_summary, btn_refresh]:
            primary_actions.addWidget(b)
        primary_actions.addStretch(1)
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        # Botoes numa so linha
        actions_row = QtWidgets.QHBoxLayout()
        actions_row.setSpacing(12)
        actions_row.addLayout(primary_actions)

        main_layout.addLayout(actions_row)
        # pesquisa/filtros logo abaixo dos botoes
        search_row = QtWidgets.QHBoxLayout()
        search_row.setSpacing(8)
        search_row.addLayout(search_bar, stretch=1)
        search_row.addWidget(self.pasta_container, stretch=1)
        main_layout.addLayout(search_row)
        main_layout.addWidget(header_box)
        # titulo e pesquisa imediatamente acima da tabela
        table_header = QtWidgets.QHBoxLayout()
        table_header.setSpacing(8)
        lbl_table = QtWidgets.QLabel("Lista de Orcamentos")
        lbl_table.setStyleSheet("font-weight:bold;")
        table_header.addWidget(lbl_table)
        table_header.addStretch(1)

        main_layout.addLayout(table_header)
        main_layout.addWidget(self.table)
        # esticar tabela para ocupar o espaco disponivel imediatamente apos o cabecalho
        main_layout.setStretch(0, 0)  # acoes
        main_layout.setStretch(1, 0)  # pesquisa
        main_layout.setStretch(2, 0)  # header_box
        main_layout.setStretch(3, 0)  # titulo tabela
        main_layout.setStretch(4, 1)  # tabela

        self._setup_dirty_tracking()
        self._prepare_new_form()
        self.refresh()

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

    def on_price_changed_from_itens(self, orc_id: int, novo_preco: object) -> None:
        """NOVO: Callback quando o preco e revertido/atualizado no menu Items."""
        try:
            if self._current_id == orc_id and not getattr(self, "_dirty", False):
                from Martelo_Orcamentos_V2.app.models import Orcamento

                try:
                    self.db.expire_all()
                except Exception:
                    pass
                orcamento = self.db.get(Orcamento, orc_id)
                if orcamento and hasattr(self, "ed_preco"):
                    preco_atual = getattr(orcamento, "preco_total", None)
                    self.ed_preco.blockSignals(True)
                    try:
                        self.ed_preco.setText("" if preco_atual is None else self._format_currency(preco_atual))
                    finally:
                        self.ed_preco.blockSignals(False)
                    self._preco_manual_active = bool(getattr(orcamento, "preco_total_manual", False))
                    self._preco_manual_changed = False
                self._update_preco_tooltip()
        except Exception:
            pass

    def refresh_table(self) -> None:
        """Atualiza a lista geral preservando o contexto visual atual."""
        self._smart_refresh_table()

    def _on_preco_edited(self, *_args) -> None:
        if getattr(self, "_loading_form", False):
            return
        self._preco_manual_changed = True
        self._update_preco_tooltip()  # NOVO: Atualizar tooltip quando preco e editado
        self._set_dirty(True)

    def _update_preco_tooltip(self) -> None:
        """NOVO: Atualiza o tooltip do campo de preco com status (manual/calculado)."""
        try:
            if self._current_id and hasattr(self, "ed_preco"):
                from Martelo_Orcamentos_V2.app.models import Orcamento
                from Martelo_Orcamentos_V2.app.services import price_management as svc_price
                
                orcamento = self.db.get(Orcamento, self._current_id)
                if orcamento:
                    tooltip = svc_price.get_price_tooltip(orcamento)
                    self.ed_preco.setToolTip(tooltip)
        except Exception:
            pass

    def _on_cliente_selected(self, _index: int) -> None:
        if getattr(self, "_loading_form", False) or getattr(self, "_ignore_cliente_change", False):
            return
        self._handle_cliente_change(self.cb_cliente.currentText())

    def _on_cliente_edit_finished(self) -> None:
        if getattr(self, "_loading_form", False) or getattr(self, "_ignore_cliente_change", False):
            return
        self._handle_cliente_change(self.cb_cliente.currentText())

    def _handle_cliente_change(self, text: str) -> None:
        plan = build_cliente_change_plan(text, consumidor_final_label=CONSUMIDOR_FINAL_LABEL)
        if plan.should_open_temp_dialog:
            self._maybe_handle_consumidor_final(plan.normalized_text)
            return
        if plan.remember_text:
            self._last_cliente_text = plan.remember_text

    def _maybe_handle_consumidor_final(self, text: str) -> None:
        plan = build_cliente_change_plan(text, consumidor_final_label=CONSUMIDOR_FINAL_LABEL)
        if not plan.should_open_temp_dialog:
            return
        if self._temp_dialog_open:
            return
        self._temp_dialog_open = True
        try:
            if not self._open_temp_client_dialog():
                self._ignore_cliente_change = True
                try:
                    self.cb_cliente.setCurrentText(self._last_cliente_text or "")
                finally:
                    self._ignore_cliente_change = False
        finally:
            self._temp_dialog_open = False

    def _resolve_selected_cliente(self) -> Optional[ClienteComboItem]:
        return svc_orc_client_workflow.resolve_selected_cliente(
            self.db,
            items=self._clients,
            current_text=self.cb_cliente.currentText(),
            current_index=self.cb_cliente.currentIndex(),
            consumidor_final_id=self._consumidor_final_id,
        )

    def _open_temp_client_dialog(self) -> bool:
        if not self._consumidor_final_id:
            QtWidgets.QMessageBox.warning(
                self,
                "Cliente",
                "Nao foi encontrado o cliente 'CONSUMIDOR FINAL' na tabela PHC.\n"
                "Atualize os clientes (menu Clientes -> Atualizar PHC) e tente novamente.",
            )
            return False

        dlg = TempClientDialog(parent=self, db=self.db)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return False

        try:
            nome = svc_orc_client_workflow.resolve_temp_client_dialog_selection(
                self.db,
                dialog_data=dlg.result_data() or {},
                phc_name_set=getattr(self, "_phc_name_set", set()),
            )
        except ValueError as exc:
            if str(exc) == "Cliente temporario invalido.":
                return False
            QtWidgets.QMessageBox.warning(self, "Cliente", str(exc))
            return False

        self._load_clients()
        self._ignore_cliente_change = True
        try:
            self.cb_cliente.setCurrentText(nome)
        finally:
            self._ignore_cliente_change = False
        self._last_cliente_text = nome
        return True

    def _on_form_change(self, *_args) -> None:
        if getattr(self, "_loading_form", False):
            return
        self._set_dirty(True)

    def _on_date_changed(self, date: QDate) -> None:
        # Protecao: evitar datas anteriores ao dia atual (apenas em interacao do utilizador).
        if getattr(self, "_loading_form", False):
            self._last_valid_date = date
            return
        today = QDate.currentDate()
        if date < today:
            self._notify_silent("A data nao pode ser anterior ao dia atual.", timeout_ms=4000)
            try:
                self.ed_data.blockSignals(True)
                self.ed_data.setDate(self._last_valid_date or today)
            finally:
                self.ed_data.blockSignals(False)
            return
        self._last_valid_date = date
        self._set_dirty(True)

    def _setup_dirty_tracking(self) -> None:
        widgets_line_edit = (
            getattr(self, "ed_ver", None),
            getattr(self, "ed_enc_phc", None),
            getattr(self, "ed_ref_cliente", None),
            getattr(self, "ed_obra", None),
            getattr(self, "ed_loc", None),
        )
        for w in widgets_line_edit:
            if hasattr(w, "textEdited"):
                w.textEdited.connect(self._on_user_edit)
        if hasattr(self.ed_preco, "textEdited"):
            self.ed_preco.textEdited.connect(self._on_preco_edited)

        combos = (
            getattr(self, "cb_cliente", None),
            getattr(self, "cb_ano", None),
            getattr(self, "cb_status", None),
            getattr(self, "cb_owner_user", None),
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

        if hasattr(self, "ed_data") and hasattr(self.ed_data, "dateChanged"):
            self.ed_data.dateChanged.connect(self._on_date_changed)

        for w in (getattr(self, "ed_desc", None), getattr(self, "ed_info1", None), getattr(self, "ed_info2", None)):
            if hasattr(w, "textChanged"):
                w.textChanged.connect(self._on_form_change)

    # Dados
    def refresh(self, select_first: bool = True):
        prev_id = self.selected_id()
        estado_f = self.cb_estado_filter.currentText().strip()
        cliente_f = self.cb_cliente_filter.currentText().strip()
        user_f = self.cb_user_filter.currentText().strip()
        table_state = build_orcamento_table_state(
            list_orcamentos(self.db),
            estado_filter=estado_f,
            cliente_filter=cliente_f,
            user_filter=user_f,
        )
        self.model.set_rows(table_state.rows)

        def _reload_combo(combo, values, current):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Todos", "")
            for v in values:
                combo.addItem(v, v)
            if current:
                combo.setCurrentText(current)
            combo.blockSignals(False)

        _reload_combo(self.cb_estado_filter, table_state.estados, estado_f)
        _reload_combo(self.cb_cliente_filter, table_state.clientes, cliente_f)
        _reload_combo(self.cb_user_filter, table_state.users, user_f)

        selection_plan = plan_table_selection(
            table_state.rows,
            preferred_id=prev_id,
            select_first=select_first,
        )
        if selection_plan.preferred_id is not None and self._select_row_by_id(selection_plan.preferred_id):
            return

        if selection_plan.has_rows and selection_plan.select_first:
            self.table.selectRow(0)
        else:
            self.table.clearSelection()

    def selected_row(self):
        sel_model = self.table.selectionModel()
        if sel_model is not None:
            selected = sel_model.selectedRows()
            if selected:
                try:
                    return self.model.get_row(selected[0].row())
                except Exception:
                    pass
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        return self.model.get_row(idx.row())

    def _auto_refresh_table(self) -> None:
        """Auto-refresh periodico da tabela de orcamentos para detectar novos orcamentos adicionados por outros utilizadores."""
        try:
            # NAO refrescar se:
            # - Ha edicoes nao gravadas
            # - Formulario esta a carregar dados
            # - Pesquisa esta ativa
            # - Utilizador esta a navegar a tabela
            # - Modo novo orcamento ativo
            if (getattr(self, "_dirty", False) or 
                getattr(self, "_loading_form", False) or
                self._search_text or
                self._table_user_scrolling or
                self._creating_new_orcamento):
                return
            
            # Smart refresh que preserva posicao visual
            self._smart_refresh_table()
        except Exception as e:
            logger.debug(f"Erro no auto-refresh da tabela de orcamentos: {e}")

    def _smart_refresh_table(self) -> None:
        """Refresh inteligente que preserva posicao visual e scroll position."""
        try:
            # 1. Guardar estado visual atual
            prev_id = self.selected_id()
            prev_scroll_row = 0
            
            # Tentar guardar primeira linha visovel
            try:
                first_visual_index = self.table.rowAt(0)
                if first_visual_index >= 0:
                    prev_scroll_row = first_visual_index
            except Exception:
                pass
            
            # 2. Carregar dados atualizados
            rows = list_orcamentos(self.db)
            estado_f = self.cb_estado_filter.currentText().strip()
            cliente_f = self.cb_cliente_filter.currentText().strip()
            user_f = self.cb_user_filter.currentText().strip()
            refresh_state = build_auto_refresh_state(
                rows,
                last_row_count=self._last_row_count,
                estado_filter=estado_f,
                cliente_filter=cliente_f,
                user_filter=user_f,
            )
            
            # 3. Detectar novos orcamentos e mostrar aviso
            if refresh_state.new_count > 0:
                self._show_new_orcamentos_notification(refresh_state.new_count)
            
            self._last_row_count = refresh_state.current_row_count
            
            # 4. Atualizar tabela
            self.model.set_rows(refresh_state.table_state.rows)
            
            # 5. Restaurar posicao visual (sem interromper scroll do utilizador)
            if prev_scroll_row >= 0 and prev_scroll_row < len(refresh_state.table_state.rows):
                try:
                    self.table.scrollTo(self.model.index(prev_scroll_row, 0))
                except Exception:
                    pass
            
            # 6. Restaurar selecao
            if prev_id is not None:
                self._select_row_by_id(prev_id)
            
        except Exception as e:
            logger.debug(f"Erro no smart refresh: {e}")

    def _show_new_orcamentos_notification(self, count: int) -> None:
        """Mostrar notificacao de novos orcamentos adicionados."""
        try:
            msg = f"Ha {count} novo(s) orcamento(s) adicionado(s)."
            # Mostrar como tooltip breve ou na barra de status se houver
            # Por enquanto, apenas log (pode ser expandido para QSystemTrayIcon ou balao)
            logger.info(f"Notificacao: {msg}")
        except Exception:
            pass

    def eventFilter(self, obj, event):
        """Detectar quando utilizador interage com a tabela (scroll, arrow keys, etc)."""
        try:
            # Detectar scroll ou navegacao na tabela
            if obj is self.table:
                from PySide6.QtCore import QEvent
                # Arrow keys, Page Up/Down, Home, End, scroll
                if event.type() in (QEvent.KeyPress, QEvent.Wheel, QEvent.MouseMove):
                    # Marcar tabela como sendo navegada
                    self._table_user_scrolling = True
                    # Resetar flag apos 2 segundos de inatividade
                    self._table_scroll_reset_timer.stop()
                    self._table_scroll_reset_timer.start(2000)
        except Exception:
            pass
        
        return super().eventFilter(obj, event)

    def selected_id(self):
        row = self.selected_row()
        return row.id if row else None

    def _select_row_by_id(self, oid: int) -> bool:
        if oid is None:
            return False
        try:
            idx = find_row_index_by_id(self.model._rows, oid)
        except Exception:
            idx = None
        if idx is None:
            return False
        try:
            self.table.selectRow(idx)
            self.table.scrollTo(self.model.index(idx, 0))
        except Exception:
            return False
        return True

    def _reset_list_filters(self) -> None:
        self._search_text = ""
        try:
            self.ed_search.blockSignals(True)
            self.ed_search.clear()
        finally:
            self.ed_search.blockSignals(False)
        self._update_clear_search_button()

        for combo in (
            getattr(self, "cb_estado_filter", None),
            getattr(self, "cb_cliente_filter", None),
            getattr(self, "cb_user_filter", None),
        ):
            if combo is None:
                continue
            combo.blockSignals(True)
            try:
                combo.setCurrentIndex(0)
            except Exception:
                combo.setCurrentText("Todos")
            finally:
                combo.blockSignals(False)

    def _update_clear_search_button(self, _text: str = "") -> None:
        btn = getattr(self, "btn_clear_search", None)
        ed = getattr(self, "ed_search", None)
        if btn is None or ed is None:
            return
        btn.setEnabled(bool(ed.text().strip()))

    def _clear_search(self) -> None:
        if not hasattr(self, "ed_search"):
            return
        self.ed_search.clear()

    def focus_orcamento_by_id(self, oid: int, *, open_items: bool = False) -> bool:
        request = build_focus_request(oid, open_items=open_items)
        if request is None:
            return False
        self._reset_list_filters()
        self.refresh(select_first=False)
        if not self._select_row_by_id(request.target_id):
            return False
        self.load_selected()
        if request.open_items:
            self.on_open()
        return True

    def show_daily_summary_dialog(self, *, force: bool = False) -> bool:
        user_id = getattr(self.current_user, "id", None)
        if not user_id:
            return False

        try:
            summary = svc_lembretes.build_daily_summary(
                self.db,
                user_id=int(user_id),
                username=str(getattr(self.current_user, "username", "") or ""),
            )
        except Exception as exc:
            logger.exception("daily.summary erro user_id=%s", user_id)
            if force:
                QtWidgets.QMessageBox.critical(self, "Resumo Diario", f"Falha ao gerar o resumo diario: {exc}")
            return False

        has_any_rows = bool(summary.items) or bool(getattr(summary, "hidden_count", 0))
        if not has_any_rows:
            if force:
                QtWidgets.QMessageBox.information(
                    self,
                    "Resumo Diario",
                    "Nao foram encontrados lembretes relevantes para o utilizador atual.",
                )
            return False

        if (not force) and (not svc_lembretes.should_auto_show_today(self.db, user_id=int(user_id), today=summary.today)):
            return False

        if (not force) and summary.actionable_count <= 0:
            return False

        dlg = DailyOrcamentoReminderDialog(
            summary,
            db_session=self.db,
            user_id=int(user_id),
            username=str(getattr(self.current_user, "username", "") or ""),
            parent=self,
            auto_mode=(not force),
        )
        result = dlg.exec()

        if not force:
            try:
                svc_lembretes.mark_auto_show_seen(self.db, user_id=int(user_id), today=summary.today)
                self.db.commit()
            except Exception:
                self.db.rollback()
                logger.exception("daily.summary mark_seen erro user_id=%s", user_id)

        selected_id, open_items = dlg.selected_action()
        if result == QtWidgets.QDialog.Accepted and selected_id is not None:
            return self.focus_orcamento_by_id(selected_id, open_items=open_items)
        return True

    def _load_clients(self):
        current_text = self.cb_cliente.currentText().strip()
        try:
            with SessionLocal() as refresh_db:
                state = svc_orc_client_workflow.load_cliente_combo_state(
                    refresh_db,
                    consumidor_final_label=CONSUMIDOR_FINAL_LABEL,
                    consumidor_final_id=self._consumidor_final_id,
                )
                refresh_db.expunge_all()
                self._consumidor_final_id = state.consumidor_final_id
                self._phc_name_set = state.phc_names
                self._clients = state.items
                names = state.names
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar clientes: {exc}")
            return

        self.cb_cliente.blockSignals(True)
        self.cb_cliente.clear()
        self.cb_cliente.addItems(names)

        if self.cb_cliente.isEditable():
            comp = QCompleter(names, self)
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            comp.setFilterMode(Qt.MatchContains)
            self.cb_cliente.setCompleter(comp)

        if current_text:
            idx = next((i for i, name in enumerate(names) if name == current_text), -1)
            if idx >= 0:
                self.cb_cliente.setCurrentIndex(idx)
            else:
                self.cb_cliente.setCurrentText(current_text)

        self.cb_cliente.blockSignals(False)

    def reload_clients(self):
        self._load_clients()

    def showEvent(self, event):
        super().showEvent(event)
        self._load_clients()
        self._load_orcamento_user_choices()

    def _year_text(self) -> str:
        try:
            return (self.cb_ano.currentText() or "").strip()
        except Exception:
            return ""

    def _set_year_text(self, year: str, *, ensure_in_list: bool = True) -> None:
        year_txt = str(year or "").strip()
        if not year_txt:
            year_txt = str(QDate.currentDate().year())

        if ensure_in_list:
            existing = {self.cb_ano.itemText(i) for i in range(self.cb_ano.count())}
            if year_txt not in existing:
                years = {year_txt, *existing}
                years_int = sorted({int(y) for y in years if str(y).isdigit()}, reverse=True)
                self.cb_ano.blockSignals(True)
                try:
                    self.cb_ano.clear()
                    for y in years_int:
                        self.cb_ano.addItem(str(y), str(y))
                finally:
                    self.cb_ano.blockSignals(False)

        self.cb_ano.setCurrentText(year_txt)
        try:
            self.cb_ano.setEditText(year_txt)
        except Exception:
            pass

    def _populate_years(self) -> None:
        current_year = int(QDate.currentDate().year())
        years = [str(y) for y in range(current_year + 5, current_year - 6, -1)]
        self.cb_ano.blockSignals(True)
        try:
            self.cb_ano.clear()
            for y in years:
                self.cb_ano.addItem(y, y)
            self.cb_ano.setCurrentText(str(current_year))
        finally:
            self.cb_ano.blockSignals(False)

    def _on_ano_changed(self, _text: str) -> None:
        # apenas recalcular sequencia quando estamos em modo "novo"
        if self._current_id is not None:
            return
        ano_txt = self._year_text()
        if len(ano_txt) != 4 or not ano_txt.isdigit():
            return
        try:
            seq_txt = next_seq_for_year(self.db, ano_txt)
        except Exception:
            seq_txt = "0001"
        self.ed_num.setText(seq_txt)

    def _on_ano_editing_finished(self) -> None:
        if self._current_id is not None:
            return
        ano_txt = self._year_text()
        if len(ano_txt) != 4 or not ano_txt.isdigit():
            return
        self._set_year_text(ano_txt, ensure_in_list=True)

    def _selected_owner_user_id(self) -> Optional[int]:
        try:
            user_id = self.cb_owner_user.currentData()
            if user_id in (None, ""):
                return None
            return int(user_id)
        except Exception:
            return None

    def _load_orcamento_user_choices(
        self,
        *,
        selected_user_id: Optional[int] = None,
        preserve_current: bool = True,
    ) -> None:
        current_selected_id = self._selected_owner_user_id() if preserve_current else None
        target_user_id = selected_user_id if selected_user_id not in (None, "") else current_selected_id
        if target_user_id in (None, ""):
            target_user_id = getattr(self.current_user, "id", None)

        try:
            with SessionLocal() as refresh_db:
                choices = svc_orc_tasks.list_active_user_choices(refresh_db)
                known_ids = {choice.id for choice in choices}
                if target_user_id not in (None, "") and int(target_user_id) not in known_ids:
                    extra_user = refresh_db.get(User, int(target_user_id))
                    username = str(getattr(extra_user, "username", "") or "").strip() if extra_user else ""
                    if username:
                        choices.append(svc_orc_tasks.UserChoice(id=int(target_user_id), username=username))
                        choices = sorted(choices, key=lambda choice: choice.username.casefold())
        except Exception:
            logger.exception("orcamento.users load erro current_user_id=%s", getattr(self.current_user, "id", None))
            choices = []
            fallback_id = getattr(self.current_user, "id", None)
            fallback_name = str(getattr(self.current_user, "username", "(utilizador)") or "(utilizador)")
            if fallback_id not in (None, ""):
                choices.append(svc_orc_tasks.UserChoice(id=int(fallback_id), username=fallback_name))

        self._orcamento_user_choices = choices
        self.cb_owner_user.blockSignals(True)
        try:
            self.cb_owner_user.clear()
            for choice in choices:
                self.cb_owner_user.addItem(choice.username, choice.id)
            if self.cb_owner_user.count() <= 0:
                return
            if target_user_id not in (None, ""):
                index = self.cb_owner_user.findData(int(target_user_id))
                if index >= 0:
                    self.cb_owner_user.setCurrentIndex(index)
                    return
            fallback_index = self.cb_owner_user.findData(getattr(self.current_user, "id", None))
            self.cb_owner_user.setCurrentIndex(fallback_index if fallback_index >= 0 else 0)
        finally:
            self.cb_owner_user.blockSignals(False)

    def _set_identity_lock(self, locked: bool):
        self.cb_ano.setEnabled(not locked)
        self.ed_ver.setReadOnly(locked)
        # O numero e sempre gerido automaticamente
        self.ed_num.setReadOnly(True)

    def _base_orcamentos_path(self) -> str:
        try:
            return get_setting(
                self.db,
                "base_path_orcamentos",
                r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2",
            )
        except Exception:
            return r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2"

    def _apply_loaded_form_values(self, values) -> None:
        self._set_year_text(values.ano_text, ensure_in_list=True)
        self.ed_num.setText(values.seq_text)
        self.ed_ver.setText(values.versao_text)
        if values.parsed_date is not None:
            self.ed_data.setDate(QDate(values.parsed_date.year, values.parsed_date.month, values.parsed_date.day))
        else:
            self.ed_data.setDate(QDate.currentDate())
        self.cb_status.setCurrentText(values.status_text)
        self.ed_enc_phc.setText(values.enc_phc)
        self.ed_ref_cliente.setText(values.ref_cliente)
        self.ed_obra.setText(values.obra)
        self.ed_preco.setText(values.preco_text)
        self._update_preco_tooltip()
        self.ed_desc.setPlainText(values.descricao)
        self.ed_loc.setText(values.localizacao)
        self.ed_info1.setPlainText(values.info_1)
        self.ed_info2.setPlainText(values.info_2)

    def _apply_loaded_selection_state(self, state) -> None:
        self._current_id = state.current_id
        self._preco_manual_active = state.manual_flag
        self._preco_manual_changed = False
        self._set_identity_lock(True)
        self._ignore_cliente_change = True
        try:
            if state.selected_client_name:
                self.cb_cliente.setCurrentText(state.selected_client_name)
                self._last_cliente_text = state.selected_client_name
        finally:
            self._ignore_cliente_change = False
        self._apply_loaded_form_values(state.form_values)
        self._load_orcamento_user_choices(selected_user_id=state.selected_user_id, preserve_current=False)
        self._set_pasta_orc_path(state.folder_path)

    def load_selected(self):
        row = self.selected_row()
        if not row:
            self._set_pasta_orc_path(None)
            return
        self._loading_form = True

        try:
            state = prepare_loaded_orcamento_selection(
                row,
                orcamento_loader=lambda oid: svc_orc_workflow.load_orcamento_with_client(self.db, oid),
                available_client_names={c.nome for c in self._clients if c.nome},
                temp_client_name_key=TEMP_CLIENT_NAME_KEY,
                format_version=self._format_version,
                format_currency=self._format_currency,
                manual_flag_extractor=self._extract_preco_manual,
                folder_path_builder=self._existing_orcamento_folder_path,
            )
            if not state:
                return
            self._apply_loaded_selection_state(state)
        finally:
            self._ignore_cliente_change = False
            self._loading_form = False
        self._set_dirty(False)

    def _set_pasta_orc_path(self, path: Optional[str]) -> None:
        text = (path or "").strip()
        if text:
            self.ed_pasta_orc.setText(text)
            self.ed_pasta_orc.setToolTip(text)
            self.lbl_pasta_orc.setVisible(True)
            self.ed_pasta_orc.setVisible(True)
            return
        self.ed_pasta_orc.clear()
        self.ed_pasta_orc.setToolTip("")
        self.lbl_pasta_orc.setVisible(False)
        self.ed_pasta_orc.setVisible(False)

    def _open_cliente_info(self, *_args) -> None:
        row = self.selected_row()
        if not row:
            return
        try:
            state = svc_orc_client_workflow.load_cliente_info_state(
                self.db,
                row_id=getattr(row, "id", None),
                temp_id=getattr(row, "temp_client_id", None),
                temp_nome=str(getattr(row, "temp_client_nome", "") or "").strip(),
            )
        except ValueError as exc:
            QtWidgets.QMessageBox.information(self, "Cliente", str(exc))
            return
        if not state:
            return
        dlg = ClienteInfoDialog(parent=self, origem=state.origem, data=state.data)
        dlg.exec()

    def _normalize_simplex(self, value: str) -> str:
        return normalize_simplex(value)

    def _get_temp_simplex_for_orcamento(self, o) -> Optional[str]:
        return extract_temp_simplex_from_extras(
            getattr(o, "extras", None),
            temp_client_id_key=TEMP_CLIENT_ID_KEY,
            temp_client_name_key=TEMP_CLIENT_NAME_KEY,
            consumidor_final_label=CONSUMIDOR_FINAL_LABEL,
            temp_loader=lambda temp_id: get_cliente_temporario(self.db, temp_id),
        )

    def _resolve_orcamento_simplex(self, o, client=None) -> str:
        temp_simplex = self._get_temp_simplex_for_orcamento(o)
        if client is None and getattr(o, "client_id", None):
            from Martelo_Orcamentos_V2.app.models import Client

            client = self.db.get(Client, o.client_id)
        return resolve_orcamento_simplex(client=client, temp_simplex=temp_simplex)

    def _existing_orcamento_folder_path(self, o, client) -> Optional[str]:
        return build_existing_orcamento_folder_path(
            base_path=self._base_orcamentos_path(),
            ano=getattr(o, "ano", None),
            num_orc=getattr(o, "num_orcamento", None),
            simplex=self._resolve_orcamento_simplex(o, client),
            versao=getattr(o, "versao", None),
            format_version=self._format_version,
        )

    # Acoes
    @staticmethod
    def _format_version(value):
        if value is None:
            return "01"
        text = str(value).strip()
        if not text:
            return "01"
        if text.isdigit():
            try:
                return f"{int(text):02d}"
            except ValueError:
                pass
        return text.zfill(2) if len(text) == 1 else text

    @staticmethod
    def _format_currency(value) -> str:
        return format_currency_pt(value)

    @staticmethod
    def _format_enc_phc(value) -> str:
        if value in (None, ""):
            return ""
        text = str(value).strip()
        if not text:
            return ""
        digits = re.sub(r"\D", "", text)
        if not digits:
            return text
        if len(digits) <= 4:
            return digits.zfill(4)
        return digits

    @staticmethod
    def _extract_preco_manual(extras) -> bool:
        if not extras:
            return False
        if isinstance(extras, dict):
            return bool(extras.get(PRECO_MANUAL_KEY))
        return False

    def _preco_tooltip(self, row_obj, _val, _spec):
        """NOVO: Retorna tooltip mostrando status do preco (manual/calculado) e timestamp."""
        try:
            from Martelo_Orcamentos_V2.app.services import price_management as svc_price
            
            # Se row_obj tiver os campos da nova coluna
            if hasattr(row_obj, 'preco_total_manual') and hasattr(row_obj, 'preco_atualizado_em'):
                tooltip = svc_price.get_price_tooltip(row_obj)
                return tooltip if tooltip else None
            
            # Fallback para compatibilidade com dados antigos (JSON extras)
            if getattr(row_obj, "preco_manual", False):
                return "Preco: Manual (adicionado manualmente)"
            
            return None
        except Exception:
            return None

    @staticmethod
    def _parse_currency(text):
        return parse_currency_pt(text)

    def _confirm_ref_cliente_duplicate(self, ref_cliente: str, matches) -> bool:
        rows = svc_orc_workflow.build_ref_cliente_match_rows(self.db, matches)
        return confirm_ref_cliente_duplicate(self, ref_cliente=ref_cliente, match_rows=rows)

    def _prepare_new_form(self, ano: Optional[str] = None):
        """Prepara o formulario para um novo orcamento."""
        self._loading_form = True
        self.table.clearSelection()
        self._current_id = None
        self._preco_manual_active = False
        self._preco_manual_changed = False
        self._last_cliente_text = ""
        self._set_identity_lock(False)

        # Ano atual (ou passado como argumento)
        ano_full = (ano or str(QDate.currentDate().year())).strip() or str(QDate.currentDate().year())
        if self.cb_ano.count() == 0:
            self._populate_years()

        # Calcula proximo numero sequencial (0001, 0002, ...)
        try:
            seq_txt = next_seq_for_year(self.db, ano_full)
        except Exception:
            seq_txt = "0001"
        new_state = build_new_orcamento_form_state(
            ano_text=ano_full,
            seq_text=seq_txt,
        )
        self._set_year_text(new_state.ano_text, ensure_in_list=True)
        self.ed_num.setText(new_state.seq_text)

        # Valores iniciais padrao
        self.ed_ver.setText(new_state.versao_text)
        self.ed_data.setDate(QDate.currentDate())
        self.cb_status.setCurrentText(new_state.status_text)
        self.cb_cliente.blockSignals(True)
        self.cb_cliente.setCurrentIndex(-1)
        if self.cb_cliente.isEditable():
            self.cb_cliente.setCurrentText("")
        self.cb_cliente.blockSignals(False)

        # Limpar restantes campos editaveis
        for w in [self.ed_enc_phc, self.ed_ref_cliente, self.ed_obra, self.ed_preco, self.ed_loc]:
            w.clear()
        self.ed_desc.clear()
        self.ed_info1.clear()
        self.ed_info2.clear()
        self._load_orcamento_user_choices(selected_user_id=getattr(self.current_user, "id", None), preserve_current=False)
        self._set_pasta_orc_path(None)
        self._loading_form = False
        self._set_dirty(False)

    def on_novo(self):
        """Acao do botao Inserir Novo Orcamento."""
        # Desabilitar auto-refresh enquanto cria novo orcamento
        self._creating_new_orcamento = True
        self._prepare_new_form(self._year_text() or None)

    def _notify_silent(self, text: str, timeout_ms: int = 3000) -> None:
        """Mostra feedback discreto (sem popup). Tenta StatusBar; se nao existir, nao faz nada."""
        win = self.window()
        if isinstance(win, QtWidgets.QMainWindow):
            sb = win.statusBar()
            if sb is None:
                sb = QtWidgets.QStatusBar(win)
                win.setStatusBar(sb)
            sb.showMessage(text, timeout_ms)

    def _apply_post_save_plan(self, *, was_new: bool, saved_id: Optional[int], ano_text: str) -> None:
        plan = build_post_save_plan(
            was_new=was_new,
            saved_id=saved_id,
            ano_text=ano_text,
        )
        self.refresh(select_first=plan.refresh_select_first)
        if plan.select_id is not None:
            self._select_row_by_id(plan.select_id)
        if plan.prepare_new_form_year:
            self._prepare_new_form(plan.prepare_new_form_year)
        if plan.leave_new_mode:
            self._creating_new_orcamento = False
            
    def on_save(self):
        """Acao do botao Gravar Orcamento."""
        try:
            request = svc_orc_workflow.prepare_orcamento_save_request(
                cliente_item=self._resolve_selected_cliente(),
                consumidor_final_id=self._consumidor_final_id,
                owner_user_id=self._selected_owner_user_id(),
                year_text=self._year_text(),
                seq_text=self.ed_num.text(),
                version_text=self.ed_ver.text(),
                format_version=self._format_version,
                ref_cliente_text=self.ed_ref_cliente.text(),
                data_value=format_date_storage(self.ed_data.date().toPython()),
                status_text=self.cb_status.currentText(),
                enc_phc=self.ed_enc_phc.text().strip() or None,
                obra=self.ed_obra.text().strip() or None,
                preco_val=self._parse_currency(self.ed_preco.text()),
                descricao_orcamento=self.ed_desc.toPlainText() or None,
                localizacao=self.ed_loc.text().strip() or None,
                info_1=self.ed_info1.toPlainText() or None,
                info_2=self.ed_info2.toPlainText() or None,
            )
        except ValueError as exc:
            title = "Ano" if "AAAA" in str(exc) else "Cliente"
            QtWidgets.QMessageBox.warning(self, title, str(exc))
            return

        try:
            matches, identity_exists = svc_orc_workflow.check_orcamento_save_conflicts(
                self.db,
                current_id=self._current_id,
                request=request,
            )
            from datetime import datetime
            existing_orcamento, _ = svc_orc_workflow.load_orcamento_with_client(self.db, self._current_id)

            if matches and not self._confirm_ref_cliente_duplicate(request.ref_cliente_txt or "", matches):
                return
            if identity_exists:
                QtWidgets.QMessageBox.warning(self, "Duplicado", "Ja existe um orcamento com este ano, numero e versao.")
                return

            save_result = svc_orc_workflow.save_orcamento_request(
                self.db,
                current_id=self._current_id,
                request=request,
                created_by=getattr(self.current_user, "id", None),
                preco_manual_changed=self._preco_manual_changed,
                existing_manual_flag=bool(getattr(existing_orcamento, "preco_total_manual", False)),
                existing_extras=getattr(existing_orcamento, "extras", None),
                preco_manual_key=PRECO_MANUAL_KEY,
                temp_client_id_key=TEMP_CLIENT_ID_KEY,
                temp_client_name_key=TEMP_CLIENT_NAME_KEY,
                updated_at=datetime.now(),
            )
            o = save_result.orcamento
            was_new = save_result.was_new
            self._preco_manual_active = bool(save_result.manual_flag)
            self._preco_manual_changed = False

            self.db.commit()
            logger.info(
                "orcamento.save ok action=%s id=%s cliente_id=%s ano=%s num=%s ver=%s user_id=%s",
                "novo" if was_new else "editar",
                getattr(o, "id", None),
                request.client_id,
                request.ano_txt,
                request.num_orcamento,
                request.versao_txt,
                getattr(self.current_user, "id", None),
            )
            self._apply_post_save_plan(
                was_new=was_new,
                saved_id=getattr(o, "id", None),
                ano_text=request.ano_txt,
            )

            self._set_dirty(False)

            self._notify_silent("Orcamento gravado.", timeout_ms=3000) #QtWidgets.QMessageBox.information(self, "OK", "Orcamento gravado.")
        except Exception as e:
            self.db.rollback()
            logger.exception(
                "orcamento.save erro id=%s cliente_id=%s ano=%s num=%s ver=%s user_id=%s",
                self._current_id,
                getattr(request, "client_id", None) if "request" in locals() else None,
                self._year_text(),
                self.ed_num.text().strip(),
                self.ed_ver.text().strip(),
                getattr(self.current_user, "id", None),
            )
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar: {e}")

    def on_duplicate(self):
        oid = self.selected_id()
        if not oid:
            return
        try:
            dup = svc_orc_workflow.duplicate_orcamento_record(
                self.db,
                oid,
                created_by=getattr(self.current_user, "id", None),
            )
            self.db.commit()
            logger.info(
                "orcamento.duplicar ok origem_id=%s nova_id=%s versao=%s user_id=%s",
                oid,
                getattr(dup, "id", None),
                getattr(dup, "versao", None),
                getattr(self.current_user, "id", None),
            )
            self.refresh()
            QtWidgets.QMessageBox.information(self, "OK", build_duplicate_success_message(dup))
        except Exception as e:
            self.db.rollback()
            logger.exception("orcamento.duplicar erro origem_id=%s user_id=%s", oid, getattr(self.current_user, "id", None))
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao duplicar: {e}")

    def on_delete(self):
        oid = self.selected_id()
        if not oid:
            return
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle("Eliminar Orcamento")
        box.setText("O que pretende eliminar?")
        btn_bd = box.addButton("Eliminar na Base de Dados", QtWidgets.QMessageBox.AcceptRole)
        btn_pastas = box.addButton("Eliminar Pastas do Orcamento", QtWidgets.QMessageBox.DestructiveRole)
        box.addButton(QtWidgets.QMessageBox.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked == btn_bd:
            try:
                svc_orc_workflow.delete_orcamento_record(self.db, oid)
                self.db.commit()
                logger.info("orcamento.delete ok id=%s user_id=%s", oid, getattr(self.current_user, "id", None))
            except Exception as e:
                self.db.rollback()
                logger.exception("orcamento.delete erro id=%s user_id=%s", oid, getattr(self.current_user, "id", None))
                QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar: {e}")
            self.refresh()
        elif clicked == btn_pastas:
            self._delete_orcamento_folders(oid)

    def on_open(self):
        oid = self.selected_id()
        if oid:
            self.orcamento_aberto.emit(oid)

    def on_tasks(self):
        oid = self.selected_id()
        if not oid:
            QtWidgets.QMessageBox.information(self, "Tarefas", "Selecione um orcamento na lista.")
            return
        dlg = OrcamentoTasksDialog(
            db_session=self.db,
            orcamento_id=int(oid),
            current_user=self.current_user,
            parent=self,
        )
        dlg.exec()

    # Pastas
    def _delete_orcamento_folders(self, oid: int):
        o, client = svc_orc_workflow.load_orcamento_with_client(self.db, oid)
        if not o:
            return
        base = self._base_orcamentos_path()
        if not client:
            QtWidgets.QMessageBox.warning(self, "Cliente", "Cliente invalido.")
            return
        simplex = self._resolve_orcamento_simplex(o, client)
        try:
            removed = svc_orc_workflow.delete_orcamento_folders(
                base_path=base,
                ano=o.ano,
                num_orc=o.num_orcamento,
                simplex=simplex,
                versao=o.versao,
                format_version=self._format_version,
            )
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Aviso", f"Falha ao eliminar pasta: {e}")
            return
        if removed:
            QtWidgets.QMessageBox.information(self, "OK", "Pasta(s) eliminada(s):\n" + "\n".join(removed))
            if getattr(self, "_current_id", None) == oid:
                self._set_pasta_orc_path(None)

    def on_create_folder(self):
        row = self.selected_row()
        if not row:
            return
        o, client = svc_orc_workflow.load_orcamento_with_client(self.db, row.id)
        if not o:
            return
        base = self._base_orcamentos_path()
        if not client:
            QtWidgets.QMessageBox.warning(self, "Cliente", "Cliente invalido.")
            return
        temp_simplex = self._get_temp_simplex_for_orcamento(o)
        simplex_raw = (getattr(client, "nome_simplex", None) or "").strip()
        if not temp_simplex and (simplex_raw.endswith("...") or not simplex_raw):
            cliente_nome = (getattr(client, "nome", None) or "").strip() or "Cliente"
            num_phc = (getattr(client, "num_cliente_phc", None) or "").strip()
            simplex_label = simplex_raw or "(vazio)"
            QtWidgets.QMessageBox.warning(
                self,
                "Abreviado (PHC) em falta",
                "O nome cliente 'Simplex' do Martelo termina em '...' (ou esta vazio), o que indica que no PHC o campo "
                "'Abreviado' nao esta preenchido/sincronizado.\n\n"
                "Antes de criar a pasta do orcamento:\n"
                "1) No PHC, preencha o campo 'Abreviado' do cliente.\n"
                "2) No Martelo, va a Clientes e clique em 'Atualizar PHC'.\n\n"
                f"Cliente: {cliente_nome} (PHC: {num_phc or 'n/d'})\n"
                f"Simplex atual: {simplex_label}\n\n"
                "Depois volte a este orcamento e crie a pasta novamente.",
            )
            return
        simplex = self._normalize_simplex(
            getattr(client, "nome_simplex", None) or getattr(client, "nome", None) or "CLIENTE"
        )
        if temp_simplex:
            simplex = self._normalize_simplex(temp_simplex)
        try:
            dir_ver = svc_orc_workflow.create_orcamento_folder(
                base_path=base,
                ano=o.ano,
                num_orc=o.num_orcamento,
                simplex=simplex,
                versao=o.versao,
                format_version=self._format_version,
            )
            self._set_pasta_orc_path(dir_ver)
            QtWidgets.QMessageBox.information(self, "OK", f"Pasta criada:\n{dir_ver}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao criar pasta: {e}")

    def on_open_folder(self):
        row = self.selected_row()
        if not row:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um orcamento.")
            return
        o, client = svc_orc_workflow.load_orcamento_with_client(self.db, row.id)
        if not o:
            return
        if not client:
            QtWidgets.QMessageBox.warning(self, "Cliente", "Cliente invalido.")
            return
        target = svc_orc_workflow.find_existing_orcamento_folder(
            base_path=self._base_orcamentos_path(),
            ano=o.ano,
            num_orc=o.num_orcamento,
            simplex=self._resolve_orcamento_simplex(o, client),
            versao=o.versao,
            format_version=self._format_version,
        )
        try:
            if target and os.path.isdir(target):
                self._set_pasta_orc_path(target)
                os.startfile(target)
            else:
                self._set_pasta_orc_path(None)
                QtWidgets.QMessageBox.information(self, "Info", "A pasta ainda nao existe. Use 'Criar Pasta do Orcamento'.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao abrir pasta: {e}")

    def on_search(self, text: str):
        # Atualizar flag de pesquisa ativa (para evitar auto-refresh durante pesquisa)
        self._search_text = text.strip()
        
        rows = search_orcamentos(self.db, text)
        self.model.set_rows(rows)
