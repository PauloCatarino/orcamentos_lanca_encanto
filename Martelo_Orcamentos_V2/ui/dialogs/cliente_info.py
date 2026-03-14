from __future__ import annotations

from PySide6 import QtWidgets
from PySide6.QtCore import Qt


class ClienteInfoDialog(QtWidgets.QDialog):
    def __init__(self, *, parent=None, origem: str, data: dict):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle("Dados do Cliente")
        self.resize(640, 520)

        layout = QtWidgets.QVBoxLayout(self)
        lbl_origem = QtWidgets.QLabel(f"Origem: {origem}")
        lbl_origem.setStyleSheet("font-weight:bold; color:#444;")
        layout.addWidget(lbl_origem)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        def _ro_line(value: str) -> QtWidgets.QLineEdit:
            w = QtWidgets.QLineEdit()
            w.setReadOnly(True)
            w.setText(value or "")
            return w

        def _ro_text(value: str) -> QtWidgets.QTextEdit:
            w = QtWidgets.QTextEdit()
            w.setReadOnly(True)
            w.setFixedHeight(60)
            w.setPlainText(value or "")
            return w

        form.addRow("Nome Cliente:", _ro_line(str(data.get("nome") or "")))
        form.addRow("Nome Cliente Simplex:", _ro_line(str(data.get("nome_simplex") or "")))
        form.addRow("Num Cliente PHC:", _ro_line(str(data.get("num_cliente_phc") or "")))
        form.addRow("Telefone:", _ro_line(str(data.get("telefone") or "")))
        form.addRow("Telemovel:", _ro_line(str(data.get("telemovel") or "")))
        form.addRow("E-Mail:", _ro_line(str(data.get("email") or "")))
        form.addRow("Pagina WEB:", _ro_line(str(data.get("web_page") or "")))
        form.addRow("Morada:", _ro_text(str(data.get("morada") or "")))
        form.addRow("Info 1:", _ro_text(str(data.get("info_1") or "")))
        form.addRow("Info 2:", _ro_text(str(data.get("info_2") or "")))
        form.addRow("Notas:", _ro_text(str(data.get("notas") or "")))
        layout.addLayout(form)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
