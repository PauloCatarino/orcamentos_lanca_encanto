# Martelo_Orcamentos_V2/app/services/price_management.py
# =========================================================================
# Serviços para gerenciar preços (manual vs calculado)
# =========================================================================

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from Martelo_Orcamentos_V2.app.models import Orcamento


def set_price_calculated(
    db: Session,
    orcamento: Orcamento,
    preco: Decimal,
    commit: bool = True,
) -> None:
    """
    Define um preço como calculado (automático).
    Marca o timestamp e flag.
    """
    orcamento.preco_total = preco
    orcamento.preco_total_manual = 0  # False (calculado)
    orcamento.preco_atualizado_em = datetime.now()
    
    if commit:
        db.commit()


def set_price_manual(
    db: Session,
    orcamento: Orcamento,
    preco: Decimal,
    commit: bool = True,
) -> None:
    """
    Define um preço como editado manualmente.
    Marca o timestamp e flag.
    """
    orcamento.preco_total = preco
    orcamento.preco_total_manual = 1  # True (manual)
    orcamento.preco_atualizado_em = datetime.now()
    
    if commit:
        db.commit()


def revert_to_calculated(
    db: Session,
    orcamento: Orcamento,
    calculated_price: Optional[Decimal] = None,
    commit: bool = True,
) -> None:
    """
    Reverte um preço manual para calculado.
    Se calculated_price não for fornecido, mantém o preco_total atual.
    """
    if calculated_price is not None:
        orcamento.preco_total = calculated_price
    
    orcamento.preco_total_manual = 0  # False (calculado)
    orcamento.preco_atualizado_em = datetime.now()
    
    if commit:
        db.commit()


def is_price_manual(orcamento: Orcamento) -> bool:
    """Verifica se um preço foi editado manualmente."""
    return bool(orcamento.preco_total_manual)


def get_price_status(orcamento: Orcamento) -> str:
    """Retorna status legível do preço: 'Manual' ou 'Calculado'."""
    return "Manual" if is_price_manual(orcamento) else "Calculado"


def get_price_tooltip(orcamento: Orcamento) -> str:
    """Retorna tooltip informativo sobre o preço."""
    status = get_price_status(orcamento)
    
    if orcamento.preco_atualizado_em:
        try:
            data_fmt = orcamento.preco_atualizado_em.strftime("%d-%m-%Y %H:%M")
        except Exception:
            data_fmt = str(orcamento.preco_atualizado_em)
        return f"Preço: {status} (atualizado em {data_fmt})"
    
    return f"Preço: {status}"
