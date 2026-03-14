import unittest
from types import SimpleNamespace

from Martelo_Orcamentos_V2.ui.pages.orcamentos_persistence_support import (
    build_duplicate_success_message,
    build_orcamento_identity,
    determine_manual_price_flag,
    find_row_index_by_id,
    is_valid_year_text,
    merge_orcamento_extras,
)


class OrcamentosPersistenceSupportTests(unittest.TestCase):
    def test_is_valid_year_text_requires_four_digits(self):
        self.assertTrue(is_valid_year_text("2026"))
        self.assertFalse(is_valid_year_text("26"))
        self.assertFalse(is_valid_year_text("20A6"))

    def test_build_orcamento_identity_formats_number_and_version(self):
        num, ver = build_orcamento_identity(
            year_text="2026",
            seq_text="262",
            version_text="1",
            format_version=lambda value: str(value).zfill(2),
        )
        self.assertEqual(num, "260262")
        self.assertEqual(ver, "01")

    def test_determine_manual_price_flag_covers_new_and_existing(self):
        self.assertTrue(determine_manual_price_flag(is_new=True, preco_val=10, preco_manual_changed=False, existing_manual_flag=False))
        self.assertFalse(determine_manual_price_flag(is_new=True, preco_val=None, preco_manual_changed=False, existing_manual_flag=True))
        self.assertTrue(determine_manual_price_flag(is_new=False, preco_val=None, preco_manual_changed=True, existing_manual_flag=False))
        self.assertTrue(determine_manual_price_flag(is_new=False, preco_val=None, preco_manual_changed=False, existing_manual_flag=True))

    def test_merge_orcamento_extras_handles_manual_and_temp_client(self):
        item = SimpleNamespace(is_temp=True, temp_id=9, nome="TEMP")
        extras = merge_orcamento_extras(
            {"legacy": True},
            manual_flag=True,
            cliente_item=item,
            preco_manual_key="preco_manual",
            temp_client_id_key="temp_id",
            temp_client_name_key="temp_nome",
        )
        self.assertEqual(extras["preco_manual"], True)
        self.assertEqual(extras["temp_id"], 9)
        self.assertEqual(extras["temp_nome"], "TEMP")

    def test_find_row_index_by_id_and_duplicate_message(self):
        rows = [SimpleNamespace(id=1), SimpleNamespace(id=7)]
        self.assertEqual(find_row_index_by_id(rows, 7), 1)
        self.assertIsNone(find_row_index_by_id(rows, 9))
        msg = build_duplicate_success_message(SimpleNamespace(versao="02", num_orcamento="260262"))
        self.assertIn("02", msg)
        self.assertIn("260262", msg)


if __name__ == "__main__":
    unittest.main()
