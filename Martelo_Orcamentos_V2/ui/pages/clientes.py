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
from PySide6 import QtWidgets
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


class ClientesPage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = SessionLocal()

        # ------- Função auxiliar para estilizar botões primários -------
        def _style_primary_button(btn: QtWidgets.QPushButton, color: str):
            btn.setStyleSheet(
                f"background-color:{color}; color:white; font-weight:bold; padding:8px 12px; border-radius:4px;"
            )
            btn.setCursor(Qt.PointingHandCursor)

        # ------------------ Barra de pesquisa + botão limpar ------------------
        self.ed_search = QtWidgets.QLineEdit()
        self.ed_search.setPlaceholderText("Pesquisar clientes (use % para multi-termos)")
        self.ed_search.textChanged.connect(self.on_search)

        self.btn_clear = QtWidgets.QToolButton()
        self.btn_clear.setText("X")
        self.btn_clear.clicked.connect(lambda: self.ed_search.setText(""))

        search_bar = QtWidgets.QHBoxLayout()
        search_bar.setSpacing(6)
        search_bar.addWidget(self.ed_search, 1)
        search_bar.addWidget(self.btn_clear)

        # ------------------ Tabela de clientes ------------------
        self.table = QtWidgets.QTableView()
        self.model = SimpleTableModel(
            columns=[
                ("ID", "id"),
                ("Nome", "nome"),
                ("Simplex", "nome_simplex"),
                ("Morada", "morada"),
                ("Email", "email"),
                ("WEB", "web_page"),
                ("Telefone", "telefone"),
                ("Telemovel", "telemovel"),
                ("Num_PHC", "num_cliente_phc"),
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

        # --- Mapeamento de larguras por coluna (%% AJUSTAR AQUI %%) ---
        # Se queres alterar larguras iniciais, muda aqui.
        width_map = {
            "ID": 40,
            "Nome": 210,
            "Simplex": 110,
            "Morada": 220,
            "Email": 210,
            "WEB": 120,
            "Telefone": 110,
            "Telemovel": 110,
            "Num_PHC": 90,
            "Info 1": 250,   # largura desejada para Info 1 (%% AJUSTAR AQUI %%)
            "Info 2": 250,   # largura desejada para Info 2 (%% AJUSTAR AQUI %%)
        }

        for idx, col in enumerate(self.model.columns):
            label = col[0]
            if label in width_map:
                header.resizeSection(idx, width_map[label])
            if label in ("Info 1", "Info 2"):
                # força modo FIXED para garantir largura
                header.setSectionResizeMode(idx, QtWidgets.QHeaderView.Fixed)

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
        btn_save = QtWidgets.QPushButton("Guardar Cliente")
        btn_del = QtWidgets.QPushButton("Eliminar Cliente")

        style = self.style()
        btn_new.setIcon(style.standardIcon(QStyle.SP_FileIcon))
        btn_save.setIcon(style.standardIcon(QStyle.SP_DialogSaveButton))
        btn_del.setIcon(style.standardIcon(QStyle.SP_TrashIcon))

        _style_primary_button(btn_new, "#4CAF50")
        _style_primary_button(btn_save, "#2196F3")
        _style_primary_button(btn_del, "#F44336")

        btn_new.clicked.connect(self.on_new)
        btn_save.clicked.connect(self.on_save)
        btn_del.clicked.connect(self.on_delete)

        primary_actions = QtWidgets.QHBoxLayout()
        primary_actions.setSpacing(10)
        primary_actions.addWidget(btn_new)
        primary_actions.addWidget(btn_save)
        primary_actions.addWidget(btn_del)
        primary_actions.addStretch(1)

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

    # ------------------ Helpers / Operações sobre a tabela ------------------
    def refresh(self):
        """Recarrega a tabela a partir da base de dados e reaplica larguras fixas."""
        rows = list_clients(self.db)
        self.model.set_rows(rows)
        if rows:
            self.table.selectRow(0)
            self.load_selected()

        # Reaplicar tamanhos fixos para Info1 / Info2 (ajuda a garantir 200px)
        header = self.table.horizontalHeader()
        for idx, col in enumerate(self.model.columns):
            label = col[0]
            if label in ("Info 1", "Info 2"):
                header.resizeSection(idx, 200)
                header.setSectionResizeMode(idx, QtWidgets.QHeaderView.Fixed)

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

    # ------------------ Ações dos botões ------------------
    def on_new(self):
        self._current_id = None
        for w in [self.ed_nome, self.ed_simplex, self.ed_email, self.ed_web, self.ed_tel, self.ed_tm, self.ed_phc]:
            w.clear()
        self.ed_morada.clear()
        self.ed_info1.clear()
        self.ed_info2.clear()
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
