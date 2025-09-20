from typing import Optional
from PySide6 import QtWidgets
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import QStyle, QCompleter, QToolButton
from sqlalchemy import select, and_
from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.orcamentos import (
    list_orcamentos, create_orcamento, delete_orcamento,
    next_seq_for_year, duplicate_orcamento_version, search_orcamentos,
)
from Martelo_Orcamentos_V2.app.services.clients import list_clients
from Martelo_Orcamentos_V2.app.services.settings import get_setting
from .clientes import label_with_icon
from ..models.qt_table import SimpleTableModel
import os


class OrcamentosPage(QtWidgets.QWidget):
    orcamento_aberto = Signal(int)  # id_orcamento

    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.db = SessionLocal()

        # Pesquisa + tabela
        search_bar = QtWidgets.QHBoxLayout()
        self.ed_search = QtWidgets.QLineEdit()
        self.ed_search.setPlaceholderText("Pesquisar orçamentos… use % para multi-termos")
        btn_clear = QToolButton(); btn_clear.setText("✕"); btn_clear.clicked.connect(lambda: self.ed_search.setText(""))
        search_bar.addWidget(self.ed_search, 1); search_bar.addWidget(btn_clear)
        self.ed_search.textChanged.connect(self.on_search)

        self.table = QtWidgets.QTableView(self)
        self.model = SimpleTableModel(columns=[
            ("ID", "id"),
            ("Ano", "ano"),
            ("Nº Orçamento", "num_orcamento"),
            ("Versão", "versao"),
            ("Cliente", "cliente"),
            ("Data", "data"),
            ("Preço", "preco"),
            ("Utilizador", "utilizador"),
            ("Estado", "estado"),
            ("Obra", "obra"),
            ("Descrição", "descricao"),
            ("Localização", "localizacao"),
            ("Info 1", "info_1"),
            ("Info 2", "info_2"),
        ])
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.selectionModel().selectionChanged.connect(self.load_selected)

        # Botões (com ícones)
        s = self.style()
        btn_novo = QtWidgets.QPushButton(); btn_novo.setIcon(s.standardIcon(QStyle.SP_FileIcon)); btn_novo.setText("Inserir Novo Orçamento"); btn_novo.clicked.connect(self.on_novo)
        btn_save = QtWidgets.QPushButton(); btn_save.setIcon(s.standardIcon(QStyle.SP_DialogSaveButton)); btn_save.setText("Gravar Orçamento"); btn_save.clicked.connect(self.on_save)
        btn_dup = QtWidgets.QPushButton(); btn_dup.setIcon(s.standardIcon(QStyle.SP_BrowserReload)); btn_dup.setText("Duplicar p/ Versão"); btn_dup.clicked.connect(self.on_duplicate)
        btn_del = QtWidgets.QPushButton(); btn_del.setIcon(s.standardIcon(QStyle.SP_TrashIcon)); btn_del.setText("Eliminar Orçamento"); btn_del.clicked.connect(self.on_delete)
        btn_folder = QtWidgets.QPushButton(); btn_folder.setIcon(s.standardIcon(QStyle.SP_DirIcon)); btn_folder.setText("Criar Pasta do Orçamento"); btn_folder.clicked.connect(self.on_create_folder)
        btn_open_folder = QtWidgets.QPushButton(); btn_open_folder.setIcon(s.standardIcon(QStyle.SP_DialogOpenButton)); btn_open_folder.setText("Abrir Pasta Orçamento"); btn_open_folder.clicked.connect(self.on_open_folder)
        btn_open = QtWidgets.QPushButton(); btn_open.setIcon(s.standardIcon(QStyle.SP_ArrowRight)); btn_open.setText("Abrir Itens"); btn_open.clicked.connect(self.on_open)
        btn_refresh = QtWidgets.QPushButton(); btn_refresh.setIcon(s.standardIcon(QStyle.SP_BrowserReload)); btn_refresh.setText("Atualizar"); btn_refresh.clicked.connect(lambda: (self.refresh(), self._load_clients()))

        # Formulário
        self.cb_cliente = QtWidgets.QComboBox(); self.cb_cliente.setEditable(True); self._clients = []; self._load_clients()
        self.ed_ano = QtWidgets.QLineEdit()
        self.ed_num = QtWidgets.QLineEdit(); self.ed_num.setReadOnly(True)
        self.ed_ver = QtWidgets.QLineEdit("01")
        self.ed_data = QtWidgets.QDateEdit(); self.ed_data.setDisplayFormat("dd-MM-yyyy"); self.ed_data.setDate(QDate.currentDate())
        self.lbl_user = QtWidgets.QLabel(getattr(self.current_user, 'username', '(utilizador)') or '(utilizador)')
        self.lbl_user.setFixedHeight(20)
        self.lbl_user.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.cb_status = QtWidgets.QComboBox(); self.cb_status.addItems(["Falta Orçamentar", "Enviado", "Adjudicado", "Sem Interesse", "Não Adjudicado"])
        self.ed_enc_phc = QtWidgets.QLineEdit()
        self.ed_obra = QtWidgets.QLineEdit()
        self.ed_preco = QtWidgets.QLineEdit()
        self.ed_desc = QtWidgets.QTextEdit(); self.ed_desc.setFixedHeight(60)
        self.ed_loc = QtWidgets.QLineEdit()
        self.ed_info1 = QtWidgets.QTextEdit(); self.ed_info1.setFixedHeight(60)
        self.ed_info2 = QtWidgets.QTextEdit(); self.ed_info2.setFixedHeight(60)

        form = QtWidgets.QFormLayout()
        form.setSpacing(6)
        form.setContentsMargins(6, 6, 6, 6)
        form.addRow(label_with_icon("Cliente", QStyle.SP_ComputerIcon), self.cb_cliente)
        form.addRow(label_with_icon("Ano", QStyle.SP_FileDialogDetailedView), self.ed_ano)
        form.addRow(label_with_icon("Nº Orçamento (seq)", QStyle.SP_FileIcon), self.ed_num)
        form.addRow(label_with_icon("Versão", QStyle.SP_DialogOkButton), self.ed_ver)
        form.addRow(label_with_icon("Data", QStyle.SP_DialogYesButton), self.ed_data)
        form.addRow(label_with_icon("Utilizador", QStyle.SP_DirIcon), self.lbl_user)
        form.addRow(label_with_icon("Estado", QStyle.SP_MessageBoxInformation), self.cb_status)
        form.addRow(label_with_icon("Enc PHC", QStyle.SP_DesktopIcon), self.ed_enc_phc)
        form.addRow(label_with_icon("Obra", QStyle.SP_FileDialogListView), self.ed_obra)
        form.addRow(label_with_icon("Preço Orçamento", QStyle.SP_DriveHDIcon), self.ed_preco)
        form.addRow(label_with_icon("Descrição Orçamento", QStyle.SP_FileIcon), self.ed_desc)
        form.addRow(label_with_icon("Localização", QStyle.SP_DriveNetIcon), self.ed_loc)
        form.addRow(label_with_icon("Info 1", QStyle.SP_DialogHelpButton), self.ed_info1)
        form.addRow(label_with_icon("Info 2", QStyle.SP_DialogHelpButton), self.ed_info2)

        buttons = QtWidgets.QHBoxLayout()
        for b in [btn_novo, btn_save, btn_dup, btn_del, btn_folder, btn_open_folder, btn_open, btn_refresh]:
            buttons.addWidget(b)
        buttons.addStretch(1)

        left = QtWidgets.QWidget(); vleft = QtWidgets.QVBoxLayout(left); vleft.addLayout(search_bar); vleft.addWidget(self.table)
        right = QtWidgets.QWidget(); vright = QtWidgets.QVBoxLayout(right); vright.addLayout(form); vright.addLayout(buttons)
        split = QtWidgets.QSplitter(); split.addWidget(left); split.addWidget(right)
        split.setStretchFactor(0, 4); split.setStretchFactor(1, 3)
        split.setSizes([900, 500])

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(split)


        self._current_id = None
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
        # O número é sempre gerido automaticamente
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
        self.ed_obra.setText(o.obra or "")
        if o.preco_total is None:
            self.ed_preco.clear()
        else:
            try:
                self.ed_preco.setText(f"{float(o.preco_total):.2f}")
            except Exception:
                self.ed_preco.setText(str(o.preco_total))
        self.ed_desc.setPlainText(o.descricao_orcamento or "")
        self.ed_loc.setText(o.localizacao or "")
        self.ed_info1.setPlainText(o.info_1 or "")
        self.ed_info2.setPlainText(o.info_2 or "")

    # Ações
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

    def _prepare_new_form(self, ano: Optional[str] = None):
        """Prepara o formulário para um novo orçamento."""
        self.table.clearSelection()
        self._current_id = None
        self._set_identity_lock(False)

        # Ano atual (ou passado como argumento)
        ano_full = (ano or str(QDate.currentDate().year())).strip() or str(QDate.currentDate().year())
        self.ed_ano.setText(ano_full)

        # Calcula próximo nº sequencial (0001, 0002, …)
        try:
            seq_txt = next_seq_for_year(self.db, ano_full)
        except Exception:
            seq_txt = "0001"
        self.ed_num.setText(seq_txt)

        # Valores iniciais padrão
        self.ed_ver.setText("01")
        self.ed_data.setDate(QDate.currentDate())
        self.cb_status.setCurrentText("Falta Orçamentar")
        self.cb_cliente.blockSignals(True)
        self.cb_cliente.setCurrentIndex(-1)
        if self.cb_cliente.isEditable():
            self.cb_cliente.setCurrentText("")
        self.cb_cliente.blockSignals(False)

        # Limpar restantes campos editáveis
        for w in [self.ed_enc_phc, self.ed_obra, self.ed_preco, self.ed_loc]:
            w.clear()
        self.ed_desc.clear()
        self.ed_info1.clear()
        self.ed_info2.clear()

    def on_novo(self):
        """Ação do botão Inserir Novo Orçamento."""
        self._prepare_new_form()

    def on_save(self):
        """Ação do botão Gravar Orçamento."""
        try:
            cid = self._clients[self.cb_cliente.currentIndex()].id if self.cb_cliente.currentIndex() >= 0 else None
            if not cid:
                QtWidgets.QMessageBox.warning(self, "Cliente", "Selecione um cliente.")
                return

            ano_txt = self.ed_ano.text().strip()
            if len(ano_txt) != 4 or not ano_txt.isdigit():
                QtWidgets.QMessageBox.warning(self, "Ano", "Indique um ano válido (AAAA).")
                return

            yy = ano_txt[-2:]
            seq = self.ed_num.text().strip().zfill(4)
            num_concat = f"{yy}{seq}"
            versao_txt = self._format_version(self.ed_ver.text())

            if self._current_id is None:
                # Novo orçamento
                from Martelo_Orcamentos_V2.app.models import Orcamento
                exists = self.db.execute(
                    select(Orcamento.id).where(
                        and_(
                            Orcamento.ano == ano_txt,
                            Orcamento.num_orcamento == num_concat,
                            Orcamento.versao == versao_txt,
                        )
                    )
                ).scalar_one_or_none()
                if exists:
                    QtWidgets.QMessageBox.warning(self, "Duplicado",
                                                "Já existe um orçamento com este ano, número e versão.")
                    return
                cliente = self._clients[self.cb_cliente.currentIndex()]
                o = create_orcamento(
                    self.db,
                    ano=ano_txt,
                    num_orcamento=num_concat,
                    versao=versao_txt,
                    cliente_nome=cliente.nome,
                    client_id=cliente.id,
                    created_by=getattr(self.current_user, 'id', None),
                )
                o.client_id = cid
            else:
                # Editar orçamento existente
                from Martelo_Orcamentos_V2.app.models import Orcamento
                o = self.db.get(Orcamento, self._current_id)
                if not o:
                    QtWidgets.QMessageBox.critical(self, "Erro", "Registo não encontrado.")
                    return
                o.client_id = cid

            # Guardar restantes campos
            o.data = self.ed_data.date().toString("yyyy-MM-dd")
            o.status = self.cb_status.currentText()
            o.enc_phc = self.ed_enc_phc.text().strip() or None
            o.obra = self.ed_obra.text().strip() or None
            o.preco_total = float(self.ed_preco.text().replace(',', '.')) if self.ed_preco.text().strip() else None
            o.descricao_orcamento = self.ed_desc.toPlainText() or None
            o.localizacao = self.ed_loc.text().strip() or None
            o.info_1 = self.ed_info1.toPlainText() or None
            o.info_2 = self.ed_info2.toPlainText() or None

            self.db.commit()
            was_new = self._current_id is None
            if was_new:
                # Após gravar, já prepara o próximo nº
                self.refresh(select_first=False)
                self._prepare_new_form(ano_txt)
            else:
                self.refresh()

            QtWidgets.QMessageBox.information(self, "OK", "Orçamento gravado.")
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar: {e}")

    def on_duplicate(self):
        oid = self.selected_id()
        if not oid:
            return
        try:
            dup = duplicate_orcamento_version(self.db, oid)
            self.db.commit()
            self.refresh()
            QtWidgets.QMessageBox.information(self, "OK", f"Criada versão {dup.versao} do orçamento {dup.num_orcamento}.")
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao duplicar: {e}")

    def on_delete(self):
        oid = self.selected_id()
        if not oid:
            return
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle("Eliminar Orçamento")
        box.setText("O que pretende eliminar?")
        btn_bd = box.addButton("Eliminar na Base de Dados", QtWidgets.QMessageBox.AcceptRole)
        btn_pastas = box.addButton("Eliminar Pastas do Orçamento", QtWidgets.QMessageBox.DestructiveRole)
        box.addButton(QtWidgets.QMessageBox.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked == btn_bd:
            try:
                delete_orcamento(self.db, oid)
                self.db.commit()
            except Exception as e:
                self.db.rollback()
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
        base = get_setting(self.db, "base_path_orcamentos", r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2")
        yy_path = os.path.join(base, str(o.ano))
        client = self.db.get(Client, o.client_id)
        simplex = (client.nome_simplex or client.nome or "CLIENTE").upper().replace(' ', '_')
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
        base = get_setting(self.db, "base_path_orcamentos", r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2")
        client = self.db.get(Client, o.client_id)
        yy_path = os.path.join(base, str(o.ano))
        simplex = (client.nome_simplex or client.nome or "CLIENTE").upper().replace(' ', '_')
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
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um orçamento.")
            return
        o = self.db.get(Orcamento, row.id)
        if not o:
            return
        base = get_setting(self.db, "base_path_orcamentos", r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2")
        client = self.db.get(Client, o.client_id)
        yy_path = os.path.join(base, str(o.ano))
        simplex = (client.nome_simplex or client.nome or "CLIENTE").upper().replace(' ', '_')
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
                QtWidgets.QMessageBox.information(self, "Info", "A pasta ainda não existe. Use 'Criar Pasta do Orçamento'.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao abrir pasta: {e}")

    def on_search(self, text: str):
        rows = search_orcamentos(self.db, text)
        self.model.set_rows(rows)
