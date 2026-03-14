import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

from Martelo_Orcamentos_V2.ui.pages.custeio_items import CusteioTableModel


class _DummyPage(QtCore.QObject):
    def __init__(self) -> None:
        super().__init__()
        self.dirty = False

    def _set_rows_dirty(self, dirty: bool = True) -> None:
        self.dirty = dirty

    def confirm_qt_und_override(self, row_data, new_value) -> bool:
        return True

    def _apply_collapse_state(self) -> None:
        return None

    def _icon(self, key: str) -> QtGui.QIcon:
        return QtGui.QIcon()


class CusteioItemsQtUndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _build_model(self, *, qt_und: float = 5.0, manual: bool = False) -> CusteioTableModel:
        page = _DummyPage()
        model = CusteioTableModel(page)
        model.load_rows(
            [
                {
                    "id": 10,
                    "def_peca": "DOBRADICA",
                    "descricao": "DOBRADICA",
                    "qt_mod": 1.0,
                    "qt_und": qt_und,
                    "qt_manual_override": manual,
                    "_row_type": "child",
                    "_uid": "child-1",
                    "_parent_uid": "parent-1",
                    "_group_uid": "group-1",
                    "_child_source": "DOBRADICA",
                    "_qt_divisor": 1.0,
                    "_qt_parent_factor": 1.0,
                    "_qt_child_factor": qt_und,
                    "_qt_formula_value": 5.0,
                    "_qt_rule_tooltip": "Regra base de dobradicas",
                }
            ]
        )

        def _recalc_stub() -> None:
            row = model.rows[0]
            row["_qt_child_factor"] = row.get("qt_und")

        model.recalculate_all = _recalc_stub  # type: ignore[method-assign]
        return model

    def test_child_qt_und_allows_local_override(self) -> None:
        model = self._build_model()
        qt_und_index = model.index(0, model.column_keys.index("qt_und"))
        qt_mod_index = model.index(0, model.column_keys.index("qt_mod"))

        ok = model.setData(qt_und_index, "6", QtCore.Qt.EditRole)

        self.assertTrue(ok)
        self.assertEqual(model.rows[0]["qt_und"], 6.0)
        self.assertTrue(model.rows[0]["qt_manual_override"])
        self.assertTrue(model.rows[0]["_qt_manual_override"])
        self.assertEqual(model.rows[0]["_qt_manual_value"], 6.0)
        self.assertEqual(model.data(qt_mod_index, QtCore.Qt.DisplayRole), "1 x 1 x 6")
        tooltip = model.data(qt_und_index, QtCore.Qt.ToolTipRole) or ""
        self.assertIn("Formula local: 1 x 1 x 6 = 6", tooltip)
        font = model.data(qt_mod_index, QtCore.Qt.FontRole)
        self.assertIsNotNone(font)
        self.assertTrue(font.italic())
        self.assertTrue(font.underline())

    def test_child_qt_und_blank_reverts_to_formula(self) -> None:
        model = self._build_model(qt_und=6.0, manual=True)
        row = model.rows[0]
        row["_qt_manual_override"] = True
        row["_qt_manual_value"] = 6.0
        row["_qt_manual_tooltip"] = "Formula local: 1 x 1 x 6 = 6"
        qt_und_index = model.index(0, model.column_keys.index("qt_und"))
        qt_mod_index = model.index(0, model.column_keys.index("qt_mod"))

        ok = model.setData(qt_und_index, "", QtCore.Qt.EditRole)

        self.assertTrue(ok)
        self.assertEqual(model.rows[0]["qt_und"], 5.0)
        self.assertFalse(model.rows[0]["qt_manual_override"])
        self.assertFalse(model.rows[0]["_qt_manual_override"])
        self.assertIsNone(model.rows[0]["_qt_manual_value"])
        self.assertEqual(model.data(qt_mod_index, QtCore.Qt.DisplayRole), "1 x 1 x 5")

    def test_child_qt_mod_is_not_editable(self) -> None:
        model = self._build_model()
        qt_mod_index = model.index(0, model.column_keys.index("qt_mod"))

        flags = model.flags(qt_mod_index)

        self.assertFalse(bool(flags & QtCore.Qt.ItemIsEditable))

    def test_different_stored_value_without_manual_flag_is_not_manual(self) -> None:
        model = self._build_model(qt_und=6.0, manual=False)

        self.assertFalse(model.is_qt_und_manual(0))


if __name__ == "__main__":
    unittest.main()
