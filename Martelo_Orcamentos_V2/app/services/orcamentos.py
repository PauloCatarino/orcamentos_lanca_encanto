from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_
from ..models import Orcamento, OrcamentoItem, Client, User
import datetime
import re


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
