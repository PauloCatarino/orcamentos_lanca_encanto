from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List, Mapping, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models.definicao_peca import DefinicaoPeca
import unicodedata


def _normalize_token(value: Optional[str]) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value).strip())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.casefold()

CP_COLUMNS: tuple[str, ...] = (
    "cp01_sec",
    "cp02_orl",
    "cp03_cnc",
    "cp04_abd",
    "cp05_prensa",
    "cp06_esquad",
    "cp07_embalagem",
    "cp08_mao_de_obra",
)


def _to_decimal(value: Optional[str]) -> Optional[Decimal]:
    if value in (None, "", False):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return None


def listar_definicoes(session: Session) -> List[Dict[str, Optional[str]]]:
    stmt = select(DefinicaoPeca).order_by(DefinicaoPeca.id)
    resultados = []
    for reg in session.execute(stmt).scalars():
        item: Dict[str, Optional[str]] = {
            "id": reg.id,
            "tipo_peca_principal": reg.tipo_peca_principal,
            "subgrupo_peca": reg.subgrupo_peca,
            "nome_da_peca": reg.nome_da_peca,
        }
        for campo in CP_COLUMNS:
            valor = getattr(reg, campo, None)
            item[campo] = float(valor) if valor is not None else None
        resultados.append(item)
    return resultados


def guardar_definicoes(session: Session, linhas: Iterable[Mapping[str, Optional[str]]]) -> None:
    existentes: Dict[int, DefinicaoPeca] = {
        reg.id: reg for reg in session.execute(select(DefinicaoPeca)).scalars()
    }
    vistos: List[int] = []

    for linha in linhas:
        nome = (linha.get("nome_da_peca") or "").strip()
        if not nome:
            continue

        raw_id = linha.get("id")
        try:
            reg_id = int(raw_id) if raw_id not in (None, "", False) else None
        except (ValueError, TypeError):
            reg_id = None

        if reg_id and reg_id in existentes:
            reg = existentes[reg_id]
        else:
            reg = DefinicaoPeca()
            session.add(reg)

        reg.tipo_peca_principal = (linha.get("tipo_peca_principal") or "").strip() or nome.split(" ", 1)[0]
        reg.subgrupo_peca = (linha.get("subgrupo_peca") or "").strip() or None
        reg.nome_da_peca = nome

        for campo in CP_COLUMNS:
            setattr(reg, campo, _to_decimal(linha.get(campo)))

        session.flush()
        vistos.append(reg.id)

    if vistos:
        session.execute(delete(DefinicaoPeca).where(~DefinicaoPeca.id.in_(vistos)))
    else:
        session.execute(delete(DefinicaoPeca))

    session.commit()


def mapa_por_nome(session: Session) -> Dict[str, Dict[str, float]]:
    definicoes = listar_definicoes(session)
    mapa: Dict[str, Dict[str, float]] = {}
    for definicao in definicoes:
        nome = definicao.get("nome_da_peca")
        subgrupo = definicao.get("subgrupo_peca")
        cp_map: Dict[str, float] = {}
        for campo in CP_COLUMNS:
            valor = definicao.get(campo)
            if valor is not None:
                cp_map[campo] = float(valor)
        if nome:
            chave_nome = _normalize_token(nome)
            if chave_nome:
                mapa[chave_nome] = dict(cp_map)
        if subgrupo:
            chave_sub = _normalize_token(subgrupo)
            if chave_sub and chave_sub not in mapa:
                mapa[chave_sub] = dict(cp_map)
    return mapa
