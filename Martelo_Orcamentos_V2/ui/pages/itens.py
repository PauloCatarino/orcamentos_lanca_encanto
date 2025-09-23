from PySide6 import QtWidgets
from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.orcamentos import (
    list_items,
    create_item,
    delete_item,
    move_item,
)
from Martelo_Orcamentos_V2.app.models import Orcamento, Client, User
from ..models.qt_table import SimpleTableModel


class ItensPage(QtWidgets.QWidget):
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.db = SessionLocal()
        self._orc_id = None

        # Cabeçalho estilizado
        self.header = QtWidgets.QFrame()
        self.header.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.header.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                font-weight: bold;
                color: #333;
            }
            QLabel.value {
                font-weight: normal;
                color: #000;
            }
        """)

        self.lbl_cliente = QtWidgets.QLabel("Cliente:");   self.lbl_cliente_val = QtWidgets.QLabel("")
        self.lbl_ano = QtWidgets.QLabel("Ano:");          self.lbl_ano_val = QtWidgets.QLabel("")
        self.lbl_num = QtWidgets.QLabel("Nº Orçamento:"); self.lbl_num_val = QtWidgets.QLabel("")
        self.lbl_ver = QtWidgets.QLabel("Versão:");       self.lbl_ver_val = QtWidgets.QLabel("")
        self.lbl_user = QtWidgets.QLabel("Utilizador:");  self.lbl_user_val = QtWidgets.QLabel("")

        for w in [self.lbl_cliente_val, self.lbl_ano_val, self.lbl_num_val,
                  self.lbl_ver_val, self.lbl_user_val]:
            w.setProperty("class", "value")

        # Layout mais compacto: 3 linhas, 2 colunas
        grid = QtWidgets.QGridLayout(self.header)
        grid.setContentsMargins(5, 5, 5, 5)  # margens menores
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        # Ajustar largura mínima das labels (nomes fixos)
        for lbl in [self.lbl_cliente, self.lbl_user, self.lbl_ano, self.lbl_num, self.lbl_ver]:
            lbl.setMinimumWidth(80)   # largura mínima para alinhar
            lbl.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)

        # Linha 0: Cliente | Utilizador
        grid.addWidget(self.lbl_cliente, 0, 0)
        grid.addWidget(self.lbl_cliente_val, 0, 1)
        grid.addWidget(self.lbl_user, 0, 2)
        grid.addWidget(self.lbl_user_val, 0, 3)

        # Linha 1: Ano (sozinho, ocupa mais colunas para ser compacto)
        grid.addWidget(self.lbl_ano, 1, 0)
        grid.addWidget(self.lbl_ano_val, 1, 1, 1, 3)

        # Linha 2: Nº Orçamento | Versão
        grid.addWidget(self.lbl_num, 2, 0)
        grid.addWidget(self.lbl_num_val, 2, 1)
        grid.addWidget(self.lbl_ver, 2, 2)
        grid.addWidget(self.lbl_ver_val, 2, 3)

        # Reservar colunas extras à direita (para futuro menu)
        grid.setColumnStretch(4, 1)   # espaço flexível à direita

        # Tabela de itens
        self.table = QtWidgets.QTableView(self)
        self.model = SimpleTableModel(columns=[
            ("ID", "id_item"),
            ("Ord", "item_ord"),
            ("Código", "codigo"),
            ("Descrição", "descricao"),
            ("Altura", "altura"),
            ("Largura", "largura"),
            ("Profund.", "profundidade"),
            ("Und", "und"),
            ("Qt", "qt"),
            ("Preço Unit.", "preco_unitario"),
            ("Preço Total", "preco_total"),
        ])
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        # Toolbar
        btn_add = QtWidgets.QPushButton("Novo Item")
        btn_del = QtWidgets.QPushButton("Eliminar Item")
        btn_up = QtWidgets.QPushButton("↑")
        btn_dn = QtWidgets.QPushButton("↓")
        btn_add.clicked.connect(self.on_add)
        btn_del.clicked.connect(self.on_del)
        btn_up.clicked.connect(lambda: self.on_move(-1))
        btn_dn.clicked.connect(lambda: self.on_move(1))

        top = QtWidgets.QHBoxLayout()
        top.addWidget(self.header, 1)
        top.addWidget(btn_add)
        top.addWidget(btn_del)
        top.addWidget(btn_up)
        top.addWidget(btn_dn)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.table)

    def load_orcamento(self, orc_id: int):
        """Carrega dados do orçamento selecionado e apresenta informações básicas."""

        # Helpers locais para garantir sempre string
        def _txt(v) -> str:
            """Converte qualquer valor para texto, devolvendo '' se None."""
            return "" if v is None else str(v)

        def _fmt_ver(v) -> str:
            """Formata versão como 2 dígitos (01, 02, ...). Se não der, devolve texto simples."""
            if v is None or v == "":
                return ""
            try:
                return f"{int(v):02d}"
            except (TypeError, ValueError):
                return _txt(v)

        self._orc_id = orc_id
        o = self.db.get(Orcamento, orc_id)
        if o:
            # Cliente e utilizador
            cliente = self.db.get(Client, o.client_id)
            user = None
            if o.created_by:
                user = self.db.get(User, o.created_by)
            if not user and getattr(self.current_user, "id", None):
                user = self.db.get(User, getattr(self.current_user, "id", None))
            username = getattr(user, "username", "") or getattr(self.current_user, "username", "") or ""

            # Preencher labels SEM lançar TypeError (sempre string)
            self.lbl_cliente_val.setText(_txt(getattr(cliente, "nome", "")))
            self.lbl_ano_val.setText(_txt(getattr(o, "ano", "")))                # <- antes passava int
            self.lbl_num_val.setText(_txt(getattr(o, "num_orcamento", "")))
            self.lbl_ver_val.setText(_fmt_ver(getattr(o, "versao", "")))         # <- robusto a int/str/None
            self.lbl_user_val.setText(_txt(username))
        else:
            # Limpar quando não há orçamento
            self.lbl_cliente_val.setText("")
            self.lbl_ano_val.setText("")
            self.lbl_num_val.setText("")
            self.lbl_ver_val.setText("")
            self.lbl_user_val.setText("")

        self.refresh()

    def refresh(self):
        if not self._orc_id:
            self.model.set_rows([])
            return
        rows = list_items(self.db, self._orc_id)
        self.model.set_rows(rows)
        if rows:
            self.table.selectRow(0)

    def selected_id(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        row = self.model.get_row(idx.row())
        return row.id_item

    def on_add(self):
        if not self._orc_id:
            return
        try:
            create_item(self.db, self._orc_id)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao criar item: {e}")
        self.refresh()

    def on_del(self):
        id_item = self.selected_id()
        if not id_item:
            return
        if QtWidgets.QMessageBox.question(self, "Confirmar",
                                          f"Eliminar item {id_item}?") != QtWidgets.QMessageBox.Yes:
            return
        try:
            delete_item(self.db, id_item)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar: {e}")
        self.refresh()

    def on_move(self, direction: int):
        id_item = self.selected_id()
        if not id_item:
            return
        try:
            move_item(self.db, id_item, direction)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao mover: {e}")
        self.refresh()
