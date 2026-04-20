import unittest
from decimal import Decimal
from types import SimpleNamespace

from Martelo_Orcamentos_V2.app.services import price_management


class _FakeSession:
    def __init__(self):
        self.commit_calls = 0

    def commit(self):
        self.commit_calls += 1


class PriceManagementTests(unittest.TestCase):
    def test_set_price_calculated_clears_legacy_manual_flag(self):
        session = _FakeSession()
        orcamento = SimpleNamespace(
            preco_total=Decimal("10.00"),
            preco_total_manual=1,
            preco_atualizado_em=None,
            extras={"preco_manual": True, "outra": "info"},
        )

        price_management.set_price_calculated(session, orcamento, Decimal("25.50"), commit=False)

        self.assertEqual(orcamento.preco_total, Decimal("25.50"))
        self.assertEqual(orcamento.preco_total_manual, 0)
        self.assertNotIn("preco_manual", orcamento.extras)
        self.assertEqual(orcamento.extras["outra"], "info")
        self.assertIsNotNone(orcamento.preco_atualizado_em)
        self.assertEqual(session.commit_calls, 0)

    def test_set_price_manual_sets_column_and_legacy_flag(self):
        session = _FakeSession()
        orcamento = SimpleNamespace(
            preco_total=None,
            preco_total_manual=0,
            preco_atualizado_em=None,
            extras={"outra": "info"},
        )

        price_management.set_price_manual(session, orcamento, Decimal("99.99"), commit=False)

        self.assertEqual(orcamento.preco_total, Decimal("99.99"))
        self.assertEqual(orcamento.preco_total_manual, 1)
        self.assertTrue(orcamento.extras["preco_manual"])
        self.assertEqual(orcamento.extras["outra"], "info")
        self.assertIsNotNone(orcamento.preco_atualizado_em)

    def test_is_price_manual_falls_back_to_legacy_flag_when_column_missing(self):
        legacy_only = SimpleNamespace(extras={"preco_manual": True})

        self.assertTrue(price_management.is_price_manual(legacy_only))


if __name__ == "__main__":
    unittest.main()
