"""
Este módulo contém funções para converter entre valores booleanos e inteiros (0/1)
para o campo nao_stock na tabela de materiais.
"""
from typing import Any

def bool_to_int(value: Any) -> int:
    """
    Converte qualquer valor para inteiro (0 ou 1).
    Esta função é usada principalmente para o campo nao_stock.
    
    Args:
        value: Qualquer valor que possa ser convertido para inteiro
        
    Returns:
        1 se o valor for verdadeiro, 0 caso contrário
    """
    if value is None:
        return 0
        
    if isinstance(value, bool):
        return 1 if value else 0
        
    if isinstance(value, str):
        value = value.strip().lower()
        if value in {"1", "true", "sim", "yes", "verdadeiro"}:
            return 1
        if value in {"0", "false", "nao", "no", "falso"}:
            return 0
            
    if isinstance(value, (int, float)):
        return 1 if value != 0 else 0
        
    return 0

def int_to_bool(value: Any) -> bool:
    """
    Converte um valor inteiro (0 ou 1) para booleano.
    Esta função é usada para converter valores do banco de dados para a interface.
    
    Args:
        value: Um valor inteiro (0 ou 1)
        
    Returns:
        True se o valor for 1, False caso contrário
    """
    if value is None:
        return False
        
    if isinstance(value, bool):
        return value
        
    if isinstance(value, str):
        value = value.strip().lower()
        if value in {"1", "true", "sim", "yes", "verdadeiro"}:
            return True
        if value in {"0", "false", "nao", "no", "falso"}:
            return False
            
    if isinstance(value, (int, float)):
        return value != 0
        
    return False