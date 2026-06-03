import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Martelo_Orcamentos_V2.app.db import Base
from Martelo_Orcamentos_V2.app.models.client import Client
from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento, OrcamentoItem
from Martelo_Orcamentos_V2.app.models.user import User
from Martelo_Orcamentos_V2.app.services.orcamentos import search_orcamentos


SEARCH_TABLES = [User.__table__, Client.__table__, Orcamento.__table__, OrcamentoItem.__table__]


class OrcamentosSearchTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=SEARCH_TABLES)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.session.add(User(id=7, username="paulo", pass_hash="x"))
        self.session.add(Client(id=1, nome="MOVEIS J.F. VIVA", nome_simplex="JF_VIVA"))
        self.session.add(Client(id=2, nome="CLIENTE COZINHAS", nome_simplex="COZINHAS"))
        self.session.add(
            Orcamento(
                id=10,
                ano="2026",
                num_orcamento="260531",
                versao="01",
                client_id=1,
                status="Falta Orcamentar",
                data="09-05-2026",
                ref_cliente="2601005",
                descricao_orcamento="2 ROUPEIROS PORTAS ABRIR + MODULO ABERTO PRATELEIRAS",
                info_1="INTERIORES MLM LINHO CANCUN",
                created_by=7,
                preco_total_manual=0,
            )
        )
        self.session.add(
            Orcamento(
                id=11,
                ano="2026",
                num_orcamento="260528",
                versao="01",
                client_id=2,
                status="Enviado",
                data="08-05-2026",
                ref_cliente="COZ01",
                descricao_orcamento="COZINHA COM FRENTES EM TERMO",
                created_by=7,
                preco_total_manual=0,
            )
        )
        self.session.add(
            Orcamento(
                id=12,
                ano="2026",
                num_orcamento="260100",
                versao="01",
                client_id=1,
                status="Falta Orcamentar",
                data="07-05-2026",
                ref_cliente="COZINHA",
                descricao_orcamento="Servico tecnico diverso",
                created_by=7,
                preco_total_manual=0,
            )
        )
        self.session.add(
            OrcamentoItem(
                id_item=101,
                id_orcamento=11,
                versao="01",
                item_ord=1,
                item="Item 1",
                codigo="CZ-ILHA",
                descricao="Cozinha com ilha central e despenseiro",
                und="und",
            )
        )
        self.session.commit()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine, tables=list(reversed(SEARCH_TABLES)))
        self.engine.dispose()

    def test_search_accepts_space_separated_terms_when_legacy_phrase_fails(self):
        rows = search_orcamentos(self.session, "roupeiro prateleiras")

        self.assertEqual([row.id for row in rows], [10])

    def test_search_includes_orcamento_items(self):
        rows = search_orcamentos(self.session, "ilha central")

        self.assertEqual([row.id for row in rows], [11])
        self.assertIn("Item", rows[0].search_reason)

    def test_search_uses_domain_synonyms_as_fallback(self):
        rows = search_orcamentos(self.session, "armario batente")

        self.assertEqual([row.id for row in rows], [10])
        self.assertIn("sinonimo", rows[0].search_reason)

    def test_search_uses_fuzzy_fallback_for_small_typos(self):
        rows = search_orcamentos(self.session, "rouperio")

        self.assertEqual([row.id for row in rows], [10])
        self.assertIn("aproximacao", rows[0].search_reason)

    def test_search_ranks_reference_matches_above_description_matches(self):
        rows = search_orcamentos(self.session, "cozinha")

        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(rows[0].id, 12)
        self.assertIn("Referencia", rows[0].search_reason)
        self.assertGreater(rows[0].search_score, rows[1].search_score)


if __name__ == "__main__":
    unittest.main()
