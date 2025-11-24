from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models.modulo import CusteioModulo, CusteioModuloLinha
from Martelo_Orcamentos_V2.app.models.user import User
from Martelo_Orcamentos_V2.app.services.settings import get_setting

KEY_ORC_DB_BASE = "base_path_dados_orcamento"
DEFAULT_BASE_DADOS_ORC = r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\Base_Dados_Orcamento"

MODULE_ROW_KEYS: Sequence[str] = (
    "descricao_livre",
    "def_peca",
    "descricao",
    "qt_mod",
    "qt_und",
    "comp",
    "larg",
    "esp",
    "mat_default",
    "tab_default",
    "ref_le",
    "descricao_no_orcamento",
    "und",
    "desp",
    "orl_0_4",
    "orl_1_0",
    "tipo",
    "familia",
    "mps",
    "mo",
    "orla",
    "blk",
    "nst",
    "gravar_modulo",
)
MODULE_META_KEYS: Sequence[str] = (
    "_row_type",
    "_group_uid",
    "_parent_uid",
    "_child_source",
    "_regra_nome",
)


def _coerce_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (str, int, float)) or value is None:
        return value
    if isinstance(value, bool):
        return bool(value)
    try:
        return float(value)
    except Exception:
        return None


def limpar_linha_para_modulo(row: Mapping[str, Any]) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for key in MODULE_ROW_KEYS:
        if key in row:
            value = row.get(key)
            if key == "gravar_modulo":
                data[key] = False
                continue
            data[key] = _coerce_value(value)
    for meta_key in MODULE_META_KEYS:
        if meta_key in row:
            data[meta_key] = _coerce_value(row.get(meta_key))
    # Garantir IDs limpos para reuso
    for transient_key in ("id", "_uid"):
        if transient_key in data:
            data.pop(transient_key, None)
    return data


def limpar_linhas_para_modulo(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [limpar_linha_para_modulo(row) for row in rows]


def preparar_linhas_para_importacao(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    linhas: List[Dict[str, Any]] = []
    for row in rows:
        cleaned = limpar_linha_para_modulo(row)
        cleaned.setdefault("gravar_modulo", False)
        cleaned.pop("_uid", None)
        linhas.append(cleaned)
    return linhas


def pasta_imagens_base(db: Session) -> str:
    return get_setting(db, KEY_ORC_DB_BASE, DEFAULT_BASE_DADOS_ORC) or DEFAULT_BASE_DADOS_ORC


def listar_modulos(db: Session, user_id: Optional[int]) -> List[Dict[str, Any]]:
    stmt = (
        select(CusteioModulo, User.username)
        .select_from(CusteioModulo)
        .join(User, CusteioModulo.user_id == User.id, isouter=True)
        .where(
            (CusteioModulo.is_global.is_(True))
            | (CusteioModulo.user_id == user_id)
        )
        .order_by(CusteioModulo.is_global.desc(), CusteioModulo.nome)
    )
    result: List[Dict[str, Any]] = []
    for modulo, username in db.execute(stmt).all():
        result.append(
            {
                "id": modulo.id,
                "nome": modulo.nome,
                "descricao": modulo.descricao,
                "imagem_path": modulo.imagem_path,
                "is_global": bool(modulo.is_global),
                "user_id": modulo.user_id,
                "owner_name": username,
            }
        )
    return result


def listar_modulos_por_scope(db: Session, user_id: Optional[int], scope: str) -> List[Dict[str, Any]]:
    scope_norm = (scope or "user").lower()
    is_global = scope_norm == "global"
    stmt = (
        select(CusteioModulo, User.username)
        .select_from(CusteioModulo)
        .join(User, CusteioModulo.user_id == User.id, isouter=True)
    )
    if is_global:
        stmt = stmt.where(CusteioModulo.is_global.is_(True))
    else:
        stmt = stmt.where(CusteioModulo.user_id == user_id)
    stmt = stmt.order_by(CusteioModulo.nome)
    result: List[Dict[str, Any]] = []
    for modulo, username in db.execute(stmt).all():
        result.append(
            {
                "id": modulo.id,
                "nome": modulo.nome,
                "descricao": modulo.descricao,
                "imagem_path": modulo.imagem_path,
                "is_global": bool(modulo.is_global),
                "user_id": modulo.user_id,
                "owner_name": username,
            }
        )
    return result


def carregar_modulo_completo(db: Session, modulo_id: int) -> Optional[Dict[str, Any]]:
    modulo = db.get(CusteioModulo, modulo_id)
    if modulo is None:
        return None
    linhas_stmt = (
        select(CusteioModuloLinha)
        .where(CusteioModuloLinha.modulo_id == modulo.id)
        .order_by(CusteioModuloLinha.ordem, CusteioModuloLinha.id)
    )
    linhas = [deepcopy(entry.dados) for entry in db.execute(linhas_stmt).scalars().all()]
    return {
        "id": modulo.id,
        "nome": modulo.nome,
        "descricao": modulo.descricao,
        "imagem_path": modulo.imagem_path,
        "is_global": bool(modulo.is_global),
        "user_id": modulo.user_id,
        "linhas": linhas,
    }


def guardar_modulo(
    db: Session,
    *,
    user_id: Optional[int],
    nome: str,
    descricao: Optional[str],
    linhas: Sequence[Mapping[str, Any]],
    imagem_path: Optional[str] = None,
    is_global: bool = False,
    modulo_id: Optional[int] = None,
) -> CusteioModulo:
    nome_limpo = (nome or "").strip()
    if not nome_limpo:
        raise ValueError("O nome do modulo nao pode estar vazio.")

    linhas_limpa = limpar_linhas_para_modulo(linhas)
    if not linhas_limpa:
        raise ValueError("Nenhuma linha selecionada para gravar o modulo.")

    if modulo_id:
        modulo = db.get(CusteioModulo, modulo_id)
        if modulo is None:
            raise ValueError("Modulo selecionado nao encontrado.")
        modulo.nome = nome_limpo
        modulo.descricao = descricao
        modulo.imagem_path = imagem_path
        modulo.is_global = bool(is_global)
        modulo.user_id = user_id if not is_global else None
        db.execute(delete(CusteioModuloLinha).where(CusteioModuloLinha.modulo_id == modulo.id))
    else:
        modulo = CusteioModulo(
            nome=nome_limpo,
            descricao=descricao,
            imagem_path=imagem_path,
            is_global=bool(is_global),
            user_id=None if is_global else user_id,
        )
        db.add(modulo)
        db.flush()

    for ordem, row in enumerate(linhas_limpa):
        linha = CusteioModuloLinha(modulo_id=modulo.id, ordem=ordem, dados=row)
        db.add(linha)

    db.flush()
    return modulo
