from PySide6 import QtWidgets
from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.models import User
from Martelo_Orcamentos_V2.app.security import verify_password


class LoginDialog(QtWidgets.QDialog):
    def __init__(self):
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

