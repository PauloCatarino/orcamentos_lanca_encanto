from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from .pages.orcamentos import OrcamentosPage
from .pages.itens import ItensPage


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("Martelo Orçamentos V2")
        self.resize(1200, 800)

        # Barra lateral (placeholder)
        self.list = QtWidgets.QListWidget()
        self.list.addItems(["Orçamentos", "Itens", "Clientes", "Dados Gerais", "Relatórios", "Configurações"])
        self.list.setFixedWidth(220)

        # Área central
        self.stack = QtWidgets.QStackedWidget()
        self.pg_orc = OrcamentosPage(current_user=self.current_user)
        self.pg_itens = ItensPage(current_user=self.current_user)
        from .pages.clientes import ClientesPage
        self.pg_clientes = ClientesPage()
        self.stack.addWidget(self.pg_orc)        # idx 0
        self.stack.addWidget(self.pg_itens)      # idx 1
        self.stack.addWidget(self.pg_clientes)   # idx 2
        self.stack.addWidget(QtWidgets.QLabel("Página Dados Gerais (em construção)", alignment=Qt.AlignCenter))
        self.stack.addWidget(QtWidgets.QLabel("Página Relatórios (em construção)", alignment=Qt.AlignCenter))
        from .pages.settings import SettingsPage
        self.stack.addWidget(SettingsPage())

        self.list.currentRowChanged.connect(self.on_menu_changed)
        self.pg_orc.orcamento_aberto.connect(self.on_abrir_itens)

        # Layout
        central = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(central)
        lay.addWidget(self.list)
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(central)

    def on_abrir_itens(self, orc_id: int):
        # Ir para a página Itens e carregar items do orçamento
        self.pg_itens.load_orcamento(orc_id)
        self.stack.setCurrentWidget(self.pg_itens)

    def on_menu_changed(self, index: int):
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.pg_orc.reload_clients()
