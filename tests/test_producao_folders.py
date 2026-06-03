import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Martelo_Orcamentos_V2.app.db import Base
from Martelo_Orcamentos_V2.app.models.client import Client
from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento
from Martelo_Orcamentos_V2.app.models.producao import Producao
from Martelo_Orcamentos_V2.app.models.user import User
from Martelo_Orcamentos_V2.app.services import producao_processos


TABLES = [User.__table__, Client.__table__, Orcamento.__table__, Producao.__table__]


class ProducaoFolderResolutionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=TABLES)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine, tables=list(reversed(TABLES)))
        self.engine.dispose()

    def _add_processo(self) -> Producao:
        proc = Producao(
            id=10,
            codigo_processo="26.0417_01_02_CLIENTE_NOVO",
            ano="2026",
            num_enc_phc="0417",
            versao_obra="01",
            versao_plano="02",
            nome_cliente="Cliente Novo",
            nome_cliente_simplex="CLIENTE_NOVO",
            ref_cliente="REF",
            estado="Planeamento",
            tipo_pasta=producao_processos.DEFAULT_PASTA_ENCOMENDA,
        )
        self.session.add(proc)
        self.session.commit()
        return proc

    def test_criar_pasta_para_processo_creates_expected_hierarchy(self):
        proc = self._add_processo()

        with tempfile.TemporaryDirectory() as tmp:
            result = producao_processos.criar_pasta_para_processo_detalhe(
                self.session,
                proc.id,
                base_dir=tmp,
                tipo_pasta=producao_processos.DEFAULT_PASTA_ENCOMENDA,
            )

            expected = (
                Path(tmp)
                / "2026"
                / "Encomenda de Cliente"
                / "0417_CLIENTE_NOVO"
                / "0417_01_CLIENTE_NOVO"
                / "0417_01_02_CLIENTE_NOVO"
            )
            self.assertEqual(result.path, expected)
            self.assertTrue(result.created)
            self.assertEqual(result.warnings, ())
            self.assertTrue(expected.is_dir())
            self.assertEqual(proc.pasta_servidor, str(expected))

    def test_criar_pasta_para_processo_reuses_existing_prefix_and_warns_on_client_suffix(self):
        proc = self._add_processo()

        with tempfile.TemporaryDirectory() as tmp:
            existing = (
                Path(tmp)
                / "2026"
                / "Encomenda de Cliente"
                / "0417_CLIENTE_ANTIGO"
                / "0417_01_CLIENTE_ANTIGO"
                / "0417_01_02_CLIENTE_ANTIGO"
            )
            existing.mkdir(parents=True)

            result = producao_processos.criar_pasta_para_processo_detalhe(
                self.session,
                proc.id,
                base_dir=tmp,
                tipo_pasta=producao_processos.DEFAULT_PASTA_ENCOMENDA,
            )

            self.assertEqual(result.path, existing)
            self.assertFalse(result.created)
            self.assertTrue(result.reused_existing)
            self.assertTrue(any("CLIENTE_ANTIGO" in warning for warning in result.warnings))
            self.assertEqual(proc.pasta_servidor, str(existing))


if __name__ == "__main__":
    unittest.main()
