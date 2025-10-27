import pytest
from decimal import Decimal
from Martelo_Orcamentos_V2.app.models.materia_prima import MateriaPrima
from Martelo_Orcamentos_V2.app.models.custeio import CusteioItem
from Martelo_Orcamentos_V2.app.services.custeio_items import atualizar_orlas_custeio


def test_atualizar_orlas_custeio_basic(db_session):
    """Caso básico: orl_0_4 presente e comp_res/larg_res preenchidos.

    Espera: ml_orl_c1 == comp_res/1000 e custo_orl_c1 > 0
    """
    import pytest
    from decimal import Decimal
    from Martelo_Orcamentos_V2.app.models.materia_prima import MateriaPrima
    from Martelo_Orcamentos_V2.app.models.custeio import CusteioItem
    from Martelo_Orcamentos_V2.app.services.custeio_items import atualizar_orlas_custeio


    def test_atualizar_orlas_custeio_basic(db_session):
        """Caso básico: orl_0_4 presente e comp_res/larg_res preenchidos.

        Espera: ml_orl_c1 == comp_res/1000 e custo_orl_c1 > 0
        """
        session = db_session

        # Inserir materia prima (orla) com ref_le
        mat = MateriaPrima(
            id_mp="M1",
            ref_le="REF1",
            descricao_orcamento="ORLA_TEST",
            pliq=Decimal("20.0000"),
            esp_mp=Decimal("0.4"),
            familia="ORLAS",
        )
        session.add(mat)

        # Inserir um CusteioItem para orcamento_id=1,item_id=1
        reg = CusteioItem(
            id=1,
            orcamento_id=1,
            item_id=1,
            cliente_id=1,
            user_id=1,
            ano="2025",
            num_orcamento="1",
            versao="01",
            ordem=0,
            comp_res=Decimal("1200"),
            larg_res=Decimal("600"),
            esp_res=Decimal("18"),
            orl_0_4="REF1",
            def_peca="[1111]",
            orl_c1=Decimal("0.4"),
            orl_1_0=None,
            ref_le=None,
        )
        session.add(reg)
        session.commit()

        atualizar_orlas_custeio(session, 1, 1)

        # Reload
        updated = session.query(CusteioItem).filter_by(orcamento_id=1, item_id=1).first()
        assert updated is not None
        assert updated.ml_orl_c1 == Decimal("1.2000")
        # custo should be > 0
        assert updated.custo_orl_c1 is not None
        assert Decimal(updated.custo_orl_c1) > Decimal("0")
        assert updated.area_m2_und == Decimal("0.7200")
        assert updated.perimetro_und == Decimal("3.6000")


    def test_atualizar_orlas_no_ref_results_zero(db_session):
        """Caso sem referencias: custos devem ser zero e ml calculado quando esp_orla None -> zero ml"""
        session = db_session

        reg = CusteioItem(
            id=2,
            orcamento_id=2,
            item_id=2,
            cliente_id=1,
            user_id=1,
            ano="2025",
            num_orcamento="2",
            versao="01",
            ordem=0,
            comp_res=Decimal("1200"),
            larg_res=Decimal("600"),
            esp_res=Decimal("18"),
            orl_0_4=None,
            orl_1_0=None,
            ref_le=None,
        )
        session.add(reg)
        session.commit()

        atualizar_orlas_custeio(session, 2, 2)

        updated = session.query(CusteioItem).filter_by(orcamento_id=2, item_id=2).first()
        assert updated is not None
        # No ref -> costs zero
        assert updated.custo_orl_c1 == Decimal("0.0000") or updated.custo_orl_c1 == 0
        assert updated.custo_total_orla == Decimal("0.0000") or updated.custo_total_orla == 0
        assert updated.area_m2_und == Decimal("0.0000") or updated.area_m2_und == 0
        assert updated.perimetro_und == Decimal("0.0000") or updated.perimetro_und == 0
