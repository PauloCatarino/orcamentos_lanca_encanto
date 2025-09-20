from PySide6 import QtWidgets
from PySide6.QtCore import Signal
from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.orcamentos import list_orcamentos, create_orcamento, delete_orcamento
from ..models.qt_table import SimpleTableModel


class OrcamentosPage(QtWidgets.QWidget):
    orcamento_aberto = Signal(int)  # id_orcamento

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = SessionLocal()
        self.table = QtWidgets.QTableView(self)
        self.model = SimpleTableModel(columns=[
            ("ID", "id"),
            ("Ano", "ano"),
            ("Nº Orçamento", "num_orcamento"),
            ("Versão", "versao"),
            ("Cliente", "client_id"),
            ("Preço Total", "preco_total"),
        ])
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        # Toolbar
        btn_novo = QtWidgets.QPushButton("Novo")
        btn_del = QtWidgets.QPushButton("Eliminar")
        btn_open = QtWidgets.QPushButton("Abrir Itens")
        btn_refresh = QtWidgets.QPushButton("Atualizar")
        btn_novo.clicked.connect(self.on_novo)
        btn_del.clicked.connect(self.on_delete)
        btn_open.clicked.connect(self.on_open)
        btn_refresh.clicked.connect(self.refresh)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(btn_novo)
        top.addWidget(btn_del)
        top.addWidget(btn_open)
        top.addStretch(1)
        top.addWidget(btn_refresh)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.table)

        self.refresh()

    def refresh(self):
        rows = list_orcamentos(self.db)
        self.model.set_rows(rows)
        if rows:
            self.table.selectRow(0)

    def selected_id(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        row = self.model.get_row(idx.row())
        return row.id

    def on_novo(self):
        dlg = NovoOrcamentoDialog(self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            ano, num, ver, cliente = dlg.values()
            try:
                create_orcamento(self.db, ano=ano, num_orcamento=num, versao=ver, cliente_nome=cliente)
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao criar orçamento: {e}")
            self.refresh()

    def on_delete(self):
        oid = self.selected_id()
        if not oid:
            return
        if QtWidgets.QMessageBox.question(self, "Confirmar", f"Eliminar orçamento {oid}?") != QtWidgets.QMessageBox.Yes:
            return
        try:
            delete_orcamento(self.db, oid)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar: {e}")
        self.refresh()

    def on_open(self):
        oid = self.selected_id()
        if oid:
            self.orcamento_aberto.emit(oid)


class NovoOrcamentoDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Novo Orçamento")
        form = QtWidgets.QFormLayout(self)
        self.ed_ano = QtWidgets.QLineEdit()
        self.ed_num = QtWidgets.QLineEdit()
        self.ed_ver = QtWidgets.QLineEdit("00")
        self.ed_cli = QtWidgets.QLineEdit()
        form.addRow("Ano", self.ed_ano)
        form.addRow("Nº Orçamento", self.ed_num)
        form.addRow("Versão (00)", self.ed_ver)
        form.addRow("Cliente", self.ed_cli)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        form.addRow(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

    def values(self):
        return (
            self.ed_ano.text().strip(),
            self.ed_num.text().strip(),
            self.ed_ver.text().strip() or "00",
            self.ed_cli.text().strip() or "Cliente Genérico",
        )
