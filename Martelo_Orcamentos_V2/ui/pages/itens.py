# Martelo_Orcamentos_V2/ui/pages/itens.py
# -----------------------------------------------------------------------------
# Página de Itens (V2) – carrega layout do Qt Designer (.ui) com QUiLoader
# - O .ui fica em: Martelo_Orcamentos_V2/ui/forms/itens_form.ui
# - Mantém toda a lógica de BD, validação e operações
# -----------------------------------------------------------------------------

from decimal import Decimal, InvalidOperation
from typing import Optional
from pathlib import Path

# PySide6
from PySide6 import QtCore, QtWidgets
from PySide6.QtUiTools import QUiLoader           # ← para carregar .ui em runtime
from PySide6.QtCore import QFile, Qt, QItemSelectionModel
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QHeaderView, QMessageBox

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


# ---------- helper para carregar .ui e expor widgets por objectName ----------
def _load_ui_into(widget: QtWidgets.QWidget, ui_path: str) -> QtWidgets.QWidget:
    """
    Carrega um .ui para dentro de 'widget' usando QUiLoader e
    expõe todos os filhos (por objectName) como atributos de 'widget'.
    Ex.: no .ui existe QLineEdit com objectName 'edit_codigo' → podes usar self.edit_codigo.
    """
    loader = QUiLoader()
    f = QFile(ui_path)
    if not f.open(QFile.ReadOnly):
        raise FileNotFoundError(f"Não consegui abrir UI: {ui_path}")
    try:
        loaded = loader.load(f, widget)
    finally:
        f.close()

    if loaded is None:
        raise RuntimeError(f"Falha a carregar UI: {ui_path}")

    # Mete o widget carregado dentro deste QWidget
    lay = QtWidgets.QVBoxLayout(widget)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(loaded)

    # Expõe os filhos por objectName em 'self'
    for child in loaded.findChildren(QtCore.QObject):
        name = child.objectName()
        if name:
            setattr(widget, name, child)

    return loaded


# ---------- util tabela: formatação inteira (sem casas decimais) ----------
def _fmt_int(value):
    if value in (None, ""):
        return ""
    try:
        return str(int(Decimal(str(value))))
    except Exception:
        return str(value)


class ItensPage(QtWidgets.QWidget):
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.db = SessionLocal()
        self._orc_id: Optional[int] = None
        self._edit_item_id: Optional[int] = None

        # ------------------------------------------------------------------
        # 1) Carregar o .ui (QUiLoader em vez de uic.loadUi)
        # ------------------------------------------------------------------
        ui_path = Path(__file__).resolve().parents[1] / "forms" / "itens_form.ui"
        _load_ui_into(self, str(ui_path))

        # ------------------------------------------------------------------
        # 2) Preparar widgets do formulário
        # ------------------------------------------------------------------
        v = QDoubleValidator(0.0, 9_999_999.0, 3, self)
        v.setNotation(QDoubleValidator.StandardNotation)
        v.setLocale(QtCore.QLocale.system())

        # Validadores + alinhamento à direita nos campos numéricos
        for w in (self.edit_altura, self.edit_largura, self.edit_profundidade, self.edit_qt):
            w.setValidator(v)
            w.setAlignment(Qt.AlignRight)

        # Código em maiúsculas (mantém cursor)
        self.edit_codigo.textEdited.connect(
            lambda t: self._force_uppercase(self.edit_codigo, t)
        )

        # Enter avança o foco pelos campos
        self._input_sequence = [
            self.edit_codigo,
            self.edit_altura,
            self.edit_largura,
            self.edit_profundidade,
            self.edit_qt,
            self.edit_und,
        ]
        for i, w in enumerate(self._input_sequence):
            w.returnPressed.connect(lambda _=False, idx=i: self._focus_next_field(idx))

        # Campo "Item" é sempre automático
        self.edit_item.setReadOnly(True)
        if not self.edit_und.text().strip():
            self.edit_und.setText("und")

        # Só a TABELA cresce (tudo acima fica compacto)
        if hasattr(self, "verticalLayoutMain"):
            self.verticalLayoutMain.setStretch(0, 0)  # header
            self.verticalLayoutMain.setStretch(1, 0)  # form
            self.verticalLayoutMain.setStretch(2, 0)  # botões
            self.verticalLayoutMain.setStretch(3, 1)  # tabela

        # ------------------------------------------------------------------
        # 3) Model da tabela
        # ------------------------------------------------------------------
        table_columns = [
            ("ID", "id_item"),
            ("Item", "item_nome"),
            ("Codigo", "codigo"),
            ("Descricao", "descricao"),
            ("Altura", "altura", _fmt_int),
            ("Largura", "largura", _fmt_int),
            ("Profundidade", "profundidade", _fmt_int),
            ("Und", "und"),
            ("QT", "qt", _fmt_int),
            ("Preco_Unit", "preco_unitario", _fmt_int),
            ("Preco_Total", "preco_total", _fmt_int),
            ("Custo Produzido", "custo_produzido", _fmt_int),
            ("Ajuste", "ajuste", _fmt_int),
            ("Custo Total Orlas (€)", "custo_total_orlas", _fmt_int),
            ("Custo Total Mão de Obra (€)", "custo_total_mao_obra", _fmt_int),
            ("Custo Total Matéria Prima (€)", "custo_total_materia_prima", _fmt_int),
            ("Custo Total Acabamentos (€)", "custo_total_acabamentos", _fmt_int),
            ("Margem de Lucro (%)", "margem_lucro_perc", _fmt_int),
            ("Valor da Margem (€)", "valor_margem", _fmt_int),
            ("Custos Administrativos (%)", "custos_admin_perc", _fmt_int),
            ("Valor Custos Admin. (€)", "valor_custos_admin", _fmt_int),
            ("Margem_Acabamentos(%)", "margem_acabamentos_perc", _fmt_int),
            ("Valor Margem_Acabamentos (€)", "valor_acabamentos", _fmt_int),
            ("Margem MP_Orlas (%)", "margem_mp_orlas_perc", _fmt_int),
            ("Valor Margem MP_Orlas (€)", "valor_mp_orlas", _fmt_int),
            ("Margem Mao_Obra (%)", "margem_mao_obra_perc", _fmt_int),
            ("Valor Margem Mao_Obra (€)", "valor_mao_obra", _fmt_int),
            ("reservado_1", "reservado_1"),
            ("reservado_2", "reservado_2"),
            ("reservado_3", "reservado_3"),
        ]

        self.model = SimpleTableModel(columns=table_columns)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.ElideNone)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        f = header.font()
        f.setBold(True)
        header.setFont(f)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Larguras iniciais (podes ajustar no runtime/UI)
        column_widths = {
            "ID": 50, "Item": 60, "Codigo": 110, "Descricao": 320,
            "Altura": 80, "Largura": 80, "Profundidade": 100, "Und": 60, "QT": 60,
            "Preco_Unit": 110, "Preco_Total": 120, "Custo Produzido": 130, "Ajuste": 110,
            "Custo Total Orlas (€)": 150, "Custo Total Mão de Obra (€)": 170,
            "Custo Total Matéria Prima (€)": 190, "Custo Total Acabamentos (€)": 180,
            "Margem de Lucro (%)": 150, "Valor da Margem (€)": 150,
            "Custos Administrativos (%)": 160, "Valor Custos Admin. (€)": 170,
            "Margem_Acabamentos(%)": 160, "Valor Margem_Acabamentos (€)": 190,
            "Margem MP_Orlas (%)": 160, "Valor Margem MP_Orlas (€)": 190,
            "Margem Mao_Obra (%)": 160, "Valor Margem Mao_Obra (€)": 190,
            "reservado_1": 120, "reservado_2": 120, "reservado_3": 120,
        }
        for i, col_def in enumerate(table_columns):
            w = column_widths.get(col_def[0])
            if w:
                header.resizeSection(i, w)

        # Altura das linhas (como combinámos: 26px colapsado)
        self._row_height_collapsed = 26
        self._row_height_expanded = 70
        self._rows_expanded = False
        vh = self.table.verticalHeader()
        vh.setDefaultSectionSize(self._row_height_collapsed)
        vh.setSectionResizeMode(QHeaderView.Fixed)

        # Seleção -> preencher formulário
        if self.table.selectionModel():
            self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self._apply_row_height()

        # ------------------------------------------------------------------
        # 4) Ligar botões aos handlers existentes
        # ------------------------------------------------------------------
        self.btn_add.clicked.connect(self.on_new_item)
        self.btn_save.clicked.connect(self.on_save_item)
        self.btn_del.clicked.connect(self.on_del)
        self.btn_expand.clicked.connect(self.on_expand_rows)
        self.btn_collapse.clicked.connect(self.on_collapse_rows)
        self.btn_up.clicked.connect(lambda: self.on_move(-1))
        self.btn_dn.clicked.connect(lambda: self.on_move(1))

        # Estado inicial
        self._clear_form()

    # ==========================================================================
    # Carregamento do orçamento + refresh
    # ==========================================================================
    def load_orcamento(self, orc_id: int):
        """Carrega dados do orçamento e preenche cabeçalho."""
        def _txt(v) -> str:
            return "" if v is None else str(v)

        def _fmt_ver(v) -> str:
            if v in (None, ""):
                return ""
            try:
                return f"{int(v):02d}"
            except (TypeError, ValueError):
                return _txt(v)

        self._orc_id = orc_id
        o = self.db.get(Orcamento, orc_id)
        if o:
            cliente = self.db.get(Client, o.client_id)
            user = self.db.get(User, o.created_by) if o.created_by else None
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
        """Atualiza a tabela; se vazia, prepara próximo item."""
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

    # ==========================================================================
    # Helpers de seleção / user / parsing
    # ==========================================================================
    def selected_id(self) -> Optional[int]:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        row = self.model.get_row(idx.row())
        return getattr(row, "id_item", None)

    def _current_user_id(self) -> Optional[int]:
        return getattr(self.current_user, "id", None)

    def _parse_decimal(self, text: Optional[str], *, default: Optional[Decimal] = None) -> Optional[Decimal]:
        if text is None:
            return default
        t = text.strip()
        if not t:
            return default
        t = t.replace(",", ".")
        try:
            return Decimal(t)
        except (InvalidOperation, ValueError):
            raise ValueError

    def _force_uppercase(self, widget: QtWidgets.QLineEdit, text: str):
        cursor = widget.cursorPosition()
        widget.blockSignals(True)
        widget.setText(text.upper())
        widget.setCursorPosition(cursor)
        widget.blockSignals(False)

    def _focus_next_field(self, index: int):
        if not getattr(self, "_input_sequence", None):
            return
        next_idx = (index + 1) % len(self._input_sequence)
        w = self._input_sequence[next_idx]
        w.setFocus()
        if isinstance(w, QtWidgets.QLineEdit):
            w.selectAll()

    def _decimal_from_input(self, widget: QtWidgets.QLineEdit, label: str, *, default: Optional[Decimal] = None) -> Optional[Decimal]:
        try:
            return self._parse_decimal(widget.text(), default=default)
        except ValueError:
            raise ValueError(f"Valor inválido para {label}.")

    # ==========================================================================
    # Formulário: ler/preencher/limpar
    # ==========================================================================
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
        self._edit_item_id = None

    # ==========================================================================
    # Tabela: altura das linhas
    # ==========================================================================
    def _apply_row_height(self):
        vh = self.table.verticalHeader()
        if not vh:
            return
        h = self._row_height_expanded if getattr(self, "_rows_expanded", False) else self._row_height_collapsed
        vh.setSectionResizeMode(QHeaderView.Fixed)
        vh.setDefaultSectionSize(h)
        if self.model.rowCount():
            for r in range(self.model.rowCount()):
                vh.resizeSection(r, h)

    def _clear_table_selection(self):
        sm = self.table.selectionModel()
        if not sm:
            return
        blocker = QtCore.QSignalBlocker(sm)
        sm.clearSelection()
        sm.setCurrentIndex(QtCore.QModelIndex(), QItemSelectionModel.Clear)

    # ==========================================================================
    # Fluxo: novo/selecção/guardar/eliminar/mover
    # ==========================================================================
    def _prepare_next_item(self, *, focus_codigo: bool = True):
        self._clear_table_selection()
        self._clear_form()
        if not self._orc_id:
            return
        versao_atual = (self.lbl_ver_val.text() or "").strip()
        if not versao_atual:
            return
        versao_norm = versao_atual.zfill(2)
        proximo = self._next_item_number(self._orc_id, versao_norm)
        self.edit_item.setText(str(proximo))
        self.edit_item.setReadOnly(True)
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
        if not (self.lbl_ver_val.text() or "").strip():
            QMessageBox.warning(self, "Aviso", "Nenhuma versão definida.")
            return
        self._prepare_next_item()

    def on_save_item(self):
        if not self._orc_id:
            QMessageBox.warning(self, "Aviso", "Nenhum orçamento selecionado.")
            return
        versao_atual = (self.lbl_ver_val.text() or "").strip()
        if not versao_atual:
            QMessageBox.warning(self, "Aviso", "Nenhuma versão definida.")
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
            self.edit_item.setText(str(self._next_item_number(self._orc_id, versao_norm)))

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
                msg = "Item atualizado com sucesso."
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
                msg = "Item gravado com sucesso."

            self.db.commit()
            self.refresh(select_last=True)
            QMessageBox.information(self, "Sucesso", msg)
            self._prepare_next_item()

        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Erro", f"Erro ao gravar item:\n{str(e)}")

    def on_del(self):
        id_item = self.selected_id()
        if not id_item:
            return
        row = self.table.currentIndex().row()
        if QtWidgets.QMessageBox.question(self, "Confirmar", f"Eliminar item {id_item}?") != QtWidgets.QMessageBox.Yes:
            return
        try:
            delete_item(self.db, id_item, deleted_by=self._current_user_id())
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar: {e}")
            return
        self.refresh(select_row=row)

    def on_move(self, direction: int):
        id_item = self.selected_id()
        if not id_item:
            return
        row = self.table.currentIndex().row()
        try:
            move_item(self.db, id_item, direction, moved_by=self._current_user_id())
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao mover: {e}")
            return
        self.refresh(select_row=row)

    def on_expand_rows(self):
        self._rows_expanded = True
        self._apply_row_height()

    def on_collapse_rows(self):
        self._rows_expanded = False
        self._apply_row_height()
