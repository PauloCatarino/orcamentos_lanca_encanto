from decimal import Decimal, InvalidOperation
from typing import Optional
from PySide6 import QtWidgets
from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.orcamentos import (
    list_items,
    create_item,
    update_item,
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

# Formulário de inserção/edição
        self.form_frame = QtWidgets.QFrame()
        self.form_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.form_frame.setStyleSheet("""
            QFrame {
                background-color: #fdfdfd;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
            }
            QLabel {
                font-weight: 600;
            }
            QLineEdit {
                padding: 4px;
            }
        """)
        form = QtWidgets.QGridLayout(self.form_frame)
        form.setContentsMargins(8, 8, 8, 8)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(6)

        def _label(text: str) -> QtWidgets.QLabel:
            return QtWidgets.QLabel(text)

        self.edit_item = QtWidgets.QLineEdit()
        self.edit_codigo = QtWidgets.QLineEdit()
        self.edit_descricao = QtWidgets.QLineEdit()
        self.edit_altura = QtWidgets.QLineEdit()
        self.edit_largura = QtWidgets.QLineEdit()
        self.edit_profundidade = QtWidgets.QLineEdit()
        self.edit_und = QtWidgets.QLineEdit()
        self.edit_qt = QtWidgets.QLineEdit()
        self.edit_und.setPlaceholderText("und")
        self.edit_qt.setPlaceholderText("1")

        form.addWidget(_label("Item"), 0, 0)
        form.addWidget(self.edit_item, 0, 1)
        form.addWidget(_label("Código"), 0, 2)
        form.addWidget(self.edit_codigo, 0, 3)

        form.addWidget(_label("Descrição"), 1, 0)
        form.addWidget(self.edit_descricao, 1, 1, 1, 3)

        form.addWidget(_label("Altura"), 2, 0)
        form.addWidget(self.edit_altura, 2, 1)
        form.addWidget(_label("Largura"), 2, 2)
        form.addWidget(self.edit_largura, 2, 3)

        form.addWidget(_label("Profundidade"), 3, 0)
        form.addWidget(self.edit_profundidade, 3, 1)
        form.addWidget(_label("Und"), 3, 2)
        form.addWidget(self.edit_und, 3, 3)

        form.addWidget(_label("QT"), 4, 0)
        form.addWidget(self.edit_qt, 4, 1)
        form.setColumnStretch(1, 1)
        form.setColumnStretch(3, 1)

        # Tabela de itens
        self.table = QtWidgets.QTableView(self)
        self.model = SimpleTableModel(columns=[
            ("ID", "id_item"),
            ("Item", "item_nome"),
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

        # Toolbar
        btn_add = QtWidgets.QPushButton("Novo Item")
        btn_edit = QtWidgets.QPushButton("Editar Item")
        btn_del = QtWidgets.QPushButton("Eliminar Item")
        btn_up = QtWidgets.QPushButton("↑")
        btn_dn = QtWidgets.QPushButton("↓")
        btn_add.clicked.connect(self.on_add)
        btn_edit.clicked.connect(self.on_edit)
        btn_del.clicked.connect(self.on_del)
        btn_up.clicked.connect(lambda: self.on_move(-1))
        btn_dn.clicked.connect(lambda: self.on_move(1))

        buttons = QtWidgets.QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        buttons.addStretch(1)
        buttons.addWidget(btn_add)
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

    def _decimal_from_input(
        self,
        widget: QtWidgets.QLineEdit,
        label: str,
        *,
        default: Optional[Decimal] = None,
    ) -> Optional[Decimal]:
        try:
            return self._parse_decimal(widget.text(), default=default)
        except ValueError:
            raise ValueError(f"Valor inválido para {label}.")

    def _collect_form_data(self) -> dict:
        return {
            "item_nome": self.edit_item.text().strip() or None,
            "codigo": self.edit_codigo.text().strip() or None,
            "descricao": self.edit_descricao.text().strip() or None,
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
        self.edit_item.setText(item.item_nome or "")
        self.edit_codigo.setText(item.codigo or "")
        self.edit_descricao.setText(item.descricao or "")
        self.edit_altura.setText(self._format_decimal(item.altura))
        self.edit_largura.setText(self._format_decimal(item.largura))
        self.edit_profundidade.setText(self._format_decimal(item.profundidade))
        self.edit_und.setText(item.und or "und")
        qt_txt = self._format_decimal(item.qt)
        self.edit_qt.setText(qt_txt or "1")

    def _clear_form(self):
        self.edit_item.clear()
        self.edit_codigo.clear()
        self.edit_descricao.clear()
        self.edit_altura.clear()
        self.edit_largura.clear()
        self.edit_profundidade.clear()
        self.edit_und.setText("und")
        self.edit_qt.setText("1")

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


    def on_add(self):
        """Insere um novo item no orçamento com todos os campos corretos."""
        if not self._orc_id:
            QtWidgets.QMessageBox.warning(
                self, "Orçamento não carregado",
                "Nenhum orçamento está ativo. Carregue um orçamento antes de adicionar itens."
            )
            return

        # Tentar obter a versão atual do orçamento a partir do label (lbl_ver_val)
        versao_atual = self.lbl_ver_val.text().strip()
        if not versao_atual:
            QtWidgets.QMessageBox.warning(
                self, "Versão não definida",
                "A versão do orçamento não está definida. Verifique os dados do orçamento."
            )
            return

        try:
            # Coleta dados do formulário (item, código, medidas, etc.)
            data = self._collect_form_data()

            # 🔄 Ajustar o nome da chave 'item_nome' para 'item'
            if "item_nome" in data:
                data["item"] = data.pop("item_nome")

            # 🆕 Adicionar campo 'versao' ao dicionário de inserção
            data["versao"] = versao_atual.zfill(2)  # garante formato '01', '02', etc.

        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Dados inválidos", str(exc))
            return

        # Inserção no banco de dados
        try:
            create_item(
                self.db,
                self._orc_id,
                created_by=self._current_user_id(),
                **data,
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(
                self, "Erro ao criar item", f"Falha ao criar item: {e}"
            )
            return

        # Atualizar a tabela e selecionar o último item inserido
        self.refresh(select_last=True)

    def on_edit(self):
        """Edita o item selecionado no orçamento garantindo consistência com a base de dados."""

        # 🛑 Verificar se há item selecionado
        id_item = self.selected_id()
        if not id_item:
            QtWidgets.QMessageBox.information(
                self,
                "Editar Item",
                "Selecione um item da tabela para editar."
            )
            return

        # 🛑 Verificar se um orçamento está carregado
        if not self._orc_id:
            QtWidgets.QMessageBox.warning(
                self,
                "Orçamento não carregado",
                "Nenhum orçamento ativo. Carregue um orçamento antes de editar itens."
            )
            return

        # 🆕 Obter a versão atual associada ao orçamento
        versao_atual = self.lbl_ver_val.text().strip()
        if not versao_atual:
            QtWidgets.QMessageBox.warning(
                self,
                "Versão não definida",
                "A versão do orçamento não está definida. Verifique os dados antes de editar."
            )
            return

        # 🧪 Coletar os dados do formulário
        try:
            data = self._collect_form_data()
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Dados inválidos", str(exc))
            return

        # 🛠️ Ajustar nomes de campos para corresponder aos nomes reais da BD
        if "item_nome" in data:
            data["item"] = data.pop("item_nome")

        # ✅ Garantir que 'versao' é sempre enviado para a BD
        data["versao"] = versao_atual.zfill(2)

        # 🔄 Atualizar o item no banco de dados
        current_row = self.table.currentIndex().row()
        try:
            update_item(
                self.db,
                id_item,
                updated_by=self._current_user_id(),
                **data,
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(
                self,
                "Erro",
                f"Falha ao atualizar item no banco de dados:\n{e}"
            )
            return

        # 🔄 Atualizar a tabela e manter a seleção na mesma linha
        self.refresh(select_row=current_row)

        QtWidgets.QMessageBox.information(
            self,
            "Item atualizado",
            "O item foi atualizado com sucesso!"
        )

    def on_del(self):
        id_item = self.selected_id()
        if not id_item:
            return
        if QtWidgets.QMessageBox.question(self, "Confirmar",
                                          f"Eliminar item {id_item}?") != QtWidgets.QMessageBox.Yes:
            return
        current_row = self.table.currentIndex().row()
        try:
            delete_item(self.db, id_item)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar: {e}")
            return
        self.refresh(select_row=current_row)

    def on_move(self, direction: int):
        id_item = self.selected_id()
        if not id_item:
            return
        current_row = self.table.currentIndex().row()
        try:
            move_item(self.db, id_item, direction)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao mover: {e}")
            return
        self.refresh(select_row=current_row + direction)
