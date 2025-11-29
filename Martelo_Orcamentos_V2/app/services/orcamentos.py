import datetime
import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from ..models import (
    Orcamento,
    OrcamentoItem,
    Client,
    User,
    CusteioItem,
    CusteioItemDimensoes,
    DadosModuloMedidas,
    DadosDefPecas,
    DadosItemsMaterial,
    DadosItemsFerragem,
    DadosItemsSistemaCorrer,
    DadosItemsAcabamento,
    DadosItemsModelo,
    DadosItemsModeloItem,
)

logger = logging.getLogger(__name__)


@dataclass
class OrcamentoResumo:
    id: int
    ano: str
    num_orcamento: str
    versao: str
    cliente: str
    data: str
    preco: str
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


DECIMAL_ZERO = Decimal("0")
DECIMAL_ONE = Decimal("1")



def _select_orcamentos():
    return (
        select(
            Orcamento.id.label("id"),
            Orcamento.ano.label("ano"),
            Orcamento.num_orcamento.label("num_orcamento"),
            Orcamento.versao.label("versao"),
            Client.nome_simplex.label("cliente_simplex"),
            Client.nome.label("cliente_nome"),
            Orcamento.data.label("data"),
            Orcamento.preco_total.label("preco_total"),
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
    parsed: List[OrcamentoResumo] = []
    for row in rows:
        cliente = row.cliente_simplex or row.cliente_nome or ""
        parsed.append(
            OrcamentoResumo(
                id=row.id,
                ano=str(row.ano or ""),
                num_orcamento=str(row.num_orcamento or ""),
                versao=_format_versao(row.versao),
                cliente=cliente,
                data=row.data or "",
                preco=_format_preco(row.preco_total),
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
        Orcamento.ano.desc(), Orcamento.num_orcamento, Orcamento.versao
    )
    return _rows_from_stmt(db, stmt)


def get_orcamento(db: Session, orc_id: int) -> Optional[Orcamento]:
    return db.get(Orcamento, orc_id)


def ensure_client(db: Session, nome: str) -> Client:
    nome = (nome or "Cliente Genérico").strip() or "Cliente Genérico"
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
            raise ValueError("Cliente não encontrado")
    else:
        cli = ensure_client(db, cliente_nome)
    o = Orcamento(
        ano=str(ano),
        num_orcamento=str(num_orcamento),
        versao=versao,
        client_id=cli.id,
        data=datetime.datetime.now().strftime("%Y-%m-%d"),
        status="Falta Orçamentar",
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
    # já existe no ficheiro, deixo aqui por referência
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
    versao: str,              # ✔ versão obrigatória
    *,
    item: Optional[str] = None,     # ✔ nome visível do item
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
    Cria um novo item associado ao orçamento.
    - 'item' é preenchido automaticamente com a próxima sequência (1, 2, 3, ...)
      se o utilizador não indicar um nome.
    - 'item_ord' é a ordem visual (1..N) e acompanha a sequência.
    """

    # Normaliza versão para '01', '02', ...
    versao_norm = _format_versao(versao)

    # Próxima ordem/sequência dentro do orçamento (por id_orcamento)
    prox_ord = _next_item_ord(db, orc_id)

    # Se o utilizador não escreveu nome, usamos a sequência como texto
    item_val = _normalize_text(item) if item is not None else str(prox_ord)

    # Constrói a entidade ORM
    row = OrcamentoItem(
        id_orcamento=orc_id,
        versao=versao_norm,                 # ✔ agora o modelo aceita 'versao'
        item_ord=prox_ord,
        item=item_val,                      # ✔ atributo 'item' no ORM (não 'item_nome')
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
    versao: Optional[str] = None,         # ✅ Agora podemos atualizar a versão
    item: Optional[str] = None,           # ✅ Nome do item alinhado com a coluna da BD
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

    # 🔎 Buscar item no BD
    it = db.get(OrcamentoItem, id_item)
    if not it:
        raise ValueError("Item não encontrado")

    # ✅ Atualizar versão se fornecida
    if versao is not None:
        it.versao = _format_versao(versao)

    # ✅ Atualizar os restantes campos
    it.item = _normalize_text(item)   # ✅ Corrigido: usar 'item' em vez de 'item_nome'
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


def duplicate_item(db: Session, item_id: int, *, created_by: Optional[int] = None) -> OrcamentoItem:
    """
    Duplica um item do orçamento (e dependências diretas) no mesmo orçamento/versão.
    """
    src = db.get(OrcamentoItem, item_id)
    if not src:
        raise ValueError("Item não encontrado.")

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
    # encontrar maior sequencia começando por YY
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

    # Devolve apenas a parte sequencial com zero à esquerda
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
        raise ValueError("Orçamento não encontrado")
    new_ver = next_version_for(db, o.ano, o.num_orcamento)
    dup = Orcamento(
        ano=o.ano,
        num_orcamento=o.num_orcamento,
        versao=new_ver,
        client_id=o.client_id,
        status=o.status,
        data=datetime.datetime.now().strftime("%Y-%m-%d"),
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
        created_by=o.created_by,
    )
    db.add(dup)
    db.flush()
    # TODO: duplicar itens e filhos numa próxima etapa
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
    stmt = stmt.order_by(Orcamento.ano.desc(), Orcamento.num_orcamento, Orcamento.versao)
    return _rows_from_stmt(db, stmt)
