from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PySide6 import QtCore, QtWidgets

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.settings import get_setting, set_setting
from Martelo_Orcamentos_V2.app.services.materias_primas import (
    DEFAULT_MATERIAS_BASE_PATH,
    KEY_MATERIAS_BASE_PATH,
)
from Martelo_Orcamentos_V2.app.services import custeio_items as svc_custeio
from Martelo_Orcamentos_V2.app.services import producao as svc_producao
from Martelo_Orcamentos_V2.app.services import def_pecas as svc_def_pecas
from Martelo_Orcamentos_V2.app.services import margens as svc_margens


KEY_BASE_PATH = "base_path_orcamentos"
DEFAULT_BASE_PATH = r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2"

AUTO_DIMS_HELP_TEXT = (
    "Quando ativo, o Martelo preenche automaticamente as colunas COMP e LARG "
    "para pecas padrao (COSTA, PORTA ABRIR, LATERAL, DIVISORIA, TETO, FUNDO, "
    "PRATELEIRA AMOVIVEL, PRAT. AMOV., PRATELEIRA FIXA, PRAT.FIXA) usando as "
    "dimensoes HM/LM/PM do item. Continua possivel editar manualmente os valores."
)


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

        main_layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tabs)

        self._init_general_tab()
        self._init_producao_tab()
        self._init_def_pecas_tab()
        self._init_margens_tab()

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

        btn_rules = QtWidgets.QPushButton("Configurar Regras de Quantidade")
        btn_rules.clicked.connect(self._open_rules_dialog)
        lay.addRow(btn_rules)

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

        btn_save = QtWidgets.QPushButton("Gravar Configurações")
        btn_save.clicked.connect(self.on_save)
        lay.addRow(btn_save)

        self.tabs.addTab(tab, "Geral")

        # load defaults
        self.ed_base.setText(get_setting(self.db, KEY_BASE_PATH, DEFAULT_BASE_PATH))
        self.ed_materias.setText(get_setting(self.db, KEY_MATERIAS_BASE_PATH, DEFAULT_MATERIAS_BASE_PATH))
        self._refresh_auto_dims_summary()

    def _choose_directory(self, line_edit: QtWidgets.QLineEdit) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Escolher pasta")
        if directory:
            line_edit.setText(directory)

    def on_save(self) -> None:
        try:
            base_path = self.ed_base.text().strip() or DEFAULT_BASE_PATH
            materias_path = self.ed_materias.text().strip() or DEFAULT_MATERIAS_BASE_PATH
            set_setting(self.db, KEY_BASE_PATH, base_path)
            set_setting(self.db, KEY_MATERIAS_BASE_PATH, materias_path)
            if self._current_user_id is not None:
                svc_custeio.set_auto_dimension_enabled(self.db, self._current_user_id, self.btn_auto_dims.isChecked())
            self.db.commit()
            QtWidgets.QMessageBox.information(self, "OK", "Configuracoes gravadas.")
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
            ctx = svc_producao.build_context(self.db, orcamento_id, self._current_user_id, versao=versao)
        except Exception as exc:
            self.db.rollback()
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
            "Tabela de referência para o cálculo das linhas do custeio. Altere ou acrescente peças conforme necessário."
        )
        self.lbl_def_pecas_info.setWordWrap(True)
        layout.addWidget(self.lbl_def_pecas_info)

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
        self.tbl_def_pecas.itemChanged.connect(self._on_def_pecas_item_changed)
        layout.addWidget(self.tbl_def_pecas, 1)

        self.tabs.addTab(tab, "Definições Peças")
        self._set_def_pecas_controls_enabled(True)

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

        self._populate_def_pecas_table(dados)
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

    def _on_tab_changed(self, index: int) -> None:
        widget = self.tabs.widget(index)
        if getattr(self, "tab_producao", None) is not None and widget is self.tab_producao and self._producao_ctx and self._producao_dirty:
            self._load_producao_table()
        if getattr(self, "tab_def_pecas", None) is not None and widget is self.tab_def_pecas and self._def_pecas_dirty:
            self._load_def_pecas_table(force=True)

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

    # ----------------------------------------------------------------- Helpers
    def closeEvent(self, event: QtCore.QEvent) -> None:  # type: ignore[override]
        try:
            self.db.close()
        finally:
            super().closeEvent(event)


class QtRulesDialog(QtWidgets.QDialog):
    HEADERS = ["Regra", "Matches", "Expressao", "Tooltip"]

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Regras de Quantidade (Qt_und)")
        self.resize(820, 480)

        layout = QtWidgets.QVBoxLayout(self)

        target_layout = QtWidgets.QHBoxLayout()
        target_layout.addWidget(QtWidgets.QLabel("Orcamento ID:"))
        self.ed_orcamento = QtWidgets.QLineEdit()
        self.ed_orcamento.setPlaceholderText("Deixe vazio para regras padrao")
        target_layout.addWidget(self.ed_orcamento)

        target_layout.addWidget(QtWidgets.QLabel("Versao:"))
        self.ed_versao = QtWidgets.QLineEdit()
        self.ed_versao.setPlaceholderText("01")
        target_layout.addWidget(self.ed_versao)

        btn_load = QtWidgets.QPushButton("Carregar")
        btn_load.clicked.connect(self._on_load)
        target_layout.addWidget(btn_load)

        btn_reset = QtWidgets.QPushButton("Repor")
        btn_reset.clicked.connect(self._on_reset)
        target_layout.addWidget(btn_reset)

        target_layout.addStretch(1)
        layout.addLayout(target_layout)

        self.table = QtWidgets.QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        actions_layout = QtWidgets.QHBoxLayout()
        btn_add = QtWidgets.QPushButton("Adicionar Regra")
        btn_add.clicked.connect(self._on_add_rule)
        actions_layout.addWidget(btn_add)

        btn_remove = QtWidgets.QPushButton("Remover Selecionada")
        btn_remove.clicked.connect(self._on_remove_rule)
        actions_layout.addWidget(btn_remove)

        actions_layout.addStretch(1)

        btn_save = QtWidgets.QPushButton("Guardar")
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
            raise ValueError("Orcamento deve ser numerico.") from exc
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
        self.table.resizeColumnsToContents()

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
