from typing import Optional

from PySide6 import QtWidgets
from PySide6.QtCore import Qt

from .pages.orcamentos import OrcamentosPage
from .pages.itens import ItensPage
from .pages.materias_primas import MateriasPrimasPage
from .pages.clientes import ClientesPage
from .pages.dados_gerais import DadosGeraisPage
from .pages.settings import SettingsPage


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("Martelo Orçamentos V2")
        self.resize(1200, 800)

        self.current_orcamento_id: Optional[int] = None

        self.list = QtWidgets.QListWidget()
        self.list.addItems([
            "Orçamentos",
            "Itens",
            "Matérias Primas",
            "Clientes",
            "Dados Gerais",
            "Relatórios",
            "Configurações",
        ])
        self.list.setFixedWidth(220)

        self.stack = QtWidgets.QStackedWidget()

        self.pg_orc = OrcamentosPage(current_user=self.current_user)
        self.pg_itens = ItensPage(current_user=self.current_user)
        self.pg_materias = MateriasPrimasPage(current_user=self.current_user)
        self.pg_clientes = ClientesPage()
        self.pg_dados = DadosGeraisPage(current_user=self.current_user)

        self.stack.addWidget(self.pg_orc)
        self.stack.addWidget(self.pg_itens)
        self.stack.addWidget(self.pg_materias)
        self.stack.addWidget(self.pg_clientes)
        self.stack.addWidget(self.pg_dados)
        self.stack.addWidget(QtWidgets.QLabel("Página Relatórios (em construção)", alignment=Qt.AlignCenter))
        self.stack.addWidget(SettingsPage())

        self.list.currentRowChanged.connect(self.on_menu_changed)
        self.pg_orc.orcamento_aberto.connect(self.on_abrir_orcamento)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(central)
        layout.addWidget(self.list)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        assert self.list.count() == self.stack.count(), (
            f"Lista({self.list.count()}) e Stack({self.stack.count()}) têm tamanhos diferentes!"
        )

    def on_abrir_orcamento(self, orc_id: int):
        self.current_orcamento_id = orc_id
        self.pg_itens.load_orcamento(orc_id)
        self.pg_dados.load_orcamento(orc_id)

        if self.list.currentRow() != 1:
            self.list.blockSignals(True)
            self.list.setCurrentRow(1)
            self.list.blockSignals(False)
        self.stack.setCurrentIndex(1)

    def on_menu_changed(self, index: int):
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.pg_orc.reload_clients()
        elif index == 4 and self.current_orcamento_id:
            self.pg_dados.load_orcamento(self.current_orcamento_id)

