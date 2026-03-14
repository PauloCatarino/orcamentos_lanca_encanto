from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.models import User
from Martelo_Orcamentos_V2.app.security import hash_password, verify_password


class CreateUserDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None, *, require_admin: bool = True) -> None:
        super().__init__(parent)
        self.setWindowIcon(QtWidgets.QApplication.windowIcon())
        self.setWindowTitle("Criar Utilizador - Martelo V2")

        self._require_admin = require_admin
        self._created_username: str | None = None
        self._created_password: str | None = None

        layout = QtWidgets.QFormLayout(self)
        tip_admin_required = (
            "Só é possível criar um novo utilizador após validar as credenciais do administrador 'admin'."
        )

        if self._require_admin:
            layout.addRow(QtWidgets.QLabel("Autorizacao (admin):"))
            self.ed_admin_user = QtWidgets.QLineEdit(self)
            self.ed_admin_pass = QtWidgets.QLineEdit(self)
            self.ed_admin_pass.setEchoMode(QtWidgets.QLineEdit.Password)
            self.ed_admin_user.setToolTip(tip_admin_required)
            layout.addRow("Utilizador admin", self.ed_admin_user)
            layout.addRow("Password admin", self.ed_admin_pass)
            layout.addRow(QtWidgets.QLabel("Novo utilizador:"))
        else:
            layout.addRow(QtWidgets.QLabel("Novo utilizador:"))

        self.ed_new_user = QtWidgets.QLineEdit(self)
        self.ed_new_pass = QtWidgets.QLineEdit(self)
        self.ed_new_pass.setEchoMode(QtWidgets.QLineEdit.Password)
        self.ed_new_pass2 = QtWidgets.QLineEdit(self)
        self.ed_new_pass2.setEchoMode(QtWidgets.QLineEdit.Password)
        self.ed_new_user.setToolTip(tip_admin_required)
        self.ed_new_email = QtWidgets.QLineEdit(self)
        self.ed_new_email.setPlaceholderText("ex.: orcamentos@lancaencanto.pt")
        self.ed_new_email.setToolTip(tip_admin_required)

        layout.addRow("Utilizador", self.ed_new_user)
        layout.addRow("Email (remetente)", self.ed_new_email)
        layout.addRow("Password", self.ed_new_pass)
        layout.addRow("Confirmar password", self.ed_new_pass2)

        self.chk_show = QtWidgets.QCheckBox("Mostrar passwords", self)
        self.chk_show.toggled.connect(self._toggle_show_passwords)
        layout.addRow("", self.chk_show)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.button(QtWidgets.QDialogButtonBox.Ok).setText("Criar")
        btns.accepted.connect(self._on_create)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def created_credentials(self) -> tuple[str, str] | None:
        if not self._created_username or not self._created_password:
            return None
        return (self._created_username, self._created_password)

    def _toggle_show_passwords(self, checked: bool) -> None:
        mode = QtWidgets.QLineEdit.Normal if checked else QtWidgets.QLineEdit.Password
        if self._require_admin:
            self.ed_admin_pass.setEchoMode(mode)
        self.ed_new_pass.setEchoMode(mode)
        self.ed_new_pass2.setEchoMode(mode)

    def _validate_admin(self, db) -> bool:
        if not self._require_admin:
            return True
        admin_username = self.ed_admin_user.text().strip()
        admin_password = self.ed_admin_pass.text()
        if not admin_username or not admin_password:
            QtWidgets.QMessageBox.warning(self, "Dados em falta", "Introduza utilizador e password de admin.")
            return False
        u = db.query(User).filter(User.username == admin_username, User.is_active == True).first()  # noqa: E712
        if not u or (u.role or "").lower() != "admin" or not verify_password(admin_password, u.pass_hash):
            QtWidgets.QMessageBox.critical(self, "Falha", "Credenciais de admin invalidas.")
            return False
        return True

    def _on_create(self) -> None:
        username = self.ed_new_user.text().strip()
        email = self.ed_new_email.text().strip().lower() or None
        password = self.ed_new_pass.text()
        password2 = self.ed_new_pass2.text()

        if not username or not password:
            QtWidgets.QMessageBox.warning(self, "Dados em falta", "Introduza utilizador e password.")
            return
        if len(username) > 64:
            QtWidgets.QMessageBox.warning(self, "Utilizador", "O nome de utilizador e demasiado longo (max. 64).")
            return
        if password != password2:
            QtWidgets.QMessageBox.warning(self, "Password", "As passwords nao coincidem.")
            return
        if len(password) < 4:
            QtWidgets.QMessageBox.warning(self, "Password", "A password deve ter pelo menos 4 caracteres.")
            return
        if email:
            if len(email) > 255:
                QtWidgets.QMessageBox.warning(self, "Email", "O email e demasiado longo (max. 255).")
                return
            if "@" not in email or email.startswith("@") or email.endswith("@"):
                QtWidgets.QMessageBox.warning(self, "Email", "Introduza um email valido (ex.: orcamentos@empresa.pt).")
                return
            _local, _domain = email.rsplit("@", 1)
            if not _local or not _domain or "." not in _domain:
                QtWidgets.QMessageBox.warning(self, "Email", "Introduza um email valido (ex.: orcamentos@empresa.pt).")
                return

        db = SessionLocal()
        try:
            if not self._validate_admin(db):
                return

            existing = db.query(User).filter(User.username == username).first()
            if existing:
                QtWidgets.QMessageBox.warning(self, "Utilizador", f"Ja existe um utilizador '{username}'.")
                return

            if email:
                email_owner = db.query(User).filter(User.email == email).first()
                if email_owner:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Email",
                        f"O email '{email}' ja esta associado ao utilizador '{email_owner.username}'.",
                    )
                    return

            u = User(
                username=username,
                email=email,
                pass_hash=hash_password(password),
                role="user",
                is_active=True,
            )
            db.add(u)
            db.commit()
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao criar utilizador: {exc}")
            return
        finally:
            db.close()

        self._created_username = username
        self._created_password = password
        QtWidgets.QMessageBox.information(self, "OK", f"Utilizador '{username}' criado com sucesso.")
        self.accept()


class ManageUsersDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowIcon(QtWidgets.QApplication.windowIcon())
        self.setWindowTitle("Gerir Utilizadores - Martelo V2")

        self._admin_validated = False
        self._user_cache: dict[int, dict[str, object]] = {}

        layout = QtWidgets.QVBoxLayout(self)

        self.grp_admin = QtWidgets.QGroupBox("Autorizacao (admin)", self)
        admin_form = QtWidgets.QFormLayout(self.grp_admin)
        self.ed_admin_user = QtWidgets.QLineEdit(self)
        self.ed_admin_pass = QtWidgets.QLineEdit(self)
        self.ed_admin_pass.setEchoMode(QtWidgets.QLineEdit.Password)
        admin_form.addRow("Utilizador admin", self.ed_admin_user)
        admin_form.addRow("Password admin", self.ed_admin_pass)

        self.btn_validate = QtWidgets.QPushButton("Validar", self)
        self.btn_validate.clicked.connect(self._on_validate_admin)
        admin_form.addRow("", self.btn_validate)
        layout.addWidget(self.grp_admin)

        self.grp_user = QtWidgets.QGroupBox("Utilizadores", self)
        user_form = QtWidgets.QFormLayout(self.grp_user)
        self.cmb_users = QtWidgets.QComboBox(self)
        self.cmb_users.currentIndexChanged.connect(self._on_user_changed)

        self.lbl_username = QtWidgets.QLabel("", self)
        self.lbl_role = QtWidgets.QLabel("", self)
        self.ed_email = QtWidgets.QLineEdit(self)
        self.ed_email.setPlaceholderText("ex.: orcamentos@lancaencanto.pt")
        self.chk_active = QtWidgets.QCheckBox("Ativo", self)

        self.ed_new_pass = QtWidgets.QLineEdit(self)
        self.ed_new_pass.setEchoMode(QtWidgets.QLineEdit.Password)
        self.ed_new_pass2 = QtWidgets.QLineEdit(self)
        self.ed_new_pass2.setEchoMode(QtWidgets.QLineEdit.Password)

        self.chk_show_passwords = QtWidgets.QCheckBox("Mostrar passwords", self)
        self.chk_show_passwords.toggled.connect(self._toggle_show_passwords)

        user_form.addRow("Selecionar utilizador", self.cmb_users)
        user_form.addRow("Utilizador", self.lbl_username)
        user_form.addRow("Role", self.lbl_role)
        user_form.addRow("Email (remetente)", self.ed_email)
        user_form.addRow("", self.chk_active)
        user_form.addRow("Nova password", self.ed_new_pass)
        user_form.addRow("Confirmar password", self.ed_new_pass2)
        user_form.addRow("", self.chk_show_passwords)

        layout.addWidget(self.grp_user)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_reload = QtWidgets.QPushButton("Recarregar", self)
        self.btn_reload.clicked.connect(self._reload_users)
        self.btn_save = QtWidgets.QPushButton("Guardar", self)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_close = QtWidgets.QPushButton("Fechar", self)
        self.btn_close.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_reload)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

        self.grp_user.setEnabled(False)
        self.btn_reload.setEnabled(False)
        self.btn_save.setEnabled(False)

    def _toggle_show_passwords(self, checked: bool) -> None:
        mode = QtWidgets.QLineEdit.Normal if checked else QtWidgets.QLineEdit.Password
        self.ed_admin_pass.setEchoMode(mode)
        self.ed_new_pass.setEchoMode(mode)
        self.ed_new_pass2.setEchoMode(mode)

    def _validate_admin(self, db) -> bool:
        admin_username = self.ed_admin_user.text().strip()
        admin_password = self.ed_admin_pass.text()
        if not admin_username or not admin_password:
            QtWidgets.QMessageBox.warning(self, "Dados em falta", "Introduza utilizador e password de admin.")
            return False
        u = db.query(User).filter(User.username == admin_username, User.is_active == True).first()  # noqa: E712
        if not u or (u.role or "").lower() != "admin" or not verify_password(admin_password, u.pass_hash):
            QtWidgets.QMessageBox.critical(self, "Falha", "Credenciais de admin invalidas.")
            return False
        return True

    def _on_validate_admin(self) -> None:
        db = SessionLocal()
        try:
            if not self._validate_admin(db):
                return
        finally:
            db.close()

        self._admin_validated = True
        self.ed_admin_user.setEnabled(False)
        self.ed_admin_pass.setEnabled(False)
        self.btn_validate.setEnabled(False)
        self.grp_user.setEnabled(True)
        self.btn_reload.setEnabled(True)
        self.btn_save.setEnabled(True)
        self._reload_users()

    def _reload_users(self) -> None:
        if not self._admin_validated:
            return
        current_id = self.cmb_users.currentData()

        db = SessionLocal()
        try:
            rows = (
                db.query(User.id, User.username, User.email, User.role, User.is_active)
                .order_by(User.username)
                .all()
            )
        finally:
            db.close()

        self._user_cache = {
            int(user_id): {
                "id": int(user_id),
                "username": username,
                "email": email,
                "role": role,
                "is_active": bool(is_active),
            }
            for user_id, username, email, role, is_active in rows
        }

        self.cmb_users.blockSignals(True)
        try:
            self.cmb_users.clear()
            for user_id, username, _email, _role, _is_active in rows:
                self.cmb_users.addItem(username, int(user_id))
        finally:
            self.cmb_users.blockSignals(False)

        if current_id is not None:
            idx = self.cmb_users.findData(current_id)
            if idx >= 0:
                self.cmb_users.setCurrentIndex(idx)

        self._on_user_changed()

    def _on_user_changed(self, _index: int = -1) -> None:
        user_id = self.cmb_users.currentData()
        data = self._user_cache.get(int(user_id)) if user_id is not None else None
        if not data:
            self.lbl_username.setText("")
            self.lbl_role.setText("")
            self.ed_email.setText("")
            self.chk_active.setChecked(True)
            self.ed_new_pass.setText("")
            self.ed_new_pass2.setText("")
            return

        self.lbl_username.setText(str(data.get("username") or ""))
        self.lbl_role.setText(str(data.get("role") or ""))
        self.ed_email.setText(str(data.get("email") or ""))
        self.chk_active.setChecked(bool(data.get("is_active", True)))
        self.ed_new_pass.setText("")
        self.ed_new_pass2.setText("")

    def _on_save(self) -> None:
        if not self._admin_validated:
            QtWidgets.QMessageBox.warning(self, "Permissao", "Valide as credenciais de admin primeiro.")
            return

        user_id = self.cmb_users.currentData()
        if user_id is None:
            QtWidgets.QMessageBox.warning(self, "Utilizador", "Selecione um utilizador.")
            return
        user_id = int(user_id)

        email = self.ed_email.text().strip().lower() or None
        is_active = bool(self.chk_active.isChecked())
        new_password = self.ed_new_pass.text()
        new_password2 = self.ed_new_pass2.text()

        if email:
            if len(email) > 255:
                QtWidgets.QMessageBox.warning(self, "Email", "O email e demasiado longo (max. 255).")
                return
            if "@" not in email or email.startswith("@") or email.endswith("@"):
                QtWidgets.QMessageBox.warning(self, "Email", "Introduza um email valido (ex.: orcamentos@empresa.pt).")
                return
            _local, _domain = email.rsplit("@", 1)
            if not _local or not _domain or "." not in _domain:
                QtWidgets.QMessageBox.warning(self, "Email", "Introduza um email valido (ex.: orcamentos@empresa.pt).")
                return

        if new_password or new_password2:
            if new_password != new_password2:
                QtWidgets.QMessageBox.warning(self, "Password", "As passwords nao coincidem.")
                return
            if len(new_password) < 4:
                QtWidgets.QMessageBox.warning(self, "Password", "A password deve ter pelo menos 4 caracteres.")
                return

        db = SessionLocal()
        try:
            user = db.get(User, user_id)
            if not user:
                QtWidgets.QMessageBox.warning(self, "Utilizador", "Utilizador nao encontrado.")
                return

            if email:
                email_owner = db.query(User).filter(User.email == email, User.id != user_id).first()
                if email_owner:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Email",
                        f"O email '{email}' ja esta associado ao utilizador '{email_owner.username}'.",
                    )
                    return

            if (user.role or "").lower() == "admin" and not is_active:
                active_admins = (
                    db.query(User)
                    .filter(User.is_active == True, User.role == "admin")  # noqa: E712
                    .count()
                )
                if active_admins <= 1 and user.is_active:
                    QtWidgets.QMessageBox.warning(self, "Admin", "Nao e possivel desativar o ultimo admin ativo.")
                    return

            user.email = email
            user.is_active = is_active
            if new_password:
                user.pass_hash = hash_password(new_password)

            db.commit()
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao guardar: {exc}")
            return
        finally:
            db.close()

        QtWidgets.QMessageBox.information(self, "OK", "Utilizador atualizado com sucesso.")
        self._reload_users()


class LoginDialog(QtWidgets.QDialog):
    def __init__(self, auto_user=None, auto_password=None, auto_submit=False):
        super().__init__()
        self.setWindowIcon(QtWidgets.QApplication.windowIcon())
        self.setWindowTitle("Entrar • Martelo V2")
        self.current_user = None
        layout = QtWidgets.QFormLayout(self)
        self.ed_user = QtWidgets.QLineEdit(self)
        self.ed_pass = QtWidgets.QLineEdit(self); self.ed_pass.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addRow("Utilizador", self.ed_user)
        layout.addRow("Palavra-passe", self.ed_pass)

        btn_create = QtWidgets.QPushButton("Criar utilizador...", self)
        btn_create.clicked.connect(self._open_create_user)
        layout.addRow("", btn_create)

        btn_manage = QtWidgets.QPushButton("Gerir utilizadores (admin)...", self)
        btn_manage.clicked.connect(self._open_manage_users)
        layout.addRow("", btn_manage)

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

    def _has_any_admin(self) -> bool:
        db = SessionLocal()
        try:
            users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
            return any((u.role or "").lower() == "admin" for u in users)
        except Exception:
            return True
        finally:
            db.close()

    def _open_create_user(self) -> None:
        require_admin = self._has_any_admin()
        dlg = CreateUserDialog(self, require_admin=require_admin)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        creds = dlg.created_credentials()
        if not creds:
            return
        username, password = creds
        self.ed_user.setText(username)
        self.ed_pass.setText(password)
        self.ed_pass.setFocus()

    def _open_manage_users(self) -> None:
        dlg = ManageUsersDialog(self)
        dlg.exec()

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
