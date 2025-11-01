from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStyledItemDelegate, QCheckBox
from bool_converter import coerce_bool_to_int, coerce_int_to_bool

class BooleanItemDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        checkbox = QCheckBox(parent)
        return checkbox

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        editor.setChecked(coerce_int_to_bool(value))

    def setModelData(self, editor, model, index):
        value = coerce_bool_to_int(editor.isChecked())
        model.setData(index, value, Qt.EditRole)