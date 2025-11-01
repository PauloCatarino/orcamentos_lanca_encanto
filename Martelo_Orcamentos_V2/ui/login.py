from PySide6 import QtCore, QtWidgets
from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.models import User
from Martelo_Orcamentos_V2.app.security import verify_password


class LoginDialog(QtWidgets.QDialog):
    def __init__(self, auto_user=None, auto_password=None, auto_submit=False):
        super().__init__()
        self.setWindowTitle("Entrar • Martelo V2")
        self.current_user = None
        layout = QtWidgets.QFormLayout(self)
        self.ed_user = QtWidgets.QLineEdit(self)
        self.ed_pass = QtWidgets.QLineEdit(self); self.ed_pass.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addRow("Utilizador", self.ed_user)
        layout.addRow("Palavra‑passe", self.ed_pass)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.try_login)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)
        if auto_user is not None:
            self.ed_user.setText(auto_user)
        if auto_password is not None:
            self.ed_pass.setText(auto_password)
        if auto_submit and auto_user and auto_password:
            QtCore.QTimer.singleShot(0, self.try_login)

    def try_login(self):
        username = self.ed_user.text().strip()
        password = self.ed_pass.text()
        if not username or not password:
            QtWidgets.QMessageBox.warning(self, "Dados em falta", "Introduza utilizador e palavra‑passe.")
            return
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.username == username, User.is_active == True).first()  # noqa: E712
            if not u or not verify_password(password, u.pass_hash):
                QtWidgets.QMessageBox.critical(self, "Falha", "Credenciais inválidas.")
                return
            self.current_user = u
            self.accept()
        finally:
            db.close()

