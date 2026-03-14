# Martelo_Orcamentos_V2/ui/dialogs/price_management.py
# =========================================================================
# Diálogos para gerenciar preços manuais vs calculados
# =========================================================================

from PySide6 import QtWidgets, QtCore
from typing import Literal


def show_price_conflict_dialog(parent: QtWidgets.QWidget) -> Literal["update", "keep", "cancel"]:
    """
    Mostra diálogo quando há conflito de preço (manual vs calculado).
    Detectado quando o utilizador clicou "Atualizar Custos" e o preço foi editado manualmente.
    
    Returns:
        - 'update': Substituir preço manual pelo calculado
        - 'keep': Manter preço manual
        - 'cancel': Cancelar operação
    """
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("Conflito de Preço")
    dialog.setModal(True)
    dialog.setMinimumWidth(500)

    layout = QtWidgets.QVBoxLayout(dialog)
    
    # Ícone e texto principal
    header_layout = QtWidgets.QHBoxLayout()
    icon_label = QtWidgets.QLabel()
    icon = dialog.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
    icon_label.setPixmap(icon.pixmap(48, 48))
    
    text_label = QtWidgets.QLabel(
        "<b>Conflito de Preço Detectado</b>\n\n"
        "O preço final foi editado manualmente, mas ao atualizar os custos "
        "do orçamento, foi calculado um novo valor.\n\n"
        "O que deseja fazer?"
    )
    text_label.setWordWrap(True)
    
    header_layout.addWidget(icon_label)
    header_layout.addWidget(text_label, 1)
    layout.addLayout(header_layout)
    
    layout.addSpacing(10)
    
    # Opções
    btn_update = QtWidgets.QPushButton("Usar Preço Calculado")
    btn_update.setToolTip("Substituir o preço manual pelo novo valor calculado")
    btn_keep = QtWidgets.QPushButton("Manter Preço Manual")
    btn_keep.setToolTip("Ignorar o novo valor calculado e manter o preço editado")
    btn_cancel = QtWidgets.QPushButton("Cancelar")
    btn_cancel.setToolTip("Não fazer nada, voltar à edição")
    
    buttons_layout = QtWidgets.QHBoxLayout()
    buttons_layout.addWidget(btn_update)
    buttons_layout.addWidget(btn_keep)
    buttons_layout.addWidget(btn_cancel)
    layout.addLayout(buttons_layout)
    
    # Conectar botões
    btn_update.clicked.connect(lambda: dialog.done(1))  # update
    btn_keep.clicked.connect(lambda: dialog.done(2))     # keep
    btn_cancel.clicked.connect(dialog.reject)             # cancel
    
    result = dialog.exec()
    
    if result == 1:
        return "update"
    elif result == 2:
        return "keep"
    else:
        return "cancel"


def show_price_reverted_dialog(parent: QtWidgets.QWidget) -> None:
    """
    Mostra confirmação de que o preço foi revertido para calculado.
    """
    QtWidgets.QMessageBox.information(
        parent,
        "Preço Revertido",
        "O preço final foi revertido para o valor calculado automaticamente.",
    )


def show_price_sync_info_dialog(parent: QtWidgets.QWidget) -> None:
    """
    Mostra informação sobre sincronização de preço entre menus.
    """
    QtWidgets.QMessageBox.information(
        parent,
        "Preço Sincronizado",
        "O preço foi atualizado em todos os menus (Items e Orçamentos).",
    )
