from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt


class DadosGeraisDelegate(QtWidgets.QStyledItemDelegate):
    """Table delegate that opens editors on a single click and keeps text editing snappy."""

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QtWidgets.QLineEdit):
            QtCore.QTimer.singleShot(0, editor.selectAll)
        elif isinstance(editor, QtWidgets.QComboBox):
            QtCore.QTimer.singleShot(0, editor.showPopup)
        return editor

    def editorEvent(self, event, model, option, index):
        if (
            event.type() == QtCore.QEvent.MouseButtonPress
            and not (index.flags() & Qt.ItemIsUserCheckable)
        ):
            view = option.widget
            if view and view.edit(index):
                return True
        return super().editorEvent(event, model, option, index)

    def setEditorData(self, editor, index):
        if isinstance(editor, QtWidgets.QComboBox):
            value = index.model().data(index, Qt.EditRole)
            if value is None:
                return
            pos = editor.findText(str(value))
            if pos >= 0:
                editor.setCurrentIndex(pos)
            else:
                editor.setCurrentText(str(value))
        else:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QtWidgets.QComboBox):
            model.setData(index, editor.currentText(), Qt.EditRole)
        else:
            super().setModelData(editor, model, index)
