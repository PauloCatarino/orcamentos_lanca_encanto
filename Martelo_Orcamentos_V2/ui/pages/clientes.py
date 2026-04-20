# -*- coding: utf-8 -*-
"""
ClientesPage - interface para listar/editar/eliminar clientes.

Versão:
 - ícones coloridos (gerados dinamicamente)
 - rótulos alinhados à esquerda (encostados à esquerda)
 - colunas 'Info 1' e 'Info 2' fixas para 200 px (%% AJUSTAR AQUI %%)
 - comentários em Português indicando onde editar
"""

import os
from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStyle, QApplication, QSizePolicy
from PySide6.QtGui import QPixmap, QPainter, QColor

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.clients import (
    list_clients,
    search_clients,
    upsert_client,
    delete_client,
    suggestion_tokens,
    sync_clients_from_phc,
)
from Martelo_Orcamentos_V2.app.services.clientes_temporarios import (
    list_clientes_temporarios,
    search_clientes_temporarios,
    upsert_cliente_temporario,
    delete_cliente_temporario,
    suggestion_tokens as suggestion_tokens_temporarios,
)
from ..models.qt_table import SimpleTableModel

# Alias seguro (PySide6 mudou o enum em versões recentes)
SP = getattr(QStyle, "StandardPixmap", QStyle)


def colored_icon_pixmap(icon: QStyle.StandardPixmap, color: str = "#0A84FF", icon_size: int = 16, icon_path: str = None):
    """
    Gera um QPixmap de ícone colorido.
    - Se icon_path existir (ficheiro PNG), carrega esse ficheiro e devolve pixmap escalado.
    - Caso contrário, desenha um círculo colorido e coloca por cima o ícone padrão do QStyle.
    Parâmetros:
    - icon: QStyle.StandardPixmap (ícone semântico)
    - color: string com cor (hex ou nome)
    - icon_size: tamanho em px
    - icon_path: caminho para PNG custom (opcional)
    """
    # Usar ficheiro custom se existir
    if icon_path and os.path.exists(icon_path):
        pm = QPixmap(icon_path)
        return pm.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # Criar pixmap transparente
    pix = QPixmap(icon_size, icon_size)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # Desenhar círculo colorido de fundo
    qcolor = QColor(color)
    p.setBrush(qcolor)
    p.setPen(Qt.NoPen)
    # leve margem para que o círculo não toque as bordas
    margem = 1
    p.drawEllipse(margem, margem, icon_size - 2 * margem, icon_size - 2 * margem)

    # Sobrepor o ícone padrão (reduzido) no centro, se possível
    try:
        std_icon = QApplication.style().standardIcon(icon)
        # desenhar o ícone um pouco mais pequeno que o círculo
        symbol_size = max(1, icon_size - 6)
        symbol_pix = std_icon.pixmap(symbol_size, symbol_size)
        # calcular posição centralizada
        x = (icon_size - symbol_size) // 2
        y = (icon_size - symbol_size) // 2
        # desenhar o símbolo por cima (mantendo cores originais do símbolo)
        p.drawPixmap(x, y, symbol_pix)
    except Exception:
        # se algo falhar, apenas deixamos o círculo
        pass

    p.end()
    return pix


def label_with_icon(text: str, icon: QStyle.StandardPixmap, color: str = "#0A84FF", icon_size: int = 14, spacing: int = 6, icon_path: str = None):
    """
    Cria um widget contendo icon + texto.
    - text: texto do rótulo
    - icon: QStyle.StandardPixmap (caso não haja ficheiro)
    - color: cor do ícone (hex) - %% AJUSTAR AQUI %%
    - icon_size: tamanho do ícone em px - %% AJUSTAR AQUI %%
    - spacing: espaçamento entre ícone e texto - %% AJUSTAR AQUI %%
    - icon_path: caminho para PNG custom (opcional)
    """
    w = QtWidgets.QWidget()
    h = QtWidgets.QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(spacing)

    lbl_icon = QtWidgets.QLabel()
    pix = colored_icon_pixmap(icon, color=color, icon_size=icon_size, icon_path=icon_path)
    lbl_icon.setPixmap(pix)
    lbl_icon.setFixedSize(icon_size, icon_size)
    lbl_icon.setContentsMargins(0, 0, 0, 0)

    lbl_text = QtWidgets.QLabel(text)
    lbl_text.setContentsMargins(4, 0, 0, 0)

    # Tornamos o widget do label compacto
    w.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

    # Alinhamento interno: esquerda + centrado verticalmente (rotulos encostados à esquerda)
    h.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    h.addWidget(lbl_icon)
    h.addWidget(lbl_text)
    return w


def _digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def format_phone_display(value: str) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    digits = _digits_only(text)
    if len(digits) == 9:
        return f"{digits[0:3]} {digits[3:6]} {digits[6:9]}"
    return text


class ClientesTab(QtWidgets.QWidget):
    def __init__(
        self,
        *,
        parent=None,
        list_fn,
        search_fn,
        upsert_fn,
        delete_fn,
        suggestion_fn,
        phone_formatter=None,
        show_refresh: bool = False,
        show_sync: bool = False,
        sync_fn=None,
        require_data_on_new: bool = False,
        mark_dirty_on_change: bool = False,
        validate_phone: bool = False,
        search_placeholder: str = "Pesquisar clientes (use % para multi-termos)",
    ):
        super().__init__(parent)
        self.db = SessionLocal()
        self._list_fn = list_fn
        self._search_fn = search_fn
        self._upsert_fn = upsert_fn
        self._delete_fn = delete_fn
        self._suggestion_fn = suggestion_fn
        self._sync_fn = sync_fn
        self._phone_formatter = phone_formatter
        self._show_refresh = bool(show_refresh)
        self._show_sync = bool(show_sync)
        self._require_data_on_new = bool(require_data_on_new)
        self._mark_dirty_on_change = bool(mark_dirty_on_change)
        self._validate_phone = bool(validate_phone)
        self._dirty = False
        self._suspend_dirty = False

        # ------- Função auxiliar para estilizar botões primários -------
        def _style_primary_button(btn: QtWidgets.QPushButton, color: str):
            btn.setStyleSheet(
                f"background-color:{color}; color:white; font-weight:bold; padding:8px 12px; border-radius:4px;"
            )
            btn.setCursor(Qt.PointingHandCursor)

        # ------------------ Barra de pesquisa + botão limpar ------------------
        self.ed_search = QtWidgets.QLineEdit()
        self.ed_search.setPlaceholderText(search_placeholder)
        self.ed_search.textChanged.connect(self.on_search)
        self.ed_search.textChanged.connect(self._update_clear_search_button)

        self.btn_clear = QtWidgets.QToolButton()
        self.btn_clear.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogResetButton))
        self.btn_clear.setToolTip("Limpar pesquisa")
        self.btn_clear.setEnabled(False)
        self.btn_clear.clicked.connect(self.ed_search.clear)

        search_bar = QtWidgets.QHBoxLayout()
        search_bar.setSpacing(6)
        search_bar.addWidget(self.ed_search, 1)
        search_bar.addWidget(self.btn_clear)

        # ------------------ Tabela de clientes ------------------
        self.table = QtWidgets.QTableView()
        phone_formatter = self._phone_formatter
        self.model = SimpleTableModel(
            columns=[
                ("ID", "id"),
                ("Nome", "nome"),
                ("Simplex", "nome_simplex"),
                ("Morada", "morada"),
                ("Email", "email"),
                ("WEB", "web_page"),
                ("Telefone", "telefone", phone_formatter),
                ("Telemovel", "telemovel", phone_formatter),
                {"header": "Num_PHC", "attr": "num_cliente_phc", "type": "int"},
                ("Info 1", "info_1"),
                ("Info 2", "info_2"),
            ]
        )
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.setStretchLastSection(False)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        self.table.setSortingEnabled(True)

        # --- Mapeamento de larguras por coluna (%% AJUSTAR AQUI %%) ---
        # Se queres alterar larguras iniciais, muda aqui.
        self._table_width_map = {
            "ID": 48,
            "Nome": 260,
            "Simplex": 170,
            "Morada": 320,
            "Email": 260,
            "WEB": 150,
            "Telefone": 125,
            "Telemovel": 125,
            "Num_PHC": 100,
            "Info 1": 280,
            "Info 2": 280,
        }
        self._table_fixed_headers = {"ID", "Telefone", "Telemovel", "Num_PHC"}
        self._table_stretch_headers = {"Nome", "Morada", "Email", "Info 1", "Info 2"}

        self._apply_table_column_layout()

        # Conectar mudança de seleção
        self.table.selectionModel().selectionChanged.connect(lambda *_: self.load_selected())

        # ------------------ Formulário de edição: "Dados do Cliente" ------------------
        self.ed_nome = QtWidgets.QLineEdit()
        self.ed_simplex = QtWidgets.QLineEdit()
        self.ed_morada = QtWidgets.QTextEdit()
        self.ed_morada.setFixedHeight(48)
        self.ed_email = QtWidgets.QLineEdit()
        self.ed_web = QtWidgets.QLineEdit()
        self.ed_tel = QtWidgets.QLineEdit()
        self.ed_tm = QtWidgets.QLineEdit()
        self.ed_phc = QtWidgets.QLineEdit()
        self.ed_info1 = QtWidgets.QTextEdit()
        self.ed_info1.setFixedHeight(68)
        self.ed_info2 = QtWidgets.QTextEdit()
        self.ed_info2.setFixedHeight(68)
        self._save_base_text = "Guardar Cliente"
        self._btn_save = None

        # Grid layout
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        grid.setContentsMargins(8, 8, 8, 8)

        # Cores para os ícones (%% AJUSTAR AQUI %%)
        color_map = {
            "Nome Cliente": "#0A84FF",
            "Nome Cliente Simplex": "#FF8C00",
            "Num Cliente PHC": "#6E6E6E",
            "Telefone": "#2E7D32",
            "Telemóvel": "#00897B",
            "E-Mail": "#1E88E5",
            "Página WEB": "#00ACC1",
            "Morada": "#FBC02D",
            "Info 1": "#7E57C2",
            "Info 2": "#7E57C2",
        }

        # Função auxiliar para adicionar par (rótulo + widget)
        def add_row(r, c, label_text, icon, widget, icon_color=None, icon_path: str = None):
            # criar widget do label com ícone colorido
            color = icon_color or color_map.get(label_text, "#0A84FF")
            lbl = label_with_icon(label_text, icon, color=color, icon_size=14, spacing=4, icon_path=icon_path)
            # rótulos encostados à esquerda
            grid.addWidget(lbl, r, c * 2, alignment=Qt.AlignLeft)
            grid.addWidget(widget, r, c * 2 + 1)

        # Linha 1
        add_row(0, 0, "Nome Cliente", SP.SP_FileIcon, self.ed_nome)
        add_row(0, 1, "Nome Cliente Simplex", SP.SP_DirLinkIcon, self.ed_simplex)
        add_row(0, 2, "Num Cliente PHC", SP.SP_DriveHDIcon, self.ed_phc)
        add_row(0, 3, "Telefone", SP.SP_DialogOkButton, self.ed_tel)
        add_row(0, 4, "Telemóvel", SP.SP_ComputerIcon, self.ed_tm)
        # Linha 2
        add_row(1, 0, "E-Mail", SP.SP_MessageBoxInformation, self.ed_email)
        add_row(1, 1, "Página WEB", SP.SP_DesktopIcon, self.ed_web)
        add_row(1, 2, "Morada", SP.SP_DirIcon, self.ed_morada)

        # Info 1 & 2 (ocupam colunas maiores)
        lbl_info1 = label_with_icon("Info 1", SP.SP_FileDialogDetailedView, color=color_map["Info 1"], icon_size=14)
        grid.addWidget(lbl_info1, 2, 0, alignment=Qt.AlignLeft)
        grid.addWidget(self.ed_info1, 2, 1, 1, 2)

        lbl_info2 = label_with_icon("Info 2", SP.SP_FileDialogDetailedView, color=color_map["Info 2"], icon_size=14)
        grid.addWidget(lbl_info2, 2, 3, alignment=Qt.AlignLeft)
        grid.addWidget(self.ed_info2, 2, 4, 1, 2)

        # ------------------ CONFIGURAÇÃO DE COLUNAS DO GRID ------------------
        total_columns = 10
        for col in range(total_columns):
            if col % 2 == 0:
                grid.setColumnStretch(col, 0)   # colunas de rótulo: não esticar
            else:
                grid.setColumnStretch(col, 1)   # colunas de campos: podem esticar

        # %% AJUSTAR AQUI %% - Tornar o campo "Morada" mais largo:
        morada_widget_col = 2 * 2 + 1
        grid.setColumnStretch(morada_widget_col, 3)
        grid.setColumnMinimumWidth(morada_widget_col, 300)
        self.ed_morada.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.ed_morada.setMinimumWidth(320)
        # FIM %% AJUSTAR AQUI %%

        dados_box = QtWidgets.QGroupBox("Dados do Cliente")
        dados_box.setLayout(grid)

        # ------------------ Botões principais ------------------
        btn_new = QtWidgets.QPushButton("Novo Cliente")
        btn_save = QtWidgets.QPushButton(self._save_base_text)
        btn_del = QtWidgets.QPushButton("Eliminar Cliente")
        btn_refresh = QtWidgets.QPushButton("Atualizar") if self._show_refresh else None
        btn_phc_sync = QtWidgets.QPushButton("Atualizar PHC") if self._show_sync else None
        self._btn_save = btn_save

        style = self.style()
        btn_new.setIcon(style.standardIcon(QStyle.SP_FileIcon))
        btn_save.setIcon(style.standardIcon(QStyle.SP_DialogSaveButton))
        btn_del.setIcon(style.standardIcon(QStyle.SP_TrashIcon))
        if btn_refresh is not None:
            btn_refresh.setIcon(style.standardIcon(getattr(QStyle, "SP_BrowserReload", QStyle.SP_BrowserStop)))
        if btn_phc_sync is not None:
            btn_phc_sync.setIcon(style.standardIcon(getattr(QStyle, "SP_BrowserReload", QStyle.SP_BrowserStop)))

        _style_primary_button(btn_new, "#4CAF50")
        _style_primary_button(btn_save, "#2196F3")
        _style_primary_button(btn_del, "#F44336")
        if btn_refresh is not None:
            _style_primary_button(btn_refresh, "#607D8B")
            btn_refresh.setToolTip("Atualiza a listagem de clientes.")
        if btn_phc_sync is not None:
            _style_primary_button(btn_phc_sync, "#607D8B")
            btn_phc_sync.setToolTip(
                "Atualiza a listagem de clientes do Martelo com os dados do PHC (dbo.CL).\n"
                "IMPORTANTE: no PHC é apenas leitura (SELECT)."
            )

        btn_new.clicked.connect(self.on_new)
        btn_save.setToolTip("Guardar cliente na base de dados. Atalho: Ctrl+G.")
        btn_save.clicked.connect(self.on_save)
        self._shortcut_save = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+G"), self)
        self._shortcut_save.setContext(Qt.WidgetWithChildrenShortcut)
        self._shortcut_save.activated.connect(self.on_save)
        btn_del.clicked.connect(self.on_delete)
        if btn_refresh is not None:
            btn_refresh.clicked.connect(self.refresh)
        if btn_phc_sync is not None:
            btn_phc_sync.clicked.connect(self.on_sync_phc)

        primary_actions = QtWidgets.QHBoxLayout()
        primary_actions.setSpacing(10)
        primary_actions.addWidget(btn_new)
        primary_actions.addWidget(btn_save)
        primary_actions.addWidget(btn_del)
        if btn_refresh is not None:
            primary_actions.addWidget(btn_refresh)
        if btn_phc_sync is not None:
            primary_actions.addWidget(btn_phc_sync)
        primary_actions.addStretch(1)

        if self._mark_dirty_on_change:
            for w in [self.ed_nome, self.ed_simplex, self.ed_email, self.ed_web, self.ed_tel, self.ed_tm, self.ed_phc]:
                w.textChanged.connect(self._on_field_changed)
            for w in [self.ed_morada, self.ed_info1, self.ed_info2]:
                w.textChanged.connect(self._on_field_changed)

        # ------------------ Layout principal ------------------
        dados_container = QtWidgets.QWidget()
        dados_layout = QtWidgets.QHBoxLayout(dados_container)
        dados_layout.setContentsMargins(6, 4, 6, 4)
        dados_layout.addWidget(dados_box)

        content = QtWidgets.QVBoxLayout()
        content.setSpacing(8)
        content.addLayout(primary_actions)
        content.addLayout(search_bar)
        content.addWidget(dados_container)
        content.addWidget(self.table, 1)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(content)

        self._current_id = None
        self.refresh()
        self._setup_completer()
        self._update_clear_search_button(self.ed_search.text())

    # ------------------ Helpers / Operações sobre a tabela ------------------
    def _column_header(self, col) -> str:
        return self.model._col_spec(col).get("header", "")

    def _apply_table_column_layout(self):
        header = self.table.horizontalHeader()
        for idx, col in enumerate(self.model.columns):
            label = self._column_header(col)
            if label in self._table_fixed_headers:
                header.setSectionResizeMode(idx, QtWidgets.QHeaderView.Fixed)
            elif label in self._table_stretch_headers:
                header.setSectionResizeMode(idx, QtWidgets.QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(idx, QtWidgets.QHeaderView.Interactive)

            width = self._table_width_map.get(label)
            if width is not None:
                header.resizeSection(idx, width)

    def _update_clear_search_button(self, text: str):
        self.btn_clear.setEnabled(bool((text or "").strip()))

    def refresh(self):
        """Recarrega a tabela a partir da base de dados e reaplica o layout das colunas."""
        rows = self._list_fn(self.db)
        self.model.set_rows(rows)
        if rows:
            self.table.selectRow(0)
            self.load_selected()

        self._apply_table_column_layout()

    def _setup_completer(self):
        toks = self._suggestion_fn(self.db)
        comp = QtWidgets.QCompleter(toks, self)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        self.ed_search.setCompleter(comp)

    def on_search(self, text: str):
        rows = self._search_fn(self.db, text)
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
        self._suspend_dirty = True
        try:
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
        finally:
            self._suspend_dirty = False
        self._set_dirty(False)

    # ------------------ Ações dos botões ------------------
    def on_new(self):
        self._current_id = None
        self._suspend_dirty = True
        try:
            for w in [self.ed_nome, self.ed_simplex, self.ed_email, self.ed_web, self.ed_tel, self.ed_tm, self.ed_phc]:
                w.clear()
            self.ed_morada.clear()
            self.ed_info1.clear()
            self.ed_info2.clear()
        finally:
            self._suspend_dirty = False
        self._set_dirty(False)
        self.ed_nome.setFocus()

    def _set_dirty(self, dirty: bool):
        if not self._mark_dirty_on_change:
            return
        self._dirty = bool(dirty)
        if not self._btn_save:
            return
        if self._dirty:
            if not self._btn_save.text().endswith("*"):
                self._btn_save.setText(f"{self._save_base_text} *")
        else:
            self._btn_save.setText(self._save_base_text)

    def _on_field_changed(self, *args, **kwargs):
        if self._suspend_dirty or not self._mark_dirty_on_change:
            return
        self._set_dirty(True)

    def _confirm_phone_value(self, label: str, widget: QtWidgets.QLineEdit):
        text = (widget.text() or "").strip()
        if not text:
            return text, True
        digits = _digits_only(text)
        if len(digits) == 9:
            return text, True
        msg = (
            f"O numero em {label} nao tem 9 algarismos.\n"
            "Para numeros internacionais indique o indicativo (ex: +351).\n\n"
            "Pretende manter este numero registado?"
        )
        if QtWidgets.QMessageBox.question(self, "Confirmar numero", msg) == QtWidgets.QMessageBox.Yes:
            return text, True
        widget.setFocus()
        return text, False

    def on_save(self):
        if self._require_data_on_new and self._current_id is None:
            values = [
                self.ed_nome.text(),
                self.ed_simplex.text(),
                self.ed_morada.toPlainText(),
                self.ed_email.text(),
                self.ed_web.text(),
                self.ed_tel.text(),
                self.ed_tm.text(),
                self.ed_phc.text(),
                self.ed_info1.toPlainText(),
                self.ed_info2.toPlainText(),
            ]
            if not any(v and v.strip() for v in values):
                QtWidgets.QMessageBox.warning(
                    self,
                    "Atencao",
                    "Esta a tentar inserir um novo cliente sem dados.",
                )
                return
        tel_value = (self.ed_tel.text() or "").strip()
        tm_value = (self.ed_tm.text() or "").strip()
        if self._validate_phone:
            tel_value, ok = self._confirm_phone_value("Telefone", self.ed_tel)
            if not ok:
                return
            tm_value, ok = self._confirm_phone_value("Telemovel", self.ed_tm)
            if not ok:
                return
        try:
            self._upsert_fn(
                self.db,
                id=self._current_id,
                nome=self.ed_nome.text(),
                nome_simplex=self.ed_simplex.text(),
                morada=self.ed_morada.toPlainText(),
                email=self.ed_email.text(),
                web_page=self.ed_web.text(),
                telefone=tel_value,
                telemovel=tm_value,
                num_cliente_phc=self.ed_phc.text(),
                info_1=self.ed_info1.toPlainText(),
                info_2=self.ed_info2.toPlainText(),
            )
            self.db.commit()
            self.refresh()
            self._setup_completer()
            self._set_dirty(False)
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
            self._delete_fn(self.db, self._current_id)
            self.db.commit()
            self.refresh()
            self.on_new()
        except Exception as e:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar: {e}")

    def on_sync_phc(self):
        if not self._show_sync or self._sync_fn is None:
            return
        msg = (
            "Isto vai sincronizar/atualizar os clientes do Martelo com os dados do PHC.\n\n"
            "No PHC e apenas leitura (SELECT). A atualizacao e feita na base de dados do Martelo.\n\n"
            "Continuar?"
        )
        if QtWidgets.QMessageBox.question(self, "Atualizar PHC", msg) != QtWidgets.QMessageBox.Yes:
            return

        try:
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            result = self._sync_fn(self.db)
            self.db.commit()
            self.refresh()
            self._setup_completer()
            QtWidgets.QMessageBox.information(
                self,
                "OK",
                "Atualizacao PHC concluida.\n\n"
                f"Total PHC: {result.get('total_phc', 0)}\n"
                f"Novos: {result.get('created', 0)}\n"
                f"Atualizados: {result.get('updated', 0)}\n"
                f"Ignorados: {result.get('skipped', 0)}",
            )
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao atualizar clientes a partir do PHC:\n\n{exc}")
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()


class ClientesPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        tabs = QtWidgets.QTabWidget(self)

        self.tab_phc = ClientesTab(
            parent=self,
            list_fn=list_clients,
            search_fn=search_clients,
            upsert_fn=upsert_client,
            delete_fn=delete_client,
            suggestion_fn=suggestion_tokens,
            show_sync=True,
            sync_fn=sync_clients_from_phc,
            search_placeholder="Pesquisar clientes PHC (use % para multi-termos)",
        )
        self.tab_temp = ClientesTab(
            parent=self,
            list_fn=list_clientes_temporarios,
            search_fn=search_clientes_temporarios,
            upsert_fn=upsert_cliente_temporario,
            delete_fn=delete_cliente_temporario,
            suggestion_fn=suggestion_tokens_temporarios,
            phone_formatter=format_phone_display,
            show_refresh=True,
            show_sync=False,
            sync_fn=None,
            require_data_on_new=True,
            mark_dirty_on_change=True,
            validate_phone=True,
            search_placeholder="Pesquisar clientes temporarios (use % para multi-termos)",
        )

        tabs.addTab(self.tab_phc, "Clientes PHC")
        tabs.addTab(self.tab_temp, "Clientes Temporarios")

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(tabs)
