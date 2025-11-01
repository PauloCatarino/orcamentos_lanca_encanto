from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt


class DadosGeraisDelegate(QtWidgets.QStyledItemDelegate):
    """Table delegate that opens editors on a single click and keeps editing clean."""

    def paint(self, painter, option, index):
        state_editing = getattr(QtWidgets.QStyle.StateFlag, "State_Editing", None)
        if state_editing is None:
            state_editing = getattr(QtWidgets.QStyle, "State_Editing", 0)
        if option.state & state_editing:
            return
        super().paint(painter, option, index)

    def createEditor(self, parent, option, index):
        model = index.model()
        column_kind = None
        if hasattr(model, "columns") and 0 <= index.column() < len(model.columns):
            column_kind = getattr(model.columns[index.column()], "kind", None)
        if column_kind == "bool":
            return None
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QtWidgets.QLineEdit):
            if column_kind in {"money", "decimal", "percent", "integer"}:
                editor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            QtCore.QTimer.singleShot(0, editor.selectAll)
        elif isinstance(editor, QtWidgets.QComboBox):
            QtCore.QTimer.singleShot(0, editor.showPopup)
        return editor

    def editorEvent(self, event, model, option, index):
        if (
            event.type() == QtCore.QEvent.Type.MouseButtonPress
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
            if hasattr(editor, "_refresh_options"):
                editor._refresh_options(index, value)  # type: ignore[attr-defined]
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
