from __future__ import annotations

from datetime import datetime

from PySide6 import QtCore, QtWidgets


class CutRiteProgressDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enviar CUT-RITE")
        self.setModal(False)
        self.resize(680, 420)

        layout = QtWidgets.QVBoxLayout(self)
        self._label = QtWidgets.QLabel(
            "Acompanhar os passos executados pelo Martelo para criar o plano no CUT-RITE."
        )
        self._label.setWordWrap(True)
        layout.addWidget(self._label)

        self._log = QtWidgets.QPlainTextEdit(self)
        self._log.setReadOnly(True)
        layout.addWidget(self._log, 1)

        self._close_button = QtWidgets.QPushButton("Fechar", self)
        self._close_button.setEnabled(False)
        self._close_button.clicked.connect(self.accept)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self._close_button)
        layout.addLayout(buttons)

    def add_step(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log.appendPlainText(f"[{timestamp}] {message}")
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents, 50)

    def finish(self, *, success: bool) -> None:
        self.add_step("Concluido." if success else "Interrompido com erro.")
        self._close_button.setEnabled(True)
