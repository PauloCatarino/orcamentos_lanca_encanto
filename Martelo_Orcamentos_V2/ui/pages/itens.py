# Martelo_Orcamentos_V2/ui/pages/itens.py
# -----------------------------------------------------------------------------
# Página de Itens do Orçamento (V2)
# - Campo "Item" é sempre gerado automaticamente (sequencial por orçamento+versão)
#   e não pode ser editado pelo utilizador.
# - Botões: "Inserir Novo Item" (limpa e prepara formulário) e
#           "Gravar Item" (insere na BD e seleciona última linha).
# - Edição: "Editar Item" atualiza os campos permitidos, mantendo o "Item".
# - Descrição: QTextEdit (multi-linha), usa .toPlainText().
# -----------------------------------------------------------------------------

from decimal import Decimal, InvalidOperation
from typing import Optional

from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt

# SQLAlchemy
from sqlalchemy import select, func

# Projeto
from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.orcamentos import (
    list_items,
    create_item,
    update_item,
    delete_item,
    move_item,
)
from Martelo_Orcamentos_V2.app.models import Orcamento, Client, User
from Martelo_Orcamentos_V2.app.models.orcamento import OrcamentoItem
from ..models.qt_table import SimpleTableModel


class ItensPage(QtWidgets.QWidget):
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.db = SessionLocal()
        self._orc_id = None

        # ---------- Cabeçalho ----------
        self.header = QtWidgets.QFrame()
        self.header.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.header.setStyleSheet("""
            QFrame { background-color: #f5f5f5; border: 1px solid #ccc; border-radius: 8px; padding: 10px; }
            QLabel { font-weight: bold; color: #333; }
            QLabel.value { font-weight: normal; color: #000; }
        """)

        self.lbl_cliente = QtWidgets.QLabel("Cliente:");   self.lbl_cliente_val = QtWidgets.QLabel("")
        self.lbl_ano = QtWidgets.QLabel("Ano:");          self.lbl_ano_val = QtWidgets.QLabel("")
        self.lbl_num = QtWidgets.QLabel("Nº Orçamento:"); self.lbl_num_val = QtWidgets.QLabel("")
        self.lbl_ver = QtWidgets.QLabel("Versão:");       self.lbl_ver_val = QtWidgets.QLabel("")
        self.lbl_user = QtWidgets.QLabel("Utilizador:");  self.lbl_user_val = QtWidgets.QLabel("")

        for w in [self.lbl_cliente_val, self.lbl_ano_val, self.lbl_num_val, self.lbl_ver_val, self.lbl_user_val]:
            w.setProperty("class", "value")

        grid = QtWidgets.QGridLayout(self.header)
        grid.setContentsMargins(5, 5, 5, 5)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        for lbl in [self.lbl_cliente, self.lbl_user, self.lbl_ano, self.lbl_num, self.lbl_ver]:
            lbl.setMinimumWidth(80)
            lbl.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)

        grid.addWidget(self.lbl_cliente, 0, 0); grid.addWidget(self.lbl_cliente_val, 0, 1)
        grid.addWidget(self.lbl_user, 0, 2);    grid.addWidget(self.lbl_user_val, 0, 3)

        grid.addWidget(self.lbl_ano, 1, 0);     grid.addWidget(self.lbl_ano_val, 1, 1, 1, 3)

        grid.addWidget(self.lbl_num, 2, 0);     grid.addWidget(self.lbl_num_val, 2, 1)
        grid.addWidget(self.lbl_ver, 2, 2);     grid.addWidget(self.lbl_ver_val, 2, 3)
        grid.setColumnStretch(4, 1)

        # ---------- Formulário ----------
        self.form_frame = QtWidgets.QFrame()
        self.form_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.form_frame.setStyleSheet("""
            QFrame { background-color: #fdfdfd; border: 1px solid #d0d0d0; border-radius: 6px; }
            QLabel { font-weight: 600; }
            QLineEdit, QTextEdit { padding: 4px; }
        """)
        form = QtWidgets.QGridLayout(self.form_frame)
        form.setContentsMargins(8, 8, 8, 8)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(6)

        def _label(text: str) -> QtWidgets.QLabel:
            return QtWidgets.QLabel(text)

        self.edit_item = QtWidgets.QLineEdit()
        self.edit_item.setReadOnly(True)  # 🔒 Item nunca é editável
        self.edit_item.setStyleSheet("background-color: #eaeaea;")
        self.edit_codigo = QtWidgets.QLineEdit()
        # Descrição multi-linha (confirmado por ti): QTextEdit
        self.edit_descricao = QtWidgets.QTextEdit()
        self.edit_descricao.setPlaceholderText("Descrição do item (multi-linha)")

        self.edit_altura = QtWidgets.QLineEdit()
        self.edit_largura = QtWidgets.QLineEdit()
        self.edit_profundidade = QtWidgets.QLineEdit()
        self.edit_und = QtWidgets.QLineEdit()
        self.edit_qt = QtWidgets.QLineEdit()
        self.edit_und.setPlaceholderText("und")
        self.edit_qt.setPlaceholderText("1")

        form.addWidget(_label("Item"), 0, 0);      form.addWidget(self.edit_item, 0, 1)
        form.addWidget(_label("Código"), 0, 2);    form.addWidget(self.edit_codigo, 0, 3)

        form.addWidget(_label("Descrição"), 1, 0); form.addWidget(self.edit_descricao, 1, 1, 1, 3)

        form.addWidget(_label("Altura"), 2, 0);    form.addWidget(self.edit_altura, 2, 1)
        form.addWidget(_label("Largura"), 2, 2);   form.addWidget(self.edit_largura, 2, 3)

        form.addWidget(_label("Profundidade"), 3, 0); form.addWidget(self.edit_profundidade, 3, 1)
        form.addWidget(_label("Und"), 3, 2);          form.addWidget(self.edit_und, 3, 3)

        form.addWidget(_label("QT"), 4, 0);        form.addWidget(self.edit_qt, 4, 1)
        form.setColumnStretch(1, 1); form.setColumnStretch(3, 1)

        # ---------- Tabela ----------
        self.table = QtWidgets.QTableView(self)
        self.model = SimpleTableModel(columns=[
            ("ID", "id_item"),
            ("Item", "item_nome"),  # mapeia para coluna 'item' (ORM usa synonym)
            ("Codigo", "codigo"),
            ("Descricao", "descricao"),
            ("Altura", "altura"),
            ("Largura", "largura"),
            ("Profundidade", "profundidade"),
            ("Und", "und"),
            ("QT", "qt"),
            ("Preco_Unit", "preco_unitario"),
            ("Preco_Total", "preco_total"),
            ("Custo Produzido", "custo_produzido"),
            ("Ajuste", "ajuste"),
            ("Custo Total Orlas (€)", "custo_total_orlas"),
            ("Custo Total Mão de Obra (€)", "custo_total_mao_obra"),
            ("Custo Total Matéria Prima (€)", "custo_total_materia_prima"),
            ("Custo Total Acabamentos (€)", "custo_total_acabamentos"),
            ("Margem de Lucro (%)", "margem_lucro_perc"),
            ("Valor da Margem (€)", "valor_margem"),
            ("Custos Administrativos (%)", "custos_admin_perc"),
            ("Valor Custos Admin. (€)", "valor_custos_admin"),
            ("Margem_Acabamentos(%)", "margem_acabamentos_perc"),
            ("Valor Margem_Acabamentos (€)", "valor_acabamentos"),
            ("Margem MP_Orlas (%)", "margem_mp_orlas_perc"),
            ("Valor Margem MP_Orlas (€)", "valor_mp_orlas"),
            ("Margem Mao_Obra (%)", "margem_mao_obra_perc"),
            ("Valor Margem Mao_Obra (€)", "valor_mao_obra"),
            ("reservado_1", "reservado_1"),
            ("reservado_2", "reservado_2"),
            ("reservado_3", "reservado_3"),
        ])
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)

        # ---------- Toolbar ----------
        btn_add = QtWidgets.QPushButton("Inserir Novo Item")  # antes: "Novo Item"
        btn_save = QtWidgets.QPushButton("Gravar Item")       # novo
        btn_edit = QtWidgets.QPushButton("Editar Item")
        btn_del = QtWidgets.QPushButton("Eliminar Item")
        btn_up = QtWidgets.QPushButton("↑")
        btn_dn = QtWidgets.QPushButton("↓")

        btn_add.clicked.connect(self.on_new_item)
        btn_save.clicked.connect(self.on_save_item)
        btn_edit.clicked.connect(self.on_edit)
        btn_del.clicked.connect(self.on_del)
        btn_up.clicked.connect(lambda: self.on_move(-1))
        btn_dn.clicked.connect(lambda: self.on_move(1))

        buttons = QtWidgets.QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        buttons.addStretch(1)
        buttons.addWidget(btn_add)
        buttons.addWidget(btn_save)
        buttons.addWidget(btn_edit)
        buttons.addWidget(btn_del)
        buttons.addWidget(btn_up)
        buttons.addWidget(btn_dn)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(8)
        lay.addWidget(self.header)
        lay.addWidget(self.form_frame)
        lay.addLayout(buttons)
        lay.addWidget(self.table)

        self._clear_form()

    # =========================================
    # Carregamento, refresh e helpers
    # =========================================
    def load_orcamento(self, orc_id: int):
        """Carrega dados do orçamento e preenche cabeçalho."""
        def _txt(v) -> str:
            return "" if v is None else str(v)

        def _fmt_ver(v) -> str:
            if v is None or v == "":
                return ""
            try:
                return f"{int(v):02d}"
            except (TypeError, ValueError):
                return _txt(v)

        self._orc_id = orc_id
        o = self.db.get(Orcamento, orc_id)
        if o:
            cliente = self.db.get(Client, o.client_id)
            user = None
            if o.created_by:
                user = self.db.get(User, o.created_by)
            if not user and getattr(self.current_user, "id", None):
                user = self.db.get(User, getattr(self.current_user, "id", None))
            username = getattr(user, "username", "") or getattr(self.current_user, "username", "") or ""

            self.lbl_cliente_val.setText(_txt(getattr(cliente, "nome", "")))
            self.lbl_ano_val.setText(_txt(getattr(o, "ano", "")))
            self.lbl_num_val.setText(_txt(getattr(o, "num_orcamento", "")))
            self.lbl_ver_val.setText(_fmt_ver(getattr(o, "versao", "")))
            self.lbl_user_val.setText(_txt(username))
        else:
            self.lbl_cliente_val.setText("")
            self.lbl_ano_val.setText("")
            self.lbl_num_val.setText("")
            self.lbl_ver_val.setText("")
            self.lbl_user_val.setText("")

        self.refresh()

    def refresh(self, select_row: Optional[int] = None, select_last: bool = False):
        if not self._orc_id:
            self.model.set_rows([])
            self._clear_form()
            return
        rows = list_items(self.db, self._orc_id)
        self.model.set_rows(rows)
        if rows:
            if select_row is not None:
                row_to_select = max(0, min(select_row, len(rows) - 1))
            elif select_last:
                row_to_select = len(rows) - 1
            else:
                row_to_select = 0
            self.table.selectRow(row_to_select)
        else:
            self._clear_form()

    def selected_id(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        row = self.model.get_row(idx.row())
        return row.id_item

    def _current_user_id(self):
        return getattr(self.current_user, "id", None)

    # ---------- Helpers de parsing/validação ----------
    def _parse_decimal(self, text: Optional[str], *, default: Optional[Decimal] = None) -> Optional[Decimal]:
        if text is None:
            return default
        txt = text.strip()
        if not txt:
            return default
        txt = txt.replace(",", ".")
        try:
            return Decimal(txt)
        except (InvalidOperation, ValueError):
            raise ValueError

    def _decimal_from_input(self, widget: QtWidgets.QLineEdit, label: str, *, default: Optional[Decimal] = None) -> Optional[Decimal]:
        try:
            return self._parse_decimal(widget.text(), default=default)
        except ValueError:
            raise ValueError(f"Valor inválido para {label}.")

    # Coleta os dados do formulário (OBS: 'descricao' é QTextEdit → toPlainText)
    def _collect_form_data(self) -> dict:
        return {
            "item": self.edit_item.text().strip() or None,  # nome visível do item
            "codigo": self.edit_codigo.text().strip() or None,
            "descricao": (self.edit_descricao.toPlainText().strip() or None),
            "altura": self._decimal_from_input(self.edit_altura, "Altura"),
            "largura": self._decimal_from_input(self.edit_largura, "Largura"),
            "profundidade": self._decimal_from_input(self.edit_profundidade, "Profundidade"),
            "und": self.edit_und.text().strip() or None,
            "qt": self._decimal_from_input(self.edit_qt, "QT", default=Decimal("1")),
        }

    def _format_decimal(self, value) -> str:
        if value in (None, ""):
            return ""
        try:
            dec = Decimal(str(value))
        except Exception:
            return str(value)
        text = format(dec, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    def _populate_form(self, item):
        # item.item_nome mapeia para coluna "item" na BD (synonym no ORM)
        self.edit_item.setText(item.item_nome or "")
        self.edit_codigo.setText(item.codigo or "")
        self.edit_descricao.setPlainText(item.descricao or "")
        self.edit_altura.setText(self._format_decimal(item.altura))
        self.edit_largura.setText(self._format_decimal(item.largura))
        self.edit_profundidade.setText(self._format_decimal(item.profundidade))
        self.edit_und.setText(item.und or "und")
        qt_txt = self._format_decimal(item.qt)
        self.edit_qt.setText(qt_txt or "1")
        # 🔒 garantir sempre bloqueado
        self.edit_item.setReadOnly(True)
        self.edit_item.setStyleSheet("background-color: #eaeaea;")

    def _clear_form(self):
        self.edit_item.clear()
        self.edit_codigo.clear()
        self.edit_descricao.clear()
        self.edit_altura.clear()
        self.edit_largura.clear()
        self.edit_profundidade.clear()
        self.edit_und.setText("und")
        self.edit_qt.setText("1")
        self.edit_item.setReadOnly(True)
        self.edit_item.setStyleSheet("background-color: #eaeaea;")

    def on_selection_changed(self, selected, deselected):
        idx = self.table.currentIndex()
        if not idx.isValid():
            self._clear_form()
            return
        try:
            row = self.model.get_row(idx.row())
        except IndexError:
            self._clear_form()
            return
        self._populate_form(row)

    # =========================================
    # Inserção com nova lógica de botões
    # =========================================
    def _next_item_number(self, orc_id, versao):
        """
        Calcula o próximo número de item com base nos itens já existentes
        no orçamento e versão atuais.
        """
        try:
            result = self.db.execute(
                text("""
                    SELECT COALESCE(MAX(item), 0) + 1 AS next_item
                    FROM orcamento_items
                    WHERE id_orcamento = :orc_id AND versao = :versao
                """),
                {"orc_id": orc_id, "versao": versao}
            ).fetchone()

            return result.next_item if result else 1
        except Exception as e:
            print("Erro ao calcular próximo item:", e)
            return 1

    def on_new_item(self):
        """
        Prepara o formulário para inserir um novo item:
        - Limpa os campos.
        - Calcula e preenche o próximo nº de 'Item' (sequencial por orçamento+versão).
        - Mantém o campo 'Item' bloqueado.
        """
        if not self._orc_id:
            QMessageBox.warning(self, "Aviso", "Nenhum orçamento selecionado.")
            return

        versao_atual = (self.lbl_ver_val.text() or "").strip()
        if not versao_atual:
            QMessageBox.warning(self, "Aviso", "Nenhuma versão definida.")
            return

        versao_norm = versao_atual.zfill(2)

        # ✅ 1. Calcular o próximo número de item
        proximo_numero = self._next_item_number(self._orc_id, versao_norm)

        # ✅ 2. Limpar campos do formulário
        self._clear_form()

        # ✅ 3. Preencher automaticamente o campo item com o próximo número
        self.edit_item.setText(str(proximo_numero))
        self.edit_item.setReadOnly(True)
        self.edit_item.setStyleSheet("background-color: #eaeaea;")

        # ✅ 4. Posicionar o cursor no primeiro campo útil
        self.edit_codigo.setFocus()

    def on_save_item(self):
        """
        Grava um item no orçamento:
        - Se não houver item selecionado => INSERE novo item.
        - Se houver item selecionado => ATUALIZA item existente.
        - O campo 'item' é sempre automático e não pode ser alterado.
        - O formulário é limpo após a gravação e já mostra o próximo número de item.
        """

        if not self._orc_id:
            QMessageBox.warning(self, "Aviso", "Nenhum orçamento selecionado.")
            return

        versao_atual = (self.lbl_ver_val.text() or "").strip()
        if not versao_atual:
            QMessageBox.warning(self, "Aviso", "Nenhuma versão definida.")
            return

        versao_norm = versao_atual.zfill(2)

        # Verificar se há item selecionado (para decidir se é INSERT ou UPDATE)
        idx = self.table.currentIndex()
        id_item = None
        if idx.isValid():
            try:
                row = self.model.get_row(idx.row())
                id_item = row.id_item
            except Exception:
                id_item = None

        # ✅ Calcular o próximo número de item se for novo
        if not (self.edit_item.text() or "").strip():
            proximo_numero = self._next_item_number(self._orc_id, versao_norm)
            self.edit_item.setText(str(proximo_numero))

        # ✅ Coletar dados do formulário
        try:
            form = self._collect_form_data()
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
            return

        try:
            if id_item:  # ATUALIZAR ITEM EXISTENTE
                update_item(
                    self.db,
                    id_item,
                    versao=versao_norm,
                    item=form["item"],  # mantém o número original
                    codigo=form["codigo"],
                    descricao=form["descricao"],
                    altura=form["altura"],
                    largura=form["largura"],
                    profundidade=form["profundidade"],
                    und=form["und"],
                    qt=form["qt"],
                    updated_by=self._current_user_id(),
                )
                mensagem = "Item atualizado com sucesso."
            else:  # INSERIR NOVO ITEM
                create_item(
                    self.db,
                    self._orc_id,
                    versao=versao_norm,
                    item=form["item"],
                    codigo=form["codigo"],
                    descricao=form["descricao"],
                    altura=form["altura"],
                    largura=form["largura"],
                    profundidade=form["profundidade"],
                    und=form["und"] or "und",
                    qt=form["qt"],
                    created_by=self._current_user_id(),
                )
                mensagem = "Item gravado com sucesso."

            self.db.commit()
            self.refresh(select_last=True)
            QMessageBox.information(self, "Sucesso", mensagem)

            # ✅ Limpar formulário e preparar para novo item
            self._clear_form()
            proximo_numero = self._next_item_number(self._orc_id, versao_norm)
            self.edit_item.setText(str(proximo_numero))
            self.edit_item.setReadOnly(True)
            self.edit_item.setStyleSheet("background-color: #eaeaea;")
            self.edit_codigo.setFocus()

        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Erro", f"Erro ao gravar item:\n{str(e)}")

    # =========================================
    # Edição, Eliminação e Movimento
    # =========================================
    def on_edit(self):
        """
        Edita manualmente o item selecionado (opcional).
        - Campo 'item' permanece bloqueado e inalterável.
        """
        idx = self.table.currentIndex()
        if not idx.isValid():
            QMessageBox.warning(self, "Aviso", "Selecione um item para editar.")
            return

        try:
            row = self.model.get_row(idx.row())
        except IndexError:
            QMessageBox.warning(self, "Aviso", "Seleção inválida.")
            return

        id_item = row.id_item
        versao_norm = (self.lbl_ver_val.text() or "").strip().zfill(2)

        try:
            form = self._collect_form_data()
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
            return

        try:
            update_item(
                self.db,
                id_item,
                versao=versao_norm,
                item=row.item_nome,  # mantém número original
                codigo=form["codigo"],
                descricao=form["descricao"],
                altura=form["altura"],
                largura=form["largura"],
                profundidade=form["profundidade"],
                und=form["und"],
                qt=form["qt"],
                updated_by=self._current_user_id(),
            )
            self.db.commit()
            self.refresh()
            QMessageBox.information(self, "Sucesso", "Item atualizado com sucesso.")
        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Erro", f"Erro ao atualizar item:\n{str(e)}")


    def on_del(self):
        id_item = self.selected_id()
        if not id_item:
            return
        current_row = self.table.currentIndex().row()
        if QtWidgets.QMessageBox.question(self, "Confirmar", f"Eliminar item {id_item}?") != QtWidgets.QMessageBox.Yes:
            return
        try:
            delete_item(self.db, id_item, deleted_by=self._current_user_id())
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar: {e}")
            return
        # Após eliminar, atualiza e mantém seleção coerente
        self.refresh(select_row=current_row)

    def on_move(self, direction: int):
        id_item = self.selected_id()
        if not id_item:
            return
        current_row = self.table.currentIndex().row()
        try:
            move_item(self.db, id_item, direction, moved_by=self._current_user_id())
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao mover: {e}")
            return
        self.refresh(select_row=current_row)
# Fim do ficheiro