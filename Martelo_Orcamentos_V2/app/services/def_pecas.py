from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

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
MAT_DEFAULT_COLUMNS: tuple[str, ...] = (
    "mat_default_origem",
    "mat_default_grupos",
    "mat_default_default",
)
_MAT_DEFAULT_MENU_ALIASES: Dict[str, str] = {
    "materiais": "materiais",
    "material": "materiais",
    "placas": "materiais",
    "ferragens": "ferragens",
    "ferragem": "ferragens",
    "ferragens e acessorios": "ferragens",
    "ferragens & acessorios": "ferragens",
    "acessorios": "ferragens",
    "sistemas correr": "sistemas_correr",
    "sistema correr": "sistemas_correr",
    "sistemas_correr": "sistemas_correr",
    "sist correr": "sistemas_correr",
}

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEF_PECAS_CSV = _PACKAGE_ROOT / "data" / "def_pecas.csv"


def _to_decimal(value: Optional[str]) -> Optional[Decimal]:
    if value in (None, "", False):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _clean_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def listar_definicoes(session: Session) -> List[Dict[str, Optional[str]]]:
    stmt = select(DefinicaoPeca).order_by(DefinicaoPeca.id)
    resultados = []
    for reg in session.execute(stmt).scalars():
        item: Dict[str, Optional[str]] = {
            "id": reg.id,
            "tipo_peca_principal": reg.tipo_peca_principal,
            "subgrupo_peca": reg.subgrupo_peca,
            "nome_da_peca": reg.nome_da_peca,
            "mat_default_origem": reg.mat_default_origem,
            "mat_default_grupos": reg.mat_default_grupos,
            "mat_default_default": reg.mat_default_default,
        }
        for campo in CP_COLUMNS:
            valor = getattr(reg, campo, None)
            item[campo] = float(valor) if valor is not None else None
        resultados.append(item)
    return resultados


def carregar_definicoes_csv(csv_path: Optional[Path] = None) -> List[Dict[str, Optional[str]]]:
    origem = Path(csv_path or DEFAULT_DEF_PECAS_CSV)
    if not origem.exists():
        raise FileNotFoundError(f"Nao foi possivel encontrar o ficheiro de origem: {origem}")

    rows: List[Dict[str, Optional[str]]] = []
    with origem.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for raw_row in reader:
            normalized: Dict[str, Optional[str]] = {}
            for key, value in raw_row.items():
                if key is None:
                    continue
                normalized[key.lower()] = _clean_value(value)
            rows.append(normalized)
    return rows


def fundir_definicoes_com_base(
    base_rows: Sequence[Mapping[str, Optional[str]]],
    existing_rows: Sequence[Mapping[str, Optional[str]]],
) -> List[Dict[str, Optional[str]]]:
    existing_by_name: Dict[str, Mapping[str, Optional[str]]] = {}
    existing_by_id: Dict[str, Mapping[str, Optional[str]]] = {}
    for row in existing_rows:
        nome_token = _normalize_token(row.get("nome_da_peca"))
        if nome_token:
            existing_by_name[nome_token] = row
        reg_id = row.get("id")
        if reg_id not in (None, "", False):
            existing_by_id[str(reg_id)] = row

    resultado: List[Dict[str, Optional[str]]] = []
    vistos_nomes = set()
    vistos_ids = set()

    for base_row in base_rows:
        merged: Dict[str, Optional[str]] = {str(k).lower(): _clean_value(v) for k, v in base_row.items()}
        nome_token = _normalize_token(merged.get("nome_da_peca"))
        base_id = merged.get("id")

        existing = None
        if nome_token:
            existing = existing_by_name.get(nome_token)
        if existing is None and base_id not in (None, "", False):
            existing = existing_by_id.get(str(base_id))

        if existing is not None:
            for key, value in existing.items():
                normalized_key = str(key).lower()
                if normalized_key == "id":
                    continue
                if value not in (None, "", False):
                    merged[normalized_key] = _clean_value(value)

        if nome_token:
            vistos_nomes.add(nome_token)
        if merged.get("id") not in (None, "", False):
            vistos_ids.add(str(merged["id"]))
        resultado.append(merged)

    for row in existing_rows:
        nome_token = _normalize_token(row.get("nome_da_peca"))
        reg_id = row.get("id")
        if nome_token and nome_token in vistos_nomes:
            continue
        if reg_id not in (None, "", False) and str(reg_id) in vistos_ids:
            continue
        extra = {str(k).lower(): _clean_value(v) for k, v in row.items()}
        resultado.append(extra)

    def _sort_key(row: Mapping[str, Optional[str]]) -> tuple[int, str]:
        raw_id = row.get("id")
        try:
            return (int(raw_id), "")
        except Exception:
            return (10**9, str(row.get("nome_da_peca") or ""))

    resultado.sort(key=_sort_key)
    return resultado


def restaurar_definicoes_a_partir_csv(
    session: Session,
    *,
    csv_path: Optional[Path] = None,
    preservar_existentes: bool = True,
) -> List[Dict[str, Optional[str]]]:
    base_rows = carregar_definicoes_csv(csv_path)
    atuais = listar_definicoes(session)
    if preservar_existentes:
        merged = fundir_definicoes_com_base(base_rows, atuais)
    else:
        merged = [{str(k).lower(): _clean_value(v) for k, v in row.items()} for row in base_rows]
    session.execute(delete(DefinicaoPeca))
    session.flush()
    guardar_definicoes(session, merged)
    return merged


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
            if reg_id:
                reg.id = reg_id
            session.add(reg)

        reg.tipo_peca_principal = (linha.get("tipo_peca_principal") or "").strip() or nome.split(" ", 1)[0]
        reg.subgrupo_peca = (linha.get("subgrupo_peca") or "").strip() or None
        reg.nome_da_peca = nome
        reg.mat_default_origem = normalizar_origem_mat_default(linha.get("mat_default_origem"))
        reg.mat_default_grupos = serializar_grupos_mat_default(linha.get("mat_default_grupos"))
        reg.mat_default_default = (linha.get("mat_default_default") or "").strip() or None

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


def normalizar_origem_mat_default(value: Optional[str]) -> Optional[str]:
    token = _normalize_token(value)
    if not token:
        return None
    return _MAT_DEFAULT_MENU_ALIASES.get(token)


def parse_grupos_mat_default(value: Optional[str]) -> List[str]:
    if value in (None, "", False):
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        partes = [str(item).strip() for item in value if str(item).strip()]
    else:
        partes = [part.strip() for part in re.split(r"[,\n;\|]+", str(value)) if part.strip()]
    resultado: List[str] = []
    vistos = set()
    for parte in partes:
        token = _normalize_token(parte)
        if not token or token in vistos:
            continue
        vistos.add(token)
        resultado.append(parte)
    return resultado


def serializar_grupos_mat_default(value: Optional[str]) -> Optional[str]:
    grupos = parse_grupos_mat_default(value)
    if not grupos:
        return None
    return "; ".join(grupos)


def _normalize_piece_lookup_tokens(value: Optional[str]) -> List[str]:
    if value in (None, "", False):
        return []
    text = str(value).strip()
    if not text:
        return []
    variantes: List[str] = []
    candidatos = [
        text,
        text.split("+", 1)[0].strip(),
        re.sub(r"\[[^\]]*\]", "", text).strip(),
        re.sub(r"[_\s]+\d+$", "", re.sub(r"\[[^\]]*\]", "", text).strip()).strip(),
    ]
    vistos = set()
    for candidato in candidatos:
        token = _normalize_token(candidato)
        if not token or token in vistos:
            continue
        vistos.add(token)
        variantes.append(token)
    return variantes


def _build_row_lookup_tokens(row: Mapping[str, Any]) -> List[str]:
    candidatos: List[str] = []
    row_type = str(row.get("_row_type") or "").strip().casefold()
    def_peca = str(row.get("def_peca") or "").strip()
    if row_type == "parent" and "+" in def_peca:
        candidatos.append(def_peca.split("+", 1)[0].strip())
    candidatos.extend(
        [
            def_peca,
            str(row.get("_child_source") or "").strip(),
            str(row.get("descricao") or "").strip(),
            str(row.get("_parent_label") or "").strip(),
        ]
    )
    resultado: List[str] = []
    vistos = set()
    for candidato in candidatos:
        for token in _normalize_piece_lookup_tokens(candidato):
            if token in vistos:
                continue
            vistos.add(token)
            resultado.append(token)
    return resultado


def _score_definicao_match(regra: Mapping[str, Optional[str]], row_tokens: Sequence[str]) -> int:
    if not row_tokens:
        return 0
    nome_tokens = _normalize_piece_lookup_tokens(regra.get("nome_da_peca"))
    subgrupo_tokens = _normalize_piece_lookup_tokens(regra.get("subgrupo_peca"))
    tipo_tokens = _normalize_piece_lookup_tokens(regra.get("tipo_peca_principal"))
    score = 0
    for token in row_tokens:
        if token in nome_tokens:
            score = max(score, 500)
        if token in subgrupo_tokens:
            score = max(score, 360)
        if token in tipo_tokens:
            score = max(score, 260)
        for alvo in nome_tokens:
            if alvo and (alvo.startswith(token) or token.startswith(alvo)):
                score = max(score, 210)
        for alvo in subgrupo_tokens:
            if alvo and (alvo.startswith(token) or token.startswith(alvo)):
                score = max(score, 170)
        for alvo in tipo_tokens:
            if alvo and (alvo.startswith(token) or token.startswith(alvo)):
                score = max(score, 130)
    return score


def resolver_regra_mat_default(
    session: Session,
    row: Mapping[str, Any],
    *,
    definicoes: Optional[Sequence[Mapping[str, Optional[str]]]] = None,
) -> Optional[Dict[str, Any]]:
    row_tokens = _build_row_lookup_tokens(row)
    if not row_tokens:
        return None

    candidatos = list(definicoes or listar_definicoes(session))
    melhor: Optional[Mapping[str, Optional[str]]] = None
    melhor_score = 0
    for definicao in candidatos:
        score = _score_definicao_match(definicao, row_tokens)
        if score > melhor_score:
            melhor_score = score
            melhor = definicao

    if not melhor or melhor_score <= 0:
        return None

    grupos = parse_grupos_mat_default(melhor.get("mat_default_grupos"))
    origem = normalizar_origem_mat_default(melhor.get("mat_default_origem"))
    default = (melhor.get("mat_default_default") or "").strip() or None
    return {
        "definition_id": melhor.get("id"),
        "nome_da_peca": melhor.get("nome_da_peca"),
        "subgrupo_peca": melhor.get("subgrupo_peca"),
        "tipo_peca_principal": melhor.get("tipo_peca_principal"),
        "menu": origem,
        "grupos": grupos,
        "default": default,
        "score": melhor_score,
    }
