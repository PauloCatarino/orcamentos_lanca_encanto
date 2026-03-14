from __future__ import annotations

from datetime import date, datetime
from typing import Optional


DATE_INPUT_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d.%m.%Y",
    "%Y/%m/%d",
)


def parse_date_value(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    raw = str(value).strip()
    if not raw:
        return None

    for fmt in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def format_date_storage(value) -> str:
    parsed = parse_date_value(value)
    return parsed.isoformat() if parsed is not None else ""


def format_date_display(value) -> str:
    parsed = parse_date_value(value)
    return parsed.strftime("%d-%m-%Y") if parsed is not None else ""


def today_storage() -> str:
    return date.today().isoformat()
