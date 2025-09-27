from PySide6 import QtWidgets
from PySide6.QtCore import Qt

# Páginas
from .pages.orcamentos import OrcamentosPage
from .pages.itens import ItensPage
from .pages.materias_primas import MateriasPrimasPage  # ← NOVO
from .pages.clientes import ClientesPage
from .pages.settings import SettingsPage


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("Martelo Orçamentos V2")
        self.resize(1200, 800)

        # ---------------------------
        # Lista lateral (menu)
        # ---------------------------
        self.list = QtWidgets.QListWidget()
        # Ordem dos itens **deve** corresponder à ordem de inserção no QStackedWidget
        self.list.addItems([
            "Orçamentos",        # idx 0
            "Itens",             # idx 1
            "Matérias Primas",   # idx 2  ← VOLTOU
            "Clientes",          # idx 3
            "Dados Gerais",      # idx 4 (placeholder)
            "Relatórios",        # idx 5 (placeholder)
            "Configurações"      # idx 6
        ])
        self.list.setFixedWidth(220)

        # ---------------------------
        # Área central (stack)
        # ---------------------------
        self.stack = QtWidgets.QStackedWidget()

        # Instâncias das páginas (em MESMA ORDEM da lista)
        self.pg_orc = OrcamentosPage(current_user=self.current_user)   # idx 0
        self.pg_itens = ItensPage(current_user=self.current_user)      # idx 1
        self.pg_materias = MateriasPrimasPage(current_user=self.current_user)  # idx 2
        self.pg_clientes = ClientesPage()                              # idx 3

        # Adicionar páginas ao stack na MESMA ORDEM da lista
        self.stack.addWidget(self.pg_orc)        # 0
        self.stack.addWidget(self.pg_itens)      # 1
        self.stack.addWidget(self.pg_materias)   # 2
        self.stack.addWidget(self.pg_clientes)   # 3
        self.stack.addWidget(QtWidgets.QLabel(
            "Página Dados Gerais (em construção)", alignment=Qt.AlignCenter))  # 4
        self.stack.addWidget(QtWidgets.QLabel(
            "Página Relatórios (em construção)", alignment=Qt.AlignCenter))    # 5
        self.stack.addWidget(SettingsPage())     # 6

        # Sincronizar lista ⇄ stack
        self.list.currentRowChanged.connect(self.on_menu_changed)

        # Quando o orçamento é aberto, saltar para Itens
        self.pg_orc.orcamento_aberto.connect(self.on_abrir_itens)

        # Layout principal
        central = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(central)
        lay.addWidget(self.list)
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        # (Opcional) Garantir que a contagem bate certo; ajuda a detectar erros cedo
        assert self.list.count() == self.stack.count(), \
            f"Lista({self.list.count()}) e Stack({self.stack.count()}) têm tamanhos diferentes!"

    # -------------------------------------------------
    # Ações de navegação
    # -------------------------------------------------
    def on_abrir_itens(self, orc_id: int):
        """Ir para a página Itens e carregar dados do orçamento"""
        self.pg_itens.load_orcamento(orc_id)

        # Selecionar a aba "Itens" (idx 1) na lista lateral sem disparar sinal recursivo
        if self.list.currentRow() != 1:
            self.list.blockSignals(True)
            self.list.setCurrentRow(1)
            self.list.blockSignals(False)

        # Garantir que o stack também mostra a página Itens
        self.stack.setCurrentIndex(1)

    def on_menu_changed(self, index: int):
        """Quando o utilizador muda de item no menu"""
        self.stack.setCurrentIndex(index)

        # Comportamentos específicos por página (exemplos)
        if index == 0:  # Orçamentos
            # Atualiza dropdowns/listas dependentes de clientes, etc.
            self.pg_orc.reload_clients()
        # if index == 2:  # Matérias Primas
        #     self.pg_materias.refresh()  # (se tiveres um método para reload)
