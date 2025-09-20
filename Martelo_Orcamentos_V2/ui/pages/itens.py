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
        # Header com info do orçamento
        self.lbl = QtWidgets.QLabel("Sem orçamento selecionado")
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
        top.addWidget(self.lbl)
        top.addStretch(1)
        top.addWidget(btn_add)
        top.addWidget(btn_del)
        top.addWidget(btn_up)
        top.addWidget(btn_dn)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.table)

    def load_orcamento(self, orc_id: int):
        """Carrega dados do orçamento selecionado e apresenta informações básicas."""
        self._orc_id = orc_id
        o = self.db.get(Orcamento, orc_id)
        if o:
            cliente = self.db.get(Client, o.client_id)
            user = None
            if o.created_by:
                user = self.db.get(User, o.created_by)
            if not user and getattr(self.current_user, "id", None):
                user = self.db.get(User, getattr(self.current_user, "id", None))
            username = user.username if user else getattr(self.current_user, "username", "") or ""
            cliente_nome = cliente.nome if cliente else ""
            ano = o.ano or ""
            numero = o.num_orcamento or ""
            versao = f"{int(o.versao):02d}" if str(o.versao).isdigit() else (o.versao or "")
            self.lbl.setText(
                "  |  ".join(
                    [
                        f"Cliente: {cliente_nome}",
                        f"Ano: {ano}",
                        f"Nº Orçamento: {numero}",
                        f"Versão: {versao}",
                        f"Utilizador: {username}",
                    ]
                )
            )
        else:
            self.lbl.setText("Sem orçamento selecionado")
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
        if QtWidgets.QMessageBox.question(self, "Confirmar", f"Eliminar item {id_item}?") != QtWidgets.QMessageBox.Yes:
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
