from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.services.clients import list_clients
from Martelo_Orcamentos_V2.app.services.clientes_temporarios import (
    get_cliente_temporario,
    get_cliente_temporario_por_nome,
    list_clientes_temporarios,
)
from Martelo_Orcamentos_V2.app.services import orcamentos_workflow
from Martelo_Orcamentos_V2.ui.pages.orcamentos_support import (
    ClienteComboItem,
    build_cliente_combo_items,
    build_cliente_info_data,
    build_temp_cliente_item,
    resolve_selected_cliente_item,
)


@dataclass(frozen=True)
class ClienteComboState:
    items: list[ClienteComboItem]
    phc_names: set[str]
    consumidor_final_id: Optional[int]
    names: list[str]


@dataclass(frozen=True)
class ClienteInfoState:
    origem: str
    data: dict


def load_cliente_combo_state(
    db: Session,
    *,
    consumidor_final_label: str,
    consumidor_final_id: Optional[int],
) -> ClienteComboState:
    clients = list_clients(db)
    temp_clients = list_clientes_temporarios(db)
    items, phc_names, effective_consumidor_final_id = build_cliente_combo_items(
        clients=clients,
        temp_clients=temp_clients,
        consumidor_final_label=consumidor_final_label,
        consumidor_final_id=consumidor_final_id,
    )
    return ClienteComboState(
        items=items,
        phc_names=phc_names,
        consumidor_final_id=effective_consumidor_final_id,
        names=[item.nome for item in items if item.nome],
    )


def resolve_selected_cliente(
    db: Session,
    *,
    items: Sequence[ClienteComboItem],
    current_text: str,
    current_index: int,
    consumidor_final_id: Optional[int],
) -> Optional[ClienteComboItem]:
    text = str(current_text or "").strip()
    temp_item = None
    temp = get_cliente_temporario_por_nome(db, text)
    if temp:
        temp_item = build_temp_cliente_item(
            temp=temp,
            consumidor_final_id=consumidor_final_id,
            fallback_name=text,
        )
    return resolve_selected_cliente_item(
        items=items,
        current_text=text,
        current_index=current_index,
        temp_item=temp_item,
    )


def resolve_temp_client_dialog_selection(
    db: Session,
    *,
    dialog_data: dict,
    phc_name_set: set[str],
) -> str:
    nome = str((dialog_data or {}).get("nome") or "").strip()
    if not nome:
        raise ValueError("Cliente temporario invalido.")

    temp_nome_real = nome
    temp_id = (dialog_data or {}).get("temp_id")
    if temp_id:
        try:
            temp_obj = get_cliente_temporario(db, int(temp_id))
            if temp_obj and getattr(temp_obj, "nome", None):
                temp_nome_real = str(temp_obj.nome).strip()
        except Exception:
            temp_nome_real = nome

    if temp_nome_real.casefold() in {str(n).casefold() for n in (phc_name_set or set())}:
        raise ValueError(
            "Ja existe um cliente oficial no PHC com este nome.\n"
            "Use o cliente oficial ou escolha outro nome temporario."
        )

    return nome


def load_cliente_info_state(
    db: Session,
    *,
    row_id: Optional[int],
    temp_id: Optional[int],
    temp_nome: str,
) -> Optional[ClienteInfoState]:
    temp_nome_txt = str(temp_nome or "").strip()
    if temp_id or temp_nome_txt:
        temp = get_cliente_temporario(db, int(temp_id)) if temp_id else None
        if temp:
            data = build_cliente_info_data(temp)
        else:
            data = {"nome": temp_nome_txt}
        return ClienteInfoState(origem="Temporario (CONSUMIDOR FINAL)", data=data)

    orcamento, client = orcamentos_workflow.load_orcamento_with_client(db, row_id)
    if not orcamento:
        return None
    if not client:
        raise ValueError("Cliente nao encontrado na base de dados.")
    return ClienteInfoState(origem="PHC", data=build_cliente_info_data(client))
