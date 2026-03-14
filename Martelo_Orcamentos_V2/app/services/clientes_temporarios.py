from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, func
import difflib

from ..models import ClienteTemporario


SEARCH_FIELDS = (
    ClienteTemporario.nome,
    ClienteTemporario.nome_simplex,
    ClienteTemporario.morada,
    ClienteTemporario.email,
    ClienteTemporario.web_page,
    ClienteTemporario.telefone,
    ClienteTemporario.telemovel,
    ClienteTemporario.num_cliente_phc,
    ClienteTemporario.info_1,
    ClienteTemporario.info_2,
)


def list_clientes_temporarios(db: Session) -> List[ClienteTemporario]:
    return db.execute(
        select(ClienteTemporario).order_by(ClienteTemporario.nome.asc())
    ).scalars().all()


def search_clientes_temporarios(db: Session, query: str) -> List[ClienteTemporario]:
    if not (query or "").strip():
        return list_clientes_temporarios(db)
    terms = [t.strip() for t in query.split('%') if t.strip()]
    if not terms:
        return list_clientes_temporarios(db)
    filters = []
    for t in terms:
        tlike = f"%{t}%"
        filters.append(or_(*[f.ilike(tlike) for f in SEARCH_FIELDS]))
    stmt = select(ClienteTemporario).where(*filters).order_by(ClienteTemporario.nome.asc())
    results = db.execute(stmt).scalars().all()
    if not results and len(terms) == 1:
        all_names = [c.nome for c in list_clientes_temporarios(db)]
        close = difflib.get_close_matches(terms[0], all_names, n=10, cutoff=0.6)
        if close:
            stmt2 = select(ClienteTemporario).where(ClienteTemporario.nome.in_(close))
            return db.execute(stmt2).scalars().all()
    return results


def get_cliente_temporario(db: Session, cid: int) -> Optional[ClienteTemporario]:
    return db.get(ClienteTemporario, cid)


def get_cliente_temporario_por_nome(db: Session, nome: str) -> Optional[ClienteTemporario]:
    nome_txt = (nome or "").strip()
    if not nome_txt:
        return None
    stmt = select(ClienteTemporario).where(func.lower(ClienteTemporario.nome) == nome_txt.casefold())
    found = db.execute(stmt).scalar_one_or_none()
    if found:
        return found
    return db.execute(
        select(ClienteTemporario).where(func.lower(ClienteTemporario.nome_simplex) == nome_txt.casefold())
    ).scalar_one_or_none()


def upsert_cliente_temporario(
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
    notas: Optional[str] = None,
) -> ClienteTemporario:
    if id:
        c = db.get(ClienteTemporario, id)
        if not c:
            raise ValueError("Cliente temporario nao encontrado")
    else:
        c = ClienteTemporario()
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
    c.notas = notas
    db.flush()
    return c


def delete_cliente_temporario(db: Session, cid: int) -> None:
    c = db.get(ClienteTemporario, cid)
    if not c:
        return
    db.delete(c)


def suggestion_tokens(db: Session) -> List[str]:
    rows = list_clientes_temporarios(db)
    tokens = set()
    for c in rows:
        for s in [c.nome, c.nome_simplex, c.email, c.morada, c.web_page]:
            if not s:
                continue
            for t in str(s).replace(',', ' ').replace(';', ' ').split():
                if t and len(t) > 1:
                    tokens.add(t)
    return sorted(tokens)
