from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from Martelo_Orcamentos_V2.app.services import orcamento_lembretes as svc_lembretes
from Martelo_Orcamentos_V2.app.services import orcamento_tasks as svc_tasks
from Martelo_Orcamentos_V2.app.services.orcamento_lembretes import DailyReminderSummary, OrcamentoReminder


def _clip_text(text: str, limit: int = 120) -> str:
    raw = " ".join(str(text or "").split())
    if len(raw) <= limit:
        return raw
    return raw[: limit - 3].rstrip() + "..."


class DailyOrcamentoReminderDialog(QtWidgets.QDialog):
    def __init__(
        self,
        summary: DailyReminderSummary,
        *,
        db_session,
        user_id: int,
        username: str,
        parent: QtWidgets.QWidget | None = None,
        auto_mode: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setWindowTitle("Resumo Diario de Orcamentos")
        self.setWindowFlag(QtCore.Qt.WindowMinMaxButtonsHint, True)
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, True)
        self.resize(1600, 900)
        self.setMinimumSize(1220, 700)

        self._db = db_session
        self._user_id = int(user_id)
        self._username = str(username or "")
        self._summary = summary
        self._auto_mode = bool(auto_mode)
        self._selected_orcamento_id: int | None = None
        self._open_items = False
        self._updating_table = False
        self._table_items: list[OrcamentoReminder] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Resumo diario personalizado")
        title.setStyleSheet("font-size:16px; font-weight:700;")
        layout.addWidget(title)

        controls_row = QtWidgets.QHBoxLayout()
        self.lbl_subtitle = QtWidgets.QLabel("")
        self.lbl_subtitle.setWordWrap(True)
        self.lbl_subtitle.setStyleSheet("color:#444;")
        controls_row.addWidget(self.lbl_subtitle, 1)

        self.chk_show_hidden = QtWidgets.QCheckBox("Mostrar ocultados")
        self.chk_show_hidden.setToolTip(
            "Mostra linhas legacy ocultadas pelo utilizador.\n"
            "As tarefas formais devem ser concluidas ou suspensas."
        )
        self.chk_show_hidden.toggled.connect(self._reload_summary)
        controls_row.addWidget(self.chk_show_hidden, 0)
        layout.addLayout(controls_row)

        hint = QtWidgets.QLabel(
            "O resumo mostra primeiro tarefas formais por orcamento. "
            "Quando ainda nao existem tarefas formais, continua a usar Info 1, Info 2 e Notas como fallback."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#666;")
        layout.addWidget(hint)

        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(
            [
                "Acao",
                "Tipo",
                "Prioridade",
                "N Orc",
                "Cliente",
                "Ref.Cliente",
                "Estado",
                "Data Orc",
                "Prazo",
                "Descricao",
                "Lembrete",
            ]
        )
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(QtCore.Qt.ElideRight)
        self.table.setStyleSheet("QTableWidget::item{padding:4px 6px;}")
        self.table.itemDoubleClicked.connect(lambda *_: self._accept_current(open_items=False))
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.itemSelectionChanged.connect(self._apply_empty_state)
        layout.addWidget(self.table, 1)

        empty_message = QtWidgets.QLabel(
            "Nao foram encontrados lembretes relevantes para este utilizador."
        )
        empty_message.setStyleSheet("font-weight:600; color:#555;")
        empty_message.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(empty_message)
        self._empty_message = empty_message

        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)
        self.btn_complete_task = QtWidgets.QPushButton("Concluir Tarefa")
        self.btn_suspend_task = QtWidgets.QPushButton("Suspender Tarefa")
        self.btn_open_orc = QtWidgets.QPushButton("Abrir Orcamento")
        self.btn_open_items = QtWidgets.QPushButton("Abrir Itens")
        self.btn_close = QtWidgets.QPushButton("Fechar")
        self.btn_complete_task.clicked.connect(lambda: self._set_current_task_status(svc_tasks.TASK_STATUS_COMPLETED))
        self.btn_suspend_task.clicked.connect(lambda: self._set_current_task_status(svc_tasks.TASK_STATUS_SUSPENDED))
        self.btn_open_orc.clicked.connect(lambda: self._accept_current(open_items=False))
        self.btn_open_items.clicked.connect(lambda: self._accept_current(open_items=True))
        self.btn_close.clicked.connect(self.reject)
        button_row.addWidget(self.btn_complete_task)
        button_row.addWidget(self.btn_suspend_task)
        button_row.addWidget(self.btn_open_orc)
        button_row.addWidget(self.btn_open_items)
        button_row.addWidget(self.btn_close)
        layout.addLayout(button_row)

        self._apply_summary(summary)

    def _apply_empty_state(self) -> None:
        has_rows = self.table.rowCount() > 0
        self.table.setVisible(has_rows)
        self._empty_message.setVisible(not has_rows)
        self.btn_open_orc.setEnabled(has_rows)
        self.btn_open_items.setEnabled(has_rows)
        reminder = self._current_reminder()
        is_task = bool(reminder and reminder.entry_kind == "task")
        self.btn_complete_task.setEnabled(is_task)
        self.btn_suspend_task.setEnabled(is_task)

    def _refresh_subtitle(self) -> None:
        summary = self._summary
        parts = [
            f"Utilizador: {summary.username or '-'}",
            f"Data: {summary.today.isoformat()}",
            f"Orcamentos: {summary.total_orcamentos}",
            f"Tarefas: {summary.task_count}",
            f"Apontamentos legacy: {summary.legacy_count}",
            f"Lembretes acionaveis: {summary.actionable_count}",
        ]
        if summary.hidden_count:
            parts.append(f"Ocultados: {summary.hidden_count}")
        self.lbl_subtitle.setText(" | ".join(parts))

    def _row_color(self, reminder: OrcamentoReminder) -> QtGui.QColor:
        if reminder.hidden:
            return QtGui.QColor("#e5e7eb")
        if reminder.priority_rank >= 3:
            return QtGui.QColor("#f8d7da")
        if reminder.priority_rank == 2:
            return QtGui.QColor("#fff3cd")
        if reminder.priority_rank == 1:
            return QtGui.QColor("#dbeafe")
        return QtGui.QColor("#f3f4f6")

    def _priority_tooltip(self, reminder: OrcamentoReminder) -> str:
        parts = [f"Prioridade: {reminder.priority_label}"]
        parts.append("Origem: Tarefa formal" if reminder.entry_kind == "task" else "Origem: Apontamento legacy")
        if reminder.hidden:
            parts.append("Estado: ocultado pelo utilizador")
        if reminder.task_due_date:
            parts.append("Prazo: " + reminder.task_due_date.strftime("%d-%m-%Y"))
        if reminder.matched_keywords:
            parts.append("Palavras-chave: " + ", ".join(reminder.matched_keywords))
        if reminder.mentioned_dates:
            parts.append(
                "Datas detetadas: " + ", ".join(dt.strftime("%d-%m-%Y") for dt in reminder.mentioned_dates)
            )
        if reminder.source_fields:
            parts.append("Campos: " + ", ".join(reminder.source_fields))
        return "\n".join(parts)

    def _reload_summary(self) -> None:
        try:
            summary = svc_lembretes.build_daily_summary(
                self._db,
                user_id=self._user_id,
                username=self._username,
                include_hidden=self.chk_show_hidden.isChecked(),
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Resumo Diario", f"Falha ao atualizar o resumo: {exc}")
            return
        self._apply_summary(summary)

    def _apply_summary(self, summary: DailyReminderSummary) -> None:
        self._summary = summary
        self._refresh_subtitle()
        self._populate_table(summary.items)
        self._apply_empty_state()

    def _set_action_item(self, row_idx: int, reminder: OrcamentoReminder, bg: QtGui.QColor) -> None:
        item = QtWidgets.QTableWidgetItem()
        if reminder.entry_kind == "task":
            item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            item.setText("-")
            item.setToolTip("Para tarefas formais use os botoes 'Concluir Tarefa' ou 'Suspender Tarefa'.")
        else:
            item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked if reminder.hidden else QtCore.Qt.Unchecked)
            item.setToolTip(
                "Marque para ocultar esta linha nas notificacoes futuras.\n"
                "Use 'Mostrar ocultados' para rever ou reativar linhas ocultas."
            )
        item.setBackground(bg)
        item.setData(QtCore.Qt.UserRole, reminder.orcamento_id)
        item.setData(QtCore.Qt.UserRole + 1, reminder.task_id)
        self.table.setItem(row_idx, 0, item)

    def _populate_table(self, rows: list[OrcamentoReminder]) -> None:
        self._updating_table = True
        try:
            self._table_items = list(rows)
            self.table.setRowCount(0)
            for row_idx, reminder in enumerate(rows):
                self.table.insertRow(row_idx)
                bg = self._row_color(reminder)
                prazo = reminder.task_due_date.strftime("%d-%m-%Y") if reminder.task_due_date else (
                    reminder.latest_note_date.strftime("%d-%m-%Y") if reminder.latest_note_date else ""
                )
                number_label = f"{reminder.ano}/{reminder.num_orcamento} v{reminder.versao}"
                reminder_text = reminder.details_text or "-"
                description_text = reminder.descricao or "(sem descricao)"
                kind_label = "Tarefa" if reminder.entry_kind == "task" else "Apontamento"
                status_label = reminder.task_status or reminder.estado or "-"

                self._set_action_item(row_idx, reminder, bg)

                values = [
                    kind_label,
                    reminder.priority_label,
                    number_label,
                    reminder.cliente or "-",
                    reminder.ref_cliente or "-",
                    status_label,
                    reminder.data_orcamento or "-",
                    prazo or "-",
                    _clip_text(description_text, 110),
                    _clip_text(reminder_text, 160),
                ]

                for col_idx, value in enumerate(values, start=1):
                    item = QtWidgets.QTableWidgetItem(value)
                    item.setBackground(bg)
                    item.setData(QtCore.Qt.UserRole, reminder.orcamento_id)
                    item.setData(QtCore.Qt.UserRole + 1, reminder.task_id)
                    if col_idx == 1:
                        item.setToolTip(kind_label)
                    elif col_idx == 2:
                        item.setToolTip(self._priority_tooltip(reminder))
                        if reminder.priority_rank >= 3:
                            item.setForeground(QtGui.QBrush(QtGui.QColor("#7f1d1d")))
                        elif reminder.hidden:
                            item.setForeground(QtGui.QBrush(QtGui.QColor("#374151")))
                    elif col_idx == 9:
                        item.setToolTip(description_text)
                    elif col_idx == 10:
                        item.setToolTip(reminder_text)
                    elif col_idx == 8 and prazo:
                        flags = []
                        if reminder.overdue:
                            flags.append("atrasada")
                        if reminder.today_match:
                            flags.append("hoje")
                        if flags:
                            item.setToolTip("Prazo " + ", ".join(flags))
                            item.setForeground(QtGui.QBrush(QtGui.QColor("#9a3412")))
                    self.table.setItem(row_idx, col_idx, item)
                    if reminder.hidden and col_idx > 1:
                        item.setForeground(QtGui.QBrush(QtGui.QColor("#4b5563")))

                self.table.setRowHeight(row_idx, 42)

            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(7, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(8, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(9, QtWidgets.QHeaderView.Stretch)
            header.setSectionResizeMode(10, QtWidgets.QHeaderView.Stretch)
            if self.table.rowCount() > 0:
                self.table.selectRow(0)
        finally:
            self._updating_table = False

    def _on_item_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if self._updating_table or item.column() != 0:
            return
        orcamento_id = item.data(QtCore.Qt.UserRole)
        task_id = item.data(QtCore.Qt.UserRole + 1)
        if task_id is not None or orcamento_id is None:
            return
        hidden = item.checkState() == QtCore.Qt.Checked
        try:
            svc_lembretes.set_orcamento_hidden(
                self._db,
                user_id=self._user_id,
                orcamento_id=int(orcamento_id),
                hidden=hidden,
            )
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            QtWidgets.QMessageBox.critical(self, "Resumo Diario", f"Falha ao atualizar o estado da linha: {exc}")
            self._reload_summary()
            return
        self._reload_summary()

    def _current_reminder(self) -> OrcamentoReminder | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._table_items):
            return None
        return self._table_items[row]

    def _set_current_task_status(self, status: str) -> None:
        reminder = self._current_reminder()
        if reminder is None or reminder.entry_kind != "task" or reminder.task_id is None:
            QtWidgets.QMessageBox.information(self, "Resumo Diario", "Selecione uma tarefa formal na lista.")
            return
        try:
            svc_tasks.set_orcamento_task_status(
                self._db,
                task_id=int(reminder.task_id),
                status=status,
                updated_by=self._user_id,
            )
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            QtWidgets.QMessageBox.critical(self, "Resumo Diario", f"Falha ao atualizar a tarefa: {exc}")
            return
        self._reload_summary()

    def _current_orcamento_id(self) -> int | None:
        reminder = self._current_reminder()
        return reminder.orcamento_id if reminder is not None else None

    def _accept_current(self, *, open_items: bool) -> None:
        selected_id = self._current_orcamento_id()
        if selected_id is None:
            QtWidgets.QMessageBox.information(self, "Resumo Diario", "Selecione um orcamento na lista.")
            return
        self._selected_orcamento_id = selected_id
        self._open_items = bool(open_items)
        self.accept()

    def selected_action(self) -> tuple[int | None, bool]:
        return self._selected_orcamento_id, self._open_items
