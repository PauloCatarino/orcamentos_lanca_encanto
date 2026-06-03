import datetime
import json
import difflib
import logging
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Sequence

from sqlalchemy import String, cast, select, func, and_, or_, delete
from sqlalchemy.orm import Session

from ..utils.date_utils import today_storage

from ..models import (
    Orcamento,
    OrcamentoItem,
    Client,
    ClienteTemporario,
    User,
    CusteioItem,
    CusteioItemDimensoes,
    CusteioDespBackup,
    CusteioProducaoConfig,
    CusteioProducaoValor,
    DadosModuloMedidas,
    DadosDefPecas,
    DadosGeraisMaterial,
    DadosGeraisFerragem,
    DadosGeraisSistemaCorrer,
    DadosGeraisAcabamento,
    DadosItemsMaterial,
    DadosItemsFerragem,
    DadosItemsSistemaCorrer,
    DadosItemsAcabamento,
    DadosItemsModelo,
    DadosItemsModeloItem,
)

logger = logging.getLogger(__name__)

PRECO_MANUAL_KEY = "preco_manual"
TEMP_CLIENT_ID_KEY = "temp_client_id"
TEMP_CLIENT_NAME_KEY = "temp_client_nome"
ORCAMENTO_FUZZY_CANDIDATE_LIMIT = 5000

_SEARCH_SYNONYMS_ORCAMENTOS: dict[str, tuple[str, ...]] = {
    "armario": ("roupeiro", "closet"),
    "armarios": ("roupeiros", "closets"),
    "closet": ("roupeiro", "armario"),
    "closets": ("roupeiros", "armarios"),
    "batente": ("abrir",),
    "batentes": ("abrir",),
    "lacado": ("laca", "pintado"),
    "lacada": ("laca", "pintada"),
    "lacados": ("laca", "pintados"),
    "lacadas": ("laca", "pintadas"),
    "melamina": ("mlm",),
    "mlm": ("melamina",),
    "gavetao": ("gaveta",),
    "gavetoes": ("gavetas",),
}

_SEARCH_FIELDS_ORCAMENTOS = (
    cast(Orcamento.id, String),
    Orcamento.num_orcamento,
    Orcamento.ano,
    Orcamento.versao,
    Orcamento.enc_phc,
    Orcamento.status,
    Orcamento.data,
    cast(Orcamento.preco_total, String),
    Orcamento.ref_cliente,
    Orcamento.obra,
    Orcamento.descricao_orcamento,
    Orcamento.localizacao,
    Orcamento.info_1,
    Orcamento.info_2,
    Orcamento.notas,
    Client.nome,
    Client.nome_simplex,
    User.username,
)

_SEARCH_FIELDS_ORCAMENTO_ITEMS = (
    OrcamentoItem.item,
    OrcamentoItem.codigo,
    OrcamentoItem.descricao,
    cast(OrcamentoItem.altura, String),
    cast(OrcamentoItem.largura, String),
    cast(OrcamentoItem.profundidade, String),
    OrcamentoItem.und,
    cast(OrcamentoItem.qt, String),
    OrcamentoItem.notas,
)


def _delete_item_related_rows(db: Session, id_item: int) -> None:
    model_ids = db.execute(
        select(DadosItemsModelo.id).where(DadosItemsModelo.item_id == id_item)
    ).scalars().all()
    if model_ids:
        db.execute(
            delete(DadosItemsModeloItem).where(DadosItemsModeloItem.modelo_id.in_(model_ids))
        )

    custeio_item_ids = select(CusteioItem.id).where(CusteioItem.item_id == id_item)

    delete_specs = (
        (CusteioDespBackup, CusteioDespBackup.custeio_item_id.in_(custeio_item_ids)),
        (CusteioItemDimensoes, CusteioItemDimensoes.item_id == id_item),
        (CusteioItem, CusteioItem.item_id == id_item),
        (DadosItemsModelo, DadosItemsModelo.item_id == id_item),
        (DadosItemsAcabamento, DadosItemsAcabamento.item_id == id_item),
        (DadosItemsSistemaCorrer, DadosItemsSistemaCorrer.item_id == id_item),
        (DadosItemsFerragem, DadosItemsFerragem.item_id == id_item),
        (DadosItemsMaterial, DadosItemsMaterial.item_id == id_item),
        (DadosDefPecas, DadosDefPecas.id_item_fk == id_item),
        (DadosModuloMedidas, DadosModuloMedidas.id_item_fk == id_item),
    )
    for model, condition in delete_specs:
        db.execute(delete(model).where(condition))
    db.flush()


@dataclass
class OrcamentoResumo:
    id: int
    ano: str
    num_orcamento: str
    versao: str
    enc_phc: str
    cliente: str
    temp_client_id: int | None
    temp_client_nome: str
    data: str
    preco: Decimal | float | None
    preco_manual: bool
    preco_total_manual: int  # 0=calculado, 1=manual
    preco_atualizado_em: Optional[datetime.datetime]
    utilizador: str
    estado: str
    obra: str
    descricao: str
    localizacao: str
    info_1: str
    info_2: str
    ref_cliente: str
    search_score: float = 0.0
    search_reason: str = ""


def _format_versao(value: Optional[str]) -> str:
    if value is None:
        return "00"
    try:
        return f"{int(str(value)):02d}"
    except Exception:
        return str(value)


def _format_preco(value) -> str:
    if value in (None, ""):
        return ""
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)

def _normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_codigo(value: Optional[str]) -> Optional[str]:
    text = _normalize_text(value)
    return text.upper() if text else None


def _coerce_decimal(value, default: Decimal) -> Decimal:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    text = str(value).strip()
    if not text:
        return default
    text = text.replace(",", ".")
    try:
        return Decimal(text)
    except Exception:
        return default


def _parse_orcamento_extras(extras_raw) -> dict:
    if isinstance(extras_raw, dict):
        return extras_raw
    if extras_raw in (None, ""):
        return {}
    if isinstance(extras_raw, str):
        try:
            parsed = json.loads(extras_raw)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _parse_temp_client_id(extras: dict) -> Optional[int]:
    if not isinstance(extras, dict):
        return None
    temp_id_val = extras.get(TEMP_CLIENT_ID_KEY)
    if temp_id_val in (None, ""):
        return None
    try:
        return int(temp_id_val)
    except Exception:
        return None


def resolve_orcamento_temp_cliente(db: Session, orcamento: Optional[Orcamento]) -> Optional[ClienteTemporario]:
    if not db or not orcamento:
        return None
    extras = _parse_orcamento_extras(getattr(orcamento, "extras", None))
    temp_id = _parse_temp_client_id(extras)
    if not temp_id:
        return None
    try:
        return db.get(ClienteTemporario, temp_id)
    except Exception:
        return None


def resolve_orcamento_cliente_nome(
    db: Session,
    orcamento: Optional[Orcamento],
    *,
    client: Optional[Client] = None,
) -> str:
    if not orcamento:
        return (getattr(client, "nome", "") or "").strip()
    extras = _parse_orcamento_extras(getattr(orcamento, "extras", None))
    temp_nome = str(extras.get(TEMP_CLIENT_NAME_KEY) or "").strip() if isinstance(extras, dict) else ""
    temp_id = _parse_temp_client_id(extras)
    if temp_id:
        try:
            temp = db.get(ClienteTemporario, temp_id)
        except Exception:
            temp = None
        if temp:
            nome_real = (getattr(temp, "nome", "") or "").strip()
            if nome_real:
                return nome_real
            if temp_nome:
                return temp_nome
            nome_simplex = (getattr(temp, "nome_simplex", "") or "").strip()
            if nome_simplex:
                return nome_simplex
    if temp_nome:
        return temp_nome
    if client is None and getattr(orcamento, "client_id", None):
        try:
            client = db.get(Client, orcamento.client_id)
        except Exception:
            client = None
    return (getattr(client, "nome", "") or "").strip()


DECIMAL_ZERO = Decimal("0")
DECIMAL_ONE = Decimal("1")



def _select_orcamentos():
    return (
        select(
            Orcamento.id.label("id"),
            Orcamento.ano.label("ano"),
            Orcamento.num_orcamento.label("num_orcamento"),
            Orcamento.versao.label("versao"),
            Orcamento.enc_phc.label("enc_phc"),
            Client.nome_simplex.label("cliente_simplex"),
            Client.nome.label("cliente_nome"),
            Orcamento.data.label("data"),
            Orcamento.preco_total.label("preco_total"),
            Orcamento.preco_total_manual.label("preco_total_manual"),
            Orcamento.preco_atualizado_em.label("preco_atualizado_em"),
            Orcamento.extras.label("extras"),
            User.username.label("utilizador"),
            Orcamento.status.label("estado"),
            Orcamento.obra.label("obra"),
            Orcamento.descricao_orcamento.label("descricao"),
            Orcamento.localizacao.label("localizacao"),
            Orcamento.info_1.label("info_1"),
            Orcamento.info_2.label("info_2"),
            Orcamento.ref_cliente.label("ref_cliente"),
        )
        .select_from(Orcamento)
        .outerjoin(Client, Orcamento.client_id == Client.id)
        .outerjoin(User, Orcamento.created_by == User.id)
    )


def _rows_from_stmt(db: Session, stmt) -> List[OrcamentoResumo]:
    rows = db.execute(stmt).all()
    extras_list: List[dict] = []
    temp_ids: set[int] = set()
    for row in rows:
        extras_raw = getattr(row, "extras", None)
        extras = {}
        if isinstance(extras_raw, dict):
            extras = extras_raw
        elif extras_raw not in (None, ""):
            try:
                extras = json.loads(extras_raw)
            except Exception:
                extras = {}
        extras_list.append(extras if isinstance(extras, dict) else {})
        temp_id_val = extras.get(TEMP_CLIENT_ID_KEY) if isinstance(extras, dict) else None
        if temp_id_val not in (None, ""):
            try:
                temp_ids.add(int(temp_id_val))
            except Exception:
                pass

    temp_simplex_map: dict[int, str] = {}
    if temp_ids:
        try:
            temps = (
                db.execute(select(ClienteTemporario).where(ClienteTemporario.id.in_(temp_ids)))
                .scalars()
                .all()
            )
        except Exception:
            temps = []
        for temp in temps:
            name = str(getattr(temp, "nome_simplex", None) or getattr(temp, "nome", None) or "").strip()
            if name:
                temp_simplex_map[int(getattr(temp, "id", 0) or 0)] = name
    parsed: List[OrcamentoResumo] = []
    for row, extras in zip(rows, extras_list):
        legacy_preco_manual = bool(extras.get(PRECO_MANUAL_KEY)) if isinstance(extras, dict) else False
        preco_total_manual = 1 if bool(getattr(row, "preco_total_manual", 0) or legacy_preco_manual) else 0
        temp_nome = ""
        temp_id = None
        if isinstance(extras, dict):
            temp_nome = str(extras.get(TEMP_CLIENT_NAME_KEY) or "").strip()
            temp_id_val = extras.get(TEMP_CLIENT_ID_KEY)
            if temp_id_val not in (None, ""):
                try:
                    temp_id = int(temp_id_val)
                except Exception:
                    temp_id = None
        temp_simplex = temp_simplex_map.get(temp_id or -1, "")
        cliente_base = (row.cliente_simplex or row.cliente_nome or "").strip()
        if temp_simplex:
            cliente = temp_simplex
        elif temp_nome:
            cliente = temp_nome
        else:
            cliente = cliente_base
        parsed.append(
            OrcamentoResumo(
                id=row.id,
                ano=str(row.ano or ""),
                num_orcamento=str(row.num_orcamento or ""),
                versao=_format_versao(row.versao),
                enc_phc=str(getattr(row, "enc_phc", "") or ""),
                cliente=cliente,
                temp_client_id=temp_id,
                temp_client_nome=temp_nome,
                data=row.data or "",
                preco=row.preco_total,
                preco_manual=bool(preco_total_manual),
                preco_total_manual=preco_total_manual,
                preco_atualizado_em=getattr(row, "preco_atualizado_em", None),
                utilizador=row.utilizador or "",
                estado=row.estado or "",
                obra=row.obra or "",
                descricao=row.descricao or "",
                localizacao=row.localizacao or "",
                info_1=row.info_1 or "",
                info_2=row.info_2 or "",
                ref_cliente=row.ref_cliente or "",
            )
        )
    return parsed


def list_orcamentos(db: Session) -> List[OrcamentoResumo]:
    stmt = _select_orcamentos().order_by(
        Orcamento.ano.desc(), Orcamento.num_orcamento.desc(), Orcamento.versao
    )
    return _rows_from_stmt(db, stmt)


def get_orcamento(db: Session, orc_id: int) -> Optional[Orcamento]:
    return db.get(Orcamento, orc_id)


def ensure_client(db: Session, nome: str) -> Client:
    nome = (nome or "Cliente GenÃ©rico").strip() or "Cliente GenÃ©rico"
    c = db.execute(select(Client).where(Client.nome == nome)).scalar_one_or_none()
    if c:
        return c
    c = Client(nome=nome)
    db.add(c)
    db.flush()
    return c


def create_orcamento(
    db: Session,
    *,
    ano: str,
    num_orcamento: str,
    versao: str = "01",
    cliente_nome: str = "",
    client_id: Optional[int] = None,
    created_by: Optional[int] = None,
) -> Orcamento:
    versao = f"{int(versao):02d}" if versao and versao.isdigit() else (versao if versao else "01")
    if client_id:
        cli = db.get(Client, client_id)
        if not cli:
            raise ValueError("Cliente nÃ£o encontrado")
    else:
        cli = ensure_client(db, cliente_nome)
    o = Orcamento(
        ano=str(ano),
        num_orcamento=str(num_orcamento),
        versao=versao,
        client_id=cli.id,
        data=today_storage(),
        status="Falta Orcamentar",
        created_by=created_by,
    )
    db.add(o)
    db.flush()
    return o


def delete_orcamento(db: Session, orc_id: int) -> None:
    o = db.get(Orcamento, orc_id)
    if not o:
        return
    db.delete(o)


def list_items(db: Session, orc_id: int, versao: str | None = None) -> List[OrcamentoItem]:
    stmt = select(OrcamentoItem).where(OrcamentoItem.id_orcamento == orc_id)
    if versao:
        stmt = stmt.where(OrcamentoItem.versao == versao)
    return db.execute(stmt.order_by(OrcamentoItem.item_ord, OrcamentoItem.id_item)).scalars().all()


def _next_item_ord(db: Session, orc_id: int) -> int:
    # jÃ¡ existe no ficheiro, deixo aqui por referÃªncia
    q = db.execute(
        select(func.max(OrcamentoItem.item_ord)).where(OrcamentoItem.id_orcamento == orc_id)
    ).scalar()
    return int(q or 0) + 1


def _reindex_items(
    db: Session,
    orc_id: int,
    *,
    versao: Optional[str] = None,
    updated_by: Optional[int] = None,
) -> List[OrcamentoItem]:
    """
    Reaplica ordenacao e numeracao (item_ord e Item) sequencialmente para o orcamento/versao.
    Renumera sempre a coluna Item para manter a correspondencia 1..N visivel.
    """
    # Garantir que quaisquer alteracoes pendentes (ex.: troca de item_ord) entram no SELECT
    db.flush()

    stmt = select(OrcamentoItem).where(OrcamentoItem.id_orcamento == orc_id)
    if versao:
        stmt = stmt.where(OrcamentoItem.versao == versao)

    rows = db.execute(stmt.order_by(OrcamentoItem.item_ord, OrcamentoItem.id_item)).scalars().all()

    for idx, row in enumerate(rows, start=1):
        row.item_ord = idx
        row.item = str(idx)
        if updated_by is not None:
            row.updated_by = updated_by

    db.flush()
    return rows


def create_item(
    db: Session,
    orc_id: int,
    versao: str,              # âœ” versÃ£o obrigatÃ³ria
    *,
    item: Optional[str] = None,     # âœ” nome visÃ­vel do item
    codigo: Optional[str] = None,
    descricao: Optional[str] = None,
    altura=None,
    largura=None,
    profundidade=None,
    und: Optional[str] = None,
    qt=None,
    created_by: Optional[int] = None,
) -> OrcamentoItem:
    """
    Cria um novo item associado ao orÃ§amento.
    - 'item' Ã© preenchido automaticamente com a prÃ³xima sequÃªncia (1, 2, 3, ...)
      se o utilizador nÃ£o indicar um nome.
    - 'item_ord' Ã© a ordem visual (1..N) e acompanha a sequÃªncia.
    """

    # Normaliza versÃ£o para '01', '02', ...
    versao_norm = _format_versao(versao)

    # PrÃ³xima ordem/sequÃªncia dentro do orÃ§amento (por id_orcamento)
    prox_ord = _next_item_ord(db, orc_id)

    # Se o utilizador nÃ£o escreveu nome, usamos a sequÃªncia como texto
    item_val = _normalize_text(item) if item is not None else str(prox_ord)

    # ConstrÃ³i a entidade ORM
    row = OrcamentoItem(
        id_orcamento=orc_id,
        versao=versao_norm,                 # âœ” agora o modelo aceita 'versao'
        item_ord=prox_ord,
        item=item_val,                      # âœ” atributo 'item' no ORM (nÃ£o 'item_nome')
        codigo=_normalize_codigo(codigo),
        descricao=_normalize_text(descricao),
        altura=_coerce_decimal(altura, DECIMAL_ZERO),
        largura=_coerce_decimal(largura, DECIMAL_ZERO),
        profundidade=_coerce_decimal(profundidade, DECIMAL_ZERO),
        und=_normalize_text(und) or "und",
        qt=_coerce_decimal(qt, DECIMAL_ONE),
        created_by=created_by,
        updated_by=created_by,
    )

    db.add(row)
    db.flush()   # para obter id_item imediatamente, se precisares
    return row


def delete_item(
    db: Session,
    id_item: int,
    *,
    deleted_by: Optional[int] = None
) -> bool:
    """
    Remove um item do orcamento com validacoes e logging.
    Retorna True se foi eliminado, False se nao foi encontrado.
    """
    it = db.get(OrcamentoItem, id_item)
    if not it:
        return False

    orc_id = it.id_orcamento
    versao = it.versao
    item_nome = it.item or "(sem nome)"

    logger.info(
        "A remover item '%s' (ID=%s) do orcamento %s versao %s por utilizador %s",
        item_nome,
        id_item,
        orc_id,
        versao,
        deleted_by,
    )

    _delete_item_related_rows(db, id_item)
    db.delete(it)
    db.flush()

    # Reorganizar ordenacao/numeracao dos restantes itens da mesma versao
    _reindex_items(db, orc_id, versao=versao, updated_by=deleted_by)
    logger.info(
        "Item '%s' (ID=%s) removido do orcamento %s versao %s por utilizador %s",
        item_nome,
        id_item,
        orc_id,
        versao,
        deleted_by,
    )
    return True


def update_item(
    db: Session,
    id_item: int,
    *,
    versao: Optional[str] = None,         # âœ… Agora podemos atualizar a versÃ£o
    item: Optional[str] = None,           # âœ… Nome do item alinhado com a coluna da BD
    codigo: Optional[str] = None,
    descricao: Optional[str] = None,
    altura=None,
    largura=None,
    profundidade=None,
    und: Optional[str] = None,
    qt=None,
    updated_by: Optional[int] = None,
) -> OrcamentoItem:
    """Atualiza um item existente na tabela orcamento_items."""

    # ðŸ”Ž Buscar item no BD
    it = db.get(OrcamentoItem, id_item)
    if not it:
        raise ValueError("Item nÃ£o encontrado")

    # âœ… Atualizar versÃ£o se fornecida
    if versao is not None:
        it.versao = _format_versao(versao)

    # âœ… Atualizar os restantes campos
    it.item = _normalize_text(item)   # âœ… Corrigido: usar 'item' em vez de 'item_nome'
    it.codigo = _normalize_codigo(codigo)
    it.descricao = _normalize_text(descricao)
    it.altura = _coerce_decimal(altura, DECIMAL_ZERO)
    it.largura = _coerce_decimal(largura, DECIMAL_ZERO)
    it.profundidade = _coerce_decimal(profundidade, DECIMAL_ZERO)
    it.und = _normalize_text(und) or "und"
    it.qt = _coerce_decimal(qt, DECIMAL_ONE)
    it.updated_by = updated_by

    db.flush()
    return it


def move_item(
    db: Session,
    id_item: int,
    direction: int,
    *,
    moved_by: Optional[int] = None
) -> bool:
    """
    Move um item para cima (-1) ou para baixo (+1) com validacoes e logging.
    Retorna True se o movimento foi realizado, False caso contrario.
    """
    it = db.get(OrcamentoItem, id_item)
    if not it:
        return False

    versao = it.versao
    base_query = select(OrcamentoItem).where(OrcamentoItem.id_orcamento == it.id_orcamento)
    if versao:
        base_query = base_query.where(OrcamentoItem.versao == versao)

    if direction > 0:
        neighbor = db.execute(
            base_query.where(OrcamentoItem.item_ord > it.item_ord)
            .order_by(OrcamentoItem.item_ord.asc())
            .limit(1)
        ).scalar_one_or_none()
    else:
        neighbor = db.execute(
            base_query.where(OrcamentoItem.item_ord < it.item_ord)
            .order_by(OrcamentoItem.item_ord.desc())
            .limit(1)
        ).scalar_one_or_none()

    if not neighbor:
        logger.debug("Movimento ignorado: sem vizinho disponivel para item %s", id_item)
        return False

    it.item_ord, neighbor.item_ord = neighbor.item_ord, it.item_ord
    it.updated_by = moved_by
    neighbor.updated_by = moved_by

    logger.info(
        "Item ID=%s trocado com ID=%s no orcamento %s por utilizador %s",
        id_item,
        neighbor.id_item,
        it.id_orcamento,
        moved_by,
    )

    _reindex_items(db, it.id_orcamento, versao=versao, updated_by=moved_by)
    return True


def _clone_rows(db: Session, model, filters, overrides: dict) -> list:
    rows = db.query(model).filter(*filters).all()
    clones = []
    for row in rows:
        data = {}
        for col in model.__table__.columns:
            if col.primary_key:
                continue
            name = col.name
            if name in {"created_at", "updated_at"}:
                continue
            if name in overrides:
                data[name] = overrides[name]
            else:
                data[name] = getattr(row, name)
        clone = model(**data)
        db.add(clone)
        clones.append(clone)
    db.flush()
    return clones


def _clone_rows_with_item_map(db: Session, model, item_map: dict, overrides: dict) -> list:
    if not item_map:
        return []
    rows = db.query(model).filter(model.item_id.in_(item_map.keys())).all()
    clones = []
    for row in rows:
        data = {}
        for col in model.__table__.columns:
            if col.primary_key:
                continue
            name = col.name
            if name in {"created_at", "updated_at"}:
                continue
            if name == "item_id":
                data[name] = item_map.get(getattr(row, "item_id"))
            elif name in overrides:
                data[name] = overrides[name]
            else:
                data[name] = getattr(row, name)
        clone = model(**data)
        db.add(clone)
        clones.append(clone)
    db.flush()
    return clones


def duplicate_item(db: Session, item_id: int, *, created_by: Optional[int] = None) -> OrcamentoItem:
    """
    Duplica um item do orÃ§amento (e dependÃªncias diretas) no mesmo orÃ§amento/versÃ£o.
    """
    src = db.get(OrcamentoItem, item_id)
    if not src:
        raise ValueError("Item nÃ£o encontrado.")

    new_item_ord = _next_item_ord(db, src.id_orcamento)
    new_item_num = str(new_item_ord)
    versao = _format_versao(src.versao or "01")

    new_item = OrcamentoItem(
        id_orcamento=src.id_orcamento,
        versao=versao,
        item_ord=new_item_ord,
        item=new_item_num,
        codigo=src.codigo,
        descricao=src.descricao,
        altura=src.altura,
        largura=src.largura,
        profundidade=src.profundidade,
        und=src.und,
        qt=src.qt,
        preco_unitario=src.preco_unitario,
        preco_total=src.preco_total,
        custo_produzido=src.custo_produzido,
        ajuste=src.ajuste,
        custo_total_orlas=src.custo_total_orlas,
        custo_total_mao_obra=src.custo_total_mao_obra,
        custo_total_materia_prima=src.custo_total_materia_prima,
        custo_total_acabamentos=src.custo_total_acabamentos,
        margem_lucro_perc=src.margem_lucro_perc,
        valor_margem=src.valor_margem,
        custos_admin_perc=src.custos_admin_perc,
        valor_custos_admin=src.valor_custos_admin,
        margem_acabamentos_perc=src.margem_acabamentos_perc,
        valor_acabamentos=src.valor_acabamentos,
        margem_mp_orlas_perc=src.margem_mp_orlas_perc,
        valor_mp_orlas=src.valor_mp_orlas,
        margem_mao_obra_perc=src.margem_mao_obra_perc,
        valor_mao_obra=src.valor_mao_obra,
        notas=src.notas,
        extras=src.extras,
        custo_colagem=src.custo_colagem,
        reservado_2=src.reservado_2,
        reservado_3=src.reservado_3,
        created_by=created_by or src.created_by,
        updated_by=created_by or src.updated_by,
    )
    db.add(new_item)
    db.flush()

    _clone_rows(db, DadosModuloMedidas, [DadosModuloMedidas.id_item_fk == src.id_item], {"id_item_fk": new_item.id_item})
    _clone_rows(db, DadosDefPecas, [DadosDefPecas.id_item_fk == src.id_item], {"id_item_fk": new_item.id_item})

    _clone_rows(db, DadosItemsMaterial, [DadosItemsMaterial.item_id == src.id_item], {"item_id": new_item.id_item})
    _clone_rows(db, DadosItemsFerragem, [DadosItemsFerragem.item_id == src.id_item], {"item_id": new_item.id_item})
    _clone_rows(db, DadosItemsSistemaCorrer, [DadosItemsSistemaCorrer.item_id == src.id_item], {"item_id": new_item.id_item})
    _clone_rows(db, DadosItemsAcabamento, [DadosItemsAcabamento.item_id == src.id_item], {"item_id": new_item.id_item})

    modelos = db.query(DadosItemsModelo).filter(DadosItemsModelo.item_id == src.id_item).all()
    modelo_map = {}
    for modelo in modelos:
        data = {}
        for col in DadosItemsModelo.__table__.columns:
            if col.primary_key:
                continue
            name = col.name
            if name in {"created_at", "updated_at"}:
                continue
            if name == "item_id":
                data[name] = new_item.id_item
            else:
                data[name] = getattr(modelo, name)
        new_modelo = DadosItemsModelo(**data)
        db.add(new_modelo)
        db.flush()
        modelo_map[modelo.id] = new_modelo.id
    for old_id, new_id in modelo_map.items():
        _clone_rows(db, DadosItemsModeloItem, [DadosItemsModeloItem.modelo_id == old_id], {"modelo_id": new_id})

    custeio_rows = db.query(CusteioItem).filter(
        CusteioItem.orcamento_id == src.id_orcamento,
        CusteioItem.item_id == src.id_item,
        CusteioItem.versao == versao,
    ).all()
    for ci in custeio_rows:
        data = {}
        for col in CusteioItem.__table__.columns:
            if col.primary_key:
                continue
            name = col.name
            if name in {"created_at", "updated_at"}:
                continue
            if name == "item_id":
                data[name] = new_item.id_item
            else:
                data[name] = getattr(ci, name)
        new_ci = CusteioItem(**data)
        db.add(new_ci)
    db.flush()

    _clone_rows(
        db,
        CusteioItemDimensoes,
        [
            CusteioItemDimensoes.orcamento_id == src.id_orcamento,
            CusteioItemDimensoes.item_id == src.id_item,
            CusteioItemDimensoes.versao == versao,
        ],
        {"item_id": new_item.id_item},
    )

    _reindex_items(db, src.id_orcamento, versao=versao, updated_by=created_by)
    db.flush()
    return new_item


def next_num_orcamento(db: Session, ano: Optional[str] = None) -> str:
    """Gera 'YYNNNN' baseado no ano (atual por defeito)."""
    if not ano:
        ano = str(datetime.datetime.now().year)
    yy = ano[-2:]
    # encontrar maior sequencia comeÃ§ando por YY
    max_seq = 0
    rows = db.execute(select(Orcamento.num_orcamento).where(Orcamento.num_orcamento.like(f"{yy}%"))).scalars().all()
    for s in rows:
        try:
            if len(s) >= 6 and s[:2] == yy:
                seq = int(s[2:6])
                if seq > max_seq:
                    max_seq = seq
        except Exception:
            continue
    return f"{yy}{(max_seq+1):04d}"


def next_seq_for_year(db: Session, ano: Optional[str] = None) -> str:
    """Devolve apenas a parte sequencial (NNNN) para o ano indicado."""
    if not ano:
        ano = str(datetime.datetime.now().year)
    ano_txt = str(ano).strip() or str(datetime.datetime.now().year)
    yy = ano_txt[-2:]
    max_seq = 0
    largura = 4

    rows = db.execute(
        select(Orcamento.num_orcamento).where(Orcamento.ano == ano_txt)
    ).scalars().all()

    # Extrai apenas a parte sequencial
    for raw in rows:
        if raw is None:
            continue

        texto = str(raw).strip()
        if not texto:
            continue

        sufixo = ""
        prefixo = ""


        if texto.startswith(yy):
            prefixo = texto[: len(yy)]
            sufixo = texto[len(yy):]
        else:
            m = re.search(r"(\d+)$", texto)
            if m:
                sufixo = m.group(1)
                prefixo = texto[: -len(sufixo)]

        if not sufixo:
            continue
        try:
            seq = int(sufixo)
        except ValueError:
            continue

    # Devolve apenas a parte sequencial com zero Ã  esquerda
        if seq > max_seq:
            max_seq = seq
            largura = len(sufixo)
            if not prefixo.strip():
                largura = max(largura, 4)

    largura = max(largura, 4)
    return f"{max_seq + 1:0{largura}d}"


def next_version_for(db: Session, ano: str, num_orc: str) -> str:
    cur = db.execute(select(Orcamento.versao).where(and_(Orcamento.ano == str(ano), Orcamento.num_orcamento == str(num_orc)))).scalars().all()
    maxv = 0
    for v in cur:
        try:
            n = int(str(v))
            if n > maxv:
                maxv = n
        except Exception:
            continue
    return f"{(maxv+1):02d}"


def duplicate_orcamento_version(
    db: Session,
    orc_id: int,
    *,
    created_by: Optional[int] = None,
) -> Orcamento:
    o = db.get(Orcamento, orc_id)
    if not o:
        raise ValueError("OrÃ§amento nÃ£o encontrado")
    old_ver = _format_versao(o.versao)
    new_ver = _format_versao(next_version_for(db, o.ano, o.num_orcamento))
    dup = Orcamento(
        ano=o.ano,
        num_orcamento=o.num_orcamento,
        versao=new_ver,
        client_id=o.client_id,
        status="Falta Orcamentar",
        data=today_storage(),
        preco_total=o.preco_total,
        ref_cliente=o.ref_cliente,
        enc_phc=o.enc_phc,
        obra=o.obra,
        descricao_orcamento=o.descricao_orcamento,
        localizacao=o.localizacao,
        info_1=o.info_1,
        info_2=o.info_2,
        notas=o.notas,
        extras=o.extras,
        created_by=created_by or o.created_by,
        updated_by=created_by or o.updated_by,
    )
    db.add(dup)
    db.flush()

    dados_gerais_overrides = {
        "ano": o.ano,
        "num_orcamento": o.num_orcamento,
        "versao": new_ver,
        "cliente_id": o.client_id,
    }
    def _dados_gerais_filters(model):
        return [
            model.ano == o.ano,
            model.num_orcamento == o.num_orcamento,
            model.versao == old_ver,
            model.cliente_id == o.client_id,
        ]

    _clone_rows(db, DadosGeraisMaterial, _dados_gerais_filters(DadosGeraisMaterial), dados_gerais_overrides)
    _clone_rows(db, DadosGeraisFerragem, _dados_gerais_filters(DadosGeraisFerragem), dados_gerais_overrides)
    _clone_rows(db, DadosGeraisSistemaCorrer, _dados_gerais_filters(DadosGeraisSistemaCorrer), dados_gerais_overrides)
    _clone_rows(db, DadosGeraisAcabamento, _dados_gerais_filters(DadosGeraisAcabamento), dados_gerais_overrides)

    items = (
        db.query(OrcamentoItem)
        .filter(OrcamentoItem.id_orcamento == o.id, OrcamentoItem.versao == old_ver)
        .order_by(OrcamentoItem.item_ord, OrcamentoItem.id_item)
        .all()
    )
    item_map = {}
    for item in items:
        data = {}
        for col in OrcamentoItem.__table__.columns:
            if col.primary_key:
                continue
            name = col.name
            if name in {"created_at", "updated_at"}:
                continue
            if name == "id_orcamento":
                data[name] = dup.id
            elif name == "versao":
                data[name] = new_ver
            elif name in {"created_by", "updated_by"}:
                data[name] = created_by or getattr(item, name)
            else:
                data[name] = getattr(item, name)
        new_item = OrcamentoItem(**data)
        db.add(new_item)
        db.flush()
        item_map[item.id_item] = new_item.id_item

    for old_item_id, new_item_id in item_map.items():
        _clone_rows(db, DadosModuloMedidas, [DadosModuloMedidas.id_item_fk == old_item_id], {"id_item_fk": new_item_id})
        _clone_rows(db, DadosDefPecas, [DadosDefPecas.id_item_fk == old_item_id], {"id_item_fk": new_item_id})

    item_context_overrides = {
        "orcamento_id": dup.id,
        "versao": new_ver,
        "ano": o.ano,
        "num_orcamento": o.num_orcamento,
        "cliente_id": o.client_id,
    }
    _clone_rows_with_item_map(db, DadosItemsMaterial, item_map, item_context_overrides)
    _clone_rows_with_item_map(db, DadosItemsFerragem, item_map, item_context_overrides)
    _clone_rows_with_item_map(db, DadosItemsSistemaCorrer, item_map, item_context_overrides)
    _clone_rows_with_item_map(db, DadosItemsAcabamento, item_map, item_context_overrides)

    modelos = db.query(DadosItemsModelo).filter(DadosItemsModelo.orcamento_id == o.id).all()
    modelo_map = {}
    for modelo in modelos:
        if modelo.item_id is not None and modelo.item_id not in item_map:
            continue
        data = {}
        for col in DadosItemsModelo.__table__.columns:
            if col.primary_key:
                continue
            name = col.name
            if name in {"created_at", "updated_at"}:
                continue
            if name == "orcamento_id":
                data[name] = dup.id
            elif name == "item_id":
                data[name] = item_map.get(modelo.item_id) if modelo.item_id is not None else None
            else:
                data[name] = getattr(modelo, name)
        new_modelo = DadosItemsModelo(**data)
        db.add(new_modelo)
        db.flush()
        modelo_map[modelo.id] = new_modelo.id
    for old_id, new_id in modelo_map.items():
        _clone_rows(db, DadosItemsModeloItem, [DadosItemsModeloItem.modelo_id == old_id], {"modelo_id": new_id})

    custeio_rows = []
    if item_map:
        custeio_rows = db.query(CusteioItem).filter(
            CusteioItem.orcamento_id == o.id,
            CusteioItem.item_id.in_(item_map.keys()),
            CusteioItem.versao == old_ver,
        ).all()
    custeio_map = {}
    for row in custeio_rows:
        data = {}
        for col in CusteioItem.__table__.columns:
            if col.primary_key:
                continue
            name = col.name
            if name in {"created_at", "updated_at"}:
                continue
            if name == "orcamento_id":
                data[name] = dup.id
            elif name == "item_id":
                data[name] = item_map.get(row.item_id)
            elif name == "versao":
                data[name] = new_ver
            elif name == "ano":
                data[name] = o.ano
            elif name == "num_orcamento":
                data[name] = o.num_orcamento
            elif name == "cliente_id":
                data[name] = o.client_id
            else:
                data[name] = getattr(row, name)
        new_row = CusteioItem(**data)
        db.add(new_row)
        db.flush()
        custeio_map[row.id] = new_row.id

    _clone_rows_with_item_map(db, CusteioItemDimensoes, item_map, item_context_overrides)

    if custeio_map:
        backup_rows = db.query(CusteioDespBackup).filter(
            CusteioDespBackup.orcamento_id == o.id,
            CusteioDespBackup.versao == old_ver,
            CusteioDespBackup.custeio_item_id.in_(custeio_map.keys()),
        ).all()
        for row in backup_rows:
            data = {}
            for col in CusteioDespBackup.__table__.columns:
                if col.primary_key:
                    continue
                name = col.name
                if name in {"created_at", "updated_at"}:
                    continue
                if name == "orcamento_id":
                    data[name] = dup.id
                elif name == "versao":
                    data[name] = new_ver
                elif name == "custeio_item_id":
                    data[name] = custeio_map.get(row.custeio_item_id)
                else:
                    data[name] = getattr(row, name)
            db.add(CusteioDespBackup(**data))
        db.flush()

    configs = db.query(CusteioProducaoConfig).filter(
        CusteioProducaoConfig.orcamento_id == o.id,
        CusteioProducaoConfig.versao == old_ver,
    ).all()
    for cfg in configs:
        data = {}
        for col in CusteioProducaoConfig.__table__.columns:
            if col.primary_key:
                continue
            name = col.name
            if name in {"created_at", "updated_at"}:
                continue
            if name == "orcamento_id":
                data[name] = dup.id
            elif name == "versao":
                data[name] = new_ver
            elif name == "ano":
                data[name] = o.ano
            elif name == "num_orcamento":
                data[name] = o.num_orcamento
            elif name == "cliente_id":
                data[name] = o.client_id
            else:
                data[name] = getattr(cfg, name)
        new_cfg = CusteioProducaoConfig(**data)
        db.add(new_cfg)
        db.flush()
        _clone_rows(
            db,
            CusteioProducaoValor,
            [CusteioProducaoValor.config_id == cfg.id],
            {"config_id": new_cfg.id},
        )

    return dup


def _normalize_search_text(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    txt = unicodedata.normalize("NFKD", raw)
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = txt.casefold()
    txt = re.sub(r"[^0-9a-z]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _uniq_search_terms(terms: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for term in terms:
        token = (term or "").strip()
        if not token:
            continue
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(token)
    return out


def _split_terms_percent(query: str) -> list[str]:
    return _uniq_search_terms([term.strip() for term in str(query or "").split("%") if term.strip()])


def _split_terms_raw(query: str) -> list[str]:
    if not (query or "").strip():
        return []
    cleaned = str(query).replace("%", " ").strip()
    parts = [part.strip(".,;:!?'\"()[]{}<>") for part in cleaned.split()]
    return _uniq_search_terms([part for part in parts if part])


def _split_terms_normalized(query: str) -> list[str]:
    norm = _normalize_search_text(query or "")
    return _uniq_search_terms(norm.split()) if norm else []


def _term_alternatives(term: str, *, expand: bool) -> tuple[str, ...]:
    alternatives = [str(term or "").strip()]
    if expand:
        norm = _normalize_search_text(term)
        if norm and norm not in {alt.casefold() for alt in alternatives}:
            alternatives.append(norm)
        alternatives.extend(_SEARCH_SYNONYMS_ORCAMENTOS.get(norm, ()))
    return tuple(_uniq_search_terms(alternatives))


def _item_search_exists(term: str):
    like = f"%{term}%"
    return (
        select(OrcamentoItem.id_item)
        .where(
            OrcamentoItem.id_orcamento == Orcamento.id,
            OrcamentoItem.versao == Orcamento.versao,
            or_(*[field.ilike(like) for field in _SEARCH_FIELDS_ORCAMENTO_ITEMS]),
        )
        .correlate(Orcamento)
        .exists()
    )


def _build_search_filters_orcamentos(
    terms: Sequence[str],
    *,
    expand: bool = False,
    include_items: bool = False,
):
    filters = []
    for term in terms:
        term_filters = []
        for alternative in _term_alternatives(term, expand=expand):
            like = f"%{alternative}%"
            term_filters.extend(field.ilike(like) for field in _SEARCH_FIELDS_ORCAMENTOS)
            if include_items:
                term_filters.append(_item_search_exists(alternative))
        if term_filters:
            filters.append(or_(*term_filters))
    return filters


def _orcamento_blob(row: OrcamentoResumo) -> str:
    parts = []
    for attr in (
        "id",
        "ano",
        "num_orcamento",
        "versao",
        "enc_phc",
        "cliente",
        "temp_client_nome",
        "data",
        "preco",
        "utilizador",
        "estado",
        "obra",
        "descricao",
        "localizacao",
        "info_1",
        "info_2",
        "ref_cliente",
    ):
        value = getattr(row, attr, None)
        if value in (None, ""):
            continue
        parts.append(str(value))
    return " | ".join(parts)


def _item_blobs_for_orcamentos(db: Session, rows: Sequence[OrcamentoResumo]) -> dict[int, str]:
    ids = [int(row.id) for row in rows if getattr(row, "id", None) is not None]
    if not ids:
        return {}
    stmt = select(
        OrcamentoItem.id_orcamento,
        OrcamentoItem.item,
        OrcamentoItem.codigo,
        OrcamentoItem.descricao,
        OrcamentoItem.notas,
        cast(OrcamentoItem.altura, String),
        cast(OrcamentoItem.largura, String),
        cast(OrcamentoItem.profundidade, String),
        OrcamentoItem.und,
    ).where(OrcamentoItem.id_orcamento.in_(ids))
    item_blobs: dict[int, list[str]] = {}
    for row in db.execute(stmt).all():
        parts = [
            str(value)
            for value in row[1:]
            if value not in (None, "")
        ]
        if not parts:
            continue
        item_blobs.setdefault(int(row.id_orcamento), []).append(" | ".join(parts))
    return {oid: " || ".join(parts) for oid, parts in item_blobs.items()}


def _expanded_normalized_terms(term_norm: str) -> list[str]:
    terms = [term_norm]
    terms.extend(_SEARCH_SYNONYMS_ORCAMENTOS.get(term_norm, ()))
    return _uniq_search_terms([_normalize_search_text(term) for term in terms if term])


def _score_term_in_text(term_norm: str, text_norm: str) -> tuple[float, str, str]:
    if not term_norm or not text_norm:
        return 0.0, "", ""
    alternatives = _expanded_normalized_terms(term_norm)
    for alt in alternatives:
        if alt and alt in text_norm:
            if alt == term_norm:
                return 1.0, "direct", alt
            return 0.9, "synonym", alt
    if len(term_norm) < 4:
        return 0.0, "", ""
    close = difflib.get_close_matches(term_norm, set(text_norm.split()), n=1, cutoff=0.84)
    if not close:
        return 0.0, "", ""
    ratio = difflib.SequenceMatcher(None, term_norm, close[0]).ratio()
    return ratio * 0.72, "fuzzy", close[0]


def _build_search_reason(label: str, term_norm: str, kind: str, matched: str) -> str:
    if kind == "synonym":
        return f"Encontrado por sinonimo: {term_norm} -> {matched} ({label})"
    if kind == "fuzzy":
        return f"Encontrado por aproximacao: {term_norm} ~ {matched} ({label})"
    return f"Encontrado em: {label}"


def _rank_orcamento_rows(
    db: Session,
    rows: Sequence[OrcamentoResumo],
    query: str,
    *,
    item_blobs: Optional[dict[int, str]] = None,
) -> List[OrcamentoResumo]:
    rows_list = list(rows)
    terms_norm = _split_terms_normalized(query)
    if not rows_list or not terms_norm:
        return rows_list
    item_blobs = item_blobs if item_blobs is not None else _item_blobs_for_orcamentos(db, rows_list)

    ranked: list[tuple[float, str, str, str, OrcamentoResumo]] = []
    for row in rows_list:
        sections = (
            ("Referencia", 8.0, f"{row.num_orcamento} {row.enc_phc} {row.ref_cliente} {row.ano} {row.versao}"),
            ("Cliente", 7.0, f"{row.cliente} {row.temp_client_nome}"),
            ("Obra", 6.0, row.obra),
            ("Descricao", 5.0, row.descricao),
            ("Item", 4.5, item_blobs.get(int(row.id), "")),
            ("Info/Localizacao", 3.0, f"{row.info_1} {row.info_2} {row.localizacao}"),
            ("Estado/Utilizador/Data", 2.0, f"{row.estado} {row.utilizador} {row.data}"),
        )
        score = 0.0
        best_reason = ""
        best_reason_score = 0.0
        for term_norm in terms_norm:
            best_term_score = 0.0
            best_term_reason = ""
            for label, weight, text_value in sections:
                match_score, match_kind, matched = _score_term_in_text(term_norm, _normalize_search_text(text_value))
                if match_score <= 0:
                    continue
                weighted = weight * match_score
                if weighted > best_term_score:
                    best_term_score = weighted
                    best_term_reason = _build_search_reason(label, term_norm, match_kind, matched)
            score += best_term_score
            if best_term_score > best_reason_score:
                best_reason_score = best_term_score
                best_reason = best_term_reason

        row.search_score = float(score)
        row.search_reason = best_reason
        ranked.append((float(score), str(row.ano), str(row.num_orcamento), str(row.versao), row))

    ranked.sort(key=lambda item: item[:4], reverse=True)
    return [row for _, _, _, _, row in ranked]


def _fuzzy_match_blob(blob_norm: str, *, terms_norm: Sequence[str]) -> Optional[float]:
    if not terms_norm:
        return 0.0
    if not blob_norm:
        return None
    words = set(blob_norm.split())
    score = 0.0
    for term in terms_norm:
        if term in blob_norm:
            score += 1.0
            continue
        alternatives = _SEARCH_SYNONYMS_ORCAMENTOS.get(term, ())
        if any(alt in blob_norm for alt in alternatives):
            score += 0.95
            continue
        if len(term) < 4:
            return None
        close = difflib.get_close_matches(term, words, n=1, cutoff=0.82)
        if not close:
            return None
        score += difflib.SequenceMatcher(None, term, close[0]).ratio()
    return score


def _fuzzy_search_orcamentos(db: Session, query: str) -> List[OrcamentoResumo]:
    terms_norm = _split_terms_normalized(query)
    stmt = (
        _select_orcamentos()
        .order_by(Orcamento.ano.desc(), Orcamento.num_orcamento.desc(), Orcamento.versao)
        .limit(ORCAMENTO_FUZZY_CANDIDATE_LIMIT)
    )
    candidates = _rows_from_stmt(db, stmt)
    item_blobs = _item_blobs_for_orcamentos(db, candidates)
    scored: list[tuple[float, OrcamentoResumo]] = []
    for row in candidates:
        blob = f"{_orcamento_blob(row)} | {item_blobs.get(int(row.id), '')}"
        score = _fuzzy_match_blob(_normalize_search_text(blob), terms_norm=terms_norm)
        if score is None:
            continue
        scored.append((float(score), row))
    scored.sort(key=lambda item: (item[0], str(item[1].ano), str(item[1].num_orcamento), str(item[1].versao)), reverse=True)
    fuzzy_scores = {int(getattr(row, "id", 0) or 0): float(score) for score, row in scored}
    ranked_rows = _rank_orcamento_rows(db, [row for _, row in scored], query, item_blobs=item_blobs)
    for row in ranked_rows:
        row_id = int(getattr(row, "id", 0) or 0)
        row.search_score = max(float(getattr(row, "search_score", 0.0) or 0.0), fuzzy_scores.get(row_id, 0.0))
        if not row.search_reason:
            row.search_reason = "Encontrado por aproximacao"
    ranked_rows.sort(key=lambda row: (float(getattr(row, "search_score", 0.0) or 0.0), str(row.ano), str(row.num_orcamento), str(row.versao)), reverse=True)
    return ranked_rows


def search_orcamentos(db: Session, query: str, *, approx: bool = True) -> List[OrcamentoResumo]:
    if not (query or "").strip():
        return list_orcamentos(db)

    def _run_sql(
        terms: Sequence[str],
        *,
        expand: bool = False,
        include_items: bool = False,
    ) -> List[OrcamentoResumo]:
        filters = _build_search_filters_orcamentos(terms, expand=expand, include_items=include_items)
        if not filters:
            return []
        stmt = _select_orcamentos().where(*filters)
        stmt = stmt.order_by(Orcamento.ano.desc(), Orcamento.num_orcamento.desc(), Orcamento.versao)
        return _rank_orcamento_rows(db, _rows_from_stmt(db, stmt), query)

    # 1) comportamento antigo: multi-termos apenas por '%'.
    legacy_terms = _split_terms_percent(query)
    if not legacy_terms:
        return list_orcamentos(db)
    rows = _run_sql(legacy_terms)
    if rows:
        return rows

    # 2) pesquisa natural: '%' e espaco como separadores de multi-termos.
    raw_terms = _split_terms_raw(query)
    if raw_terms and raw_terms != legacy_terms:
        rows = _run_sql(raw_terms)
        if rows:
            return rows

    # 3) expansao leve: texto sem acentos/pontuacao e sinonimos do dominio.
    search_terms = raw_terms or legacy_terms
    rows = _run_sql(search_terms, expand=True)
    if rows:
        return rows

    rows = _run_sql(search_terms, expand=True, include_items=True)
    if rows:
        return rows

    norm_terms = _split_terms_normalized(query)
    if norm_terms and norm_terms != search_terms:
        rows = _run_sql(norm_terms, expand=True)
        if rows:
            return rows
        rows = _run_sql(norm_terms, expand=True, include_items=True)
        if rows:
            return rows

    if not approx:
        return []

    # 4) fallback aproximado em memoria sobre os orcamentos mais recentes.
    return _fuzzy_search_orcamentos(db, query)

