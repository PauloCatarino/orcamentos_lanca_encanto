from Martelo_Orcamentos_V2.app.services import custeio_items as svc_custeio


def test_auto_dimension_setting_roundtrip(db_session):
    user_id = 42

    assert svc_custeio.is_auto_dimension_enabled(db_session, user_id) is False

    svc_custeio.set_auto_dimension_enabled(db_session, user_id, True)
    assert svc_custeio.is_auto_dimension_enabled(db_session, user_id) is True

    svc_custeio.set_auto_dimension_enabled(db_session, user_id, False)
    assert svc_custeio.is_auto_dimension_enabled(db_session, user_id) is False


def test_aplicar_dimensoes_automaticas_prefills_expected():
    rows = [
        {"def_peca": "Costa 01", "comp": None, "larg": None},
        {"def_peca": "PORTA ABRIR ESQ", "comp": None, "larg": None},
        {"def_peca": "LATERAL DIR", "comp": "", "larg": None},
        {"def_peca": "DIVISORIA_2", "comp": None, "larg": None},
        {"def_peca": "PRATELEIRA AMOVIVEL 900", "comp": None, "larg": None},
        {"def_peca": "PRAT.FIXA 600", "comp": None, "larg": "custom"},
        {"def_peca": "OUTRA PECA", "comp": None, "larg": None},
    ]

    svc_custeio.aplicar_dimensoes_automaticas(rows)

    assert rows[0]["comp"] == "HM"
    assert rows[0]["larg"] == "LM"

    assert rows[1]["comp"] == "HM"
    assert rows[1]["larg"] == "LM"

    assert rows[2]["comp"] == "HM"
    assert rows[2]["larg"] == "PM"

    assert rows[3]["comp"] == "HM"
    assert rows[3]["larg"] == "PM"

    assert rows[4]["comp"] == "LM"
    assert rows[4]["larg"] == "PM"

    assert rows[5]["comp"] == "LM"
    assert rows[5]["larg"] == "custom"

    assert rows[6]["comp"] is None or rows[6]["comp"] == ""
    assert rows[6]["larg"] is None or rows[6]["larg"] == ""


def test_auto_dimension_prefix_selection(db_session):
    user_id = 99
    defaults = svc_custeio.list_available_auto_dimension_rules()
    selected = [defaults[0][0], defaults[2][0]]

    svc_custeio.save_auto_dimension_prefixes(db_session, user_id, selected)
    rules = svc_custeio.get_auto_dimension_rules(db_session, user_id)
    assert [rule[0] for rule in rules] == selected

    rows = [
        {"def_peca": f"{selected[0]} TESTE", "comp": None, "larg": None},
        {"def_peca": "PORTA ABRIR", "comp": None, "larg": None},
    ]

    svc_custeio.aplicar_dimensoes_automaticas(rows, rules=rules)

    assert rows[0]["comp"] == defaults[0][1]
    assert rows[0]["larg"] == defaults[0][2]

    # PORTA ABRIR não está selecionada, logo permanece vazio
    assert rows[1]["comp"] in (None, "")
    assert rows[1]["larg"] in (None, "")


def test_atualizar_orlas_custeio_sets_spp_and_skips_division(db_session):
    from Martelo_Orcamentos_V2.app.models.custeio import CusteioItem
    from decimal import Decimal

    # SPP line
    reg_spp = CusteioItem(
        id=1,
        orcamento_id=1,
        item_id=1,
        cliente_id=1,
        user_id=1,
        ano="2025",
        num_orcamento="1",
        versao="01",
        ordem=0,
        def_peca="VARAO {SPP}",
        und="ML",
        comp_res=Decimal("1200"),
        larg_res=Decimal("100"),
        esp_res=Decimal("18"),
    )
    db_session.add(reg_spp)

    # Divisão independente
    reg_div = CusteioItem(
        id=2,
        orcamento_id=1,
        item_id=1,
        cliente_id=1,
        user_id=1,
        ano="2025",
        num_orcamento="1",
        versao="01",
        ordem=1,
        def_peca="DIVISAO INDEPENDENTE",
        comp_res=Decimal("500"),
        larg_res=Decimal("200"),
        esp_res=Decimal("18"),
        area_m2_und=Decimal("1.23"),
        perimetro_und=Decimal("4.56"),
    )
    db_session.add(reg_div)
    db_session.commit()

    svc_custeio.atualizar_orlas_custeio(db_session, 1, 1)

    updated_spp = db_session.query(CusteioItem).filter_by(orcamento_id=1, item_id=1, ordem=0).one()
    assert updated_spp.spp_ml_und == Decimal("1.20")

    updated_div = db_session.query(CusteioItem).filter_by(orcamento_id=1, item_id=1, ordem=1).one()
    assert updated_div.area_m2_und is None
    assert updated_div.perimetro_und is None
    assert updated_div.spp_ml_und is None
