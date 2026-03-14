from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from Martelo_Orcamentos_V2.app.services import orcamento_tasks as svc_tasks
from Martelo_Orcamentos_V2.app.services import orcamentos_workflow as svc_orc_workflow


class OrcamentoTasksDialog(QtWidgets.QDialog):
    def __init__(self, *, db_session, orcamento_id: int, current_user=None, parent=None) -> None:
        super().__init__(parent)
        self._db = db_session
        self._orcamento_id = int(orcamento_id)
        self._current_user = current_user
        self._current_task_id: Optional[int] = None
        self._task_rows = []
        self._loading = False

        self.setWindowTitle("Tarefas do Orcamento")
        self.setWindowFlag(QtCore.Qt.WindowMinMaxButtonsHint, True)
        self.resize(980, 640)
        self.setMinimumSize(860, 560)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.lbl_context = QtWidgets.QLabel("")
        self.lbl_context.setWordWrap(True)
        self.lbl_context.setStyleSheet("font-size:14px; font-weight:700;")
        layout.addWidget(self.lbl_context)

        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Estado", "Prazo", "Utilizador", "Tarefa", "Atualizado"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_select_task)
        layout.addWidget(self.table, 1)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.ed_text = QtWidgets.QPlainTextEdit(self)
        self.ed_text.setPlaceholderText("Texto da tarefa")
        self.ed_text.setFixedHeight(90)
        self.cb_user = QtWidgets.QComboBox(self)
        self.ed_due = QtWidgets.QDateEdit(self)
        self.ed_due.setCalendarPopup(True)
        self.ed_due.setDate(QtCore.QDate.currentDate())
        self.cb_status = QtWidgets.QComboBox(self)
        self.cb_status.addItems(list(svc_tasks.TASK_STATUS_VALUES))
        form.addRow("Tarefa:", self.ed_text)
        form.addRow("Utilizador:", self.cb_user)
        form.addRow("Data limite:", self.ed_due)
        form.addRow("Estado:", self.cb_status)
        layout.addLayout(form)

        buttons = QtWidgets.QHBoxLayout()
        self.btn_new = QtWidgets.QPushButton("Nova")
        self.btn_save = QtWidgets.QPushButton("Guardar")
        self.btn_complete = QtWidgets.QPushButton("Concluir")
        self.btn_suspend = QtWidgets.QPushButton("Suspender")
        self.btn_reopen = QtWidgets.QPushButton("Reabrir")
        self.btn_delete = QtWidgets.QPushButton("Eliminar")
        self.btn_close = QtWidgets.QPushButton("Fechar")
        self.btn_new.clicked.connect(self._new_task)
        self.btn_save.clicked.connect(self._save_task)
        self.btn_complete.clicked.connect(lambda: self._set_status(svc_tasks.TASK_STATUS_COMPLETED))
        self.btn_suspend.clicked.connect(lambda: self._set_status(svc_tasks.TASK_STATUS_SUSPENDED))
        self.btn_reopen.clicked.connect(lambda: self._set_status(svc_tasks.TASK_STATUS_PENDING))
        self.btn_delete.clicked.connect(self._delete_task)
        self.btn_close.clicked.connect(self.accept)
        for btn in (
            self.btn_new,
            self.btn_save,
            self.btn_complete,
            self.btn_suspend,
            self.btn_reopen,
            self.btn_delete,
            self.btn_close,
        ):
            buttons.addWidget(btn)
        layout.addLayout(buttons)

        self._load_context()
        self._load_users()
        self._reload_tasks()
        self._new_task()

    def _current_user_id(self) -> Optional[int]:
        return getattr(self._current_user, "id", None)

    def _load_context(self) -> None:
        orcamento, client = svc_orc_workflow.load_orcamento_with_client(self._db, self._orcamento_id)
        if not orcamento:
            self.lbl_context.setText("Orcamento nao encontrado")
            return
        client_name = str(getattr(client, "nome", None) or "").strip() or "-"
        self.lbl_context.setText(
            f"Orcamento {getattr(orcamento, 'ano', '')}/{getattr(orcamento, 'num_orcamento', '')} v{getattr(orcamento, 'versao', '')} | Cliente: {client_name}"
        )

    def _load_users(self) -> None:
        current_user_id = self._current_user_id()
        self.cb_user.blockSignals(True)
        try:
            self.cb_user.clear()
            for choice in svc_tasks.list_active_user_choices(self._db):
                self.cb_user.addItem(choice.username, choice.id)
        finally:
            self.cb_user.blockSignals(False)
        if current_user_id is not None:
            idx = self.cb_user.findData(int(current_user_id))
            if idx >= 0:
                self.cb_user.setCurrentIndex(idx)

    def _reload_tasks(self, *, select_task_id: Optional[int] = None) -> None:
        self._loading = True
        try:
            self._task_rows = svc_tasks.list_orcamento_task_rows(self._db, orcamento_id=self._orcamento_id, include_closed=True)
            self.table.setRowCount(0)
            for row_idx, row in enumerate(self._task_rows):
                self.table.insertRow(row_idx)
                values = [
                    row.status,
                    row.due_date_text,
                    row.assigned_username or "-",
                    row.texto,
                    row.updated_at_text or row.created_at_text or "-",
                ]
                for col_idx, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(str(value or ""))
                    item.setData(QtCore.Qt.UserRole, row.id)
                    if col_idx == 0 and row.overdue:
                        item.setForeground(QtGui.QBrush(QtGui.QColor("#9a3412")))
                    self.table.setItem(row_idx, col_idx, item)
                self.table.setRowHeight(row_idx, 34)
            header = self.table.horizontalHeader()
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
            header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
            if self.table.rowCount() > 0:
                target_id = select_task_id if select_task_id is not None else self._task_rows[0].id
                self._select_task_by_id(target_id)
        finally:
            self._loading = False
        self._update_action_buttons()

    def _select_task_by_id(self, task_id: Optional[int]) -> None:
        if task_id is None:
            return
        for row_idx in range(self.table.rowCount()):
            item = self.table.item(row_idx, 0)
            if item is not None and item.data(QtCore.Qt.UserRole) == task_id:
                self.table.selectRow(row_idx)
                break

    def _current_task_row(self):
        row_idx = self.table.currentRow()
        if row_idx < 0 or row_idx >= len(self._task_rows):
            return None
        return self._task_rows[row_idx]

    def _fill_form_from_task(self, task_row) -> None:
        self._current_task_id = task_row.id
        self.ed_text.setPlainText(task_row.texto)
        idx = self.cb_user.findData(task_row.assigned_user_id)
        if idx >= 0:
            self.cb_user.setCurrentIndex(idx)
        self.ed_due.setDate(QtCore.QDate(task_row.due_date.year, task_row.due_date.month, task_row.due_date.day))
        self.cb_status.setCurrentText(task_row.status)

    def _new_task(self) -> None:
        self._current_task_id = None
        self.ed_text.clear()
        self.ed_due.setDate(QtCore.QDate.currentDate())
        self.cb_status.setCurrentText(svc_tasks.TASK_STATUS_PENDING)
        current_user_id = self._current_user_id()
        if current_user_id is not None:
            idx = self.cb_user.findData(int(current_user_id))
            if idx >= 0:
                self.cb_user.setCurrentIndex(idx)
        self.table.clearSelection()
        self._update_action_buttons()

    def _on_select_task(self) -> None:
        if self._loading:
            return
        task_row = self._current_task_row()
        if task_row is None:
            self._update_action_buttons()
            return
        self._fill_form_from_task(task_row)
        self._update_action_buttons()

    def _update_action_buttons(self) -> None:
        has_task = self._current_task_id is not None
        task_row = self._current_task_row()
        status = task_row.status if task_row is not None else ""
        self.btn_delete.setEnabled(has_task)
        self.btn_complete.setEnabled(has_task and status != svc_tasks.TASK_STATUS_COMPLETED)
        self.btn_suspend.setEnabled(has_task and status != svc_tasks.TASK_STATUS_SUSPENDED)
        self.btn_reopen.setEnabled(has_task and status != svc_tasks.TASK_STATUS_PENDING)

    def _save_task(self) -> None:
        try:
            if self._current_task_id is None:
                task = svc_tasks.create_orcamento_task(
                    self._db,
                    orcamento_id=self._orcamento_id,
                    texto=self.ed_text.toPlainText(),
                    assigned_user_id=self.cb_user.currentData(),
                    due_date=self.ed_due.date().toPython(),
                    created_by=self._current_user_id(),
                    status=self.cb_status.currentText(),
                )
            else:
                task = svc_tasks.update_orcamento_task(
                    self._db,
                    task_id=int(self._current_task_id),
                    texto=self.ed_text.toPlainText(),
                    assigned_user_id=self.cb_user.currentData(),
                    due_date=self.ed_due.date().toPython(),
                    status=self.cb_status.currentText(),
                    updated_by=self._current_user_id(),
                )
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            QtWidgets.QMessageBox.critical(self, "Tarefas", f"Falha ao guardar tarefa: {exc}")
            return
        self._reload_tasks(select_task_id=int(task.id))

    def _set_status(self, status: str) -> None:
        if self._current_task_id is None:
            QtWidgets.QMessageBox.information(self, "Tarefas", "Selecione uma tarefa.")
            return
        try:
            task = svc_tasks.set_orcamento_task_status(
                self._db,
                task_id=int(self._current_task_id),
                status=status,
                updated_by=self._current_user_id(),
            )
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            QtWidgets.QMessageBox.critical(self, "Tarefas", f"Falha ao atualizar tarefa: {exc}")
            return
        self._reload_tasks(select_task_id=int(task.id))

    def _delete_task(self) -> None:
        if self._current_task_id is None:
            QtWidgets.QMessageBox.information(self, "Tarefas", "Selecione uma tarefa.")
            return
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Eliminar tarefa",
            "Pretende eliminar a tarefa selecionada?",
        )
        if confirm != QtWidgets.QMessageBox.Yes:
            return
        try:
            svc_tasks.delete_orcamento_task(self._db, task_id=int(self._current_task_id))
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            QtWidgets.QMessageBox.critical(self, "Tarefas", f"Falha ao eliminar tarefa: {exc}")
            return
        self._reload_tasks()
        self._new_task()
