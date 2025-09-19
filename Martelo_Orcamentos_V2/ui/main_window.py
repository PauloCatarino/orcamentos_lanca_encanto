from PySide6 import QtWidgets, QtGui


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
        self.stack.addWidget(QtWidgets.QLabel("Página Orçamentos (em construção)", alignment=QtGui.Qt.AlignCenter))
        self.stack.addWidget(QtWidgets.QLabel("Página Itens (em construção)", alignment=QtGui.Qt.AlignCenter))
        self.stack.addWidget(QtWidgets.QLabel("Página Dados Gerais (em construção)", alignment=QtGui.Qt.AlignCenter))
        self.stack.addWidget(QtWidgets.QLabel("Página Relatórios (em construção)", alignment=QtGui.Qt.AlignCenter))
        self.stack.addWidget(QtWidgets.QLabel("Página Configurações (em construção)", alignment=QtGui.Qt.AlignCenter))

        self.list.currentRowChanged.connect(self.stack.setCurrentIndex)

        # Layout
        central = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(central)
        lay.addWidget(self.list)
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(central)

