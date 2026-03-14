import datetime
import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, func, and_, or_
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
        preco_manual = bool(extras.get(PRECO_MANUAL_KEY)) if isinstance(extras, dict) else False
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
                preco_manual=preco_manual,
                preco_total_manual=getattr(row, "preco_total_manual", 0) or 0,
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
        "Item '%s' (ID=%s) removido do orcamento %s por utilizador %s",
        item_nome,
        id_item,
        orc_id,
        deleted_by,
    )

    db.delete(it)
    db.flush()

    # Reorganizar ordenacao/numeracao dos restantes itens da mesma versao
    _reindex_items(db, orc_id, versao=versao, updated_by=deleted_by)
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


def search_orcamentos(db: Session, query: str) -> List[OrcamentoResumo]:
    if not (query or "").strip():
        return list_orcamentos(db)
    terms = [t.strip() for t in query.split('%') if t.strip()]
    if not terms:
        return list_orcamentos(db)
    # Join leve com clients para procurar por nome
    stmt = _select_orcamentos()
    for t in terms:
        like = f"%{t}%"
        stmt = stmt.where(
            or_(
                Orcamento.num_orcamento.ilike(like),
                Orcamento.ano.ilike(like),
                Orcamento.versao.ilike(like),
                Orcamento.status.ilike(like),
                Orcamento.ref_cliente.ilike(like),
                Orcamento.obra.ilike(like),
                Orcamento.descricao_orcamento.ilike(like),
                Orcamento.localizacao.ilike(like),
                Orcamento.info_1.ilike(like),
                Orcamento.info_2.ilike(like),
                Client.nome.ilike(like),
                Client.nome_simplex.ilike(like),
            )
        )
    stmt = stmt.order_by(Orcamento.ano.desc(), Orcamento.num_orcamento.desc(), Orcamento.versao)
    return _rows_from_stmt(db, stmt)

