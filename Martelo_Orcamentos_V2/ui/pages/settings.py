from typing import Any, Dict, Optional
from PySide6 import QtCore, QtWidgets
from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.settings import get_setting, set_setting
from Martelo_Orcamentos_V2.app.services.materias_primas import KEY_MATERIAS_BASE_PATH, DEFAULT_MATERIAS_BASE_PATH
from Martelo_Orcamentos_V2.app.services import custeio_items as svc_custeio


KEY_BASE_PATH = "base_path_orcamentos"
DEFAULT_BASE_PATH = r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2"

AUTO_DIMS_HELP_TEXT = (
    "Quando ativo, o Martelo preenche automaticamente as colunas COMP e LARG "
    "para peças padrão (COSTA, PORTA ABRIR, LATERAL, DIVISORIA, TETO, FUNDO, "
    "PRATELEIRA AMOVIVEL, PRAT. AMOV., PRATELEIRA FIXA, PRAT.FIXA) usando as "
    "dimensões HM/LM/PM do item. Continua possível editar manualmente os valores."
)

class SettingsPage(QtWidgets.QWidget):
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self._current_user_id = getattr(current_user, "id", None) if current_user is not None else None
        self.db = SessionLocal()
        lay = QtWidgets.QFormLayout(self)
        self.ed_base = QtWidgets.QLineEdit()
        btn_base_browse = QtWidgets.QPushButton("Procurar…")
        btn_base_browse.clicked.connect(lambda: self._choose_directory(self.ed_base))
        h_base = QtWidgets.QHBoxLayout()
        h_base.addWidget(self.ed_base, 1)
        h_base.addWidget(btn_base_browse)
        lay.addRow("Pasta base dos Orçamentos", h_base)

        self.ed_materias = QtWidgets.QLineEdit()
        btn_mp_browse = QtWidgets.QPushButton("Procurar…")
        btn_mp_browse.clicked.connect(lambda: self._choose_directory(self.ed_materias))
        h_mp = QtWidgets.QHBoxLayout()
        h_mp.addWidget(self.ed_materias, 1)
        h_mp.addWidget(btn_mp_browse)
        lay.addRow("Pasta Matérias Primas", h_mp)

        btn_rules = QtWidgets.QPushButton("Configurar Regras de Quantidade")
        btn_rules.clicked.connect(self._open_rules_dialog)
        lay.addRow(btn_rules)

        self.btn_auto_dims = QtWidgets.QPushButton()
        self.btn_auto_dims.setCheckable(True)
        self.btn_auto_dims.toggled.connect(self._update_auto_dims_label)
        if self._current_user_id is None:
            self.btn_auto_dims.setEnabled(False)
            self.btn_auto_dims.setToolTip("Disponível apenas para utilizadores autenticados.")
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

        btn_save = QtWidgets.QPushButton("Gravar Configurações")
        btn_save.clicked.connect(self.on_save)
        lay.addRow(btn_save)
        # load
        self.ed_base.setText(get_setting(self.db, KEY_BASE_PATH, DEFAULT_BASE_PATH))
        self.ed_materias.setText(get_setting(self.db, KEY_MATERIAS_BASE_PATH, DEFAULT_MATERIAS_BASE_PATH))

    def _choose_directory(self, line_edit: QtWidgets.QLineEdit):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Escolher pasta")
        if d:
            line_edit.setText(d)

    def on_save(self):
        try:
            base_path = self.ed_base.text().strip() or DEFAULT_BASE_PATH
            materias_path = self.ed_materias.text().strip() or DEFAULT_MATERIAS_BASE_PATH
            set_setting(self.db, KEY_BASE_PATH, base_path)
            set_setting(self.db, KEY_MATERIAS_BASE_PATH, materias_path)
            if self._current_user_id is not None:
                svc_custeio.set_auto_dimension_enabled(self.db, self._current_user_id, self.btn_auto_dims.isChecked())
            self.db.commit()
            QtWidgets.QMessageBox.information(self, "OK", "Configurações gravadas.")
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar: {e}")

    def _open_rules_dialog(self):
        dlg = QtRulesDialog(self.db, self)
        dlg.exec()

    def _update_auto_dims_label(self, checked: bool) -> None:
        state = "ON" if checked else "OFF"
        self.btn_auto_dims.setText(f"Auto preenchimento: {state}")
        self.btn_auto_dims.setToolTip(
            f"{AUTO_DIMS_HELP_TEXT}\n\nEstado atual: {state}."
        )

    def _show_auto_dims_help(self) -> None:
        QtWidgets.QMessageBox.information(self, "Ajuda", AUTO_DIMS_HELP_TEXT, QtWidgets.QMessageBox.Ok)


class QtRulesDialog(QtWidgets.QDialog):
    HEADERS = ["Regra", "Matches", "Expressão", "Tooltip"]

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("Regras de Quantidade (Qt_und)")
        self.resize(820, 480)

        layout = QtWidgets.QVBoxLayout(self)

        target_layout = QtWidgets.QHBoxLayout()
        target_layout.addWidget(QtWidgets.QLabel("Orçamento ID:"))
        self.ed_orcamento = QtWidgets.QLineEdit()
        self.ed_orcamento.setPlaceholderText("Deixe vazio para regras padrão")
        target_layout.addWidget(self.ed_orcamento)

        target_layout.addWidget(QtWidgets.QLabel("Versão:"))
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


