from PySide6 import QtWidgets
from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.settings import get_setting, set_setting
from Martelo_Orcamentos_V2.app.services.materias_primas import KEY_MATERIAS_BASE_PATH, DEFAULT_MATERIAS_BASE_PATH


KEY_BASE_PATH = "base_path_orcamentos"
DEFAULT_BASE_PATH = r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2"


class SettingsPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
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
            self.db.commit()
            QtWidgets.QMessageBox.information(self, "OK", "Configurações gravadas.")
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar: {e}")



