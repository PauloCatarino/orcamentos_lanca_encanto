import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Martelo_Orcamentos_V2.app.db import Base
from Martelo_Orcamentos_V2.app.models.client import Client
from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento
from Martelo_Orcamentos_V2.app.models.producao import Producao
from Martelo_Orcamentos_V2.app.models.user import User
from Martelo_Orcamentos_V2.app.services.producao_processos import listar_processos


SEARCH_TABLES = [User.__table__, Client.__table__, Orcamento.__table__, Producao.__table__]


class ProducaoSearchTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=SEARCH_TABLES)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.session.add(
            Producao(
                id=10,
                codigo_processo="26.0501_01_01_JF_VIVA",
                ano="2026",
                num_enc_phc="0501",
                versao_obra="01",
                versao_plano="01",
                estado="Planeamento",
                responsavel="Paulo",
                nome_cliente="MOVEIS J.F. VIVA",
                ref_cliente="250811",
                descricao_producao="7 ROUPEIROS PORTAS ABRIR",
                descricao_artigos="Modulo aberto com prateleiras",
            )
        )
        self.session.add(
            Producao(
                id=11,
                codigo_processo="26.0702_01_01_GSW",
                ano="2026",
                num_enc_phc="0702",
                versao_obra="01",
                versao_plano="01",
                estado="Planeamento",
                responsavel="Dario",
                nome_cliente="GSW, LDA",
                ref_cliente="REF-COZ",
                descricao_producao="COZINHA",
                descricao_artigos="Cozinha com ilha",
            )
        )
        self.session.add(
            Producao(
                id=12,
                codigo_processo="26.0900_01_01_TESTE",
                ano="2026",
                num_enc_phc="0900",
                versao_obra="01",
                versao_plano="01",
                estado="Planeamento",
                responsavel="Andreia",
                nome_cliente="COZINHA PRIME",
                ref_cliente="OUTRO",
                descricao_producao="Servico tecnico",
            )
        )
        self.session.commit()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine, tables=list(reversed(SEARCH_TABLES)))
        self.engine.dispose()

    def test_search_uses_domain_synonyms_as_fallback(self):
        rows = listar_processos(self.session, search="armario batente")

        self.assertEqual([row.id for row in rows], [10])
        self.assertIn("sinonimo", rows[0].search_reason)

    def test_search_uses_fuzzy_fallback_for_small_typos(self):
        rows = listar_processos(self.session, search="rouperio")

        self.assertEqual([row.id for row in rows], [10])
        self.assertIn("aproximacao", rows[0].search_reason)

    def test_search_ranks_reference_matches_above_description_matches(self):
        rows = listar_processos(self.session, search="cozinha")

        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(rows[0].id, 12)
        self.assertIn("Cliente", rows[0].search_reason)
        self.assertGreater(rows[0].search_score, rows[1].search_score)


if __name__ == "__main__":
    unittest.main()
