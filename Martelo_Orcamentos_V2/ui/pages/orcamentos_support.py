from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence


@dataclass
class ClienteComboItem:
    id: int
    nome: str
    is_temp: bool = False
    temp_id: Optional[int] = None


@dataclass
class OrcamentoTableState:
    rows: list
    estados: list[str]
    clientes: list[str]
    users: list[str]


@dataclass
class OrcamentoSelectionPlan:
    preferred_id: Optional[int]
    select_first: bool
    has_rows: bool


@dataclass
class OrcamentoAutoRefreshState:
    table_state: OrcamentoTableState
    current_row_count: int
    new_count: int


@dataclass
class OrcamentoFocusRequest:
    target_id: int
    open_items: bool = False


@dataclass
class OrcamentoPostSavePlan:
    refresh_select_first: bool
    select_id: Optional[int]
    prepare_new_form_year: Optional[str]
    leave_new_mode: bool


@dataclass
class ClienteChangePlan:
    normalized_text: str
    remember_text: Optional[str]
    should_open_temp_dialog: bool


def build_cliente_combo_items(
    *,
    clients: Sequence,
    temp_clients: Sequence,
    consumidor_final_label: str,
    consumidor_final_id: Optional[int],
) -> tuple[list[ClienteComboItem], set[str], Optional[int]]:
    effective_consumidor_id = consumidor_final_id
    if effective_consumidor_id is None:
        consumidor = next(
            (c for c in clients if (getattr(c, "nome", "") or "").strip().casefold() == consumidor_final_label.casefold()),
            None,
        )
        effective_consumidor_id = getattr(consumidor, "id", None)

    phc_names = {str(getattr(c, "nome", "") or "").strip().casefold() for c in clients if getattr(c, "nome", None)}
    items = [
        ClienteComboItem(id=getattr(c, "id", 0), nome=str(getattr(c, "nome", "") or "").strip(), is_temp=False, temp_id=None)
        for c in clients
        if str(getattr(c, "nome", "") or "").strip()
    ]
    for temp in temp_clients:
        temp_nome = str(getattr(temp, "nome", "") or "").strip()
        if not temp_nome or temp_nome.casefold() in phc_names:
            continue
        temp_nome_simplex = str(getattr(temp, "nome_simplex", None) or temp_nome).strip()
        if not temp_nome_simplex:
            continue
        items.append(
            ClienteComboItem(
                id=int(effective_consumidor_id or 0),
                nome=temp_nome_simplex,
                is_temp=True,
                temp_id=getattr(temp, "id", None),
            )
        )
    return items, phc_names, effective_consumidor_id


def find_cliente_item_by_name(items: Sequence[ClienteComboItem], name: str) -> Optional[ClienteComboItem]:
    if not name:
        return None
    name_cf = name.casefold()
    for item in items:
        if (item.nome or "").casefold() == name_cf:
            return item
    return None


def build_temp_cliente_item(*, temp, consumidor_final_id: Optional[int], fallback_name: str = "") -> Optional[ClienteComboItem]:
    if temp is None:
        return None
    nome = str(getattr(temp, "nome_simplex", None) or getattr(temp, "nome", None) or fallback_name or "").strip()
    if not nome:
        return None
    return ClienteComboItem(
        id=int(consumidor_final_id or 0),
        nome=nome,
        is_temp=True,
        temp_id=getattr(temp, "id", None),
    )


def resolve_selected_cliente_item(
    *,
    items: Sequence[ClienteComboItem],
    current_text: str,
    current_index: int,
    temp_item: Optional[ClienteComboItem] = None,
) -> Optional[ClienteComboItem]:
    text = (current_text or "").strip()
    if 0 <= current_index < len(items):
        item = items[current_index]
        if not text or (item.nome or "").casefold() == text.casefold():
            return item
    found = find_cliente_item_by_name(items, text)
    if found is not None:
        return found
    return temp_item


def build_cliente_info_data(record) -> dict:
    return {
        "nome": getattr(record, "nome", None),
        "nome_simplex": getattr(record, "nome_simplex", None),
        "num_cliente_phc": getattr(record, "num_cliente_phc", None),
        "telefone": getattr(record, "telefone", None),
        "telemovel": getattr(record, "telemovel", None),
        "email": getattr(record, "email", None),
        "web_page": getattr(record, "web_page", None),
        "morada": getattr(record, "morada", None),
        "info_1": getattr(record, "info_1", None),
        "info_2": getattr(record, "info_2", None),
        "notas": getattr(record, "notas", None),
    }


def filter_orcamento_rows(rows: Iterable, *, estado_filter: str, cliente_filter: str, user_filter: str) -> list:
    estado_f = (estado_filter or "").strip().lower()
    cliente_f = (cliente_filter or "").strip().lower()
    user_f = (user_filter or "").strip().lower()
    filtered = []
    for row in rows:
        if estado_f and estado_f != "todos" and estado_f not in str(getattr(row, "estado", None) or "").lower():
            continue
        if cliente_f and cliente_f != "todos" and cliente_f not in str(getattr(row, "cliente", None) or "").lower():
            continue
        if user_f and user_f != "todos" and user_f not in str(getattr(row, "utilizador", None) or "").lower():
            continue
        filtered.append(row)
    return filtered


def collect_orcamento_filter_values(rows: Iterable) -> tuple[list[str], list[str], list[str]]:
    estados = sorted({str(getattr(row, "estado", None) or "") for row in rows if getattr(row, "estado", None)})
    clientes = sorted({str(getattr(row, "cliente", None) or "") for row in rows if getattr(row, "cliente", None)})
    users = sorted({str(getattr(row, "utilizador", None) or "") for row in rows if getattr(row, "utilizador", None)})
    return estados, clientes, users


def build_orcamento_table_state(rows: Iterable, *, estado_filter: str, cliente_filter: str, user_filter: str) -> OrcamentoTableState:
    filtered_rows = filter_orcamento_rows(
        rows,
        estado_filter=estado_filter,
        cliente_filter=cliente_filter,
        user_filter=user_filter,
    )
    estados, clientes, users = collect_orcamento_filter_values(filtered_rows)
    return OrcamentoTableState(
        rows=filtered_rows,
        estados=estados,
        clientes=clientes,
        users=users,
    )


def plan_table_selection(rows: Sequence, *, preferred_id: Optional[int], select_first: bool) -> OrcamentoSelectionPlan:
    return OrcamentoSelectionPlan(
        preferred_id=preferred_id,
        select_first=bool(select_first),
        has_rows=bool(rows),
    )


def build_auto_refresh_state(
    rows: Sequence,
    *,
    last_row_count: int,
    estado_filter: str,
    cliente_filter: str,
    user_filter: str,
) -> OrcamentoAutoRefreshState:
    current_row_count = len(rows)
    return OrcamentoAutoRefreshState(
        table_state=build_orcamento_table_state(
            rows,
            estado_filter=estado_filter,
            cliente_filter=cliente_filter,
            user_filter=user_filter,
        ),
        current_row_count=current_row_count,
        new_count=max(0, current_row_count - int(last_row_count or 0)),
    )


def build_focus_request(oid: Optional[int], *, open_items: bool = False) -> Optional[OrcamentoFocusRequest]:
    if oid is None:
        return None
    return OrcamentoFocusRequest(target_id=int(oid), open_items=bool(open_items))


def build_post_save_plan(*, was_new: bool, saved_id: Optional[int], ano_text: str) -> OrcamentoPostSavePlan:
    if was_new:
        return OrcamentoPostSavePlan(
            refresh_select_first=False,
            select_id=saved_id,
            prepare_new_form_year=str(ano_text or "").strip() or None,
            leave_new_mode=True,
        )
    return OrcamentoPostSavePlan(
        refresh_select_first=True,
        select_id=saved_id,
        prepare_new_form_year=None,
        leave_new_mode=False,
    )


def build_cliente_change_plan(text: str, *, consumidor_final_label: str) -> ClienteChangePlan:
    normalized = str(text or "").strip()
    is_consumidor_final = bool(normalized) and normalized.casefold() == str(consumidor_final_label or "").casefold()
    remember_text = normalized if normalized and not is_consumidor_final else None
    return ClienteChangePlan(
        normalized_text=normalized,
        remember_text=remember_text,
        should_open_temp_dialog=is_consumidor_final,
    )
