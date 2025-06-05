# utils.py

# ... (seu código existente) ...

def formatar_valor_percentual(value):
    """
    Formata um valor decimal (ex: 0.15) para uma string de percentagem (ex: "15.00%").
    Retorna "0.00%" se o valor for None ou não for um número.
    """
    if value is None:
        return "0.00%"
    try:
        # Modificado: Formata para duas casas decimais (:.2f)
        return f"{value * 100:.2f}%"
    except (ValueError, TypeError):
        return "0.00%"

# ... (restante do seu código) ...