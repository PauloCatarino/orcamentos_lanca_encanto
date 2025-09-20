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
        self.list.addItems(["Orçamentos", "Itens", "Dados Gerais", "Relatórios", "Configurações"])
        self.list.setFixedWidth(220)

        # Área central
        self.stack = QtWidgets.QStackedWidget()
        self.pg_orc = OrcamentosPage()
        self.pg_itens = ItensPage()
        self.stack.addWidget(self.pg_orc)
        self.stack.addWidget(self.pg_itens)
        self.stack.addWidget(QtWidgets.QLabel("Página Dados Gerais (em construção)", alignment=Qt.AlignCenter))
        self.stack.addWidget(QtWidgets.QLabel("Página Relatórios (em construção)", alignment=Qt.AlignCenter))
        self.stack.addWidget(QtWidgets.QLabel("Página Configurações (em construção)", alignment=Qt.AlignCenter))

        self.list.currentRowChanged.connect(self.stack.setCurrentIndex)
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
