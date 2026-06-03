from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from Martelo_Orcamentos_V2.ui.main_window import MainWindow
from Martelo_Orcamentos_V2.ui.pages.custeio_items import CusteioItemsPage


class ItemDeleteUiSyncTests(unittest.TestCase):
    def test_main_window_loads_next_item_without_autosave_after_delete(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.current_orcamento_id = 747
        window.current_item_id = 835
        window.pg_dados_items = MagicMock()
        window.pg_custeio = MagicMock()

        MainWindow.on_item_deleted(window, 835, 840)

        self.assertEqual(window.current_item_id, 840)
        window.pg_dados_items.load_item.assert_called_once_with(747, 840)
        window.pg_custeio.load_item.assert_called_once_with(747, 840)
        window.pg_custeio.auto_save_if_dirty.assert_not_called()

    def test_custeio_autosave_discards_context_when_item_was_deleted(self) -> None:
        page = CusteioItemsPage.__new__(CusteioItemsPage)
        page.context = SimpleNamespace(item_id=835, orcamento_id=747)
        page.current_item_id = 835
        page._current_item_obj = object()
        page._pending_module_imports = [{"x": 1}]
        page._nst_override_snapshot = [True]
        page._dimensions_dirty = True
        page.session = MagicMock()
        page.session.execute.return_value.scalar_one_or_none.return_value = None
        page.table_model = MagicMock()
        page.is_dirty = MagicMock(return_value=True)
        page._save_custeio = MagicMock(return_value=False)
        page._clear_dimension_values = MagicMock()
        page._set_rows_dirty = MagicMock()
        page._update_table_placeholder_visibility = MagicMock()
        page._update_save_button_text = MagicMock()

        saved = CusteioItemsPage.auto_save_if_dirty(page)

        self.assertTrue(saved)
        self.assertIsNone(page.context)
        self.assertIsNone(page.current_item_id)
        page._save_custeio.assert_not_called()
        page.session.rollback.assert_called_once()
        page.table_model.clear.assert_called_once()


if __name__ == "__main__":
    unittest.main()
