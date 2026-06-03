from __future__ import annotations

import ast
import operator
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


Money = Decimal


def money(value: object) -> Money:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Dimensions:
    h: float
    l: float
    p: float
    hm: Optional[float] = None
    lm: Optional[float] = None
    pm: Optional[float] = None

    def variables(self) -> Dict[str, float]:
        return {
            "H": float(self.h),
            "L": float(self.l),
            "P": float(self.p),
            "HM": float(self.hm if self.hm is not None else self.h),
            "LM": float(self.lm if self.lm is not None else self.l),
            "PM": float(self.pm if self.pm is not None else self.p),
        }


@dataclass(frozen=True)
class MaterialRule:
    group: str
    ref: str
    description: str
    family: str
    unit: str
    unit_cost: Money
    source: str = "Dados Gerais"


@dataclass(frozen=True)
class LocalOverride:
    material_description: Optional[str] = None
    unit_cost: Optional[Money] = None
    quantity: Optional[float] = None
    reason: str = ""


@dataclass(frozen=True)
class ModuleLineTemplate:
    key: str
    kind: str
    description: str
    group: str
    family: str
    quantity: float = 1.0
    quantity_expr: Optional[str] = None
    comp_expr: Optional[str] = None
    larg_expr: Optional[str] = None
    esp_expr: Optional[str] = None
    edge_long_sides: int = 0
    edge_short_sides: int = 0
    finish_faces: int = 0
    labor_minutes: float = 0.0


@dataclass(frozen=True)
class ModuleDefinition:
    module_id: str
    name: str
    family: str
    description: str
    variables: Tuple[str, ...]
    lines: Tuple[ModuleLineTemplate, ...]
    inherited_rules: Tuple[str, ...] = ()
    item_overrides: Tuple[str, ...] = ()
    validations: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CusteioItemV3:
    """Separated V3 cost row contract.

    V2 stores many technical, material, formula and cost values in one heavy
    table.  V3 keeps those concerns explicit so the UI can show structure,
    rules, calculation and local overrides separately.
    """

    structure_key: str
    component_type: str
    description: str
    formula_comp: Optional[str]
    formula_larg: Optional[str]
    formula_esp: Optional[str]
    resolved_comp: Optional[float]
    resolved_larg: Optional[float]
    resolved_esp: Optional[float]
    quantity: float
    rule_group: str
    rule_source: str
    material_ref: str
    material_description: str
    material_unit_cost: Money
    usage_label: str
    cost_material: Money
    cost_edge: Money
    cost_finish: Money
    cost_labor: Money
    cost_total: Money
    material_formula: str
    edge_formula: str
    finish_formula: str
    labor_formula: str
    total_formula: str
    override_reason: str = ""


@dataclass(frozen=True)
class ProposalSummary:
    cost_material: Money
    cost_edge: Money
    cost_finish: Money
    cost_labor: Money
    cost_total: Money
    admin_value: Money
    margin_value: Money
    sell_price: Money
    line_count: int


@dataclass
class RuleSet:
    general: Dict[str, MaterialRule]
    item: Dict[str, MaterialRule] = field(default_factory=dict)

    def resolve(self, group: str) -> MaterialRule:
        if group in self.item:
            base = self.item[group]
            return MaterialRule(
                group=base.group,
                ref=base.ref,
                description=base.description,
                family=base.family,
                unit=base.unit,
                unit_cost=base.unit_cost,
                source="Dados Items",
            )
        if group in self.general:
            return self.general[group]
        return MaterialRule(
            group=group,
            ref="",
            description="Regra por definir",
            family="",
            unit="UN",
            unit_cost=money(0),
            source="Por definir",
        )


_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def evaluate_formula(expr: Optional[str], variables: Mapping[str, float]) -> Optional[float]:
    if expr is None:
        return None
    text = str(expr).strip()
    if not text:
        return None
    try:
        parsed = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Formula invalida: {text}") from exc

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in variables:
                raise ValueError(f"Variavel desconhecida na formula: {node.id}")
            return float(variables[node.id])
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            return float(_BIN_OPS[type(node.op)](_eval(node.left), _eval(node.right)))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return float(_UNARY_OPS[type(node.op)](_eval(node.operand)))
        raise ValueError(f"Formula nao suportada: {text}")

    return _eval(parsed)


def build_custeio_lines(
    module: ModuleDefinition,
    dimensions: Dimensions,
    rules: RuleSet,
    local_overrides: Optional[Mapping[str, LocalOverride]] = None,
    *,
    edge_cost_per_ml: Money = money("0.85"),
    finish_cost_per_m2_face: Money = money("4.50"),
    labor_hour_cost: Money = money("24.00"),
) -> List[CusteioItemV3]:
    variables = dimensions.variables()
    overrides = local_overrides or {}
    rows: List[CusteioItemV3] = []
    for template in module.lines:
        override = overrides.get(template.key)
        rule = rules.resolve(template.group)
        quantity = evaluate_formula(template.quantity_expr, variables) if template.quantity_expr else template.quantity
        if override and override.quantity is not None:
            quantity = override.quantity
        quantity = float(quantity or 0)

        comp = evaluate_formula(template.comp_expr, variables)
        larg = evaluate_formula(template.larg_expr, variables)
        esp = evaluate_formula(template.esp_expr, variables)
        unit_cost = override.unit_cost if override and override.unit_cost is not None else rule.unit_cost
        description = override.material_description if override and override.material_description else rule.description

        if template.kind == "peca":
            area_m2 = Decimal(str((comp or 0) * (larg or 0) / 1_000_000))
            perimeter_ml = Decimal(
                str(
                    (
                        (comp or 0) * template.edge_long_sides
                        + (larg or 0) * template.edge_short_sides
                    )
                    / 1000
                )
            )
            qty_dec = Decimal(str(quantity))
            finish_m2 = area_m2 * Decimal(template.finish_faces) * qty_dec
            cost_material = money(area_m2 * unit_cost * qty_dec)
            cost_edge = money(perimeter_ml * edge_cost_per_ml * qty_dec)
            cost_finish = money(finish_m2 * finish_cost_per_m2_face)
            usage_label = f"{area_m2 * qty_dec:.4f} m2"
            material_formula = (
                f"(({comp or 0:.0f} x {larg or 0:.0f}) / 1000000) x "
                f"{quantity:g} x {_money_text(unit_cost)} = {_money_text(cost_material)}"
            )
            edge_formula = (
                f"(({comp or 0:.0f} x {template.edge_long_sides}) + "
                f"({larg or 0:.0f} x {template.edge_short_sides})) / 1000 x "
                f"{quantity:g} x {_money_text(edge_cost_per_ml)} = {_money_text(cost_edge)}"
            )
            finish_formula = (
                f"{area_m2:.4f} x {template.finish_faces} faces x {quantity:g} x "
                f"{_money_text(finish_cost_per_m2_face)} = {_money_text(cost_finish)}"
            )
        else:
            cost_material = money(unit_cost * Decimal(str(quantity)))
            cost_edge = money(0)
            cost_finish = money(0)
            usage_label = f"{quantity:g} {rule.unit or 'UN'}"
            material_formula = f"{quantity:g} x {_money_text(unit_cost)} = {_money_text(cost_material)}"
            edge_formula = "Nao aplicavel"
            finish_formula = "Nao aplicavel"

        cost_labor = money(Decimal(str(template.labor_minutes)) / Decimal("60") * labor_hour_cost * Decimal(str(quantity)))
        cost_total = money(cost_material + cost_edge + cost_finish + cost_labor)
        labor_formula = (
            f"({template.labor_minutes:g} min / 60) x {_money_text(labor_hour_cost)} x "
            f"{quantity:g} = {_money_text(cost_labor)}"
        )
        total_formula = (
            f"{_money_text(cost_material)} + {_money_text(cost_edge)} + "
            f"{_money_text(cost_finish)} + {_money_text(cost_labor)} = {_money_text(cost_total)}"
        )
        rows.append(
            CusteioItemV3(
                structure_key=template.key,
                component_type=template.kind,
                description=template.description,
                formula_comp=template.comp_expr,
                formula_larg=template.larg_expr,
                formula_esp=template.esp_expr,
                resolved_comp=comp,
                resolved_larg=larg,
                resolved_esp=esp,
                quantity=quantity,
                rule_group=template.group,
                rule_source="Edição Local" if override else rule.source,
                material_ref=rule.ref,
                material_description=description,
                material_unit_cost=money(unit_cost),
                usage_label=usage_label,
                cost_material=cost_material,
                cost_edge=cost_edge,
                cost_finish=cost_finish,
                cost_labor=cost_labor,
                cost_total=cost_total,
                material_formula=material_formula,
                edge_formula=edge_formula,
                finish_formula=finish_formula,
                labor_formula=labor_formula,
                total_formula=total_formula,
                override_reason=override.reason if override else "",
            )
        )
    return rows


def _money_text(value: object) -> str:
    return f"{money(value)} EUR"


def validate_configuration(
    module: ModuleDefinition,
    dimensions: Dimensions,
    rules: RuleSet,
    rows: Sequence[CusteioItemV3],
) -> List[Tuple[str, str]]:
    messages: List[Tuple[str, str]] = []
    if dimensions.h <= 0 or dimensions.l <= 0 or dimensions.p <= 0:
        messages.append(("Erro", "As medidas H, L e P devem ser superiores a zero."))
    else:
        messages.append(("OK", "Medidas principais válidas."))

    missing_groups = sorted({row.rule_group for row in rows if row.rule_source == "Por definir"})
    if missing_groups:
        messages.append(("Aviso", "Regras por definir: " + ", ".join(missing_groups)))
    else:
        messages.append(("OK", "Materiais e ferragens resolvidos por Dados Gerais/Dados Items."))

    if any(row.override_reason for row in rows):
        messages.append(("Info", "Existem overrides locais no Custeio; rever motivos antes da proposta."))
    else:
        messages.append(("OK", "Sem overrides locais ativos."))

    if "correr" in module.name.lower() and not any("Calha" in row.description for row in rows):
        messages.append(("Erro", "Módulo de correr sem calhas geradas."))
    else:
        messages.append(("OK", "Estrutura técnica coerente para o módulo selecionado."))
    return messages


def build_proposal_summary(
    rows: Sequence[CusteioItemV3],
    *,
    admin_percent: Money = money("5"),
    margin_percent: Money = money("35"),
) -> ProposalSummary:
    cost_material = money(sum((row.cost_material for row in rows), Decimal("0")))
    cost_edge = money(sum((row.cost_edge for row in rows), Decimal("0")))
    cost_finish = money(sum((row.cost_finish for row in rows), Decimal("0")))
    cost_labor = money(sum((row.cost_labor for row in rows), Decimal("0")))
    cost_total = money(sum((row.cost_total for row in rows), Decimal("0")))
    admin_value = money(cost_total * admin_percent / Decimal("100"))
    margin_value = money((cost_total + admin_value) * margin_percent / Decimal("100"))
    sell_price = money(cost_total + admin_value + margin_value)
    return ProposalSummary(
        cost_material=cost_material,
        cost_edge=cost_edge,
        cost_finish=cost_finish,
        cost_labor=cost_labor,
        cost_total=cost_total,
        admin_value=admin_value,
        margin_value=margin_value,
        sell_price=sell_price,
        line_count=len(rows),
    )


def module_by_id(modules: Iterable[ModuleDefinition], module_id: str) -> ModuleDefinition:
    for module in modules:
        if module.module_id == module_id:
            return module
    raise KeyError(f"Modulo V3 nao encontrado: {module_id}")
