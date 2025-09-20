from PySide6 import QtWidgets
from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.settings import get_setting, set_setting


KEY_BASE_PATH = "base_path_orcamentos"
DEFAULT_BASE_PATH = r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2"


class SettingsPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = SessionLocal()
        lay = QtWidgets.QFormLayout(self)
        self.ed_base = QtWidgets.QLineEdit()
        btn_browse = QtWidgets.QPushButton("Procurar…")
        btn_browse.clicked.connect(self.on_browse)
        h = QtWidgets.QHBoxLayout()
        h.addWidget(self.ed_base, 1)
        h.addWidget(btn_browse)
        lay.addRow("Pasta base dos Orçamentos", h)
        btn_save = QtWidgets.QPushButton("Gravar Configurações")
        btn_save.clicked.connect(self.on_save)
        lay.addRow(btn_save)
        # load
        self.ed_base.setText(get_setting(self.db, KEY_BASE_PATH, DEFAULT_BASE_PATH))

    def on_browse(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Escolher pasta base")
        if d:
            self.ed_base.setText(d)

    def on_save(self):
        try:
            set_setting(self.db, KEY_BASE_PATH, self.ed_base.text().strip())
            self.db.commit()
            QtWidgets.QMessageBox.information(self, "OK", "Configurações gravadas.")
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar: {e}")

