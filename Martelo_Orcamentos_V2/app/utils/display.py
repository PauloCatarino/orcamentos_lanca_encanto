from __future__ import annotations

EURO_SIGN = "\u20ac"

_MOJIBAKE_HINTS = ("Ã", "Â", "â‚¬", "â€", "â€“", "â€”", "â€œ", "â€\x9d")


def repair_mojibake(value) -> str:
    text = "" if value is None else str(value)
    if not text or not any(hint in text for hint in _MOJIBAKE_HINTS):
        return text
    try:
        repaired = text.encode("latin-1").decode("utf-8")
        if repaired:
            return repaired
    except Exception:
        pass
    replacements = {
        "â‚¬": EURO_SIGN,
        "NÂº": "Nº",
        "Âº": "º",
        "Âª": "ª",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def format_currency_pt(value) -> str:
    if value in (None, ""):
        return ""
    try:
        num = float(value)
    except Exception:
        return repair_mojibake(value)
    txt = f"{num:,.2f}"
    txt = txt.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{txt} {EURO_SIGN}"


def parse_currency_pt(text) -> float | None:
    if text is None:
        return None
    raw = repair_mojibake(text).strip()
    if not raw:
        return None
    cleaned = raw.replace(EURO_SIGN, "").replace(" ", "")
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "")
        cleaned = cleaned.replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except Exception:
        return None
