# Martelo_Orcamentos_V2/ui/pages/itens.py
# -----------------------------------------------------------------------------
# Página de Itens do Orçamento (V2)
# - Carrega automaticamente o layout do Qt Designer (itens_form.ui)
# - Mantém as ligações e a lógica (CRUD, mover, expandir/colapsar, etc.)
# - Campos e botões assumem os MESMOS objectNames do .ui
# -----------------------------------------------------------------------------

from decimal import Decimal, InvalidOperation
from typing import Optional

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt, QItemSelectionModel, QFile, QIODevice
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QHeaderView, QMessageBox
from PySide6.QtUiTools import QUiLoader

# Import mantido (não é obrigatório para o load dinâmico, mas útil p/ tipagem)
from Martelo_Orcamentos_V2.ui.forms.itens_form_ui import Ui_ItensForm  # noqa: F401

from sqlalchemy import select, func

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


# -----------------------------------------------------------------------------


class ItensPage(QtWidgets.QWidget):
    """
    Widget/Tab da página de Itens.

    Espera que o ficheiro de UI (Qt Designer) tenha, no mínimo, estes objectNames:
      - Header:
        lbl_cliente_val, lbl_ano_val, lbl_num_val, lbl_ver_val, lbl_user_val
      - Form:
        edit_item, edit_codigo, edit_altura, edit_largura, edit_profundidade,
        edit_qt, edit_und, edit_descricao
      - Tabela:
        table  (QTableView)
      - Botões:
        btn_add, btn_save, btn_del, btn_expand, btn_collapse, btn_up, btn_dn

    Se mudares só o POSICIONAMENTO no Designer (sem mudar nomes), tudo continua OK.
    """

    UI_PATH = "Martelo_Orcamentos_V2/ui/forms/itens_form.ui"

    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.db = SessionLocal()
        self._orc_id: Optional[int] = None
        self._edit_item_id: Optional[int] = None

        # --- Carregar a interface do .ui dinamicamente ---
        self._load_ui(self.UI_PATH)

        # --- Validadores / helpers ---
        self._numeric_validator = QDoubleValidator(0.0, 9_999_999.0, 3, self)
        self._numeric_validator.setNotation(QDoubleValidator.StandardNotation)
        self._numeric_validator.setLocale(QtCore.QLocale.system())

        # Aplicar validador e alinhamento aos campos numéricos
        for field in (self.edit_altura, self.edit_largura, self.edit_profundidade, self.edit_qt):
            field.setValidator(self._numeric_validator)
            field.setAlignment(Qt.AlignRight)

        # Item é sempre automático (read-only)
        self.edit_item.setReadOnly(True)
        self.edit_item.setStyleSheet("background-color: #eaeaea;")

        # Enter avança foco entre campos da primeira linha
        self._input_sequence = [
            self.edit_codigo,
            self.edit_altura,
            self.edit_largura,
            self.edit_profundidade,
            self.edit_qt,
            self.edit_und,
        ]
        for idx, widget in enumerate(self._input_sequence):
            widget.returnPressed.connect(lambda _=False, i=idx: self._focus_next_field(i))

        # Forçar maiúsculas no código
        self.edit_codigo.textEdited.connect(lambda text: self._force_uppercase(self.edit_codigo, text))

        # --- Modelo e Tabela ---
        def fmt_intlike(value):
            if value is None or value == "":
                return ""
            try:
                return str(int(Decimal(str(value))))
            except Exception:
                return str(value)

        table_columns = [
            ("ID", "id_item"),
            ("Item", "item_nome"),
            ("Codigo", "codigo"),
            ("Descricao", "descricao"),
            ("Altura", "altura", fmt_intlike),
            ("Largura", "largura", fmt_intlike),
            ("Profundidade", "profundidade", fmt_intlike),
            ("Und", "und"),
            ("QT", "qt", fmt_intlike),
            ("Preco_Unit", "preco_unitario", fmt_intlike),
            ("Preco_Total", "preco_total", fmt_intlike),
            ("Custo Produzido", "custo_produzido", fmt_intlike),
            ("Ajuste", "ajuste", fmt_intlike),
            ("Custo Total Orlas (€)", "custo_total_orlas", fmt_intlike),
            ("Custo Total Mão de Obra (€)", "custo_total_mao_obra", fmt_intlike),
            ("Custo Total Matéria Prima (€)", "custo_total_materia_prima", fmt_intlike),
            ("Custo Total Acabamentos (€)", "custo_total_acabamentos", fmt_intlike),
            ("Margem de Lucro (%)", "margem_lucro_perc", fmt_intlike),
            ("Valor da Margem (€)", "valor_margem", fmt_intlike),
            ("Custos Administrativos (%)", "custos_admin_perc", fmt_intlike),
            ("Valor Custos Admin. (€)", "valor_custos_admin", fmt_intlike),
            ("Margem_Acabamentos(%)", "margem_acabamentos_perc", fmt_intlike),
            ("Valor Margem_Acabamentos (€)", "valor_acabamentos", fmt_intlike),
            ("Margem MP_Orlas (%)", "margem_mp_orlas_perc", fmt_intlike),
            ("Valor Margem MP_Orlas (€)", "valor_mp_orlas", fmt_intlike),
            ("Margem Mao_Obra (%)", "margem_mao_obra_perc", fmt_intlike),
            ("Valor Margem Mao_Obra (€)", "valor_mao_obra", fmt_intlike),
            ("reservado_1", "reservado_1"),
            ("reservado_2", "reservado_2"),
            ("reservado_3", "reservado_3"),
        ]
        self.model = SimpleTableModel(columns=table_columns)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header_font = header.font()
        header_font.setBold(True)
        header.setFont(header_font)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Larguras iniciais por coluna (opcional, ajusta conforme necessário)
        self._set_initial_column_widths(header, table_columns)

        # Altura das linhas
        self._row_height_collapsed = 26
        self._row_height_expanded = 70
        self._rows_expanded = False
        vert_header = self.table.verticalHeader()
        vert_header.setDefaultSectionSize(self._row_height_collapsed)
        vert_header.setSectionResizeMode(QHeaderView.Fixed)
        self._apply_row_height()

        # Seleção -> preencher formulário
        sel_model = self.table.selectionModel()
        if sel_model:
            sel_model.selectionChanged.connect(self.on_selection_changed)

        # --- Sinais dos botões ---
        self.btn_add.clicked.connect(self.on_new_item)
        self.btn_save.clicked.connect(self.on_save_item)
        self.btn_del.clicked.connect(self.on_del)
        self.btn_expand.clicked.connect(self.on_expand_rows)
        self.btn_collapse.clicked.connect(self.on_collapse_rows)
        self.btn_up.clicked.connect(lambda: self.on_move(-1))
        self.btn_dn.clicked.connect(lambda: self.on_move(1))

        # Preparar estado inicial
        self._clear_form()

    # -----------------------------------------------------------------------------
    # UI loader e binding
    # -----------------------------------------------------------------------------
    def _load_ui(self, ui_path: str) -> None:
        """
        Carrega o .ui e liga os widgets esperados a atributos da classe.
        Se algum objectName não existir no .ui, lança uma exceção com mensagem clara.
        """
        file = QFile(ui_path)
        if not file.exists():
            raise FileNotFoundError(f"UI não encontrado: {ui_path}")
        if not file.open(QIODevice.ReadOnly):
            raise RuntimeError(f"Não foi possível abrir o UI: {ui_path}")

        try:
            loader = QUiLoader()
            ui_root = loader.load(file, self)
            if ui_root is None:
                raise RuntimeError("Falha ao carregar UI (loader.load retornou None).")
        finally:
            file.close()

        # Inserir o UI carregado no layout deste widget
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(ui_root)

        # Helper para obter child com erro claro
        def must(name: str, t):
            w = ui_root.findChild(t, name)
            if w is None:
                raise AttributeError(
                    f"Widget '{name}' (tipo {t.__name__}) não encontrado no UI '{self.UI_PATH}'. "
                    "Confirma o objectName no Qt Designer."
                )
            setattr(self, name, w)
            return w

        # --- Header ---
        for n in ("lbl_cliente_val", "lbl_ano_val", "lbl_num_val", "lbl_ver_val", "lbl_user_val"):
            must(n, QtWidgets.QLabel)

        # --- Form ---
        for n in (
            "edit_item",
            "edit_codigo",
            "edit_altura",
            "edit_largura",
            "edit_profundidade",
            "edit_qt",
            "edit_und",
        ):
            must(n, QtWidgets.QLineEdit)
        must("edit_descricao", QtWidgets.QTextEdit)

        # --- Tabela ---
        self.table = must("table", QtWidgets.QTableView)

        # --- Botões ---
        for n in ("btn_add", "btn_save", "btn_del", "btn_expand", "btn_collapse", "btn_up", "btn_dn"):
            must(n, QtWidgets.QPushButton)

    def _set_initial_column_widths(self, header: QHeaderView, table_columns):
        widths = {
            "ID": 50,
            "Item": 60,
            "Codigo": 110,
            "Descricao": 320,
            "Altura": 80,
            "Largura": 80,
            "Profundidade": 100,
            "Und": 60,
            "QT": 60,
            "Preco_Unit": 110,
            "Preco_Total": 120,
            "Custo Produzido": 130,
            "Ajuste": 110,
            "Custo Total Orlas (€)": 150,
            "Custo Total Mão de Obra (€)": 170,
            "Custo Total Matéria Prima (€)": 190,
            "Custo Total Acabamentos (€)": 180,
            "Margem de Lucro (%)": 150,
            "Valor da Margem (€)": 150,
            "Custos Administrativos (%)": 160,
            "Valor Custos Admin. (€)": 170,
            "Margem_Acabamentos(%)": 160,
            "Valor Margem_Acabamentos (€)": 190,
            "Margem MP_Orlas (%)": 160,
            "Valor Margem MP_Orlas (€)": 190,
            "Margem Mao_Obra (%)": 160,
            "Valor Margem Mao_Obra (€)": 190,
            "reservado_1": 120,
            "reservado_2": 120,
            "reservado_3": 120,
        }
        for idx, col_def in enumerate(table_columns):
            title = col_def[0]
            width = widths.get(title)
            if width:
                header.resizeSection(idx, width)

    # -----------------------------------------------------------------------------
    # Helpers de UI
    # -----------------------------------------------------------------------------
    def _apply_row_height(self):
        vert_header = self.table.verticalHeader()
        if not vert_header:
            return
        height = self._row_height_expanded if getattr(self, "_rows_expanded", False) else self._row_height_collapsed
        vert_header.setSectionResizeMode(QHeaderView.Fixed)
        vert_header.setDefaultSectionSize(height)
        if self.model.rowCount():
            for row in range(self.model.rowCount()):
                vert_header.resizeSection(row, height)

    def _clear_table_selection(self):
        selection_model = self.table.selectionModel()
        if not selection_model:
            return
        blocker = QtCore.QSignalBlocker(selection_model)
        selection_model.clearSelection()
        selection_model.setCurrentIndex(QtCore.QModelIndex(), QItemSelectionModel.Clear)

    def _force_uppercase(self, widget: QtWidgets.QLineEdit, text: str):
        cursor = widget.cursorPosition()
        widget.blockSignals(True)
        widget.setText(text.upper())
        widget.setCursorPosition(cursor)
        widget.blockSignals(False)

    def _focus_next_field(self, index: int):
        if not getattr(self, "_input_sequence", None):
            return
        next_index = (index + 1) % len(self._input_sequence)
        w = self._input_sequence[next_index]
        w.setFocus()
        if isinstance(w, QtWidgets.QLineEdit):
            w.selectAll()

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

    # -----------------------------------------------------------------------------
    # Form
    # -----------------------------------------------------------------------------
    def _collect_form_data(self) -> dict:
        return {
            "item": self.edit_item.text().strip() or None,
            "codigo": (self.edit_codigo.text().strip().upper() or None),
            "descricao": (self.edit_descricao.toPlainText().strip() or None),
            "altura": self._decimal_from_input(self.edit_altura, "Altura"),
            "largura": self._decimal_from_input(self.edit_largura, "Largura"),
            "profundidade": self._decimal_from_input(self.edit_profundidade, "Profundidade"),
            "und": self.edit_und.text().strip() or None,
            "qt": self._decimal_from_input(self.edit_qt, "QT", default=Decimal("1")),
        }

    def _populate_form(self, item):
        self.edit_item.setText(getattr(item, "item_nome", "") or "")
        self.edit_codigo.setText((getattr(item, "codigo", "") or "").upper())
        self.edit_descricao.setPlainText(getattr(item, "descricao", "") or "")
        self.edit_altura.setText(self._format_decimal(getattr(item, "altura", None)))
        self.edit_largura.setText(self._format_decimal(getattr(item, "largura", None)))
        self.edit_profundidade.setText(self._format_decimal(getattr(item, "profundidade", None)))
        self.edit_und.setText(getattr(item, "und", "") or "und")
        qt_txt = self._format_decimal(getattr(item, "qt", None))
        self.edit_qt.setText(qt_txt or "1")
        self.edit_item.setReadOnly(True)
        self.edit_item.setStyleSheet("background-color: #eaeaea;")
        self._edit_item_id = getattr(item, "id_item", None)

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
        self._edit_item_id = None

    # -----------------------------------------------------------------------------
    # Carregamento, refresh e seleção
    # -----------------------------------------------------------------------------
    def load_orcamento(self, orc_id: int):
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
        self._apply_row_height()

        if rows:
            if select_row is not None:
                row_to_select = max(0, min(select_row, len(rows) - 1))
            elif select_last:
                row_to_select = len(rows) - 1
            else:
                row_to_select = 0
            self.table.selectRow(row_to_select)
        else:
            self._prepare_next_item(focus_codigo=False)

    def selected_id(self) -> Optional[int]:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        row = self.model.get_row(idx.row())
        return getattr(row, "id_item", None)

    def _current_user_id(self) -> Optional[int]:
        return getattr(self.current_user, "id", None)

    def _prepare_next_item(self, *, focus_codigo: bool = True):
        self._clear_table_selection()
        self._clear_form()
        if not self._orc_id:
            return
        versao_atual = (self.lbl_ver_val.text() or "").strip()
        if not versao_atual:
            return
        versao_norm = versao_atual.zfill(2)
        proximo_numero = self._next_item_number(self._orc_id, versao_norm)
        self.edit_item.setText(str(proximo_numero))
        self.edit_item.setReadOnly(True)
        self.edit_item.setStyleSheet("background-color: #eaeaea;")
        if focus_codigo:
            self.edit_codigo.setFocus()

    def on_selection_changed(self, selected, deselected):
        idx = self.table.currentIndex()
        if not idx.isValid():
            self._prepare_next_item()
            return
        try:
            row = self.model.get_row(idx.row())
        except Exception:
            self._prepare_next_item()
            return
        self._populate_form(row)

    # -----------------------------------------------------------------------------
    # Inserção / Atualização / Eliminação / Movimento
    # -----------------------------------------------------------------------------
    def _next_item_number(self, orc_id: int, versao: str) -> int:
        total = self.db.execute(
            select(func.count(OrcamentoItem.id_item)).where(
                OrcamentoItem.id_orcamento == orc_id,
                OrcamentoItem.versao == versao,
            )
        ).scalar() or 0
        return int(total) + 1

    def on_new_item(self):
        if not self._orc_id:
            QMessageBox.warning(self, "Aviso", "Nenhum orçamento selecionado.")
            return
        versao_atual = (self.lbl_ver_val.text() or "").strip()
        if not versao_atual:
            QMessageBox.warning(self, "Aviso", "Nenhuma versão definida.")
            return
        self._prepare_next_item()

    def on_save_item(self):
        if not self._orc_id:
            QMessageBox.warning(self, "Aviso", "Nenhum orçamento selecionado.")
            return
        versao_atual = (self.lbl_ver_val.text() or "").strip()
        if not versao_atual:
            QMessageBox.warning(self, "Aviso", "Nenhuma versão definido.")
            return
        versao_norm = versao_atual.zfill(2)

        id_item = self._edit_item_id
        if id_item is None:
            idx = self.table.currentIndex()
            if idx.isValid():
                try:
                    row = self.model.get_row(idx.row())
                    id_item = getattr(row, "id_item", None)
                except Exception:
                    id_item = None

        if not (self.edit_item.text() or "").strip():
            proximo_numero = self._next_item_number(self._orc_id, versao_norm)
            self.edit_item.setText(str(proximo_numero))

        try:
            form = self._collect_form_data()
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
            return

        try:
            if id_item:
                update_item(
                    self.db,
                    id_item,
                    versao=versao_norm,
                    item=form["item"],
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
            else:
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
            self._prepare_next_item()

        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Erro", f"Erro ao gravar item:\n{str(e)}")

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

    def on_expand_rows(self):
        self._rows_expanded = True
        self._apply_row_height()

    def on_collapse_rows(self):
        self._rows_expanded = False
        self._apply_row_height()
