# Martelo_Orcamentos_V2/ui/pages/itens.py
# -----------------------------------------------------------------------------
# Página de Itens do Orçamento (V2)
# - Campo "Item" é sempre gerado automaticamente (sequencial por orçamento+versão)
#   e não pode ser editado pelo utilizador.
# - Botões: "Inserir Novo Item" (limpa e prepara formulário) e
#           "Gravar Item" (insere ou atualiza na BD).
# - Descrição: QTextEdit (multi-linha), usar .toPlainText().
# -----------------------------------------------------------------------------

from decimal import Decimal, InvalidOperation
from typing import Optional

from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QMessageBox, QHeaderView, QStyle
from PySide6.QtGui import QDoubleValidator
from PySide6.QtCore import Qt, QItemSelectionModel

# SQLAlchemy
from sqlalchemy import select, func, text  # ❗ se precisares de SQL cru, volta a importar `text`

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
        self._edit_item_id = None

        # ---------- Cabeçalho ----------
        self.header = QtWidgets.QFrame()
        self.header.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.header.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        self.header.setMaximumWidth(520)
        self.header.setStyleSheet("""
            QFrame { background-color: #f5f5f5; border: 1px solid #ccc; border-radius: 8px; padding: 8px; }
            QLabel { font-weight: bold; color: #333; }
            QLabel.value { font-weight: normal; color: #000; }
        """)

        self.lbl_cliente = QtWidgets.QLabel("Cliente:");   self.lbl_cliente_val = QtWidgets.QLabel("")
        self.lbl_ano     = QtWidgets.QLabel("Ano:");       self.lbl_ano_val     = QtWidgets.QLabel("")
        self.lbl_num     = QtWidgets.QLabel("Nº Orçamento:"); self.lbl_num_val  = QtWidgets.QLabel("")
        self.lbl_ver     = QtWidgets.QLabel("Versão:");    self.lbl_ver_val     = QtWidgets.QLabel("")
        self.lbl_user    = QtWidgets.QLabel("Utilizador:");self.lbl_user_val    = QtWidgets.QLabel("")

        for w in [self.lbl_cliente_val, self.lbl_ano_val, self.lbl_num_val, self.lbl_ver_val, self.lbl_user_val]:
            w.setProperty("class", "value")

        grid = QtWidgets.QGridLayout(self.header)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)

        # Labels compactos
        for lbl in [self.lbl_cliente, self.lbl_user, self.lbl_ano, self.lbl_num, self.lbl_ver]:
            lbl.setMinimumWidth(70)
            lbl.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)

        self.lbl_cliente_val.setMinimumWidth(260)
        self.lbl_cliente_val.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.lbl_cliente_val.setStyleSheet("font-weight: 600; font-size: 13px;")

        grid.addWidget(self.lbl_cliente, 0, 0)
        grid.addWidget(self.lbl_cliente_val, 0, 1, 1, 3)

        grid.addWidget(self.lbl_ano, 1, 0)
        grid.addWidget(self.lbl_ano_val, 1, 1)
        grid.addWidget(self.lbl_user, 1, 2)
        grid.addWidget(self.lbl_user_val, 1, 3)

        grid.addWidget(self.lbl_num, 2, 0)
        grid.addWidget(self.lbl_num_val, 2, 1)
        grid.addWidget(self.lbl_ver, 2, 2)
        grid.addWidget(self.lbl_ver_val, 2, 3)

        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 1)

        # ============================================================
        # FORMULÁRIO DE INSERÇÃO / EDIÇÃO DE ITENS (Compacto + Otimizado)
        # ------------------------------------------------------------
        # ✔ Linha 1: Item | Código | Altura | Largura | Profundidade | Qt | Und
        # ✔ Linha 2: Descrição (ocupa toda a largura)
        # ✔ Labels em negrito + largura mínima -> não desperdiça espaço
        # ✔ Campos com largura por nº de caracteres (só o necessário)
        # ✔ Altura total do formulário reduzida
        # ============================================================

        self.form_frame = QtWidgets.QFrame()
        self.form_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.form_frame.setStyleSheet("""
            QFrame {
                background-color: #fdfdfd;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
            }
            QLabel {
                font-weight: bold;
                color: #333;
                font-size: 12px;
                min-width: 36px;         /* labels curtos → menos espaço desperdiçado */
            }
            QLineEdit, QTextEdit {
                padding: 3px;
                font-size: 12px;
            }
        """)

        form = QtWidgets.QGridLayout(self.form_frame)
        form.setContentsMargins(4, 4, 4, 4)   # margens mínimas
        form.setHorizontalSpacing(5)          # pouco espaço entre colunas
        form.setVerticalSpacing(2)            # pouco espaço entre linhas

        # Helpers para criar UI de forma consistente
        def _label(text: str) -> QtWidgets.QLabel:
            lbl = QtWidgets.QLabel(text)
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            fm = lbl.fontMetrics()
            lbl.setFixedWidth(max(36, fm.horizontalAdvance(text) + 6))
            return lbl

        def _set_char_width(widget: QtWidgets.QWidget, chars: int):
            """Define largura aproximada pelo nº de caracteres (compacidade controlada)."""
            fm = widget.fontMetrics()
            width = fm.horizontalAdvance("W" * max(chars, 1)) + 10
            widget.setFixedWidth(width)
            if isinstance(widget, QtWidgets.QLineEdit):
                widget.setFixedHeight(24)  # inputs mais baixinhos → reduz altura total

        # Validadores numéricos partilhados
        self._numeric_validator = QDoubleValidator(0.0, 9999999.0, 3, self)
        self._numeric_validator.setNotation(QDoubleValidator.StandardNotation)
        self._numeric_validator.setLocale(QtCore.QLocale.system())

        # --------- Campos (linha 1) ----------
        self.edit_item = QtWidgets.QLineEdit()
        self.edit_item.setReadOnly(True)                      # "Item" é sempre automático
        self.edit_item.setStyleSheet("background-color: #eaeaea;")
        _set_char_width(self.edit_item, 3)

        self.edit_codigo = QtWidgets.QLineEdit()
        _set_char_width(self.edit_codigo, 10)
        self.edit_codigo.textEdited.connect(lambda text: self._force_uppercase(self.edit_codigo, text))

        self.edit_altura = QtWidgets.QLineEdit()
        _set_char_width(self.edit_altura, 5)

        self.edit_largura = QtWidgets.QLineEdit()
        _set_char_width(self.edit_largura, 5)

        self.edit_profundidade = QtWidgets.QLineEdit()
        _set_char_width(self.edit_profundidade, 5)

        self.edit_qt = QtWidgets.QLineEdit()
        self.edit_qt.setPlaceholderText("1")
        _set_char_width(self.edit_qt, 4)

        self.edit_und = QtWidgets.QLineEdit()
        self.edit_und.setPlaceholderText("und")
        self.edit_und.setText("und")
        _set_char_width(self.edit_und, 4)

        for field in (self.edit_altura, self.edit_largura, self.edit_profundidade, self.edit_qt):
            field.setValidator(self._numeric_validator)
            field.setAlignment(Qt.AlignRight)

        self._input_sequence = [self.edit_codigo, self.edit_altura, self.edit_largura, self.edit_profundidade, self.edit_qt, self.edit_und]
        for idx, widget in enumerate(self._input_sequence):
            widget.returnPressed.connect(lambda _=False, i=idx: self._focus_next_field(i))

        # --------- Campo (linha 2): Descrição ----------
        self.edit_descricao = QtWidgets.QTextEdit()
        self.edit_descricao.setPlaceholderText("Descrição do item...")
        self.edit_descricao.setFixedHeight(68)  # ⬅️ 68px (conforme confirmado). Ajusta aqui se quiseres.
        self.edit_descricao.setMinimumWidth(240)

        # --------- Layout: adicionar widgets ----------
        # Linha 0 (compacta)
        col = 0
        form.addWidget(_label("Item"),          0, col); col += 1; form.addWidget(self.edit_item,        0, col); col += 1
        form.addWidget(_label("Código"),        0, col); col += 1; form.addWidget(self.edit_codigo,      0, col); col += 1
        form.addWidget(_label("Altura"),        0, col); col += 1; form.addWidget(self.edit_altura,      0, col); col += 1
        form.addWidget(_label("Largura"),       0, col); col += 1; form.addWidget(self.edit_largura,     0, col); col += 1
        form.addWidget(_label("Profundidade"),  0, col); col += 1; form.addWidget(self.edit_profundidade,0, col); col += 1
        form.addWidget(_label("Qt"),            0, col); col += 1; form.addWidget(self.edit_qt,          0, col); col += 1
        form.addWidget(_label("Und"),           0, col); col += 1; form.addWidget(self.edit_und,         0, col); col += 1

        # Linha 1 (descrição ocupa o resto da largura)
        form.addWidget(_label("Descrição"),     1, 0)
        form.addWidget(self.edit_descricao,     1, 1, 1, col-1)  # span ao longo das colunas restantes

        # ---------- Tabela ----------
        self.table = QtWidgets.QTableView(self)

        # Definição de colunas da tabela
        table_columns = [

            ("ID", "id_item"),

            ("Item", "item_nome"),            # mapeia para 'item' (ORM usa synonym)

            ("Codigo", "codigo"),

            ("Descricao", "descricao"),

            ("Altura", "altura", fmt2),

            ("Largura", "largura", fmt2),

            ("Profundidade", "profundidade", fmt2),

            ("Und", "und"),

            ("QT", "qt", fmt2),

            ("Preco_Unit", "preco_unitario", fmt2),

            ("Preco_Total", "preco_total", fmt2),

            ("Custo Produzido", "custo_produzido", fmt2),

            ("Ajuste", "ajuste", fmt2),

            ("Custo Total Orlas (€)", "custo_total_orlas", fmt2),

            ("Custo Total Mão de Obra (€)", "custo_total_mao_obra", fmt2),

            ("Custo Total Matéria Prima (€)", "custo_total_materia_prima", fmt2),

            ("Custo Total Acabamentos (€)", "custo_total_acabamentos", fmt2),

            ("Margem de Lucro (%)", "margem_lucro_perc", fmt2),

            ("Valor da Margem (€)", "valor_margem", fmt2),

            ("Custos Administrativos (%)", "custos_admin_perc", fmt2),

            ("Valor Custos Admin. (€)", "valor_custos_admin", fmt2),

            ("Margem_Acabamentos(%)", "margem_acabamentos_perc", fmt2),

            ("Valor Margem_Acabamentos (€)", "valor_acabamentos", fmt2),

            ("Margem MP_Orlas (%)", "margem_mp_orlas_perc", fmt2),

            ("Valor Margem MP_Orlas (€)", "valor_mp_orlas", fmt2),

            ("Margem Mao_Obra (%)", "margem_mao_obra_perc", fmt2),

            ("Valor Margem Mao_Obra (€)", "valor_mao_obra", fmt2),

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

        # Guardar larguras em atributo para ajustes futuros
        self.column_widths = {

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
            width = self.column_widths.get(title)
            if width:
                header.resizeSection(idx, width)

        # Altura padrão das linhas (ajuste estes valores conforme necessário)
        self._row_height_collapsed = 26  # altura padrão das linhas da tabela
        self._row_height_expanded = 70   # altura expandida para visualizar descrições longas
        self._rows_expanded = False

        vert_header = self.table.verticalHeader()
        vert_header.setDefaultSectionSize(self._row_height_collapsed)
        vert_header.setSectionResizeMode(QHeaderView.Fixed)

        # Seleção -> preencher formulário
        sel_model = self.table.selectionModel()
        if sel_model:
            sel_model.selectionChanged.connect(self.on_selection_changed)

        self._apply_row_height()

        # ---------- Toolbar ----------
        style = self.style()
        btn_add = QtWidgets.QPushButton("Inserir Novo Item")
        btn_add.setIcon(style.standardIcon(QStyle.SP_FileDialogNewFolder))
        btn_save = QtWidgets.QPushButton("Gravar Item")
        btn_save.setIcon(style.standardIcon(QStyle.SP_DialogSaveButton))
        btn_del = QtWidgets.QPushButton("Eliminar Item")
        btn_del.setIcon(style.standardIcon(QStyle.SP_TrashIcon))
        btn_expand = QtWidgets.QPushButton("Expandir")
        btn_expand.setIcon(style.standardIcon(QStyle.SP_TitleBarMaxButton))
        btn_collapse = QtWidgets.QPushButton("Colapsar")
        btn_collapse.setIcon(style.standardIcon(QStyle.SP_TitleBarNormalButton))
        btn_up  = QtWidgets.QPushButton()
        btn_up.setIcon(style.standardIcon(QStyle.SP_ArrowUp))
        btn_up.setToolTip("Mover item para cima")
        btn_up.setFixedWidth(32)
        btn_dn  = QtWidgets.QPushButton()
        btn_dn.setIcon(style.standardIcon(QStyle.SP_ArrowDown))
        btn_dn.setToolTip("Mover item para baixo")
        btn_dn.setFixedWidth(32)

        btn_add.clicked.connect(self.on_new_item)
        btn_save.clicked.connect(self.on_save_item)
        btn_del.clicked.connect(self.on_del)
        btn_expand.clicked.connect(self.on_expand_rows)
        btn_collapse.clicked.connect(self.on_collapse_rows)
        btn_up.clicked.connect(lambda: self.on_move(-1))
        btn_dn.clicked.connect(lambda: self.on_move(1))

        buttons = QtWidgets.QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        buttons.addStretch(1)
        buttons.addWidget(btn_add)
        buttons.addWidget(btn_save)
        buttons.addWidget(btn_del)
        buttons.addWidget(btn_expand)
        buttons.addWidget(btn_collapse)
        buttons.addWidget(btn_up)
        buttons.addWidget(btn_dn)

        # ---------- Layout raiz ----------
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(6)  # ⬅️ ligeiramente menor para a tabela “subir” mais
        lay.addWidget(self.header, 0, Qt.AlignLeft)
        lay.addWidget(self.form_frame)
        lay.addLayout(buttons)
        lay.addWidget(self.table)

        # Limpa tudo e prepara o próximo item (se orçamento tiver 0 linhas)
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
        """Atualiza linhas na tabela e seleção. Se não houver linhas, prepara próximo item."""
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
            # Sem linhas → prepara o nº do primeiro item
            self._prepare_next_item(focus_codigo=False)

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

    def _force_uppercase(self, widget: QtWidgets.QLineEdit, text: str):
        cursor = widget.cursorPosition()
        widget.blockSignals(True)
        widget.setText(text.upper())
        widget.setCursorPosition(cursor)
        widget.blockSignals(False)

    def _focus_next_field(self, index: int):
        if not getattr(self, '_input_sequence', None):
            return
        next_index = (index + 1) % len(self._input_sequence)
        widget = self._input_sequence[next_index]
        widget.setFocus()
        if isinstance(widget, QtWidgets.QLineEdit):
            widget.selectAll()

    def _decimal_from_input(self, widget: QtWidgets.QLineEdit, label: str, *, default: Optional[Decimal] = None) -> Optional[Decimal]:
        try:
            return self._parse_decimal(widget.text(), default=default)
        except ValueError:
            raise ValueError(f"Valor inválido para {label}.")

    # Coleta os dados do formulário (OBS: 'descricao' é QTextEdit → toPlainText)
    def _collect_form_data(self) -> dict:
        return {
            "item": self.edit_item.text().strip() or None,  # nome visível do item
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
        # item.item_nome mapeia para coluna "item" na BD (synonym no ORM)
        self.edit_item.setText(item.item_nome or "")
        self.edit_codigo.setText((item.codigo or "").upper())
        self.edit_descricao.setPlainText(item.descricao or "")
        self.edit_altura.setText(self._format_decimal(item.altura))
        self.edit_largura.setText(self._format_decimal(item.largura))
        self.edit_profundidade.setText(self._format_decimal(item.profundidade))
        self.edit_und.setText(item.und or "und")
        qt_txt = self._format_decimal(item.qt)
        self.edit_qt.setText(qt_txt or "1")
        # 🔒 manter bloqueado
        self.edit_item.setReadOnly(True)
        self.edit_item.setStyleSheet("background-color: #eaeaea;")
        self._edit_item_id = getattr(item, "id_item", None)

    def _clear_form(self):
        """Limpa campos e deixa 'Item' readonly."""
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

    def _prepare_next_item(self, *, focus_codigo: bool = True):
        """
        Limpa o formulário e prepara o próximo número de item.
        Chamado em: Inserir Novo, após Gravar (novo/atualização), e quando não há linhas no orçamento.
        """
        self._clear_table_selection()
        self._clear_form()

        if not self._orc_id:
            return

        versao_atual = (self.lbl_ver_val.text() or "").strip()
        if not versao_atual:
            return

        versao_norm = versao_atual.zfill(2)
        # 🔑 Cálculo do próximo nº de item SEM depender do campo estar vazio
        proximo_numero = self._next_item_number(self._orc_id, versao_norm)
        self.edit_item.setText(str(proximo_numero))
        self.edit_item.setReadOnly(True)
        self.edit_item.setStyleSheet("background-color: #eaeaea;")

        if focus_codigo:
            self.edit_codigo.setFocus()

    def on_selection_changed(self, selected, deselected):
        """Atualiza o formulário quando a seleção da tabela muda."""
        idx = self.table.currentIndex()

        # Sem seleção -> prepara estado "novo item"
        if not idx.isValid():
            self._prepare_next_item()
            return

        try:
            row = self.model.get_row(idx.row())
        except Exception:
            self._prepare_next_item()
            return

        # Preenche formulário com a linha selecionada
        self._populate_form(row)

    def on_expand_rows(self):
        self._rows_expanded = True
        self._apply_row_height()

    def on_collapse_rows(self):
        self._rows_expanded = False
        self._apply_row_height()

    # =========================================
    # Inserção / Atualização / Movimento
    # =========================================
    def _next_item_number(self, orc_id, versao) -> int:
        """
        Calcula o próximo número de item com base nos itens já existentes
        no orçamento e versão atuais (COUNT + 1).
        """
        total = self.db.execute(
            select(func.count(OrcamentoItem.id_item)).where(
                OrcamentoItem.id_orcamento == orc_id,
                OrcamentoItem.versao == versao
            )
        ).scalar() or 0
        return int(total) + 1

    def on_new_item(self):
        """
        Preparar o formulário para inserir um novo item:
        - Limpa os campos;
        - Calcula e preenche o próximo nº de 'Item' (sequencial por orçamento+versão);
        - Mantém o campo 'Item' bloqueado.
        """
        if not self._orc_id:
            QMessageBox.warning(self, "Aviso", "Nenhum orçamento selecionado.")
            return

        versao_atual = (self.lbl_ver_val.text() or "").strip()
        if not versao_atual:
            QMessageBox.warning(self, "Aviso", "Nenhuma versão definida.")
            return

        self._prepare_next_item()

    def on_save_item(self):
        """
        Gravar item no orçamento:
        - Se não houver item selecionado => INSERE novo item.
        - Se houver item selecionado => ATUALIZA item existente.
        - O campo 'item' é sempre automático e não pode ser alterado.
        - Após gravar (novo ou atualização): limpa e prepara próximo item.
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
        id_item = self._edit_item_id
        if id_item is None:
            idx = self.table.currentIndex()
            if idx.isValid():
                try:
                    row = self.model.get_row(idx.row())
                    id_item = getattr(row, "id_item", None)
                except Exception:
                    id_item = None

        # Se for NOVO e o campo "Item" ainda estiver vazio por alguma razão, calcula já aqui.
        if not (self.edit_item.text() or "").strip():
            proximo_numero = self._next_item_number(self._orc_id, versao_norm)
            self.edit_item.setText(str(proximo_numero))

        # Coletar dados do formulário
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

            # 🚀 Sempre preparar o próximo número após gravar (novo OU atualização)
            self._prepare_next_item()

        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Erro", f"Erro ao gravar item:\n{str(e)}")

    def on_del(self):
        """Eliminar item selecionado e atualizar lista."""
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
        # Após eliminar, atualiza e mantém seleção coerente;
        # se ficar sem linhas, refresh() chamará _prepare_next_item() automaticamente.
        self.refresh(select_row=current_row)

    def on_move(self, direction: int):
        """Mover item para cima/baixo mantendo seleção coerente."""
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







