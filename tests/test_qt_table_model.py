import unittest

from PySide6 import QtCore

from Martelo_Orcamentos_V2.ui.models.qt_table import SimpleTableModel


class SimpleTableModelSortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])

    def test_sort_int_column_orders_numeric_strings_numerically(self):
        model = SimpleTableModel(
            rows=[
                {"num_cliente_phc": "10"},
                {"num_cliente_phc": "2"},
                {"num_cliente_phc": "100"},
                {"num_cliente_phc": "11"},
            ],
            columns=[{"header": "Num_PHC", "attr": "num_cliente_phc", "type": "int"}],
        )

        model.sort(0, QtCore.Qt.SortOrder.AscendingOrder)

        ordered = [model.get_row(i)["num_cliente_phc"] for i in range(model.rowCount())]
        self.assertEqual(ordered, ["2", "10", "11", "100"])


if __name__ == "__main__":
    unittest.main()
