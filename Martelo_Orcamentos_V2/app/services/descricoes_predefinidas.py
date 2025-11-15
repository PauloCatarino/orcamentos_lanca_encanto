from typing import Iterable, List, Optional, Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models.descricao_predefinida import DescricaoPredefinida

VALID_TYPES = {"-", "*"}


def _normalize_tipo(tipo: Optional[str]) -> str:
    if not tipo:
        return "-"
    tipo = str(tipo).strip()[:1]
    if tipo not in VALID_TYPES:
        return "-"
    return tipo


def list_descricoes(db: Session, user_id: int, termos: Optional[Iterable[str]] = None) -> List[DescricaoPredefinida]:
    if not user_id:
        return []
    stmt = (
        select(DescricaoPredefinida)
        .where(DescricaoPredefinida.user_id == user_id)
        .order_by(DescricaoPredefinida.ordem.asc(), DescricaoPredefinida.id.asc())
    )
    termos = [t.strip() for t in (termos or []) if t and t.strip()]
    for termo in termos:
        like = f"%{termo}%"
        stmt = stmt.where(DescricaoPredefinida.texto.ilike(like))
    return list(db.execute(stmt).scalars().all())


def create_descricao(db: Session, user_id: int, texto: str, tipo: str = "-") -> DescricaoPredefinida:
    if not user_id:
        raise ValueError("Utilizador inválido para criar descrição.")
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Texto da descrição não pode ser vazio.")
    tipo_norm = _normalize_tipo(tipo)
    max_ordem = db.execute(
        select(func.max(DescricaoPredefinida.ordem)).where(DescricaoPredefinida.user_id == user_id)
    ).scalar() or 0
    row = DescricaoPredefinida(
        user_id=user_id,
        texto=texto,
        tipo=tipo_norm,
        ordem=max_ordem + 1,
    )
    db.add(row)
    db.flush()
    return row


def update_descricao(db: Session, row_id: int, user_id: int, texto: str, tipo: str = "-") -> DescricaoPredefinida:
    row = db.get(DescricaoPredefinida, row_id)
    if not row or row.user_id != user_id:
        raise ValueError("Descrição não encontrada.")
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Texto da descrição não pode ser vazio.")
    row.texto = texto
    row.tipo = _normalize_tipo(tipo)
    db.flush()
    return row


def delete_descricoes(db: Session, user_id: int, ids: Sequence[int]) -> int:
    if not ids:
        return 0
    stmt = select(DescricaoPredefinida).where(
        and_(DescricaoPredefinida.user_id == user_id, DescricaoPredefinida.id.in_(list(ids)))
    )
    rows = list(db.execute(stmt).scalars().all())
    for row in rows:
        db.delete(row)
    if rows:
        _reordenar(db, user_id)
    db.flush()
    return len(rows)


def move_descricao(db: Session, row_id: int, user_id: int, direction: str) -> bool:
    if direction not in {"up", "down"}:
        return False
    row = db.get(DescricaoPredefinida, row_id)
    if not row or row.user_id != user_id:
        return False
    if direction == "up":
        stmt = (
            select(DescricaoPredefinida)
            .where(
                and_(
                    DescricaoPredefinida.user_id == user_id,
                    DescricaoPredefinida.ordem < row.ordem,
                )
            )
            .order_by(DescricaoPredefinida.ordem.desc())
            .limit(1)
        )
    else:
        stmt = (
            select(DescricaoPredefinida)
            .where(
                and_(
                    DescricaoPredefinida.user_id == user_id,
                    DescricaoPredefinida.ordem > row.ordem,
                )
            )
            .order_by(DescricaoPredefinida.ordem.asc())
            .limit(1)
        )
    vizinho = db.execute(stmt).scalar_one_or_none()
    if not vizinho:
        return False
    row.ordem, vizinho.ordem = vizinho.ordem, row.ordem
    db.flush()
    return True


def _reordenar(db: Session, user_id: int) -> None:
    stmt = (
        select(DescricaoPredefinida)
        .where(DescricaoPredefinida.user_id == user_id)
        .order_by(DescricaoPredefinida.ordem.asc(), DescricaoPredefinida.id.asc())
    )
    rows = list(db.execute(stmt).scalars().all())
    for idx, row in enumerate(rows, start=1):
        if row.ordem != idx:
            row.ordem = idx
