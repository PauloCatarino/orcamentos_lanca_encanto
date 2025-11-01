"""
Este módulo contém funções para converter entre booleanos e inteiros (0/1).
Foi criado para resolver o problema de persistência do campo nao_stock no banco de dados.
"""

from typing import Any
from decimal import Decimal

def strip_accents(s: str) -> str:
    """Remove acentos de uma string."""
    from unicodedata import normalize
    return normalize('NFKD', s).encode('ASCII', 'ignore').decode('ASCII')

def coerce_to_int(value: Any) -> int:
    """
    Converte qualquer valor para 0 ou 1.
    Esta função é usada principalmente para o campo nao_stock.
    """
    if value in (None, ""):
        return 0
        
    if isinstance(value, bool):
        return 1 if value else 0
        
    if isinstance(value, str):
        normalized = strip_accents(value).strip().lower()
        if normalized in ("true", "sim", "yes", "1"):
            return 1
        if normalized in ("false", "nao", "no", "0"):
            return 0
            
    if isinstance(value, (int, float, Decimal)):
        try:
            return 1 if bool(Decimal(str(value))) else 0
        except Exception:
            return 0
            
    return 1 if bool(value) else 0

def coerce_to_bool(value: Any) -> bool:
    """
    Converte qualquer valor para True ou False.
    Esta função é usada para interface com campos booleanos no SQLAlchemy.
    """
    if value in (None, ""):
        return False
        
    if isinstance(value, bool):
        return value
        
    if isinstance(value, str):
        normalized = strip_accents(value).strip().lower()
        if normalized in ("true", "sim", "yes", "1"):
            return True
        if normalized in ("false", "nao", "no", "0"):
            return False
            
    if isinstance(value, (int, float, Decimal)):
        try:
            return bool(Decimal(str(value)))
        except Exception:
            return False
            
    return bool(value)