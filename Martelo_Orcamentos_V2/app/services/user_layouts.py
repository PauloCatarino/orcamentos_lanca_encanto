from __future__ import annotations

import json
from typing import Dict, Mapping, Optional

from sqlalchemy.orm import Session

from .settings import get_setting, set_setting


def _make_key(namespace: str, user_id: int) -> str:
    return f"table_layout:{namespace}:{user_id}"


def load_table_layout(
    db: Session,
    user_id: Optional[int],
    namespace: str,
) -> Dict[str, Dict[str, int]]:
    """
    Lê as larguras de colunas guardadas para um determinado utilizador
    e namespace (ex.: 'dados_gerais', 'dados_items').
    """
    if not user_id:
        return {}

    raw = get_setting(db, _make_key(namespace, user_id), "{}") or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    layout: Dict[str, Dict[str, int]] = {}
    if not isinstance(data, dict):
        return layout

    for menu, widths in data.items():
        if isinstance(widths, Mapping):
            normalized: Dict[str, int] = {}
            for field, width in widths.items():
                try:
                    normalized[str(field)] = max(20, int(width))
                except (TypeError, ValueError):
                    continue
            if normalized:
                layout[str(menu)] = normalized
    return layout


def save_table_layout(
    db: Session,
    user_id: Optional[int],
    namespace: str,
    layout: Mapping[str, Mapping[str, int]],
) -> None:
    """
    Guarda as larguras de colunas por utilizador/menu.
    Armazena apenas valores válidos (>= 20 px) para evitar corrupções.
    """
    if not user_id:
        return

    payload: Dict[str, Dict[str, int]] = {}
    for menu, widths in layout.items():
        if not isinstance(widths, Mapping):
            continue
        normalized: Dict[str, int] = {}
        for field, width in widths.items():
            try:
                normalized[str(field)] = max(20, int(width))
            except (TypeError, ValueError):
                continue
        if normalized:
            payload[str(menu)] = normalized

    set_setting(db, _make_key(namespace, user_id), json.dumps(payload))
