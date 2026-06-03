from __future__ import annotations

from Martelo_V3.domain import (
    LocalOverride,
    build_custeio_lines,
    build_proposal_summary,
    module_by_id,
    money,
    validate_configuration,
)
from Martelo_V3.sample_data import default_dimensions, default_rules, demo_item_rules, demo_modules


def _rows(module_id: str, *, rules=None, overrides=None, dimensions=None):
    module = module_by_id(demo_modules(), module_id)
    return build_custeio_lines(
        module,
        dimensions or default_dimensions(),
        rules or default_rules(),
        overrides or {},
    )


def test_catalogo_v3_contem_cinco_modulos_do_mvp() -> None:
    modules = demo_modules()
    ids = {module.module_id for module in modules}

    assert {
        "wardrobe_open_1",
        "wardrobe_open_2",
        "wardrobe_sliding",
        "kitchen_base",
        "wc_base",
    }.issubset(ids)


def test_roupeiro_uma_porta_gera_pecas_ferragens_e_preco() -> None:
    rows = _rows("wardrobe_open_1")
    proposal = build_proposal_summary(rows)
    porta = next(row for row in rows if row.description == "Porta abrir")

    assert any(row.description == "Porta abrir" for row in rows)
    assert any(row.description == "Dobradiças" for row in rows)
    assert "1000000" in porta.material_formula
    assert "EUR" in porta.total_formula
    assert proposal.cost_total > money(0)
    assert proposal.sell_price > proposal.cost_total


def test_alterar_medidas_recalcula_dimensoes_e_custos() -> None:
    small = _rows("wardrobe_open_2")
    large = _rows("wardrobe_open_2", dimensions=default_dimensions().__class__(h=2600, l=1400, p=650))

    small_porta = next(row for row in small if row.structure_key == "porta_2p")
    large_porta = next(row for row in large if row.structure_key == "porta_2p")

    assert large_porta.resolved_comp > small_porta.resolved_comp
    assert large_porta.resolved_larg > small_porta.resolved_larg
    assert build_proposal_summary(large).cost_total > build_proposal_summary(small).cost_total


def test_dados_items_substituem_dados_gerais_sem_override_local() -> None:
    rules = default_rules()
    rules.item.update(demo_item_rules())
    rows = _rows("wardrobe_open_1", rules=rules)

    porta = next(row for row in rows if row.structure_key == "porta_1p")

    assert porta.rule_source == "Dados Items"
    assert "premium" in porta.material_description.lower()
    assert porta.override_reason == ""


def test_override_local_preserva_motivo_e_nao_apaga_outras_linhas() -> None:
    overrides = {
        "porta_1p": LocalOverride(
            material_description="Porta especial",
            unit_cost=money("40"),
            reason="Cliente pediu acabamento especial.",
        )
    }
    rows = _rows("wardrobe_open_1", overrides=overrides)
    porta = next(row for row in rows if row.structure_key == "porta_1p")
    prateleiras = next(row for row in rows if row.structure_key == "prat_1p")

    assert porta.rule_source == "Edição Local"
    assert porta.override_reason == "Cliente pediu acabamento especial."
    assert porta.material_unit_cost == money("40")
    assert prateleiras.rule_source == "Dados Gerais"
    assert len(rows) == 9


def test_formula_linha_explica_material_orla_acabamento_producao_e_total() -> None:
    rows = _rows("wardrobe_open_1")
    porta = next(row for row in rows if row.structure_key == "porta_1p")
    dobradica = next(row for row in rows if row.structure_key == "dob_1p")

    assert porta.usage_label.endswith("m2")
    assert "x 2 faces" in porta.finish_formula
    assert "min / 60" in porta.labor_formula
    assert "+" in porta.total_formula
    assert dobradica.usage_label.endswith("UN")
    assert dobradica.edge_formula == "Nao aplicavel"


def test_modulos_correr_cozinha_wc_validam_cenarios_do_mvp() -> None:
    for module_id in ("wardrobe_sliding", "kitchen_base", "wc_base"):
        module = module_by_id(demo_modules(), module_id)
        rules = default_rules()
        rows = _rows(module_id, rules=rules)
        validation = validate_configuration(module, default_dimensions(), rules, rows)

        assert rows
        assert build_proposal_summary(rows).sell_price > money(0)
        assert not any(state == "Erro" for state, _message in validation)


def test_proposta_final_expoe_custo_margem_e_preco() -> None:
    rows = _rows("kitchen_base")
    proposal = build_proposal_summary(rows)

    assert proposal.cost_material > money(0)
    assert proposal.cost_labor > money(0)
    assert proposal.margin_value > money(0)
    assert proposal.sell_price == proposal.cost_total + proposal.admin_value + proposal.margin_value
