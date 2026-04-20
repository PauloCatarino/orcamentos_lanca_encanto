from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from Martelo_Orcamentos_V2.app.services import producao_workflow as svc_producao_workflow
from Martelo_Orcamentos_V2.app.services.producao_workflow import PHCStatusSyncIssue, PHCStatusUserIssueSummary


def _clip_text(text: str, limit: int = 140) -> str:
    raw = " ".join(str(text or "").split())
    if len(raw) <= limit:
        return raw
    return raw[: limit - 3].rstrip() + "..."


def _format_values(values: tuple[str, ...], *, limit: int = 3) -> str:
    picked = [str(value or "").strip() for value in values if str(value or "").strip()]
    if not picked:
        return "(sem linhas)"
    if len(picked) <= limit:
        return ", ".join(picked)
    return ", ".join(picked[:limit]) + ", ..."


def _matches_martelo_value(martelo_value: str, phc_values: tuple[str, ...], *, numeric: bool = False) -> bool:
    martelo_text = str(martelo_value or "").strip()
    if not martelo_text:
        return False
    if numeric:
        martelo_key = svc_producao_workflow._normalize_match_number(martelo_text)
        return any(
            svc_producao_workflow._normalize_match_number(value) == martelo_key
            for value in phc_values
            if str(value or "").strip()
        )
    martelo_key = svc_producao_workflow._normalize_match_text(martelo_text)
    return any(
        svc_producao_workflow._normalize_match_text(value) == martelo_key
        for value in phc_values
        if str(value or "").strip()
    )


def _comparison_text(martelo_value: str, phc_values: tuple[str, ...]) -> str:
    martelo_text = str(martelo_value or "").strip() or "(vazio)"
    phc_text = _format_values(phc_values)
    return f"Martelo: {martelo_text}\nPHC: {phc_text}"


class ProducaoPHCIssuesDialog(QtWidgets.QDialog):
    def __init__(
        self,
        summary: PHCStatusUserIssueSummary,
        *,
        db_session,
        user_id: int,
        username: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setWindowTitle("Diferencas Martelo vs PHC")
        self.setWindowFlag(QtCore.Qt.WindowMinMaxButtonsHint, True)
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, True)
        self.resize(1520, 860)
        self.setMinimumSize(1180, 680)

        self._db = db_session
        self._user_id = int(user_id)
        self._username = str(username or "").strip()
        self._summary = summary
        self._selected_processo_id: int | None = None
        self._updating_table = False
        self._table_items = list(summary.items)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Diferencas Martelo vs PHC")
        title.setStyleSheet("font-size:16px; font-weight:700;")
        layout.addWidget(title)

        controls_row = QtWidgets.QHBoxLayout()
        self.lbl_subtitle = QtWidgets.QLabel("")
        self.lbl_subtitle.setWordWrap(True)
        self.lbl_subtitle.setStyleSheet("color:#444;")
        controls_row.addWidget(self.lbl_subtitle, 1)

        self.chk_show_hidden = QtWidgets.QCheckBox("Mostrar silenciadas")
        self.chk_show_hidden.setToolTip(
            "Mostra linhas que este utilizador decidiu silenciar.\n"
            "Desmarque a caixa da linha para a reativar."
        )
        self.chk_show_hidden.toggled.connect(self._reload_summary)
        controls_row.addWidget(self.chk_show_hidden, 0)
        layout.addLayout(controls_row)

        hint = QtWidgets.QLabel(
            "Cada linha mostra a comparacao direta entre Martelo e PHC. "
            "Marque a coluna 'Silenciar' para esconder esse aviso em futuras notificacoes deste utilizador."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#666;")
        layout.addWidget(hint)

        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            [
                "Silenciar",
                "Obra",
                "Ano",
                "Num Enc PHC",
                "Num Cliente PHC",
                "Nome Cliente",
                "Estado PHC",
                "Motivo",
            ]
        )
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(56)
        self.table.setWordWrap(True)
        self.table.setStyleSheet("QTableWidget::item{padding:4px 6px;}")
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.itemDoubleClicked.connect(lambda *_: self._accept_current())
        self.table.itemSelectionChanged.connect(self._apply_empty_state)
        layout.addWidget(self.table, 1)

        self._empty_message = QtWidgets.QLabel("Nao existem divergencias visiveis para este utilizador.")
        self._empty_message.setAlignment(QtCore.Qt.AlignCenter)
        self._empty_message.setStyleSheet("font-weight:600; color:#555;")
        layout.addWidget(self._empty_message)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)
        self.btn_open = QtWidgets.QPushButton("Abrir Processo")
        self.btn_close = QtWidgets.QPushButton("Fechar")
        self.btn_open.clicked.connect(self._accept_current)
        self.btn_close.clicked.connect(self.reject)
        button_row.addWidget(self.btn_open)
        button_row.addWidget(self.btn_close)
        layout.addLayout(button_row)

        self._apply_summary(summary)

    def selected_processo_id(self) -> int | None:
        return self._selected_processo_id

    def _refresh_subtitle(self) -> None:
        parts = [
            f"Utilizador: {self._summary.username or '-'}",
            f"Data: {self._summary.today.isoformat()}",
            f"Divergencias: {self._summary.total_count}",
        ]
        if self._summary.hidden_count:
            parts.append(f"Silenciadas: {self._summary.hidden_count}")
        self.lbl_subtitle.setText(" | ".join(parts))

    def _apply_empty_state(self) -> None:
        has_rows = self.table.rowCount() > 0
        self.table.setVisible(has_rows)
        self._empty_message.setVisible(not has_rows)
        self.btn_open.setEnabled(has_rows)

    def _reload_summary(self) -> None:
        try:
            summary = svc_producao_workflow.build_user_phc_status_issue_summary(
                self._db,
                user_id=self._user_id,
                username=self._username,
                today=self._summary.today,
                include_hidden=self.chk_show_hidden.isChecked(),
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Diferencas Martelo vs PHC", f"Falha ao atualizar a lista: {exc}")
            return
        self._apply_summary(summary)

    def _apply_summary(self, summary: PHCStatusUserIssueSummary) -> None:
        self._summary = summary
        self._refresh_subtitle()
        self._populate_table(summary.items)
        self._apply_empty_state()

    def _row_background(self, hidden: bool) -> QtGui.QColor:
        if hidden:
            return QtGui.QColor("#e5e7eb")
        return QtGui.QColor("#fef2f2")

    def _comparison_background(self, is_match: bool, hidden: bool) -> QtGui.QColor:
        if hidden:
            return QtGui.QColor("#f3f4f6")
        if is_match:
            return QtGui.QColor("#ecfdf5")
        return QtGui.QColor("#fef2f2")

    def _set_action_item(self, row_idx: int, issue: PHCStatusSyncIssue, hidden: bool, bg: QtGui.QColor) -> None:
        item = QtWidgets.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable)
        item.setCheckState(QtCore.Qt.Checked if hidden else QtCore.Qt.Unchecked)
        item.setToolTip(
            "Marque para silenciar este processo nas notificacoes futuras deste utilizador.\n"
            "Use 'Mostrar silenciadas' para rever ou reativar linhas silenciadas."
        )
        item.setBackground(bg)
        item.setData(QtCore.Qt.UserRole, issue.processo_id)
        self.table.setItem(row_idx, 0, item)

    def _set_text_item(
        self,
        row_idx: int,
        col_idx: int,
        text: str,
        *,
        tooltip: str | None = None,
        bg: QtGui.QColor | None = None,
        processo_id: int,
    ) -> None:
        item = QtWidgets.QTableWidgetItem(text)
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        item.setData(QtCore.Qt.UserRole, processo_id)
        if tooltip:
            item.setToolTip(tooltip)
        if bg is not None:
            item.setBackground(bg)
        self.table.setItem(row_idx, col_idx, item)

    def _populate_table(self, rows) -> None:
        self._updating_table = True
        try:
            self._table_items = list(rows)
            self.table.setRowCount(0)
            for row_idx, entry in enumerate(rows):
                issue = entry.issue
                hidden = bool(entry.hidden)
                self.table.insertRow(row_idx)
                row_bg = self._row_background(hidden)

                self._set_action_item(row_idx, issue, hidden, row_bg)
                self._set_text_item(
                    row_idx,
                    1,
                    issue.codigo_processo or "-",
                    tooltip=f"Responsavel: {issue.responsavel or '-'}",
                    bg=row_bg,
                    processo_id=issue.processo_id,
                )

                comparisons = [
                    (2, issue.martelo_ano, issue.phc_anos, False),
                    (3, issue.martelo_num_enc_phc, issue.phc_num_encs, True),
                    (4, issue.martelo_num_cliente_phc, issue.phc_num_clientes, True),
                    (5, issue.martelo_nome_cliente, issue.phc_nomes, False),
                ]
                for col_idx, martelo_value, phc_values, numeric in comparisons:
                    matches = _matches_martelo_value(martelo_value, phc_values, numeric=numeric)
                    text = _comparison_text(martelo_value, phc_values)
                    tooltip = text.replace("\n", "\n")
                    self._set_text_item(
                        row_idx,
                        col_idx,
                        text,
                        tooltip=tooltip,
                        bg=self._comparison_background(matches, hidden),
                        processo_id=issue.processo_id,
                    )

                estado_text = _format_values(issue.phc_estados)
                self._set_text_item(
                    row_idx,
                    6,
                    estado_text,
                    tooltip=estado_text,
                    bg=row_bg,
                    processo_id=issue.processo_id,
                )
                self._set_text_item(
                    row_idx,
                    7,
                    _clip_text(issue.reason, 140),
                    tooltip=issue.reason or "-",
                    bg=row_bg,
                    processo_id=issue.processo_id,
                )

                self.table.setRowHeight(row_idx, 64)

            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(5, QtWidgets.QHeaderView.Stretch)
            header.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(7, QtWidgets.QHeaderView.Stretch)
            if self.table.rowCount() > 0:
                self.table.selectRow(0)
        finally:
            self._updating_table = False

    def _on_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if self._updating_table or item.column() != 0:
            return
        processo_id = item.data(QtCore.Qt.UserRole)
        if processo_id is None:
            return
        hidden = item.checkState() == QtCore.Qt.Checked
        try:
            svc_producao_workflow.set_producao_phc_issue_hidden(
                self._db,
                user_id=self._user_id,
                processo_id=int(processo_id),
                hidden=hidden,
            )
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            QtWidgets.QMessageBox.critical(self, "Diferencas Martelo vs PHC", f"Falha ao atualizar a linha: {exc}")
            self._reload_summary()
            return
        self._reload_summary()

    def _current_issue(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._table_items):
            return None
        return self._table_items[row]

    def _accept_current(self) -> None:
        entry = self._current_issue()
        if entry is None:
            QtWidgets.QMessageBox.information(self, "Diferencas Martelo vs PHC", "Selecione um processo na lista.")
            return
        self._selected_processo_id = int(entry.issue.processo_id)
        self.accept()
