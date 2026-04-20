# Martelo_Orcamentos_V2/app/services/price_management.py
# =========================================================================
# Servicos para gerenciar precos (manual vs calculado)
# =========================================================================

import json
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models import Orcamento

LEGACY_PRICE_MANUAL_KEY = "preco_manual"


def _coerce_extras_dict(extras_raw) -> dict:
    if isinstance(extras_raw, dict):
        return dict(extras_raw)
    if extras_raw in (None, ""):
        return {}
    if isinstance(extras_raw, str):
        try:
            parsed = json.loads(extras_raw)
        except Exception:
            return {}
        if isinstance(parsed, dict):
            return dict(parsed)
    return {}


def sync_price_metadata(
    orcamento: Orcamento,
    *,
    manual: bool,
    touch_timestamp: bool = False,
) -> None:
    """Mantem alinhado o estado do preco entre a coluna nova e o extras legacy."""
    orcamento.preco_total_manual = 1 if manual else 0
    if touch_timestamp:
        orcamento.preco_atualizado_em = datetime.now()

    extras = _coerce_extras_dict(getattr(orcamento, "extras", None))
    if manual:
        extras[LEGACY_PRICE_MANUAL_KEY] = True
    else:
        extras.pop(LEGACY_PRICE_MANUAL_KEY, None)
    orcamento.extras = extras or None


def _set_price_state(
    orcamento: Orcamento,
    *,
    preco: Optional[Decimal],
    manual: bool,
) -> None:
    if preco is not None:
        orcamento.preco_total = preco
    sync_price_metadata(orcamento, manual=manual, touch_timestamp=True)


def set_price_calculated(
    db: Session,
    orcamento: Orcamento,
    preco: Decimal,
    commit: bool = True,
) -> None:
    """
    Define um preco como calculado (automatico).
    Marca o timestamp e a origem do preco.
    """
    _set_price_state(orcamento, preco=preco, manual=False)

    if commit:
        db.commit()


def set_price_manual(
    db: Session,
    orcamento: Orcamento,
    preco: Decimal,
    commit: bool = True,
) -> None:
    """
    Define um preco como editado manualmente.
    Marca o timestamp e a origem do preco.
    """
    _set_price_state(orcamento, preco=preco, manual=True)

    if commit:
        db.commit()


def revert_to_calculated(
    db: Session,
    orcamento: Orcamento,
    calculated_price: Optional[Decimal] = None,
    commit: bool = True,
) -> None:
    """
    Reverte um preco manual para calculado.
    Se calculated_price nao for fornecido, mantem o preco_total atual.
    """
    _set_price_state(orcamento, preco=calculated_price, manual=False)

    if commit:
        db.commit()


def is_price_manual(orcamento: Orcamento) -> bool:
    """Verifica se um preco foi editado manualmente."""
    manual_flag = getattr(orcamento, "preco_total_manual", None)
    if manual_flag not in (None, ""):
        return bool(manual_flag)
    extras = _coerce_extras_dict(getattr(orcamento, "extras", None))
    return bool(extras.get(LEGACY_PRICE_MANUAL_KEY))


def get_price_status(orcamento: Orcamento) -> str:
    """Retorna status legivel do preco: 'Manual' ou 'Calculado'."""
    return "Manual" if is_price_manual(orcamento) else "Calculado"


def get_price_tooltip(orcamento: Orcamento) -> str:
    """Retorna tooltip informativo sobre o preco."""
    status = get_price_status(orcamento)

    if orcamento.preco_atualizado_em:
        try:
            data_fmt = orcamento.preco_atualizado_em.strftime("%d-%m-%Y %H:%M")
        except Exception:
            data_fmt = str(orcamento.preco_atualizado_em)
        return f"Preco: {status} (atualizado em {data_fmt})"

    return f"Preco: {status}"
