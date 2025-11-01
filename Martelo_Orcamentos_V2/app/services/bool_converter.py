from typing import Any

def bool_to_int(value: Any) -> int:
    """Converte um valor booleano para inteiro (0 ou 1)."""
    if value in {True, "True", "1", 1, "true", "yes", "sim"}:
        return 1
    return 0

def int_to_bool(value: Any) -> bool:
    """Converte um valor inteiro (0 ou 1) para booleano."""
    if value in {1, "1", True, "True", "true", "yes", "sim"}:
        return True
    return False