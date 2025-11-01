from typing import Any

def coerce_bool_to_int(value: Any) -> int:
    """
    Converte um valor booleano para 0 ou 1.
    Esta função é usada principalmente para o campo nao_stock.
    
    Args:
        value: Qualquer valor que possa ser convertido para booleano
        
    Returns:
        1 se o valor for verdadeiro, 0 caso contrário
    """
    if value in (None, "", 0, "0", False, "False", "false", "nao", "no"):
        return 0
    return 1

def coerce_int_to_bool(value: Any) -> bool:
    """
    Converte um valor inteiro (0 ou 1) para booleano.
    Esta função é usada para converter valores do banco de dados para a interface.
    
    Args:
        value: Um valor inteiro (0 ou 1)
        
    Returns:
        True se o valor for 1, False caso contrário
    """
    if value in (1, "1", True, "True", "true", "yes", "sim"):
        return True
    return False