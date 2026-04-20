from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Callable, Optional

from Martelo_Orcamentos_V2.app.utils.date_utils import parse_date_value


@dataclass
class OrcamentoFormValues:
    ano_text: str
    seq_text: str
    versao_text: str
    parsed_date: object
    status_text: str
    enc_phc: str
    ref_cliente: str
    obra: str
    preco_text: str
    descricao: str
    localizacao: str
    info_1: str
    info_2: str
    temp_nome: str


@dataclass
class LoadedOrcamentoSelectionState:
    current_id: int
    manual_flag: bool
    selected_client_name: str
    selected_user_id: Optional[int]
    folder_path: Optional[str]
    form_values: OrcamentoFormValues


@dataclass
class NewOrcamentoFormState:
    ano_text: str
    seq_text: str
    versao_text: str
    status_text: str


def _coerce_extras_dict(extras) -> dict:
    if not extras:
        return {}
    if isinstance(extras, dict):
        return dict(extras)
    if isinstance(extras, str):
        try:
            parsed = json.loads(extras)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def extract_temp_name_from_extras(extras, *, temp_client_name_key: str) -> str:
    data = _coerce_extras_dict(extras)
    return str(data.get(temp_client_name_key) or "").strip()


def normalize_simplex(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "CLIENTE"
    return text.upper().replace(" ", "_")


def extract_temp_simplex_from_extras(
    extras,
    *,
    temp_client_id_key: str,
    temp_client_name_key: str,
    consumidor_final_label: str,
    temp_loader: Callable[[int], object | None],
) -> Optional[str]:
    data = _coerce_extras_dict(extras)
    temp_id = data.get(temp_client_id_key)
    temp_nome = str(data.get(temp_client_name_key) or "").strip()
    if temp_id not in (None, ""):
        try:
            temp = temp_loader(int(temp_id))
        except Exception:
            temp = None
        if temp:
            temp_simplex = (
                str(getattr(temp, "nome_simplex", None) or getattr(temp, "nome", None) or "").strip()
            )
            if temp_simplex:
                return temp_simplex
    if temp_nome and temp_nome.casefold() != consumidor_final_label.casefold():
        return temp_nome
    return None


def resolve_orcamento_simplex(*, client, temp_simplex: Optional[str]) -> str:
    if temp_simplex:
        return normalize_simplex(temp_simplex)
    base = getattr(client, "nome_simplex", None) or getattr(client, "nome", None) or "CLIENTE"
    return normalize_simplex(str(base))


def build_existing_orcamento_folder_path(
    *,
    base_path: str,
    ano,
    num_orc,
    simplex: str,
    versao,
    format_version: Callable[[object], str],
) -> Optional[str]:
    if not (base_path and ano and num_orc):
        return None

    yy_path = os.path.join(str(base_path), str(ano))
    if not os.path.isdir(yy_path):
        return None

    expected_name = f"{num_orc}_{simplex}"
    expected_dir = os.path.join(yy_path, expected_name)
    ver_dir = format_version(versao)
    alt_ver = str(versao or "").strip()

    if os.path.isdir(expected_dir):
        dir_ver = os.path.join(expected_dir, ver_dir)
        alt_dir_ver = os.path.join(expected_dir, alt_ver) if alt_ver else ""
        if os.path.isdir(dir_ver):
            return dir_ver
        if alt_dir_ver and os.path.isdir(alt_dir_ver):
            return alt_dir_ver
        return expected_dir

    prefix = f"{num_orc}_"
    fallback_base = None
    try:
        with os.scandir(yy_path) as entries:
            for entry in entries:
                if not (entry.is_dir() and entry.name.startswith(prefix)):
                    continue
                base_dir = entry.path
                dir_ver = os.path.join(base_dir, ver_dir)
                alt_dir_ver = os.path.join(base_dir, alt_ver) if alt_ver else ""
                if os.path.isdir(dir_ver):
                    return dir_ver
                if alt_dir_ver and os.path.isdir(alt_dir_ver):
                    return alt_dir_ver
                fallback_base = fallback_base or base_dir
    except Exception:
        return None

    if fallback_base and os.path.isdir(fallback_base):
        return fallback_base
    return None


def build_orcamento_version_dir(
    *,
    base_path: str,
    ano,
    num_orc,
    simplex: str,
    versao,
    format_version: Callable[[object], str],
) -> str:
    yy_path = os.path.join(str(base_path), str(ano))
    pasta = f"{num_orc}_{simplex}"
    ver_dir = format_version(versao)
    return os.path.join(yy_path, pasta, ver_dir)


def list_candidate_orcamento_dirs(*, yy_path: str, num_orc, expected_dir: str) -> list[str]:
    candidates: list[str] = []
    if os.path.isdir(expected_dir):
        candidates.append(expected_dir)
        return candidates
    prefix = f"{num_orc}_"
    try:
        with os.scandir(yy_path) as entries:
            for entry in entries:
                if entry.is_dir() and entry.name.startswith(prefix):
                    candidates.append(entry.path)
    except Exception:
        return candidates
    return candidates


def build_orcamento_form_values(
    o,
    *,
    temp_nome: str,
    format_version: Callable[[object], str],
    format_currency: Callable[[object], str],
) -> OrcamentoFormValues:
    seq = str(getattr(o, "num_orcamento", None) or "")
    parsed_date = parse_date_value(getattr(o, "data", None))
    preco_total = getattr(o, "preco_total", None)
    return OrcamentoFormValues(
        ano_text=str(getattr(o, "ano", None) or ""),
        seq_text=seq[2:6] if len(seq) >= 6 else seq,
        versao_text=format_version(getattr(o, "versao", None) or "01"),
        parsed_date=parsed_date,
        status_text=str(getattr(o, "status", None) or "Falta Orcamentar"),
        enc_phc=str(getattr(o, "enc_phc", None) or ""),
        ref_cliente=str(getattr(o, "ref_cliente", None) or ""),
        obra=str(getattr(o, "obra", None) or ""),
        preco_text="" if preco_total is None else format_currency(preco_total),
        descricao=str(getattr(o, "descricao_orcamento", None) or ""),
        localizacao=str(getattr(o, "localizacao", None) or ""),
        info_1=str(getattr(o, "info_1", None) or ""),
        info_2=str(getattr(o, "info_2", None) or ""),
        temp_nome=temp_nome,
    )


def build_loaded_orcamento_selection_state(
    o,
    *,
    client,
    available_client_names: set[str],
    temp_client_name_key: str,
    format_version: Callable[[object], str],
    format_currency: Callable[[object], str],
    manual_flag_extractor: Callable[[object], bool],
    folder_path_builder: Callable[[object, object | None], Optional[str]],
) -> LoadedOrcamentoSelectionState:
    temp_nome = extract_temp_name_from_extras(
        getattr(o, "extras", None),
        temp_client_name_key=temp_client_name_key,
    )
    manual_flag_raw = getattr(o, "preco_total_manual", None)
    if manual_flag_raw in (None, ""):
        manual_flag = bool(manual_flag_extractor(getattr(o, "extras", None)))
    else:
        manual_flag = bool(manual_flag_raw)
    client_name = str(getattr(client, "nome", None) or "").strip()
    selected_client_name = temp_nome or (client_name if client_name in available_client_names else "")
    return LoadedOrcamentoSelectionState(
        current_id=int(getattr(o, "id")),
        manual_flag=manual_flag,
        selected_client_name=selected_client_name,
        selected_user_id=int(getattr(o, "created_by")) if getattr(o, "created_by", None) not in (None, "") else None,
        folder_path=folder_path_builder(o, client),
        form_values=build_orcamento_form_values(
            o,
            temp_nome=temp_nome,
            format_version=format_version,
            format_currency=format_currency,
        ),
    )


def prepare_loaded_orcamento_selection(
    row,
    *,
    orcamento_loader: Callable[[int], tuple[object | None, object | None]],
    available_client_names: set[str],
    temp_client_name_key: str,
    format_version: Callable[[object], str],
    format_currency: Callable[[object], str],
    manual_flag_extractor: Callable[[object], bool],
    folder_path_builder: Callable[[object, object | None], Optional[str]],
) -> Optional[LoadedOrcamentoSelectionState]:
    row_id = getattr(row, "id", None) if row is not None else None
    if not row_id:
        return None
    orcamento, client = orcamento_loader(int(row_id))
    if not orcamento:
        return None
    return build_loaded_orcamento_selection_state(
        orcamento,
        client=client,
        available_client_names=available_client_names,
        temp_client_name_key=temp_client_name_key,
        format_version=format_version,
        format_currency=format_currency,
        manual_flag_extractor=manual_flag_extractor,
        folder_path_builder=folder_path_builder,
    )


def build_new_orcamento_form_state(
    *,
    ano_text: str,
    seq_text: str,
    default_version: str = "01",
    default_status: str = "Falta Orcamentar",
) -> NewOrcamentoFormState:
    return NewOrcamentoFormState(
        ano_text=str(ano_text or "").strip(),
        seq_text=str(seq_text or "").strip(),
        versao_text=str(default_version or "01").strip() or "01",
        status_text=str(default_status or "Falta Orcamentar").strip() or "Falta Orcamentar",
    )
