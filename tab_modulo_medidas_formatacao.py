from PyQt5.QtWidgets import QStyledItemDelegate, QLineEdit, QTableWidgetItem
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtCore import Qt, QEvent, QTimer
import re

# Colunas das variáveis em grupos
GRUPO1_COLS = {0, 1, 2}       # H, L, P
GRUPO2_COLS = {3, 4, 5}       # H1, L1, P1
GRUPO3_COLS = {6, 7, 8}       # H2, L2, P2
GRUPO4_COLS = {9, 10, 11}     # H3, L3, P3
GRUPO5_COLS = {12, 13, 14}    # H4, L4, P4

# Cores associadas a cada grupo
COR_GRUPO1 = QColor(255, 150, 150)   # vermelho claro
COR_GRUPO2 = QColor(150, 255, 150)   # verde claro
COR_GRUPO3 = QColor(255, 255, 150)   # amarelo claro
COR_GRUPO4 = QColor(150, 150, 255)   # azul claro
COR_GRUPO5 = QColor(220, 220, 220)   # cinza claro
COR_BRANCO  = QColor(255, 255, 255)

FONTE_TAMANHO_DEFAULT = 10
FONTE_TAMANHO_DESTAQUE = 14

class MedidasDelegate(QStyledItemDelegate):
    """Delegate simples para aceitar ENTER e ir para a próxima célula."""

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.installEventFilter(self)
        return editor

    def eventFilter(self, editor, event):
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            table = editor.parent().parent()
            row = table.currentRow()
            col = table.currentColumn()

            # Fecha o editor primeiro para gravar o valor
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)

            # Avança para a próxima coluna, se existir
            prox_col = col + 1
            if prox_col < table.columnCount():
                QTimer.singleShot(0, lambda: table.setCurrentCell(row, prox_col))
            return True
        return super().eventFilter(editor, event)


def aplicar_formatacao(item):
    """Aplica cor de fundo e estilo conforme a coluna e se existe valor."""
    if item is None:
        return
    texto = item.text().strip()
    col = item.column()

    # Escolhe a cor de acordo com o grupo da coluna
    if texto:
        if col in GRUPO1_COLS:
            cor = COR_GRUPO1
        elif col in GRUPO2_COLS:
            cor = COR_GRUPO2
        elif col in GRUPO3_COLS:
            cor = COR_GRUPO3
        elif col in GRUPO4_COLS:
            cor = COR_GRUPO4
        elif col in GRUPO5_COLS:
            cor = COR_GRUPO5
        else:
            cor = COR_BRANCO
    else:
        cor = COR_BRANCO

    item.setBackground(QBrush(cor))

    fonte = item.font()
    if texto:
        fonte.setBold(True)
        fonte.setPointSize(FONTE_TAMANHO_DESTAQUE)
    else:
        fonte.setBold(False)
        fonte.setPointSize(FONTE_TAMANHO_DEFAULT)
    item.setFont(fonte)


def on_item_changed_modulo_medidas(item):
    """Valida entrada numérica e aplica formatação nas células."""
    if not item:
        return
    table = item.tableWidget()
    if not table:
        return

    col = item.column()
    # Evita qualquer edição nas colunas de chaves
    if col in (15, 16, 17):
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return

    texto = item.text().strip()
    if texto and not re.fullmatch(r"\d+(?:[\.,]\d+)?", texto):
        # Remove caracteres não numéricos
        item.setText("")
        texto = ""

    aplicar_formatacao(item)


def setup_tab_modulo_medidas(ui):
    """Configura delegate e sinais da tabela de medidas."""
    tbl = ui.tab_modulo_medidas
    tbl.setItemDelegate(MedidasDelegate(tbl))

    try:
        tbl.itemChanged.disconnect()
    except TypeError:
        pass
    tbl.itemChanged.connect(on_item_changed_modulo_medidas)

    # Garante que as colunas ids, num_orc e ver_orc não sejam editáveis
    for row in range(tbl.rowCount()):
        for c in (15, 16, 17):
            it = tbl.item(row, c)
            if it is None:
                it = QTableWidgetItem("")
                tbl.setItem(row, c, it)
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)

