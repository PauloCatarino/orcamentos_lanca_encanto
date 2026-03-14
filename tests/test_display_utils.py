import unittest

from Martelo_Orcamentos_V2.app.utils.display import format_currency_pt, parse_currency_pt, repair_mojibake


class DisplayUtilsTests(unittest.TestCase):
    def test_format_currency_uses_euro_symbol(self):
        self.assertEqual(format_currency_pt(1120.04), "1.120,04 €")

    def test_parse_currency_accepts_formatted_euro_value(self):
        self.assertEqual(parse_currency_pt("1.120,04 €"), 1120.04)

    def test_repair_mojibake_restores_common_text(self):
        self.assertEqual(repair_mojibake("PreÃ§o"), "Preço")


if __name__ == "__main__":
    unittest.main()
