from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_
from ..models import Orcamento, OrcamentoItem, Client
import datetime


def list_orcamentos(db: Session) -> List[Orcamento]:
    return db.execute(select(Orcamento).order_by(Orcamento.ano.desc(), Orcamento.num_orcamento, Orcamento.versao)).scalars().all()


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
    created_by: Optional[int] = None,
) -> Orcamento:
    versao = f"{int(versao):02d}" if versao and versao.isdigit() else (versao if versao else "01")
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


def list_items(db: Session, orc_id: int) -> List[OrcamentoItem]:
    return db.execute(
        select(OrcamentoItem).where(OrcamentoItem.id_orcamento == orc_id).order_by(OrcamentoItem.item_ord)
    ).scalars().all()


def _next_item_ord(db: Session, orc_id: int) -> int:
    q = db.execute(select(func.max(OrcamentoItem.item_ord)).where(OrcamentoItem.id_orcamento == orc_id)).scalar()
    return int(q or 0) + 1


def create_item(db: Session, orc_id: int, *, codigo: str = "", descricao: str = "") -> OrcamentoItem:
    item = OrcamentoItem(
        id_orcamento=orc_id,
        item_ord=_next_item_ord(db, orc_id),
        codigo=codigo.upper() if codigo else None,
        descricao=descricao or None,
        und="und",
        qt=1,
    )
    db.add(item)
    db.flush()
    return item


def delete_item(db: Session, id_item: int) -> None:
    it = db.get(OrcamentoItem, id_item)
    if not it:
        return
    db.delete(it)


def move_item(db: Session, id_item: int, direction: int) -> None:
    it = db.get(OrcamentoItem, id_item)
    if not it:
        return
    # encontra vizinho
    if direction > 0:
        neighbor = db.execute(
            select(OrcamentoItem)
            .where(OrcamentoItem.id_orcamento == it.id_orcamento, OrcamentoItem.item_ord > it.item_ord)
            .order_by(OrcamentoItem.item_ord.asc())
            .limit(1)
        ).scalar_one_or_none()
    else:
        neighbor = db.execute(
            select(OrcamentoItem)
            .where(OrcamentoItem.id_orcamento == it.id_orcamento, OrcamentoItem.item_ord < it.item_ord)
            .order_by(OrcamentoItem.item_ord.desc())
            .limit(1)
        ).scalar_one_or_none()
    if not neighbor:
        return
    it.item_ord, neighbor.item_ord = neighbor.item_ord, it.item_ord


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
    """Devolve apenas a parte sequencial de 4 dígitos para o ano indicado."""
    full = next_num_orcamento(db, ano)
    return full[2:6]


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


def duplicate_orcamento_version(db: Session, orc_id: int) -> Orcamento:
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
    )
    db.add(dup)
    db.flush()
    # TODO: duplicar itens e filhos numa próxima etapa
    return dup


def search_orcamentos(db: Session, query: str) -> List[Orcamento]:
    if not (query or "").strip():
        return list_orcamentos(db)
    terms = [t.strip() for t in query.split('%') if t.strip()]
    if not terms:
        return list_orcamentos(db)
    # Join leve com clients para procurar por nome
    stmt = select(Orcamento).join(Client, Orcamento.client_id == Client.id)
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
    return db.execute(stmt).scalars().all()
