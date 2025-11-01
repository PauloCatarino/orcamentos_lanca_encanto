from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from PySide6 import QtCore, QtWidgets

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.settings import get_setting, set_setting
from Martelo_Orcamentos_V2.app.services.materias_primas import (
    DEFAULT_MATERIAS_BASE_PATH,
    KEY_MATERIAS_BASE_PATH,
)
from Martelo_Orcamentos_V2.app.services import custeio_items as svc_custeio
from Martelo_Orcamentos_V2.app.services import producao as svc_producao


KEY_BASE_PATH = "base_path_orcamentos"
DEFAULT_BASE_PATH = r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2"

AUTO_DIMS_HELP_TEXT = (
    "Quando ativo, o Martelo preenche automaticamente as colunas COMP e LARG "
    "para pecas padrao (COSTA, PORTA ABRIR, LATERAL, DIVISORIA, TETO, FUNDO, "
    "PRATELEIRA AMOVIVEL, PRAT. AMOV., PRATELEIRA FIXA, PRAT.FIXA) usando as "
    "dimensoes HM/LM/PM do item. Continua possivel editar manualmente os valores."
)


class SettingsPage(QtWidgets.QWidget):
    PRODUCAO_HEADERS = [
        "Descricao Equipamento",
        "Abreviatura",
        "Valor Producao STD",
        "Valor Producao Serie",
        "Resumo da Descricao",
    ]

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

        main_layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tabs)

        self._init_general_tab()
        self._init_producao_tab()

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

        auto_layout = QtWidgets.QHBoxLayout()
        auto_layout.addWidget(self.btn_auto_dims)
        auto_layout.addWidget(self.btn_auto_dims_help)
        auto_layout.addStretch(1)
        lay.addRow("Preencher COMP/LARG automaticamente", auto_layout)

        btn_save = QtWidgets.QPushButton("Gravar Configuracoes")
        btn_save.clicked.connect(self.on_save)
        lay.addRow(btn_save)

        self.tabs.addTab(tab, "Geral")

        # load defaults
        self.ed_base.setText(get_setting(self.db, KEY_BASE_PATH, DEFAULT_BASE_PATH))
        self.ed_materias.setText(get_setting(self.db, KEY_MATERIAS_BASE_PATH, DEFAULT_MATERIAS_BASE_PATH))

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

    def _show_auto_dims_help(self) -> None:
        QtWidgets.QMessageBox.information(self, "Ajuda", AUTO_DIMS_HELP_TEXT, QtWidgets.QMessageBox.Ok)

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

    def _on_tab_changed(self, index: int) -> None:
        if getattr(self, "tab_producao", None) is None:
            return
        widget = self.tabs.widget(index)
        if widget is self.tab_producao and self._producao_ctx and self._producao_dirty:
            self._load_producao_table()

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
            f"Ano {ctx.ano} | Nº Orçamento {ctx.num_orcamento} | Versão {ctx.versao} | Modo atual: {self._producao_mode}"
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
