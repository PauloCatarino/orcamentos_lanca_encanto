from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import logging

from Martelo_Orcamentos_V2.app.utils.bool_converter import bool_to_int, int_to_bool

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
MENU_DEFAULT_FAMILIA = svc_dg.MENU_DEFAULT_FAMILIA

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

LAYOUT_NAMESPACE = "dados_items"


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
        data["familia"] = MENU_DEFAULT_FAMILIA.get(menu, "PLACAS")
    if "nao_stock" in data:
        data["nao_stock"] = bool(data.get("nao_stock"))
    return data


def _json_ready_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    prepared: List[Dict[str, Any]] = []
    for row in rows:
        clean = {}
        for key, value in dict(row).items():
            if isinstance(value, Decimal):
                clean[key] = float(value)
            else:
                clean[key] = value
        prepared.append(clean)
    return prepared


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
    try:
        return svc_dg._coerce(menu, field, value)  # type: ignore[attr-defined]
    except Exception:
        try:
            return svc_dg._coerce_field(menu, field, value)  # type: ignore[attr-defined]
        except Exception:
            return value


logger = logging.getLogger(__name__)

def _to_bool_int(v: Any) -> int:
    """
    Coerção segura para 0/1 a partir de bool, int, Decimal, str, None.
    - None -> 0 (podes mudar para None se preferires preservar NULL)
    - True/"true"/"1"/1 -> 1
    - False/"false"/"0"/0 -> 0
    """
    if v is None:
        return 0
    if isinstance(v, bool):
        return 1 if v else 0
    # ints, Decimals...
    try:
        if isinstance(v, (int, float)):
            return 1 if int(v) != 0 else 0
    except Exception:
        pass
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "t", "on", "yes", "y"):
            return 1
        if s in ("0", "false", "f", "off", "no", "n", ""):
            return 0
        # se for texto qualquer, assume true se não vazio
        return 1 if s else 0
    # fallback: truthiness
    return 1 if bool(v) else 0


def guardar_dados_gerais(db: Session, ctx: DadosItemsContext,
                         payload: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    """
    Guarda linhas de vários menus (materiais, ferragens, ...).
    - Apaga linhas existentes para item_id antes de inserir as novas.
    - Faz coerção explícita do campo `nao_stock` para 0/1.
    - Usa _coerce(menu, field, value) se estiver definido no módulo (mantém compatibilidade).
    """
    # segurança: payload pode ser None ou vazio
    if not payload:
        logger.debug("guardar_dados_gerais: payload vazio")
        return

    # função auxiliar para tentar usar _coerce do módulo, se existir
    def _try_coerce(menu: str, field: str, value: Any) -> Any:
        # tenta usar _coerce definido no ficheiro (se existir)
        try:
            coerced = _coerce(menu, field, value)  # noqa: F821  - NameError se não existir
            return coerced
        except NameError:
            # não existe _coerce global, fal-back para valor cru
            return value

    try:
        for menu, rows in payload.items():
            if menu not in MODEL_MAP:
                logger.debug("guardar_dados_gerais: saltando menu desconhecido %s", menu)
                continue

            model = MODEL_MAP[menu]

            # apaga linhas existentes para esse item antes de inserir as novas
            db.execute(delete(model).where(model.item_id == ctx.item_id))

            if not rows:
                # nada a inserir
                continue

            for ordem, row in enumerate(rows):
                body = dict(row)  # copiamos para não alterar o original
                # garante campo ordem
                body.setdefault("ordem", ordem)

                instance_kwargs: Dict[str, Any] = {
                    "orcamento_id": ctx.orcamento_id,
                    "item_id": ctx.item_id,
                    "cliente_id": ctx.cliente_id,
                    "user_id": ctx.user_id,
                    "ano": ctx.ano,
                    "num_orcamento": ctx.num_orcamento,
                    "versao": ctx.versao,
                    # a ordem final: prefere body["ordem"] quando existe, senão usa enumerate
                    "ordem": int(body.get("ordem", ordem) or ordem),
                }

                # percorre os campos que este menu aceita
                for field in MENU_FIELDS[menu]:
                    value = body.get(field)
                    # tratamento especial para nao_stock — queres 0/1 no BD
                    if field == "nao_stock":
                        coerced = _to_bool_int(value)
                    else:
                        # tenta manter a coerção já existente no projecto (se houver)
                        coerced = _try_coerce(menu, field, value)
                    instance_kwargs[field] = coerced

                # cria e adiciona a instância SQLAlchemy
                db.add(model(**instance_kwargs))

        # tenta commitar todas as alterações
        db.commit()

        # DEBUG: depois do commit, opcional: mostrar resumo de nao_stock gravado para este item
        try:
            logger.debug("Após commit - resumos do item_id=%s", ctx.item_id)
            for menu in (MENU_MATERIAIS, MENU_FERRAGENS, MENU_SIS_CORRER, MENU_ACABAMENTOS):
                if menu not in MODEL_MAP:
                    continue
                model = MODEL_MAP[menu]
                rows_saved = db.execute(
                    select(model.id, model.ordem, model.nao_stock).where(model.item_id == ctx.item_id)
                    .order_by(model.ordem, model.id)
                ).all()
                logger.debug("[AFTER COMMIT] menu=%r rows_saved=%d", menu, len(rows_saved))
                for r in rows_saved[:10]:
                    logger.debug("  id=%s ordem=%s nao_stock=%s", r.id, r.ordem, r.nao_stock)
        except Exception:
            # não é crítico; apenas logar
            logger.exception("Erro ao obter resumo pós-commit")

    except Exception as exc:
        # garante rollback em caso de erro e re-levanta exceção para tratamento acima
        logger.exception("Falha ao guardar dados do item: %s", exc)
        try:
            db.rollback()
        except Exception:
            logger.exception("Falha ao fazer rollback")
        raise



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
        payload = json.dumps(_json_ready_rows(rows))
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
