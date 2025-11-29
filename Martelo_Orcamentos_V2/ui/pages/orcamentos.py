import logging
import os
from typing import Optional
from PySide6 import QtWidgets
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import QStyle, QCompleter, QToolButton, QAbstractSpinBox
from sqlalchemy import select, and_
from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.orcamentos import (
    list_orcamentos,
    create_orcamento,
    delete_orcamento,
    next_seq_for_year,
    duplicate_orcamento_version,
    search_orcamentos,
)
from Martelo_Orcamentos_V2.app.services.clients import list_clients
from Martelo_Orcamentos_V2.app.services.settings import get_setting
from ..models.qt_table import SimpleTableModel


logger = logging.getLogger(__name__)


class OrcamentosPage(QtWidgets.QWidget):
    orcamento_aberto = Signal(int)  # id_orcamento

    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.db = SessionLocal()
        self._current_id: Optional[int] = None

        # Campos base
        self.cb_cliente = QtWidgets.QComboBox()
        self.cb_cliente.setEditable(True)
        self._clients = []
        self._load_clients()

        self.ed_ano = QtWidgets.QLineEdit()
        self.ed_num = QtWidgets.QLineEdit()
        self.ed_num.setReadOnly(True)
        self.ed_ver = QtWidgets.QLineEdit("01")
        self.ed_data = QtWidgets.QDateEdit()
        self.ed_data.setDisplayFormat("dd-MM-yyyy")
        self.ed_data.setCalendarPopup(True)
        self.ed_data.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.ed_data.setDate(QDate.currentDate())
        self.lbl_user = QtWidgets.QLabel(getattr(self.current_user, "username", "(utilizador)") or "(utilizador)")
        self.lbl_user.setFixedHeight(20)
        self.lbl_user.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.cb_status = QtWidgets.QComboBox()
        self.cb_status.addItems(["Falta Orçamentar", "Enviado", "Adjudicado", "Sem Interesse", "Não Adjudicado"])
        self.ed_enc_phc = QtWidgets.QLineEdit()
        self.ed_ref_cliente = QtWidgets.QLineEdit()
        self.ed_obra = QtWidgets.QLineEdit()
        self.ed_preco = QtWidgets.QLineEdit()
        self.ed_desc = QtWidgets.QTextEdit()
        self.ed_desc.setFixedHeight(28)
        self.ed_desc.setPlaceholderText("Descricao curta...")
        self.ed_loc = QtWidgets.QLineEdit()
        self.ed_info1 = QtWidgets.QTextEdit()
        self.ed_info1.setFixedHeight(28)
        self.ed_info2 = QtWidgets.QTextEdit()
        self.ed_info2.setFixedHeight(28)

        # Pesquisa
        search_bar = QtWidgets.QHBoxLayout()
        search_bar.setSpacing(6)
        lbl_search = QtWidgets.QLabel("Pesquisa:")
        self.ed_search = QtWidgets.QLineEdit()
        self.ed_search.setMinimumWidth(320)
        self.ed_search.setPlaceholderText("Pesquisar orcamentos - use % para multi-termos")
        btn_clear = QToolButton()
        btn_clear.setText("✕")
        btn_clear.setToolTip("Limpar pesquisa")
        btn_clear.clicked.connect(lambda: self.ed_search.setText(""))
        search_bar.addWidget(lbl_search)
        search_bar.addWidget(self.ed_search, 3)
        search_bar.addWidget(btn_clear)
        search_bar.addStretch(1)
        self.ed_search.textChanged.connect(self.on_search)

        # Tabela
        self.table = QtWidgets.QTableView(self)
        self.model = SimpleTableModel(
            columns=[
                ("ID", "id"),
                ("Ano", "ano"),
                ("Nº Orcamento", "num_orcamento"),
                ("Versao", "versao"),
                ("Cliente", "cliente"),
                ("Ref. Cliente", "ref_cliente"),
                ("Data", "data"),
                ("Preco", "preco", lambda v: self._format_currency(v)),
                ("Utilizador", "utilizador"),
                ("Estado", "estado"),
                ("Obra", "obra"),
                ("Descricao", "descricao"),
                ("Localizacao", "localizacao"),
                ("Info 1", "info_1"),
                ("Info 2", "info_2"),
            ]
        )
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "QTableView::item:selected { background: #555555; color: white; }"
            "QTableView::item:selected:!active { background: #666666; color: white; }"
        )
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        # Largura das colunas Lista Orcamentos
        width_map = {
            "ID": 30,
            "Ano": 50,
            "Nº Orcamento": 100,
            "Versao": 60,
            "Cliente": 170,
            "Ref. Cliente": 80,
            "Data": 80,
            "Preco": 80,
            "Utilizador": 90,
            "Estado": 110,
            "Obra": 180,
            "Descricao": 200,
            "Localizacao": 140,
            "Info 1": 200,
            "Info 2": 150,
        }
        for idx, col in enumerate(self.model.columns):
            spec = self.model._col_spec(col)
            label = spec.get("header", "")
            header.setSectionResizeMode(idx, QtWidgets.QHeaderView.Interactive)
            if label in width_map:
                header.resizeSection(idx, width_map[label])
        self.table.selectionModel().selectionChanged.connect(self.load_selected)

        # Botões
        def _style_primary_button(btn: QtWidgets.QPushButton, color: str):
            btn.setStyleSheet(
                f"background-color:{color}; color:white; font-weight:bold; padding:8px 12px; border-radius:4px;"
            )
            btn.setCursor(Qt.PointingHandCursor)

        s = self.style()
        btn_novo = QtWidgets.QPushButton("Novo Orcamento")
        btn_novo.setIcon(s.standardIcon(QStyle.SP_FileIcon))
        _style_primary_button(btn_novo, "#4CAF50")
        btn_novo.clicked.connect(self.on_novo)

        btn_save = QtWidgets.QPushButton("Salvar")
        btn_save.setIcon(s.standardIcon(QStyle.SP_DialogSaveButton))
        _style_primary_button(btn_save, "#2196F3")
        btn_save.clicked.connect(self.on_save)

        btn_open = QtWidgets.QPushButton("Abrir Itens")
        btn_open.setIcon(s.standardIcon(QStyle.SP_ArrowRight))
        _style_primary_button(btn_open, "#FF9800")
        btn_open.clicked.connect(self.on_open)

        btn_dup = QtWidgets.QPushButton("Duplicar p/ Versao")
        btn_dup.setIcon(s.standardIcon(QStyle.SP_BrowserReload))
        btn_dup.setStyleSheet("font-weight:bold; padding:6px 10px;")
        btn_dup.setCursor(Qt.PointingHandCursor)
        btn_dup.clicked.connect(self.on_duplicate)

        btn_del = QtWidgets.QPushButton("Eliminar Orcamento")
        btn_del.setIcon(s.standardIcon(QStyle.SP_TrashIcon))
        btn_del.setStyleSheet("font-weight:bold; padding:6px 10px;")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.clicked.connect(self.on_delete)

        btn_folder = QtWidgets.QPushButton("Criar Pasta do Orcamento")
        btn_folder.setIcon(s.standardIcon(QStyle.SP_DirIcon))
        btn_folder.setStyleSheet("font-weight:bold; padding:6px 10px;")
        btn_folder.setCursor(Qt.PointingHandCursor)
        btn_folder.clicked.connect(self.on_create_folder)

        btn_open_folder = QtWidgets.QPushButton("Abrir Pasta Orcamento")
        btn_open_folder.setIcon(s.standardIcon(QStyle.SP_DialogOpenButton))
        btn_open_folder.setStyleSheet("font-weight:bold; padding:6px 10px;")
        btn_open_folder.setCursor(Qt.PointingHandCursor)
        btn_open_folder.clicked.connect(self.on_open_folder)

        btn_refresh = QtWidgets.QPushButton("Atualizar")
        btn_refresh.setIcon(s.standardIcon(QStyle.SP_BrowserReload))
        btn_refresh.setStyleSheet("font-weight:bold; padding:6px 10px;")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(lambda: (self.refresh(), self._load_clients()))

        # Header grid
        def _lbl(text: str) -> QtWidgets.QLabel:
            w = QtWidgets.QLabel(text)
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            return w

        header_grid = QtWidgets.QGridLayout()
        header_grid.setHorizontalSpacing(2)
        header_grid.setVerticalSpacing(2)
        header_grid.setContentsMargins(6, 4, 6, 4)

        header_grid.addWidget(_lbl("Cliente:"), 0, 0)
        header_grid.addWidget(self.cb_cliente, 0, 1, 1, 3)
        header_grid.addWidget(_lbl("Ano:"), 0, 4)
        header_grid.addWidget(self.ed_ano, 0, 5)
        header_grid.addWidget(_lbl("Nº Orcamento (seq):"), 0, 6)
        header_grid.addWidget(self.ed_num, 0, 7)
        header_grid.addWidget(_lbl("Versao:"), 0, 8)
        header_grid.addWidget(self.ed_ver, 0, 9)
        header_grid.addWidget(_lbl("Data:"), 0, 10)
        header_grid.addWidget(self.ed_data, 0, 11)

        header_grid.addWidget(_lbl("Ref. Cliente:"), 1, 0)
        header_grid.addWidget(self.ed_ref_cliente, 1, 1, 1, 2)
        header_grid.addWidget(_lbl("Utilizador:"), 1, 3)
        header_grid.addWidget(self.lbl_user, 1, 4)
        header_grid.addWidget(_lbl("Estado:"), 1, 5)
        header_grid.addWidget(self.cb_status, 1, 6)
        header_grid.addWidget(_lbl("Enc PHC:"), 1, 7)
        header_grid.addWidget(self.ed_enc_phc, 1, 8)
        header_grid.addWidget(_lbl("Preco Orcamento:"), 1, 9)
        header_grid.addWidget(self.ed_preco, 1, 10, 1, 2)

        header_grid.addWidget(_lbl("Obra:"), 2, 0)
        header_grid.addWidget(self.ed_obra, 2, 1, 1, 4)
        header_grid.addWidget(_lbl("Descricao Orcamento:"), 2, 5)
        header_grid.addWidget(self.ed_desc, 2, 6, 1, 5)

        header_grid.addWidget(_lbl("Localizacao:"), 3, 0)
        header_grid.addWidget(self.ed_loc, 3, 1, 1, 2)
        header_grid.addWidget(_lbl("Info 1:"), 3, 3)
        header_grid.addWidget(self.ed_info1, 3, 4, 1, 3)
        header_grid.addWidget(_lbl("Info 2:"), 3, 7)
        header_grid.addWidget(self.ed_info2, 3, 8, 1, 3)

        label_cols = [0, 3, 4, 5, 6, 7, 8, 9, 10]
        field_cols = [1, 2, 4, 5, 6, 7, 8, 9, 10, 11]
        for c in label_cols:
            header_grid.setColumnStretch(c, 0)
        for c in field_cols:
            header_grid.setColumnStretch(c, 4)

        header_box = QtWidgets.QGroupBox("Campos do Orcamento")
        header_box.setLayout(header_grid)
        header_box.setStyleSheet("QGroupBox { padding-top: 10px; }")
        header_box.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
        header_box.setMaximumHeight(230)

        primary_actions = QtWidgets.QHBoxLayout()
        primary_actions.setSpacing(10)
        primary_actions.addWidget(btn_novo)
        primary_actions.addWidget(btn_save)
        primary_actions.addWidget(btn_open)
        primary_actions.addStretch(1)

        secondary_actions = QtWidgets.QHBoxLayout()
        secondary_actions.setSpacing(8)
        for b in [btn_dup, btn_del, btn_folder, btn_open_folder, btn_refresh]:
            secondary_actions.addWidget(b)
        secondary_actions.addStretch(1)

        table_header = QtWidgets.QHBoxLayout()
        table_header.setSpacing(10)
        lbl_table = QtWidgets.QLabel("Lista de Orcamentos")
        lbl_table.setStyleSheet("font-weight:bold;")
        table_header.addWidget(lbl_table)
        table_header.addSpacing(12)
        table_header.addLayout(search_bar, stretch=1)
        table_header.addStretch(1)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        main_layout.addLayout(primary_actions)
        main_layout.addWidget(header_box)
        main_layout.addLayout(secondary_actions)
        main_layout.addLayout(table_header)
        main_layout.addWidget(self.table)
        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 0)
        main_layout.setStretch(2, 0)
        main_layout.setStretch(3, 0)
        main_layout.setStretch(4, 1)

        self._prepare_new_form()
        self.refresh()

    # Dados
    def refresh(self, select_first: bool = True):
        rows = list_orcamentos(self.db)
        self.model.set_rows(rows)
        if rows and select_first:
            self.table.selectRow(0)
        elif not select_first:
            self.table.clearSelection()

    def selected_row(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        return self.model.get_row(idx.row())

    def selected_id(self):
        row = self.selected_row()
        return row.id if row else None

    def _load_clients(self):
        current_text = self.cb_cliente.currentText().strip()
        try:
            with SessionLocal() as refresh_db:
                clients = list_clients(refresh_db)
                refresh_db.expunge_all()
                self._clients = clients
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar clientes: {exc}")
            return

        names = [c.nome for c in self._clients]

        self.cb_cliente.blockSignals(True)
        self.cb_cliente.clear()
        self.cb_cliente.addItems(names)

        if self.cb_cliente.isEditable():
            comp = QCompleter(names, self)
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            comp.setFilterMode(Qt.MatchContains)
            self.cb_cliente.setCompleter(comp)

        if current_text:
            idx = next((i for i, name in enumerate(names) if name == current_text), -1)
            if idx >= 0:
                self.cb_cliente.setCurrentIndex(idx)
            else:
                self.cb_cliente.setCurrentText(current_text)

        self.cb_cliente.blockSignals(False)

    def reload_clients(self):
        self._load_clients()

    def showEvent(self, event):
        super().showEvent(event)
        self._load_clients()

    def _set_identity_lock(self, locked: bool):
        self.ed_ano.setReadOnly(locked)
        self.ed_ver.setReadOnly(locked)
        # O numero e sempre gerido automaticamente
        self.ed_num.setReadOnly(True)

    def load_selected(self):
        row = self.selected_row()
        if not row:
            return
        from Martelo_Orcamentos_V2.app.models import Orcamento, Client

        o = self.db.get(Orcamento, row.id)
        if not o:
            return
        self._current_id = o.id
        self._set_identity_lock(True)
        try:
            cli = self.db.get(Client, o.client_id)
            names = [c.nome for c in self._clients]
            if cli and cli.nome in names:
                self.cb_cliente.setCurrentIndex(names.index(cli.nome))
        except Exception:
            pass
        self.ed_ano.setText(str(o.ano or ""))
        seq = str(o.num_orcamento or "")
        self.ed_num.setText(seq[2:6] if len(seq) >= 6 else seq)
        self.ed_ver.setText(self._format_version(o.versao or "01"))
        date_text = o.data or ""
        try:
            parts = [int(p) for p in date_text.split("-")]
            if len(parts) == 3:
                if len(str(parts[0])) == 4:
                    year, month, day = parts
                else:
                    day, month, year = parts
                self.ed_data.setDate(QDate(year, month, day))
            else:
                self.ed_data.setDate(QDate.currentDate())
        except Exception:
            self.ed_data.setDate(QDate.currentDate())
        self.cb_status.setCurrentText(o.status or "Falta Orçamentar")
        self.ed_enc_phc.setText(o.enc_phc or "")
        self.ed_ref_cliente.setText(o.ref_cliente or "")
        self.ed_obra.setText(o.obra or "")
        if o.preco_total is None:
            self.ed_preco.clear()
        else:
            self.ed_preco.setText(self._format_currency(o.preco_total))
        self.ed_desc.setPlainText(o.descricao_orcamento or "")
        self.ed_loc.setText(o.localizacao or "")
        self.ed_info1.setPlainText(o.info_1 or "")
        self.ed_info2.setPlainText(o.info_2 or "")

    # Acoes
    @staticmethod
    def _format_version(value):
        if value is None:
            return "01"
        text = str(value).strip()
        if not text:
            return "01"
        if text.isdigit():
            try:
                return f"{int(text):02d}"
            except ValueError:
                pass
        return text.zfill(2) if len(text) == 1 else text

    @staticmethod
    def _format_currency(value) -> str:
        if value in (None, ""):
            return ""
        try:
            num = float(value)
        except Exception:
            return str(value)
        txt = f"{num:,.2f}"
        # trocar separador decimal para virgula mantendo milhares com ponto
        txt = txt.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{txt} €"

    @staticmethod
    def _parse_currency(text):
        if text is None:
            return None
        raw = str(text).strip()
        if not raw:
            return None
        cleaned = raw.replace("€", "").replace(" ", "")
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "")
            cleaned = cleaned.replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            return float(cleaned)
        except Exception:
            return None

    def _confirm_ref_cliente_duplicate(self, ref_cliente: str, matches) -> bool:
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Ref. Cliente duplicada")
        dialog.setModal(True)
        dialog.resize(760, 360)

        layout = QtWidgets.QVBoxLayout(dialog)
        info = QtWidgets.QLabel(
            f"Já existem orçamentos com a Ref. Cliente '{ref_cliente}'. "
            "Verifique a lista e escolha se pretende criar mesmo assim."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        headers = ["ID", "Ano", "Nº Orçamento", "Versão", "Cliente", "Ref. Cliente", "Data", "Estado", "Obra"]
        table = QtWidgets.QTableWidget(len(matches), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        for row_idx, row in enumerate(matches):
            cliente_nome = getattr(row, "cliente_nome", "")
            if not cliente_nome and getattr(row, "client_id", None):
                try:
                    from Martelo_Orcamentos_V2.app.models import Client

                    cliente = self.db.get(Client, row.client_id)
                    cliente_nome = getattr(cliente, "nome", "") if cliente else ""
                except Exception:
                    cliente_nome = ""
            vals = [
                getattr(row, "id", ""),
                getattr(row, "ano", ""),
                getattr(row, "num_orcamento", ""),
                getattr(row, "versao", ""),
                cliente_nome,
                getattr(row, "ref_cliente", ""),
                getattr(row, "data", ""),
                getattr(row, "status", ""),
                getattr(row, "obra", ""),
            ]
            for col_idx, val in enumerate(vals):
                item = QtWidgets.QTableWidgetItem(str(val or ""))
                item.setFlags(Qt.ItemIsEnabled)
                table.setItem(row_idx, col_idx, item)
        table.resizeColumnsToContents()
        layout.addWidget(table)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Yes | QtWidgets.QDialogButtonBox.No)
        buttons.button(QtWidgets.QDialogButtonBox.Yes).setText("Criar novo mesmo assim")
        buttons.button(QtWidgets.QDialogButtonBox.No).setText("Cancelar")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        return dialog.exec() == QtWidgets.QDialog.Accepted

    def _prepare_new_form(self, ano: Optional[str] = None):
        """Prepara o formulario para um novo orcamento."""
        self.table.clearSelection()
        self._current_id = None
        self._set_identity_lock(False)

        # Ano atual (ou passado como argumento)
        ano_full = (ano or str(QDate.currentDate().year())).strip() or str(QDate.currentDate().year())
        self.ed_ano.setText(ano_full)

        # Calcula proximo nº sequencial (0001, 0002, ...)
        try:
            seq_txt = next_seq_for_year(self.db, ano_full)
        except Exception:
            seq_txt = "0001"
        self.ed_num.setText(seq_txt)

        # Valores iniciais padrao
        self.ed_ver.setText("01")
        self.ed_data.setDate(QDate.currentDate())
        self.cb_status.setCurrentText("Falta Orçamentar")
        self.cb_cliente.blockSignals(True)
        self.cb_cliente.setCurrentIndex(-1)
        if self.cb_cliente.isEditable():
            self.cb_cliente.setCurrentText("")
        self.cb_cliente.blockSignals(False)

        # Limpar restantes campos editaveis
        for w in [self.ed_enc_phc, self.ed_ref_cliente, self.ed_obra, self.ed_preco, self.ed_loc]:
            w.clear()
        self.ed_desc.clear()
        self.ed_info1.clear()
        self.ed_info2.clear()

    def on_novo(self):
        """Acao do botao Inserir Novo Orcamento."""
        self._prepare_new_form()

    def on_save(self):
        """Acao do botao Gravar Orcamento."""
        try:
            cid = self._clients[self.cb_cliente.currentIndex()].id if self.cb_cliente.currentIndex() >= 0 else None
            if not cid:
                QtWidgets.QMessageBox.warning(self, "Cliente", "Selecione um cliente.")
                return

            ano_txt = self.ed_ano.text().strip()
            if len(ano_txt) != 4 or not ano_txt.isdigit():
                QtWidgets.QMessageBox.warning(self, "Ano", "Indique um ano valido (AAAA).")
                return

            yy = ano_txt[-2:]
            seq = self.ed_num.text().strip().zfill(4)
            num_concat = f"{yy}{seq}"
            versao_txt = self._format_version(self.ed_ver.text())
            ref_cliente_txt = (self.ed_ref_cliente.text() or "").strip() or None

            if self._current_id is None:
                # Novo orcamento
                from Martelo_Orcamentos_V2.app.models import Orcamento

                if ref_cliente_txt:
                    matches = (
                        self.db.execute(select(Orcamento).where(Orcamento.ref_cliente == ref_cliente_txt))
                        .scalars()
                        .all()
                    )
                    if matches and not self._confirm_ref_cliente_duplicate(ref_cliente_txt, matches):
                        return

                exists = self.db.execute(
                    select(Orcamento.id).where(
                        and_(Orcamento.ano == ano_txt, Orcamento.num_orcamento == num_concat, Orcamento.versao == versao_txt)
                    )
                ).scalar_one_or_none()
                if exists:
                    QtWidgets.QMessageBox.warning(self, "Duplicado", "Ja existe um orcamento com este ano, numero e versao.")
                    return
                cliente = self._clients[self.cb_cliente.currentIndex()]
                o = create_orcamento(
                    self.db,
                    ano=ano_txt,
                    num_orcamento=num_concat,
                    versao=versao_txt,
                    cliente_nome=cliente.nome,
                    client_id=cliente.id,
                    created_by=getattr(self.current_user, "id", None),
                )
                o.client_id = cid
            else:
                # Editar orcamento existente
                from Martelo_Orcamentos_V2.app.models import Orcamento

                o = self.db.get(Orcamento, self._current_id)
                if not o:
                    QtWidgets.QMessageBox.critical(self, "Erro", "Registo nao encontrado.")
                    return
                o.client_id = cid

            # Guardar restantes campos
            o.data = self.ed_data.date().toString("yyyy-MM-dd")
            o.status = self.cb_status.currentText()
            o.enc_phc = self.ed_enc_phc.text().strip() or None
            o.ref_cliente = ref_cliente_txt
            o.obra = self.ed_obra.text().strip() or None
            o.preco_total = self._parse_currency(self.ed_preco.text())
            o.descricao_orcamento = self.ed_desc.toPlainText() or None
            o.localizacao = self.ed_loc.text().strip() or None
            o.info_1 = self.ed_info1.toPlainText() or None
            o.info_2 = self.ed_info2.toPlainText() or None

            self.db.commit()
            was_new = self._current_id is None
            logger.info(
                "orcamento.save ok action=%s id=%s cliente_id=%s ano=%s num=%s ver=%s user_id=%s",
                "novo" if was_new else "editar",
                getattr(o, "id", None),
                cid,
                ano_txt,
                num_concat,
                versao_txt,
                getattr(self.current_user, "id", None),
            )
            if was_new:
                # Após gravar, actualiza a lista e selecciona a linha do orcamento
                # criado sem disparar o handler de selecao. Isto garante que
                # outras páginas conseguem identificar imediatamente o novo
                # orcamento (por ex.: ao clicar em 'Abrir Itens') sem reiniciar.
                self.refresh(select_first=False)
                try:
                    new_id = getattr(o, "id", None)
                    if new_id is not None:
                        # procurar index da nova linha no modelo
                        idx = next((i for i, r in enumerate(self.model._rows) if getattr(r, "id", None) == new_id), None)
                        if idx is not None:
                            sel_model = self.table.selectionModel()
                            try:
                                sel_model.blockSignals(True)
                            except Exception:
                                pass
                            try:
                                self.table.selectRow(idx)
                                self.table.scrollTo(self.model.index(idx, 0))
                            finally:
                                try:
                                    sel_model.blockSignals(False)
                                except Exception:
                                    pass
                except Exception:
                    pass
                # preparar formulário para próximo registo
                self._prepare_new_form(ano_txt)
            else:
                self.refresh()

            QtWidgets.QMessageBox.information(self, "OK", "Orcamento gravado.")
        except Exception as e:
            self.db.rollback()
            logger.exception(
                "orcamento.save erro id=%s cliente_id=%s ano=%s num=%s ver=%s user_id=%s",
                self._current_id,
                cid if "cid" in locals() else None,
                self.ed_ano.text().strip(),
                self.ed_num.text().strip(),
                self.ed_ver.text().strip(),
                getattr(self.current_user, "id", None),
            )
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar: {e}")

    def on_duplicate(self):
        oid = self.selected_id()
        if not oid:
            return
        try:
            dup = duplicate_orcamento_version(self.db, oid, created_by=getattr(self.current_user, "id", None))
            self.db.commit()
            logger.info(
                "orcamento.duplicar ok origem_id=%s nova_id=%s versao=%s user_id=%s",
                oid,
                getattr(dup, "id", None),
                getattr(dup, "versao", None),
                getattr(self.current_user, "id", None),
            )
            self.refresh()
            QtWidgets.QMessageBox.information(self, "OK", f"Criada versao {dup.versao} do orcamento {dup.num_orcamento}.")
        except Exception as e:
            self.db.rollback()
            logger.exception("orcamento.duplicar erro origem_id=%s user_id=%s", oid, getattr(self.current_user, "id", None))
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao duplicar: {e}")

    def on_delete(self):
        oid = self.selected_id()
        if not oid:
            return
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle("Eliminar Orcamento")
        box.setText("O que pretende eliminar?")
        btn_bd = box.addButton("Eliminar na Base de Dados", QtWidgets.QMessageBox.AcceptRole)
        btn_pastas = box.addButton("Eliminar Pastas do Orcamento", QtWidgets.QMessageBox.DestructiveRole)
        box.addButton(QtWidgets.QMessageBox.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked == btn_bd:
            try:
                delete_orcamento(self.db, oid)
                self.db.commit()
                logger.info("orcamento.delete ok id=%s user_id=%s", oid, getattr(self.current_user, "id", None))
            except Exception as e:
                self.db.rollback()
                logger.exception("orcamento.delete erro id=%s user_id=%s", oid, getattr(self.current_user, "id", None))
                QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar: {e}")
            self.refresh()
        elif clicked == btn_pastas:
            self._delete_orcamento_folders(oid)

    def on_open(self):
        oid = self.selected_id()
        if oid:
            self.orcamento_aberto.emit(oid)

    # Pastas
    def _delete_orcamento_folders(self, oid: int):
        from Martelo_Orcamentos_V2.app.models import Orcamento, Client

        o = self.db.get(Orcamento, oid)
        if not o:
            return
        base = get_setting(
            self.db,
            "base_path_orcamentos",
            r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2",
        )
        yy_path = os.path.join(base, str(o.ano))
        client = self.db.get(Client, o.client_id)
        simplex = (client.nome_simplex or client.nome or "CLIENTE").upper().replace(" ", "_")
        pasta_orc = f"{o.num_orcamento}_{simplex}"
        dir_orc = os.path.join(yy_path, pasta_orc)
        ver_dir = self._format_version(o.versao)
        dir_ver = os.path.join(dir_orc, ver_dir)
        alt_dir_ver = os.path.join(dir_orc, str(o.versao))
        removed = []
        for d in dict.fromkeys([dir_ver, alt_dir_ver, dir_orc]):
            try:
                if os.path.isdir(d):
                    import shutil

                    shutil.rmtree(d)
                    removed.append(d)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Aviso", f"Falha ao eliminar pasta {d}: {e}")
        if removed:
            QtWidgets.QMessageBox.information(self, "OK", "Pasta(s) eliminada(s):\n" + "\n".join(removed))

    def on_create_folder(self):
        from Martelo_Orcamentos_V2.app.models import Orcamento, Client

        row = self.selected_row()
        if not row:
            return
        o = self.db.get(Orcamento, row.id)
        if not o:
            return
        base = get_setting(
            self.db,
            "base_path_orcamentos",
            r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2",
        )
        client = self.db.get(Client, o.client_id)
        yy_path = os.path.join(base, str(o.ano))
        simplex = (client.nome_simplex or client.nome or "CLIENTE").upper().replace(" ", "_")
        pasta = f"{o.num_orcamento}_{simplex}"
        ver_dir = self._format_version(o.versao)
        dir_ver = os.path.join(yy_path, pasta, ver_dir)
        try:
            os.makedirs(dir_ver, exist_ok=True)
            QtWidgets.QMessageBox.information(self, "OK", f"Pasta criada:\n{dir_ver}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao criar pasta: {e}")

    def on_open_folder(self):
        from Martelo_Orcamentos_V2.app.models import Orcamento, Client

        row = self.selected_row()
        if not row:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um orcamento.")
            return
        o = self.db.get(Orcamento, row.id)
        if not o:
            return
        base = get_setting(
            self.db,
            "base_path_orcamentos",
            r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2",
        )
        client = self.db.get(Client, o.client_id)
        yy_path = os.path.join(base, str(o.ano))
        simplex = (client.nome_simplex or client.nome or "CLIENTE").upper().replace(" ", "_")
        pasta = f"{o.num_orcamento}_{simplex}"
        ver_dir = self._format_version(o.versao)
        dir_ver = os.path.join(yy_path, pasta, ver_dir)
        alt_dir_ver = os.path.join(yy_path, pasta, str(o.versao))
        base_pasta = os.path.join(yy_path, pasta)
        if os.path.isdir(dir_ver):
            target = dir_ver
        elif os.path.isdir(alt_dir_ver):
            target = alt_dir_ver
        else:
            target = base_pasta
        try:
            if os.path.isdir(target):
                os.startfile(target)
            else:
                QtWidgets.QMessageBox.information(self, "Info", "A pasta ainda nao existe. Use 'Criar Pasta do Orcamento'.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao abrir pasta: {e}")

    def on_search(self, text: str):
        rows = search_orcamentos(self.db, text)
        self.model.set_rows(rows)
