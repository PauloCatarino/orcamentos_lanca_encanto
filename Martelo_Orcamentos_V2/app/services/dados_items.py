from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models import (
    Client,
    Orcamento,
    OrcamentoItem,
    User,
    DadosItemsMaterial,
    DadosItemsFerragem,
    DadosItemsSistemaCorrer,
    DadosItemsAcabamento,
    DadosItemsModelo,
    DadosItemsModeloItem,
)
from Martelo_Orcamentos_V2.app.services import dados_gerais as svc_dg

MENU_MATERIAIS = svc_dg.MENU_MATERIAIS
MENU_FERRAGENS = svc_dg.MENU_FERRAGENS
MENU_SIS_CORRER = svc_dg.MENU_SIS_CORRER
MENU_ACABAMENTOS = svc_dg.MENU_ACABAMENTOS

MENU_FIXED_GROUPS = svc_dg.MENU_FIXED_GROUPS
MENU_PRIMARY_FIELD = svc_dg.MENU_PRIMARY_FIELD

MENU_FIELDS_BASE = svc_dg.MENU_FIELDS
MENU_FIELD_TYPES_BASE = svc_dg.MENU_FIELD_TYPES

MENU_FIELDS: Dict[str, Sequence[str]] = {
    MENU_MATERIAIS: MENU_FIELDS_BASE[MENU_MATERIAIS] + ("linha", "custo_mp_und", "custo_mp_total"),
    MENU_FERRAGENS: MENU_FIELDS_BASE[MENU_FERRAGENS] + ("linha", "spp_ml_und", "custo_mp_und", "custo_mp_total"),
    MENU_SIS_CORRER: MENU_FIELDS_BASE[MENU_SIS_CORRER] + ("linha", "custo_mp_und", "custo_mp_total"),
    MENU_ACABAMENTOS: MENU_FIELDS_BASE[MENU_ACABAMENTOS] + ("linha", "custo_acb_und", "custo_acb_total"),
}

MENU_FIELD_TYPES: Dict[str, Dict[str, Sequence[str]]] = {
    MENU_MATERIAIS: {
        **MENU_FIELD_TYPES_BASE[MENU_MATERIAIS],
        "integer": MENU_FIELD_TYPES_BASE[MENU_MATERIAIS]["integer"] + ("linha",),
        "decimal": MENU_FIELD_TYPES_BASE[MENU_MATERIAIS]["decimal"] + ("custo_mp_und", "custo_mp_total"),
    },
    MENU_FERRAGENS: {
        **MENU_FIELD_TYPES_BASE[MENU_FERRAGENS],
        "integer": MENU_FIELD_TYPES_BASE[MENU_FERRAGENS]["integer"] + ("linha",),
        "decimal": MENU_FIELD_TYPES_BASE[MENU_FERRAGENS]["decimal"] + ("spp_ml_und", "custo_mp_und", "custo_mp_total"),
    },
    MENU_SIS_CORRER: {
        **MENU_FIELD_TYPES_BASE[MENU_SIS_CORRER],
        "integer": MENU_FIELD_TYPES_BASE[MENU_SIS_CORRER]["integer"] + ("linha",),
        "decimal": MENU_FIELD_TYPES_BASE[MENU_SIS_CORRER]["decimal"] + ("custo_mp_und", "custo_mp_total"),
    },
    MENU_ACABAMENTOS: {
        **MENU_FIELD_TYPES_BASE[MENU_ACABAMENTOS],
        "integer": MENU_FIELD_TYPES_BASE[MENU_ACABAMENTOS]["integer"] + ("linha",),
        "decimal": MENU_FIELD_TYPES_BASE[MENU_ACABAMENTOS]["decimal"] + ("custo_acb_und", "custo_acb_total"),
    },
}

MODEL_MAP = {
    MENU_MATERIAIS: DadosItemsMaterial,
    MENU_FERRAGENS: DadosItemsFerragem,
    MENU_SIS_CORRER: DadosItemsSistemaCorrer,
    MENU_ACABAMENTOS: DadosItemsAcabamento,
}

MENU_KEYS = (MENU_MATERIAIS, MENU_FERRAGENS, MENU_SIS_CORRER, MENU_ACABAMENTOS)


@dataclass
class DadosItemsContext:
    orcamento_id: int
    item_id: int
    cliente_id: int
    user_id: Optional[int]
    ano: str
    num_orcamento: str
    versao: str
    item_ordem: Optional[int]


_DEF_ROWS_CACHE: Dict[str, List[Dict[str, Any]]] = {
    key: svc_dg._default_rows_for_menu(key)  # type: ignore[attr-defined]
    for key in MENU_KEYS
}


def carregar_contexto(db: Session, orcamento_id: int, item_id: Optional[int] = None) -> DadosItemsContext:
    if not item_id:
        raise ValueError("item_id e obrigatorio para carregar Dados Items")

    orc = db.get(Orcamento, orcamento_id)
    if not orc:
        raise ValueError("Orcamento nao encontrado")

    if orc.client_id is None:
        raise ValueError("Orcamento sem cliente associado")
    item = db.get(OrcamentoItem, item_id)
    if not item or item.id_orcamento != orcamento_id:
        raise ValueError("Item do orcamento nao encontrado")

    return DadosItemsContext(
        orcamento_id=orcamento_id,
        item_id=item_id,
        cliente_id=orc.client_id,
        user_id=item.updated_by or orc.updated_by or orc.created_by,
        ano=str(orc.ano),
        num_orcamento=str(orc.num_orcamento),
        versao=str(item.versao or orc.versao or "00"),
        item_ordem=getattr(item, "item_ord", None),
    )


def _row_to_dict(menu: str, row: Any) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "id": getattr(row, "id", None),
        "ordem": getattr(row, "ordem", 0) or 0,
    }
    fields = MENU_FIELDS[menu]
    for field in fields:
        data[field] = getattr(row, field, None)
    if "familia" in data and not data.get("familia"):
        data["familia"] = "PLACAS"
    if "nao_stock" in data:
        data["nao_stock"] = bool(data.get("nao_stock"))
    return data


def carregar_dados_gerais(db: Session, ctx: DadosItemsContext) -> Dict[str, List[Dict[str, Any]]]:
    data: Dict[str, List[Dict[str, Any]]] = {}
    for menu, model in MODEL_MAP.items():
        stmt = (
            select(model)
            .where(model.item_id == ctx.item_id)
            .order_by(model.ordem, model.id)
        )
        rows = db.execute(stmt).scalars().all()
        dict_rows = [_row_to_dict(menu, row) for row in rows]
        ensured = svc_dg._ensure_menu_rows(menu, dict_rows)  # type: ignore[attr-defined]
        data[menu] = ensured
    return data


def _coerce(menu: str, field: str, value: Any) -> Any:
    return svc_dg._coerce_field(menu, field, value)  # type: ignore[attr-defined]


def guardar_dados_gerais(db: Session, ctx: DadosItemsContext, payload: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    for menu, rows in payload.items():
        if menu not in MODEL_MAP:
            continue
        model = MODEL_MAP[menu]
        db.execute(delete(model).where(model.item_id == ctx.item_id))

        if not rows:
            continue

        for ordem, row in enumerate(rows):
            body = dict(row)
            body.setdefault("ordem", ordem)
            instance_kwargs: Dict[str, Any] = {
                "orcamento_id": ctx.orcamento_id,
                "item_id": ctx.item_id,
                "cliente_id": ctx.cliente_id,
                "user_id": ctx.user_id,
                "ano": ctx.ano,
                "num_orcamento": ctx.num_orcamento,
                "versao": ctx.versao,
                "ordem": body.get("ordem", ordem) or ordem,
            }
            for field in MENU_FIELDS[menu]:
                value = body.get(field)
                coerced = _coerce(menu, field, value)
                instance_kwargs[field] = coerced
            db.add(model(**instance_kwargs))
    db.commit()


@dataclass
class DadosItemsModeloData:
    modelo_id: int
    nome_modelo: str
    tipo_menu: str
    dados: List[Dict[str, Any]]
    replace: bool


def listar_modelos(db: Session, orcamento_id: int, *, item_id: Optional[int] = None) -> List[DadosItemsModelo]:
    stmt = select(DadosItemsModelo).where(DadosItemsModelo.orcamento_id == orcamento_id)
    if item_id is not None:
        stmt = stmt.where((DadosItemsModelo.item_id == item_id) | (DadosItemsModelo.item_id.is_(None)))
    stmt = stmt.order_by(DadosItemsModelo.nome_modelo, DadosItemsModelo.id)
    return db.execute(stmt).scalars().all()


def carregar_modelo(db: Session, modelo_id: int) -> Dict[str, List[Dict[str, Any]]]:
    stmt = (
        select(DadosItemsModeloItem)
        .where(DadosItemsModeloItem.modelo_id == modelo_id)
        .order_by(DadosItemsModeloItem.tipo_menu, DadosItemsModeloItem.ordem, DadosItemsModeloItem.id)
    )
    items = db.execute(stmt).scalars().all()
    result: Dict[str, List[Dict[str, Any]]] = {menu: [] for menu in MENU_KEYS}
    for item in items:
        try:
            dados = json.loads(item.dados)
        except Exception:
            continue
        if isinstance(dados, list):
            result[item.tipo_menu] = dados
    return result


def guardar_modelo(
    db: Session,
    ctx: DadosItemsContext,
    nome_modelo: str,
    linhas: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    replace_model_id: Optional[int] = None,
) -> DadosItemsModelo:
    if replace_model_id:
        modelo = db.get(DadosItemsModelo, replace_model_id)
        if not modelo:
            raise ValueError("Modelo nao encontrado")
        modelo.nome_modelo = nome_modelo
        modelo.item_id = ctx.item_id
        modelo.orcamento_id = ctx.orcamento_id
        modelo.user_id = ctx.user_id
        db.execute(delete(DadosItemsModeloItem).where(DadosItemsModeloItem.modelo_id == modelo.id))
    else:
        modelo = DadosItemsModelo(
            orcamento_id=ctx.orcamento_id,
            item_id=ctx.item_id,
            user_id=ctx.user_id,
            nome_modelo=nome_modelo,
            tipo_menu=MENU_MATERIAIS,
        )
        db.add(modelo)
        db.flush()

    for menu in MENU_KEYS:
        rows = linhas.get(menu, [])
        payload = json.dumps([dict(row) for row in rows])
        db.add(
            DadosItemsModeloItem(
                modelo_id=modelo.id,
                tipo_menu=menu,
                ordem=0,
                dados=payload,
            )
        )
    db.commit()
    db.refresh(modelo)
    return modelo


def eliminar_modelo(db: Session, modelo_id: int, *, orcamento_id: int) -> None:
    stmt = select(DadosItemsModelo).where(
        DadosItemsModelo.id == modelo_id,
        DadosItemsModelo.orcamento_id == orcamento_id,
    )
    modelo = db.execute(stmt).scalar_one_or_none()
    if not modelo:
        raise ValueError("Modelo nao encontrado")
    db.delete(modelo)
    db.commit()


def renomear_modelo(db: Session, modelo_id: int, *, orcamento_id: int, novo_nome: str) -> DadosItemsModelo:
    stmt = select(DadosItemsModelo).where(
        DadosItemsModelo.id == modelo_id,
        DadosItemsModelo.orcamento_id == orcamento_id,
    )
    modelo = db.execute(stmt).scalar_one_or_none()
    if not modelo:
        raise ValueError("Modelo nao encontrado")
    modelo.nome_modelo = novo_nome
    db.add(modelo)
    db.commit()
    db.refresh(modelo)
    return modelo
calcular_preco_liq = svc_dg.calcular_preco_liq
