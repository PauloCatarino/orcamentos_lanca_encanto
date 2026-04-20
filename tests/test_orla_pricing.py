from __future__ import annotations

import unittest
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Martelo_Orcamentos_V2.app.db import Base
from Martelo_Orcamentos_V2.app.models.client import Client
from Martelo_Orcamentos_V2.app.models.custeio import CusteioItem
from Martelo_Orcamentos_V2.app.models.materia_prima import MateriaPrima
from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento, OrcamentoItem
from Martelo_Orcamentos_V2.app.models.user import User
from Martelo_Orcamentos_V2.app.services import custeio_items


class OrlaPricingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        self.session.add(User(id=1, username="tester", email="tester@example.com", pass_hash="x"))
        self.session.add(Client(id=1, nome="Cliente Teste"))
        self.session.add(
            Orcamento(
                id=1,
                ano="2026",
                num_orcamento="260411",
                versao="01",
                client_id=1,
                created_by=1,
                updated_by=1,
            )
        )
        self.session.add(
            OrcamentoItem(
                id_item=1,
                id_orcamento=1,
                item_ord=1,
                versao="01",
                descricao="Item Teste",
                updated_by=1,
            )
        )
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def _add_orla_mp(self, *, ref_le: str, pliq: float, und: str, desp: float = 10.0) -> None:
        self.session.add(
            MateriaPrima(
                id_mp=ref_le,
                ref_le=ref_le,
                descricao_orcamento=f"ORLA {ref_le}",
                pliq=Decimal(str(pliq)),
                und=und,
                desp=Decimal(str(desp)),
                tipo="VIDRO" if und == "ML" else "ORLA",
                familia="FERRAGENS" if und == "ML" else "ORLAS",
            )
        )
        self.session.commit()

    def _add_custeio_item(
        self,
        *,
        row_id: int,
        ref_orla: str,
        esp_res: float,
        qt_total: float,
        comp_res: float,
        larg_res: float,
        four_sides: bool = False,
    ) -> CusteioItem:
        item = CusteioItem(
            id=row_id,
            orcamento_id=1,
            item_id=1,
            cliente_id=1,
            user_id=1,
            ano="2026",
            num_orcamento="260411",
            versao="01",
            ordem=1,
            descricao="Linha Teste",
            def_peca="PAINEL TESTE",
            qt_total=Decimal(str(qt_total)),
            comp_res=Decimal(str(comp_res)),
            larg_res=Decimal(str(larg_res)),
            esp_res=Decimal(str(esp_res)),
            orl_1_0=ref_orla,
            orl_c1=Decimal("1.0"),
            und="M2",
            pliq=Decimal("20.20"),
            desp=Decimal("10.0"),
            tipo="VIDRO" if four_sides else "MDF",
            familia="FERRAGENS" if four_sides else "PLACAS",
        )
        if four_sides:
            item.orl_c2 = Decimal("1.0")
            item.orl_l1 = Decimal("1.0")
            item.orl_l2 = Decimal("1.0")
        self.session.add(item)
        self.session.commit()
        return item

    def test_resolver_preco_orla_ml_uses_pliq_directly(self) -> None:
        preco_ml, mode = custeio_items._resolver_preco_orla_por_ml(pliq=1.2, und="ML", esp_peca=6)
        self.assertEqual(float(preco_ml), 1.20)
        self.assertEqual(mode, "direct_ml")

    def test_resolver_preco_orla_m2_keeps_conversion_factor(self) -> None:
        preco_ml, mode = custeio_items._resolver_preco_orla_por_ml(pliq=140.0, und="M2", esp_peca=19)
        self.assertEqual(float(preco_ml), 3.26)
        self.assertEqual(mode, "from_m2_factor")

    def test_atualizar_orlas_custeio_keeps_m2_conversion(self) -> None:
        self._add_orla_mp(ref_le="ORL0005", pliq=140.0, und="M2", desp=10.0)
        reg = self._add_custeio_item(
            row_id=1,
            ref_orla="ORL0005",
            esp_res=19,
            qt_total=1,
            comp_res=1000,
            larg_res=500,
            four_sides=False,
        )

        custeio_items.atualizar_orlas_custeio(self.session, 1, 1)
        self.session.refresh(reg)

        self.assertAlmostEqual(float(reg.ml_orl_c1 or 0), 1.10, places=2)
        self.assertAlmostEqual(float(reg.custo_orl_c1 or 0), 3.59, places=2)
        self.assertAlmostEqual(float(reg.custo_total_orla or 0), 3.59, places=2)

    def test_atualizar_orlas_custeio_uses_direct_ml_for_glass_edge(self) -> None:
        self._add_orla_mp(ref_le="FER0085", pliq=1.20, und="ML", desp=10.0)
        reg = self._add_custeio_item(
            row_id=2,
            ref_orla="FER0085",
            esp_res=6,
            qt_total=4,
            comp_res=1778,
            larg_res=393,
            four_sides=True,
        )

        custeio_items.atualizar_orlas_custeio(self.session, 1, 1)
        self.session.refresh(reg)

        self.assertAlmostEqual(float(reg.ml_orl_c1 or 0), 7.84, places=2)
        self.assertAlmostEqual(float(reg.ml_orl_c2 or 0), 7.84, places=2)
        self.assertAlmostEqual(float(reg.ml_orl_l1 or 0), 1.72, places=2)
        self.assertAlmostEqual(float(reg.ml_orl_l2 or 0), 1.72, places=2)
        self.assertAlmostEqual(float(reg.custo_orl_c1 or 0), 9.41, places=2)
        self.assertAlmostEqual(float(reg.custo_orl_c2 or 0), 9.41, places=2)
        self.assertAlmostEqual(float(reg.custo_orl_l1 or 0), 2.06, places=2)
        self.assertAlmostEqual(float(reg.custo_orl_l2 or 0), 2.06, places=2)
        self.assertAlmostEqual(float(reg.custo_total_orla or 0), 22.94, places=2)


if __name__ == "__main__":
    unittest.main()
