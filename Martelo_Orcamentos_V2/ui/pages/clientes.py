from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStyle, QApplication
from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.clients import (
    list_clients, search_clients, upsert_client, delete_client, suggestion_tokens,
)
from ..models.qt_table import SimpleTableModel


# Alias seguro (PySide6 mudou o enum em versões recentes)
SP = getattr(QStyle, "StandardPixmap", QStyle)


def label_with_icon(text: str, icon: QStyle.StandardPixmap):
    """Cria um label com ícone do QStyle ao lado do texto."""
    w = QtWidgets.QWidget()
    h = QtWidgets.QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)

    lbl_icon = QtWidgets.QLabel()
    icn = QApplication.style().standardIcon(icon)
    lbl_icon.setPixmap(icn.pixmap(16, 16))

    lbl_text = QtWidgets.QLabel(text)

    h.addWidget(lbl_icon)
    h.addWidget(lbl_text)
    h.addStretch(1)
    return w


class ClientesPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = SessionLocal()

        # Pesquisa + sugestões
        self.ed_search = QtWidgets.QLineEdit()
        self.ed_search.setPlaceholderText("Pesquisar clientes (use % para multi-termos)…")
        self.ed_search.textChanged.connect(self.on_search)
        self.btn_clear = QtWidgets.QToolButton()
        self.btn_clear.setText("✕")
        self.btn_clear.clicked.connect(lambda: self.ed_search.setText(""))
        top = QtWidgets.QHBoxLayout()
        top.addWidget(self.ed_search, 1)
        top.addWidget(self.btn_clear)

        # Tabela de clientes
        self.table = QtWidgets.QTableView()
        self.model = SimpleTableModel(columns=[
            ("ID", "id"),
            ("Nome", "nome"),
            ("Simplex", "nome_simplex"),
            ("Email", "email"),
            ("Telefone", "telefone"),
            ("Telemóvel", "telemovel"),
            ("PHC", "num_cliente_phc"),
        ])
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.selectionModel().selectionChanged.connect(self.load_selected)

        # Formulário de edição
        form = QtWidgets.QFormLayout()
        self.ed_nome = QtWidgets.QLineEdit()
        self.ed_simplex = QtWidgets.QLineEdit()
        self.ed_morada = QtWidgets.QTextEdit(); self.ed_morada.setFixedHeight(60)
        self.ed_email = QtWidgets.QLineEdit()
        self.ed_web = QtWidgets.QLineEdit()
        self.ed_tel = QtWidgets.QLineEdit()
        self.ed_tm = QtWidgets.QLineEdit()
        self.ed_phc = QtWidgets.QLineEdit()
        self.ed_info1 = QtWidgets.QTextEdit(); self.ed_info1.setFixedHeight(60)
        self.ed_info2 = QtWidgets.QTextEdit(); self.ed_info2.setFixedHeight(60)

        # Campos com ícones válidos
        form.addRow(label_with_icon("Nome Cliente", SP.SP_FileIcon), self.ed_nome)
        form.addRow(label_with_icon("Nome Cliente Simplex", SP.SP_FileDialogListView), self.ed_simplex)
        form.addRow(label_with_icon("Morada", SP.SP_DirIcon), self.ed_morada)
        form.addRow(label_with_icon("E-Mail", SP.SP_MessageBoxInformation), self.ed_email)
        form.addRow(label_with_icon("Página WEB", SP.SP_DesktopIcon), self.ed_web)
        form.addRow(label_with_icon("Telefone", SP.SP_DialogOkButton), self.ed_tel)
        form.addRow(label_with_icon("Telemóvel", SP.SP_ComputerIcon), self.ed_tm)
        form.addRow(label_with_icon("Num Cliente PHC", SP.SP_DriveHDIcon), self.ed_phc)
        form.addRow(label_with_icon("Info 1", SP.SP_FileDialogDetailedView), self.ed_info1)
        form.addRow(label_with_icon("Info 2", SP.SP_FileDialogDetailedView), self.ed_info2)

        # Botões
        btn_new = QtWidgets.QPushButton("Inserir novo Cliente")
        btn_save = QtWidgets.QPushButton("Gravar Cliente")
        btn_del = QtWidgets.QPushButton("Eliminar Cliente")
        btn_new.clicked.connect(self.on_new)
        btn_save.clicked.connect(self.on_save)
        btn_del.clicked.connect(self.on_delete)
        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(btn_new)
        btns.addWidget(btn_save)
        btns.addWidget(btn_del)
        btns.addStretch(1)

        # Layout principal: esquerda (pesquisa+tabela) / direita (form)
        left = QtWidgets.QWidget()
        vleft = QtWidgets.QVBoxLayout(left)
        vleft.addLayout(top)
        vleft.addWidget(self.table)

        right = QtWidgets.QWidget()
        vright = QtWidgets.QVBoxLayout(right)
        vright.addLayout(form)
        vright.addStretch(1)
        vright.addLayout(btns)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(splitter)

        self._current_id = None
        self.refresh()
        self._setup_completer()


    # Helpers
    def refresh(self):
        rows = list_clients(self.db)
        self.model.set_rows(rows)
        if rows:
            self.table.selectRow(0)

    def _setup_completer(self):
        toks = suggestion_tokens(self.db)
        comp = QtWidgets.QCompleter(toks, self)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        self.ed_search.setCompleter(comp)

    def on_search(self, text: str):
        rows = search_clients(self.db, text)
        self.model.set_rows(rows)

    def selected_row(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        return self.model.get_row(idx.row())

    def load_selected(self):
        row = self.selected_row()
        if not row:
            self._current_id = None
            return
        self._current_id = row.id
        self.ed_nome.setText(row.nome or "")
        self.ed_simplex.setText(row.nome_simplex or "")
        self.ed_morada.setPlainText(row.morada or "")
        self.ed_email.setText(row.email or "")
        self.ed_web.setText(row.web_page or "")
        self.ed_tel.setText(row.telefone or "")
        self.ed_tm.setText(row.telemovel or "")
        self.ed_phc.setText(row.num_cliente_phc or "")
        self.ed_info1.setPlainText(row.info_1 or "")
        self.ed_info2.setPlainText(row.info_2 or "")

    def on_new(self):
        self._current_id = None
        for w in [self.ed_nome, self.ed_simplex, self.ed_email, self.ed_web, self.ed_tel, self.ed_tm, self.ed_phc]:
            w.clear()
        self.ed_morada.clear(); self.ed_info1.clear(); self.ed_info2.clear()
        self.ed_nome.setFocus()

    def on_save(self):
        try:
            upsert_client(
                self.db,
                id=self._current_id,
                nome=self.ed_nome.text(),
                nome_simplex=self.ed_simplex.text(),
                morada=self.ed_morada.toPlainText(),
                email=self.ed_email.text(),
                web_page=self.ed_web.text(),
                telefone=self.ed_tel.text(),
                telemovel=self.ed_tm.text(),
                num_cliente_phc=self.ed_phc.text(),
                info_1=self.ed_info1.toPlainText(),
                info_2=self.ed_info2.toPlainText(),
            )
            self.db.commit()
            self.refresh()
            self._setup_completer()
            QtWidgets.QMessageBox.information(self, "OK", "Cliente gravado com sucesso.")
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar: {e}")

    def on_delete(self):
        if not self._current_id:
            return
        if QtWidgets.QMessageBox.question(self, "Confirmar", "Eliminar cliente selecionado?") != QtWidgets.QMessageBox.Yes:
            return
        try:
            delete_client(self.db, self._current_id)
            self.db.commit()
            self.refresh()
            self.on_new()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar: {e}")

