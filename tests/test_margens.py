import unittest
from decimal import Decimal
from types import SimpleNamespace

from Martelo_Orcamentos_V2.app.services import margens


class _FakeSession:
    def __init__(self, orcamento):
        self._orcamento = orcamento
        self.added = []
        self.flush_calls = 0

    def get(self, model, orcamento_id):
        _ = model, orcamento_id
        return self._orcamento

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flush_calls += 1


class MargensTests(unittest.TestCase):
    def test_update_sum_preco_final_prefers_column_state_over_stale_legacy_flag(self):
        orcamento = SimpleNamespace(
            id=10,
            preco_total=Decimal("10.00"),
            preco_total_manual=0,
            preco_atualizado_em=None,
            extras={"preco_manual": True, "margens_config": {"percent": {"margem_lucro_perc": 3.0}}},
        )
        session = _FakeSession(orcamento)

        margens.update_sum_preco_final(session, 10, Decimal("25.50"))

        self.assertEqual(orcamento.preco_total, Decimal("25.50"))
        self.assertEqual(orcamento.preco_total_manual, 0)
        self.assertNotIn("preco_manual", orcamento.extras)
        self.assertEqual(orcamento.extras["margens_config"]["soma_preco_final"], 25.5)
        self.assertIsNotNone(orcamento.preco_atualizado_em)
        self.assertGreaterEqual(session.flush_calls, 1)

    def test_update_sum_preco_final_preserves_manual_price_value(self):
        orcamento = SimpleNamespace(
            id=10,
            preco_total=Decimal("88.00"),
            preco_total_manual=1,
            preco_atualizado_em=None,
            extras={"margens_config": {}},
        )
        session = _FakeSession(orcamento)

        margens.update_sum_preco_final(session, 10, Decimal("25.50"))

        self.assertEqual(orcamento.preco_total, Decimal("88.00"))
        self.assertEqual(orcamento.preco_total_manual, 1)
        self.assertTrue(orcamento.extras["preco_manual"])
        self.assertEqual(orcamento.extras["margens_config"]["soma_preco_final"], 25.5)


if __name__ == "__main__":
    unittest.main()
