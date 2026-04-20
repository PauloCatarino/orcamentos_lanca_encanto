import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtTest, QtWidgets

from Martelo_Orcamentos_V2.ui.dialogs.orcamento_picker import OrcamentoPicker


def _build_row(*, row_id: int, num_orcamento: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=row_id,
        ano="2026",
        num_orcamento=num_orcamento,
        versao="01",
        enc_phc="",
        cliente="CLIENTE TESTE",
        ref_cliente="REF-TESTE",
        obra="OBRA TESTE",
        preco_total=1000.0,
        status="Enviado",
    )


class OrcamentoPickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_enter_in_search_field_reloads_results_without_accepting_dialog(self) -> None:
        initial_rows = [_build_row(row_id=1, num_orcamento="260100")]
        filtered_rows = [_build_row(row_id=2, num_orcamento="260358")]
        with patch(
            "Martelo_Orcamentos_V2.ui.dialogs.orcamento_picker.list_orcamentos",
            return_value=initial_rows,
        ), patch(
            "Martelo_Orcamentos_V2.ui.dialogs.orcamento_picker.search_orcamentos",
            return_value=filtered_rows,
        ) as search_mock:
            dialog = OrcamentoPicker(session=object())
            dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
            self.addCleanup(dialog.close)
            dialog.show()
            QtWidgets.QApplication.processEvents()

            dialog.ed_search.setFocus()
            dialog.ed_search.setText("260358")
            QtTest.QTest.keyClick(dialog.ed_search, QtCore.Qt.Key_Return)
            QtWidgets.QApplication.processEvents()

            search_mock.assert_called_once_with(dialog.session, "260358")
            self.assertEqual(dialog.result(), 0)
            self.assertEqual(dialog.model.rowCount(), 1)
            self.assertEqual(dialog.model.get_row(0)["id"], 2)

    def test_enter_in_table_accepts_selected_orcamento(self) -> None:
        rows = [_build_row(row_id=9, num_orcamento="260999")]
        with patch(
            "Martelo_Orcamentos_V2.ui.dialogs.orcamento_picker.list_orcamentos",
            return_value=rows,
        ), patch(
            "Martelo_Orcamentos_V2.ui.dialogs.orcamento_picker.search_orcamentos",
            return_value=[],
        ):
            dialog = OrcamentoPicker(session=object())
            dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
            self.addCleanup(dialog.close)
            dialog.show()
            QtWidgets.QApplication.processEvents()

            dialog.table.setFocus()
            dialog.table.selectRow(0)
            QtTest.QTest.keyClick(dialog.table, QtCore.Qt.Key_Return)
            QtWidgets.QApplication.processEvents()

            self.assertEqual(dialog.result(), QtWidgets.QDialog.Accepted)
            self.assertEqual(dialog.selected_id(), 9)

    def test_clear_search_action_clears_search_text(self) -> None:
        with patch(
            "Martelo_Orcamentos_V2.ui.dialogs.orcamento_picker.list_orcamentos",
            return_value=[],
        ), patch(
            "Martelo_Orcamentos_V2.ui.dialogs.orcamento_picker.search_orcamentos",
            return_value=[],
        ):
            dialog = OrcamentoPicker(session=object())
            dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
            self.addCleanup(dialog.close)

            dialog.ed_search.setText("260358")
            self.assertTrue(dialog._clear_search_action.isVisible())

            dialog._clear_search_action.trigger()

            self.assertEqual(dialog.ed_search.text(), "")
            self.assertFalse(dialog._clear_search_action.isVisible())


if __name__ == "__main__":
    unittest.main()
