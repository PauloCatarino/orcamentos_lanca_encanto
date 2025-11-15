from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, Mapping, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento, OrcamentoItem
from .settings import get_setting, set_setting


MARGEM_FIELDS: Iterable[Mapping[str, object]] = (
    {"key": "margem_lucro_perc", "label": "Margem Lucro (%)", "default": Decimal("3.00")},
    {"key": "custos_admin_perc", "label": "Custos Administrativos (%)", "default": Decimal("3.00")},
    {"key": "margem_acabamentos_perc", "label": "Margem Acabamentos (%)", "default": Decimal("5.00")},
    {"key": "margem_mp_orlas_perc", "label": "Margem Materias Primas & Orlas (%)", "default": Decimal("15.00")},
    {"key": "margem_mao_obra_perc", "label": "Margem Mão de Obra (%)", "default": Decimal("5.00")},
)

CONFIG_KEY = "margens_config"
OBJ_KEY = "objetivo_preco_final"
SUM_KEY = "soma_preco_final"
TWO_PLACES = Decimal("0.01")
PERCENT_KEYS = (
    "margem_lucro_perc",
    "custos_admin_perc",
    "margem_acabamentos_perc",
    "margem_mp_orlas_perc",
    "margem_mao_obra_perc",
)


def _coerce_decimal(value: object, default: Decimal) -> Decimal:
    if value is None or value == "":
        return default
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def load_margens(session: Session) -> Dict[str, Decimal]:
    valores: Dict[str, Decimal] = {}
    for field in MARGEM_FIELDS:
        key = str(field["key"])
        default = field["default"]
        default_dec = default if isinstance(default, Decimal) else Decimal(str(default))
        raw = get_setting(session, key, None)
        valores[key] = _coerce_decimal(raw, default_dec)
    return valores


def save_margens(session: Session, valores: Mapping[str, object]) -> Dict[str, Decimal]:
    stored: Dict[str, Decimal] = {}
    for field in MARGEM_FIELDS:
        key = str(field["key"])
        default = field["default"]
        default_dec = default if isinstance(default, Decimal) else Decimal(str(default))
        valor = _coerce_decimal(valores.get(key), default_dec)
        set_setting(session, key, f"{valor:.4f}")
        stored[key] = valor
    session.flush()
    return stored


def default_values() -> Dict[str, Decimal]:
    return {
        str(field["key"]): field["default"]
        if isinstance(field["default"], Decimal)
        else Decimal(str(field["default"]))
        for field in MARGEM_FIELDS
    }


def load_orcamento_config(session: Session, orcamento_id: Optional[int]) -> Dict[str, Decimal]:
    percent = load_margens(session)
    objetivo = Decimal("0.00")
    soma = Decimal("0.00")
    if not orcamento_id:
        return {"percent": percent, "objetivo": objetivo, "soma": soma}

    orc = session.get(Orcamento, orcamento_id)
    if orc is None:
        return {"percent": percent, "objetivo": objetivo, "soma": soma}
    extras = dict(getattr(orc, "extras", {}) or {})
    cfg = extras.get(CONFIG_KEY) or {}
    cfg_percent = cfg.get("percent") or {}

    for key, default in percent.items():
        raw = cfg_percent.get(key)
        percent[key] = _coerce_decimal(raw, default)

    objetivo = _coerce_decimal(cfg.get(OBJ_KEY), Decimal("0.00"))
    soma = _coerce_decimal(cfg.get(SUM_KEY), Decimal("0.00"))

    return {"percent": percent, "objetivo": objetivo, "soma": soma}


def save_orcamento_config(
    session: Session,
    orcamento_id: int,
    percent_values: Mapping[str, object],
    objetivo: Optional[Decimal],
    *,
    soma: Optional[Decimal] = None,
) -> None:
    orc = session.get(Orcamento, orcamento_id)
    if orc is None:
        return
    extras = dict(getattr(orc, "extras", {}) or {})

    defaults = load_margens(session)
    percent_payload: Dict[str, float] = {}
    for key, default in defaults.items():
        valor = _coerce_decimal(percent_values.get(key), default)
        percent_payload[key] = float(valor)

    cfg = {
        "percent": percent_payload,
        OBJ_KEY: float(_coerce_decimal(objetivo, Decimal("0.00"))),
    }
    if soma is not None:
        cfg[SUM_KEY] = float(_coerce_decimal(soma, Decimal("0.00")))
    extras[CONFIG_KEY] = cfg
    orc.extras = extras
    session.add(orc)
    session.flush()


def update_sum_preco_final(session: Session, orcamento_id: int, total: Decimal) -> None:
    orc = session.get(Orcamento, orcamento_id)
    if orc is None:
        return
    extras = dict(getattr(orc, "extras", {}) or {})
    cfg = extras.get(CONFIG_KEY) or {}
    cfg[SUM_KEY] = float(total)
    extras[CONFIG_KEY] = cfg
    orc.extras = extras
    orc.preco_total = total
    session.add(orc)
    session.flush()


def aplicar_margens_orcamento(session: Session, orcamento_id: int, percent_values: Mapping[str, object]) -> Decimal:
    percent_map: Dict[str, Decimal] = {}
    defaults = load_margens(session)
    for key, default in defaults.items():
        percent_map[key] = _coerce_decimal(percent_values.get(key), default)

    stmt = select(OrcamentoItem).where(OrcamentoItem.id_orcamento == orcamento_id)
    itens = session.execute(stmt).scalars().all()
    total = Decimal("0.00")

    for item in itens:
        custo = _coerce_decimal(getattr(item, "custo_produzido", None), Decimal("0.00"))
        qt = _coerce_decimal(getattr(item, "qt", None), Decimal("0.00"))

        perc_lucro = percent_map["margem_lucro_perc"]
        perc_admin = percent_map["custos_admin_perc"]
        perc_acab = percent_map["margem_acabamentos_perc"]
        perc_mp = percent_map["margem_mp_orlas_perc"]
        perc_mo = percent_map["margem_mao_obra_perc"]

        valor_margem = (custo * perc_lucro / Decimal("100")).quantize(TWO_PLACES)
        valor_admin = (custo * perc_admin / Decimal("100")).quantize(TWO_PLACES)
        valor_acab = (custo * perc_acab / Decimal("100")).quantize(TWO_PLACES)
        valor_mp = (custo * perc_mp / Decimal("100")).quantize(TWO_PLACES)
        valor_mo = (custo * perc_mo / Decimal("100")).quantize(TWO_PLACES)

        ajuste = _coerce_decimal(getattr(item, "ajuste", None), Decimal("0.00"))
        preco_unitario = (
            custo + valor_margem + valor_admin + valor_acab + valor_mp + valor_mo + ajuste
        ).quantize(TWO_PLACES)
        preco_total = (preco_unitario * qt).quantize(TWO_PLACES)

        item.margem_lucro_perc = perc_lucro
        item.valor_margem = valor_margem
        item.custos_admin_perc = perc_admin
        item.valor_custos_admin = valor_admin
        item.margem_acabamentos_perc = perc_acab
        item.valor_acabamentos = valor_acab
        item.margem_mp_orlas_perc = perc_mp
        item.valor_mp_orlas = valor_mp
        item.margem_mao_obra_perc = perc_mo
        item.valor_mao_obra = valor_mo
        item.preco_unitario = preco_unitario
        item.preco_total = preco_total

        total += preco_total

    session.flush()
    return total.quantize(TWO_PLACES)


def _sum_base_costs(session: Session, orcamento_id: int) -> Tuple[Decimal, Decimal]:
    stmt = select(OrcamentoItem.custo_produzido, OrcamentoItem.qt, OrcamentoItem.ajuste).where(
        OrcamentoItem.id_orcamento == orcamento_id
    )
    base_custo = Decimal("0.00")
    total_ajuste = Decimal("0.00")
    for custo, qt, ajuste in session.execute(stmt).all():
        custo_dec = _coerce_decimal(custo, Decimal("0.00"))
        qt_dec = _coerce_decimal(qt, Decimal("0.00"))
        ajuste_dec = _coerce_decimal(ajuste, Decimal("0.00"))
        base_custo += (custo_dec * qt_dec)
        total_ajuste += (ajuste_dec * qt_dec)
    return base_custo, total_ajuste


def _estimate_total(base_custo: Decimal, total_ajuste: Decimal, percent_map: Mapping[str, Decimal]) -> Decimal:
    percent_sum = Decimal("0.00")
    for key in PERCENT_KEYS:
        percent_sum += _coerce_decimal(percent_map.get(key), Decimal("0.00"))
    total = base_custo + total_ajuste + (base_custo * percent_sum / Decimal("100"))
    return total.quantize(TWO_PLACES)


def ajustar_percentuais_para_objetivo(
    session: Session,
    orcamento_id: int,
    percent_values: Mapping[str, object],
    objetivo: Decimal,
    *,
    ordem: Optional[Iterable[str]] = None,
    minimo: Decimal = Decimal("0.10"),
    tolerancia: Decimal = Decimal("0.50"),
) -> Tuple[Dict[str, Decimal], Decimal, bool]:
    if not orcamento_id:
        raise ValueError("Selecione um orçamento para ajustar as margens.")

    objetivo_dec = _coerce_decimal(objetivo, Decimal("0.00"))
    if objetivo_dec <= Decimal("0.00"):
        raise ValueError("Defina um valor positivo para 'Atingir Objetivo Preço Final (€)'.")

    base_custo, total_ajuste = _sum_base_costs(session, orcamento_id)
    if base_custo <= Decimal("0.00"):
        raise ValueError("Não existem custos produzidos para este orçamento.")

    defaults = load_margens(session)
    percent_map: Dict[str, Decimal] = {}
    for key, default in defaults.items():
        percent_map[key] = _coerce_decimal(percent_values.get(key), default)

    ordem_exec = tuple(ordem) if ordem else ("margem_lucro_perc", "custos_admin_perc", "margem_mp_orlas_perc", "margem_mao_obra_perc")
    minimo_dec = minimo if isinstance(minimo, Decimal) else Decimal(str(minimo))
    tol_dec = tolerancia.copy_abs() if isinstance(tolerancia, Decimal) else Decimal(str(tolerancia)).copy_abs()
    if tol_dec == Decimal("0.00"):
        tol_dec = Decimal("0.50")
    if minimo_dec <= Decimal("0.00"):
        minimo_dec = Decimal("0.10")

    def _current_total() -> Decimal:
        return _estimate_total(base_custo, total_ajuste, percent_map)

    for key in ordem_exec:
        if key not in percent_map:
            continue
        diff = objetivo_dec - _current_total()
        if diff.copy_abs() <= tol_dec:
            break
        delta_percent = (diff / base_custo) * Decimal("100")
        if delta_percent == Decimal("0.00"):
            continue
        novo_valor = percent_map[key] + delta_percent
        if novo_valor < minimo_dec:
            novo_valor = minimo_dec
        if novo_valor > Decimal("500.00"):
            novo_valor = Decimal("500.00")
        percent_map[key] = novo_valor.quantize(TWO_PLACES)

    total_calculado = _current_total()
    atingiu = (objetivo_dec - total_calculado).copy_abs() <= tol_dec
    return percent_map, total_calculado, atingiu


def somar_preco_total(session: Session, orcamento_id: int) -> Decimal:
    if not orcamento_id:
        return Decimal("0.00")
    total = (
        session.execute(
            select(func.coalesce(func.sum(OrcamentoItem.preco_total), 0)).where(OrcamentoItem.id_orcamento == orcamento_id)
        ).scalar()
        or Decimal("0")
    )
    return _coerce_decimal(total, Decimal("0.00")).quantize(TWO_PLACES)
