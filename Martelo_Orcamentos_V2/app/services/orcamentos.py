from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..models import Orcamento, OrcamentoItem, Client


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


def create_orcamento(db: Session, *, ano: str, num_orcamento: str, versao: str = "00", cliente_nome: str = "") -> Orcamento:
    versao = f"{int(versao):02d}" if versao and versao.isdigit() else (versao if versao else "00")
    cli = ensure_client(db, cliente_nome)
    o = Orcamento(ano=str(ano), num_orcamento=str(num_orcamento), versao=versao, client_id=cli.id)
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

