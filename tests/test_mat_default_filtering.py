from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Martelo_Orcamentos_V2.app.db import Base
from Martelo_Orcamentos_V2.app.models.client import Client
from Martelo_Orcamentos_V2.app.models.dados_gerais import (
    DadosItemsFerragem,
    DadosItemsMaterial,
    DadosItemsSistemaCorrer,
)
from Martelo_Orcamentos_V2.app.models.definicao_peca import DefinicaoPeca
from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento, OrcamentoItem
from Martelo_Orcamentos_V2.app.models.user import User
from Martelo_Orcamentos_V2.app.services import custeio_items
from Martelo_Orcamentos_V2.app.services import dados_items as svc_dados_items


class MatDefaultFilteringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(
            self.engine,
            tables=[
                User.__table__,
                Client.__table__,
                Orcamento.__table__,
                OrcamentoItem.__table__,
                DadosItemsMaterial.__table__,
                DadosItemsFerragem.__table__,
                DadosItemsSistemaCorrer.__table__,
                DefinicaoPeca.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine, future=True)
        self.session = self.Session()
        self.session.add(User(id=7, username="tester", pass_hash="x"))
        self.session.add(Client(id=1, nome="Cliente Teste", nome_simplex="CLIENTE_TESTE"))
        self.session.add(
            Orcamento(
                id=10,
                ano="2026",
                num_orcamento="260379",
                versao="01",
                client_id=1,
                created_by=7,
                updated_by=7,
            )
        )
        self.session.add(
            OrcamentoItem(
                id_item=11,
                id_orcamento=10,
                versao="01",
                item_ord=1,
                item="Item Teste",
                descricao="Teste",
                altura=2500,
                largura=1600,
                profundidade=600,
                qt=1,
                created_by=7,
                updated_by=7,
            )
        )
        self.session.flush()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()
        Base.metadata.drop_all(
            self.engine,
            tables=[
                DefinicaoPeca.__table__,
                DadosItemsSistemaCorrer.__table__,
                DadosItemsFerragem.__table__,
                DadosItemsMaterial.__table__,
                OrcamentoItem.__table__,
                Orcamento.__table__,
                Client.__table__,
                User.__table__,
            ],
        )
        self.engine.dispose()

    def _ctx(self):
        return svc_dados_items.carregar_contexto(self.session, 10, 11)

    def _add_material(self, group: str, *, descricao: str, familia: str = "PLACAS", preco_liq: float = 10.0) -> None:
        self.session.add(
            DadosItemsMaterial(
                id=100 + self.session.query(DadosItemsMaterial).count(),
                cliente_id=1,
                user_id=7,
                ano="2026",
                num_orcamento="260379",
                versao="01",
                ordem=1,
                orcamento_id=10,
                item_id=11,
                grupo_material=group,
                descricao=descricao,
                ref_le=f"REF-{group[:8]}",
                descricao_material=descricao,
                preco_liq=preco_liq,
                und="UN",
                desp=0,
                familia=familia,
                linha=1,
                custo_mp_und=1,
                custo_mp_total=1,
            )
        )

    def _add_ferragem(self, group: str, *, tipo: str, descricao: str, preco_liq: float = 3.0) -> None:
        self.session.add(
            DadosItemsFerragem(
                id=200 + self.session.query(DadosItemsFerragem).count(),
                cliente_id=1,
                user_id=7,
                ano="2026",
                num_orcamento="260379",
                versao="01",
                ordem=1,
                orcamento_id=10,
                item_id=11,
                grupo_ferragem=group,
                descricao=descricao,
                ref_le=f"FER-{group[:8]}",
                descricao_material=descricao,
                preco_liq=preco_liq,
                und="UN",
                desp=0,
                tipo=tipo,
                familia="FERRAGENS",
                linha=1,
                custo_mp_und=1,
                custo_mp_total=1,
            )
        )

    def _add_sistema(self, group: str, *, tipo: str, descricao: str, familia: str = "SISTEMAS CORRER") -> None:
        self.session.add(
            DadosItemsSistemaCorrer(
                id=300 + self.session.query(DadosItemsSistemaCorrer).count(),
                cliente_id=1,
                user_id=7,
                ano="2026",
                num_orcamento="260379",
                versao="01",
                ordem=1,
                orcamento_id=10,
                item_id=11,
                grupo_sistema=group,
                descricao=descricao,
                ref_le=f"SIS-{group[:8]}",
                descricao_material=descricao,
                preco_liq=12,
                und="UN",
                desp=0,
                tipo=tipo,
                familia=familia,
                linha=1,
                custo_mp_und=1,
                custo_mp_total=1,
            )
        )

    def _add_definicao(
        self,
        *,
        nome: str,
        tipo: str = "",
        subgrupo: str | None = None,
        origem: str | None = None,
        grupos: str | None = None,
        default: str | None = None,
    ) -> None:
        self.session.add(
            DefinicaoPeca(
                tipo_peca_principal=tipo or nome.split(" ", 1)[0],
                subgrupo_peca=subgrupo,
                nome_da_peca=nome,
                mat_default_origem=origem,
                mat_default_grupos=grupos,
                mat_default_default=default,
            )
        )

    def test_definicao_peca_prioriza_grupos_configurados_para_costa(self) -> None:
        for group in ("Costas", "Laterais", "Tetos", "Fundos", "Portas Abrir 1"):
            self._add_material(group, descricao=f"Material {group}")
        self._add_definicao(
            nome="COSTA CHAPAR",
            tipo="COSTA",
            origem="materiais",
            grupos="Costas; Laterais; Tetos; Fundos",
            default="Laterais",
        )
        self.session.flush()

        row = {"def_peca": "COSTA CHAPAR [0000]", "familia": "PLACAS"}
        options = custeio_items.resolver_opcoes_mat_default(self.session, self._ctx(), row)

        self.assertEqual(options, ["Laterais", "Costas", "Tetos", "Fundos"])
        self.assertNotIn("Portas Abrir 1", options)

    def test_fallback_contextual_para_teto_remove_grupos_absurdos(self) -> None:
        for group in ("Costas", "Laterais", "Tetos", "Fundos", "Portas Abrir 1", "Gaveta Frente"):
            self._add_material(group, descricao=f"Material {group}")
        self.session.flush()

        row = {"def_peca": "TETO [0000]", "familia": "PLACAS"}
        options = custeio_items.resolver_opcoes_mat_default(self.session, self._ctx(), row)

        self.assertEqual(options, ["Tetos", "Laterais", "Fundos", "Costas"])
        self.assertNotIn("Portas Abrir 1", options)
        self.assertNotIn("Gaveta Frente", options)

    def test_ferragem_filtra_por_tipo_sem_misturar_puxadores(self) -> None:
        self._add_ferragem("Dobradica Reta", tipo="DOBRADICAS", descricao="Dobradiça Reta DB")
        self._add_ferragem("Dobradica Canto", tipo="DOBRADICAS", descricao="Dobradiça Canto DB")
        self._add_ferragem("Puxador Fresado J", tipo="PUXADOR", descricao="Puxador DB")
        self.session.flush()

        row = {"def_peca": "DOBRADICA RETA", "tipo": "DOBRADICAS", "familia": "FERRAGENS"}
        options = custeio_items.resolver_opcoes_mat_default(self.session, self._ctx(), row)

        self.assertIn("Dobradica Reta", options)
        self.assertIn("Dobradica Canto", options)
        self.assertNotIn("Puxador Fresado J", options)

    def test_definicao_por_subgrupo_consegue_refinar_ferragem(self) -> None:
        self._add_ferragem("Dobradica Reta", tipo="DOBRADICAS", descricao="Dobradiça Reta DB")
        self._add_ferragem("Dobradica Canto", tipo="DOBRADICAS", descricao="Dobradiça Canto DB")
        self._add_ferragem("Corredica Invisivel", tipo="CORREDICAS", descricao="Corrediça DB")
        self._add_definicao(
            nome="DOBRADICA",
            subgrupo="DOBRADICA",
            origem="ferragens",
            grupos="Dobradica Reta; Dobradica Canto",
            default="Dobradica Canto",
        )
        self.session.flush()

        row = {"def_peca": "DOBRADICA RETA", "familia": "FERRAGENS"}
        options = custeio_items.resolver_opcoes_mat_default(self.session, self._ctx(), row)

        self.assertEqual(options, ["Dobradica Canto", "Dobradica Reta"])
        self.assertNotIn("Corredica Invisivel", options)

    def test_definicao_com_subgrupo_sem_lista_explicitada_ainda_filtra(self) -> None:
        self._add_ferragem("Puxador Fresado J", tipo="PUXADOR", descricao="Puxador J")
        self._add_ferragem("Puxador STD 1", tipo="PUXADOR", descricao="Puxador STD")
        self._add_ferragem("Corredica 1", tipo="CORREDICAS", descricao="Corrediça 1")
        self._add_definicao(
            nome="PUXADOR FRESADO J",
            tipo="FERRAGENS",
            subgrupo="PUXADORES",
            origem="ferragens",
        )
        self.session.flush()

        row = {"def_peca": "PUXADOR FRESADO J", "familia": "FERRAGENS"}
        options = custeio_items.resolver_opcoes_mat_default(self.session, self._ctx(), row)

        self.assertIn("Puxador Fresado J", options)
        self.assertIn("Puxador STD 1", options)
        self.assertNotIn("Corredica 1", options)

    def test_preview_mat_default_mostra_descricao_e_preco(self) -> None:
        self._add_ferragem("Ferragens Diversas 1", tipo="FERRAGENS", descricao="Acessorio Especial DB", preco_liq=2.5)
        self.session.flush()

        row = {"def_peca": "Ferragens Diversas 1", "familia": "FERRAGENS"}
        preview = custeio_items.obter_preview_mat_default(self.session, self._ctx(), row, "Ferragens Diversas 1")
        tooltip = custeio_items.formatar_tooltip_preview_mat_default(preview)

        self.assertIsNotNone(preview)
        self.assertIn("Acessorio Especial DB", tooltip)
        self.assertIn("2,50", tooltip)


if __name__ == "__main__":
    unittest.main()
