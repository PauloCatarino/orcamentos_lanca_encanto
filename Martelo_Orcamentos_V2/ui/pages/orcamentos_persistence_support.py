from __future__ import annotations

from typing import Optional


def is_valid_year_text(year_text: str) -> bool:
    text = str(year_text or "").strip()
    return len(text) == 4 and text.isdigit()


def build_orcamento_identity(*, year_text: str, seq_text: str, version_text: str, format_version) -> tuple[str, str]:
    yy = str(year_text or "").strip()[-2:]
    seq = str(seq_text or "").strip().zfill(4)
    num_concat = f"{yy}{seq}"
    versao_txt = format_version(version_text)
    return num_concat, versao_txt


def determine_manual_price_flag(
    *,
    is_new: bool,
    preco_val,
    preco_manual_changed: bool,
    existing_manual_flag: bool,
) -> bool:
    if is_new:
        return preco_val is not None
    if preco_manual_changed:
        return True
    return bool(existing_manual_flag)


def merge_orcamento_extras(
    extras,
    *,
    manual_flag: bool,
    cliente_item,
    preco_manual_key: str,
    temp_client_id_key: str,
    temp_client_name_key: str,
) -> dict | None:
    data = dict(extras or {})
    if manual_flag:
        data[preco_manual_key] = True
    else:
        data.pop(preco_manual_key, None)

    if getattr(cliente_item, "is_temp", False):
        if getattr(cliente_item, "temp_id", None) is not None:
            data[temp_client_id_key] = cliente_item.temp_id
        else:
            data.pop(temp_client_id_key, None)
        data[temp_client_name_key] = cliente_item.nome
    else:
        data.pop(temp_client_id_key, None)
        data.pop(temp_client_name_key, None)

    return data or None


def find_row_index_by_id(rows, target_id: int) -> Optional[int]:
    for index, row in enumerate(rows or []):
        if getattr(row, "id", None) == target_id:
            return index
    return None


def build_duplicate_success_message(duplicated) -> str:
    return f"Criada versao {duplicated.versao} do orcamento {duplicated.num_orcamento}."
