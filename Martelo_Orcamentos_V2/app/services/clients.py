from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, func
from ..models import Client
import difflib
import re
import unicodedata

from . import phc_sql as svc_phc


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


def _none_if_empty(value: object) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _simplex_from_nome(nome: str) -> str:
    """
    Gera um nome simplex a partir do NOME do PHC:
    - remove acentos/pontuação
    - substitui separadores por '_'
    - usa 10 primeiros caracteres e '...' se truncado

    Ex.: "ANDRÉ SANTOS RIBEIRO" -> "ANDRE_SANT..."
    """
    base = unicodedata.normalize("NFKD", nome or "")
    base = "".join(ch for ch in base if not unicodedata.combining(ch))
    base = re.sub(r"[^A-Za-z0-9]+", "_", base)
    base = re.sub(r"_+", "_", base).strip("_").upper()
    if not base:
        return "CLIENTE"
    if len(base) <= 10:
        return base
    return base[:10] + "..."


def _normalize_simplex_value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def phc_simplex_is_missing(value: object) -> bool:
    simplex = _normalize_simplex_value(value)
    return (not simplex) or simplex.endswith("...")


def phc_simplex_has_unjoined_words(value: object) -> bool:
    simplex = _normalize_simplex_value(value)
    return len(simplex.split()) >= 2


def phc_simplex_validation_issue(
    *,
    cliente_nome: str,
    num_phc: Optional[str],
    simplex: object,
    action_label: str = "continuar",
) -> Optional[tuple[str, str]]:
    cliente_label = _normalize_simplex_value(cliente_nome) or "Cliente"
    num_phc_label = _normalize_simplex_value(num_phc) or "n/d"
    simplex_label = _normalize_simplex_value(simplex)

    if phc_simplex_is_missing(simplex_label):
        return (
            "Abreviado (PHC) em falta",
            "O nome cliente 'Simplex' do Martelo termina em '...' (ou esta vazio), o que indica que no PHC o campo "
            "'Abreviatura' nao esta preenchido/sincronizado.\n\n"
            f"Antes de {action_label}:\n"
            "1) No PHC, preencha o campo 'Abreviatura' do cliente.\n"
            "2) No Martelo, va a Clientes e clique em 'Atualizar PHC'.\n\n"
            f"Cliente: {cliente_label} (PHC: {num_phc_label})\n"
            f"Simplex atual: {simplex_label or '(vazio)'}\n\n"
            "Depois volte e tente novamente.",
        )

    if phc_simplex_has_unjoined_words(simplex_label):
        return (
            "Abreviado (PHC) invalido",
            "O campo 'Abreviatura' do cliente no PHC contem 2 ou mais palavras separadas por espacos.\n\n"
            "Atualize esse campo no PHC usando '_' para unir as palavras (ex.: ALEXANDRE_CASAIS).\n\n"
            f"Antes de {action_label}:\n"
            "1) No PHC, atualize o campo 'Abreviatura' do cliente.\n"
            "2) No Martelo, va a Clientes e clique em 'Atualizar PHC'.\n\n"
            f"Cliente: {cliente_label} (PHC: {num_phc_label})\n"
            f"Abreviatura atual no PHC: {simplex_label}\n\n"
            "Depois volte e tente novamente.",
        )

    return None


def sync_clients_from_phc(db: Session) -> dict:
    """
    Sincroniza a tabela `clients` do Martelo a partir do PHC (dbo.CL).

    NOTA: o acesso ao PHC é apenas leitura (SELECT). As escritas são apenas no Martelo (MySQL).
    """
    rows = svc_phc.query_phc_clients(db)
    if not rows:
        return {"total_phc": 0, "created": 0, "updated": 0, "skipped": 0}

    # Index por Num_PHC para reduzir roundtrips
    nums: List[str] = []
    for r in rows:
        num = _none_if_empty(r.get("Num_PHC")) if isinstance(r, dict) else None
        if num:
            nums.append(num)
    unique_nums = sorted(set(nums))

    existing_by_num: dict[str, Client] = {}
    if unique_nums:
        existing = db.execute(select(Client).where(Client.num_cliente_phc.in_(unique_nums))).scalars().all()
        for c in existing:
            key = (c.num_cliente_phc or "").strip()
            if key:
                existing_by_num[key] = c

    created = 0
    updated = 0
    skipped = 0

    for r in rows:
        if not isinstance(r, dict):
            skipped += 1
            continue
        num = _none_if_empty(r.get("Num_PHC"))
        nome = _none_if_empty(r.get("Nome"))
        if not num or not nome:
            skipped += 1
            continue

        client = existing_by_num.get(num)
        is_new = False
        if client is None:
            client = Client()
            db.add(client)
            client.num_cliente_phc = num
            existing_by_num[num] = client
            created += 1
            is_new = True

        client.nome = nome

        simplex_raw = _none_if_empty(r.get("Simplex"))
        if simplex_raw:
            client.nome_simplex = simplex_raw.upper().replace(" ", "_")
        else:
            # Muitos clientes no PHC não têm NOME2 preenchido; criar um simplex curto para indicar que deve ser corrigido no PHC.
            fallback = _simplex_from_nome(nome)
            current = (client.nome_simplex or "").strip()
            old_fallback_full = nome.upper().replace(" ", "_")
            if (not current) or current == old_fallback_full or current.endswith("..."):
                client.nome_simplex = fallback

        client.morada = _none_if_empty(r.get("Morada"))
        client.email = _none_if_empty(r.get("Email"))
        client.web_page = _none_if_empty(r.get("WEB"))
        client.telemovel = _none_if_empty(r.get("Telemovel"))
        client.telefone = _none_if_empty(r.get("Telefone"))
        client.info_1 = _none_if_empty(r.get("Info_1"))

        if not is_new:
            updated += 1

    db.flush()
    return {"total_phc": len(rows), "created": created, "updated": updated, "skipped": skipped}
