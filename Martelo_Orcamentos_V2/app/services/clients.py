from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, func
from ..models import Client
import difflib


SEARCH_FIELDS = (
    Client.nome,
    Client.nome_simplex,
    Client.morada,
    Client.email,
    Client.web_page,
    Client.telefone,
    Client.telemovel,
    Client.num_cliente_phc,
    Client.info_1,
    Client.info_2,
)


def list_clients(db: Session) -> List[Client]:
    return db.execute(
        select(Client).order_by(Client.nome.asc())
    ).scalars().all()


def search_clients(db: Session, query: str) -> List[Client]:
    if not (query or "").strip():
        return list_clients(db)
    # Suporta multi-termo com separador '%', case-insensitive, substring
    terms = [t.strip() for t in query.split('%') if t.strip()]
    if not terms:
        return list_clients(db)
    filters = []
    for t in terms:
        tlike = f"%{t}%"
        filters.append(or_(*[f.ilike(tlike) for f in SEARCH_FIELDS]))
    stmt = select(Client).where(*filters).order_by(Client.nome.asc())
    results = db.execute(stmt).scalars().all()
    # Pequena ajuda de similaridade: se poucos resultados, tentar aproximação por nome
    if not results and len(terms) == 1:
        all_names = [c.nome for c in list_clients(db)]
        close = difflib.get_close_matches(terms[0], all_names, n=10, cutoff=0.6)
        if close:
            stmt2 = select(Client).where(Client.nome.in_(close))
            return db.execute(stmt2).scalars().all()
    return results


def get_client(db: Session, cid: int) -> Optional[Client]:
    return db.get(Client, cid)


def upsert_client(
    db: Session,
    *,
    id: Optional[int] = None,
    nome: str,
    nome_simplex: Optional[str] = None,
    morada: Optional[str] = None,
    email: Optional[str] = None,
    web_page: Optional[str] = None,
    telefone: Optional[str] = None,
    telemovel: Optional[str] = None,
    num_cliente_phc: Optional[str] = None,
    info_1: Optional[str] = None,
    info_2: Optional[str] = None,
) -> Client:
    if id:
        c = db.get(Client, id)
        if not c:
            raise ValueError("Cliente não encontrado")
    else:
        c = Client()
        db.add(c)
    c.nome = (nome or "").strip()
    c.nome_simplex = ((nome_simplex or c.nome).strip() or c.nome).upper().replace(" ", "_")
    c.morada = morada
    c.email = (email or "").strip() or None
    c.web_page = (web_page or "").strip() or None
    c.telefone = (telefone or "").strip() or None
    c.telemovel = (telemovel or "").strip() or None
    c.num_cliente_phc = (num_cliente_phc or "").strip() or None
    c.info_1 = info_1
    c.info_2 = info_2
    db.flush()
    return c


def delete_client(db: Session, cid: int) -> None:
    c = db.get(Client, cid)
    if not c:
        return
    db.delete(c)


def suggestion_tokens(db: Session) -> List[str]:
    # Gera tokens únicos de nomes / simplex / email para o QCompleter
    rows = list_clients(db)
    tokens = set()
    for c in rows:
        for s in [c.nome, c.nome_simplex, c.email, c.morada, c.web_page]:
            if not s:
                continue
            for t in str(s).replace(',', ' ').replace(';', ' ').split():
                if t and len(t) > 1:
                    tokens.add(t)
    return sorted(tokens)
