from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from datetime import datetime
import json
from typing import Any, Dict, List, Mapping, Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models.modulo import CusteioModulo, CusteioModuloLinha
from Martelo_Orcamentos_V2.app.models.user import User
from Martelo_Orcamentos_V2.app.services.settings import get_setting

KEY_ORC_DB_BASE = "base_path_dados_orcamento"
DEFAULT_BASE_DADOS_ORC = r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\Base_Dados_Orcamento"
MODULOS_IMPORTADOS_EXTRAS_KEY = "modulos_importados"

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


def _coerce_extras_dict(extras_raw: Any) -> Dict[str, Any]:
    if not extras_raw:
        return {}
    if isinstance(extras_raw, dict):
        return dict(extras_raw)
    if isinstance(extras_raw, str):
        try:
            parsed = json.loads(extras_raw)
        except Exception:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def _coerce_positive_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except Exception:
        return None
    return number if number > 0 else None


def _normalize_scope(value: Any, *, is_global: Optional[bool] = None) -> str:
    if is_global is True:
        return "global"
    if is_global is False:
        return "user"
    scope = str(value or "").strip().lower()
    return "global" if scope == "global" else "user"


def listar_registos_importacao_modulos(extras_raw: Any) -> List[Dict[str, Any]]:
    extras = _coerce_extras_dict(extras_raw)
    registos_raw = extras.get(MODULOS_IMPORTADOS_EXTRAS_KEY)
    if not isinstance(registos_raw, list):
        return []

    registos: List[Dict[str, Any]] = []
    for raw in registos_raw:
        if not isinstance(raw, dict):
            continue
        modulo_id = _coerce_positive_int(raw.get("modulo_id"))
        nome = str(raw.get("nome") or "").strip()
        if not nome and modulo_id is None:
            continue
        linhas_importadas = _coerce_positive_int(raw.get("linhas_importadas"))
        importado_em = str(raw.get("importado_em") or "").strip() or None
        registos.append(
            {
                "modulo_id": modulo_id,
                "nome": nome or f"Modulo {modulo_id}",
                "scope": _normalize_scope(raw.get("scope"), is_global=raw.get("is_global")),
                "linhas_importadas": linhas_importadas,
                "importado_em": importado_em,
            }
        )
    return registos


def construir_registos_importacao_modulos(
    modulos: Sequence[Mapping[str, Any]],
    *,
    imported_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    fallback_timestamp = imported_at or datetime.now().astimezone().isoformat(timespec="seconds")
    registos: List[Dict[str, Any]] = []
    for modulo in modulos:
        if not isinstance(modulo, Mapping):
            continue
        modulo_id = _coerce_positive_int(modulo.get("modulo_id") or modulo.get("id"))
        nome = str(modulo.get("nome") or "").strip()
        if not nome and modulo_id is None:
            continue
        linhas_importadas = _coerce_positive_int(modulo.get("linhas_importadas"))
        timestamp = str(modulo.get("importado_em") or "").strip() or fallback_timestamp
        registos.append(
            {
                "modulo_id": modulo_id,
                "nome": nome or f"Modulo {modulo_id}",
                "scope": _normalize_scope(modulo.get("scope"), is_global=modulo.get("is_global")),
                "linhas_importadas": linhas_importadas,
                "importado_em": timestamp,
            }
        )
    return registos


def anexar_registos_importacao_modulos(extras_raw: Any, registos: Sequence[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    extras = _coerce_extras_dict(extras_raw)
    novos_registos = construir_registos_importacao_modulos(registos) if registos else []
    if not novos_registos:
        return extras or None

    atuais = listar_registos_importacao_modulos(extras)
    extras[MODULOS_IMPORTADOS_EXTRAS_KEY] = atuais + novos_registos
    return extras or None


def resumir_registos_importacao_modulos(
    registos: Sequence[Mapping[str, Any]],
    *,
    max_names: int = 3,
) -> str:
    if not registos:
        return "-"

    agregados: Dict[str, int] = {}
    ordem: List[str] = []
    for registo in registos:
        if not isinstance(registo, Mapping):
            continue
        nome = str(registo.get("nome") or "").strip()
        if not nome:
            modulo_id = _coerce_positive_int(registo.get("modulo_id"))
            if modulo_id is None:
                continue
            nome = f"Modulo {modulo_id}"
        if nome not in agregados:
            agregados[nome] = 0
            ordem.append(nome)
        agregados[nome] += 1

    labels = [f"{nome} ({agregados[nome]}x)" if agregados[nome] > 1 else nome for nome in ordem]
    if not labels:
        return "-"
    resumo = ", ".join(labels[:max_names])
    restantes = len(labels) - max_names
    if restantes > 0:
        resumo = f"{resumo} +{restantes}"
    return resumo


def formatar_registos_importacao_modulos_tooltip(registos: Sequence[Mapping[str, Any]]) -> str:
    if not registos:
        return "Nenhum modulo registado neste item."

    linhas: List[str] = []
    for registo in registos:
        if not isinstance(registo, Mapping):
            continue
        nome = str(registo.get("nome") or "").strip()
        if not nome:
            modulo_id = _coerce_positive_int(registo.get("modulo_id"))
            if modulo_id is None:
                continue
            nome = f"Modulo {modulo_id}"

        partes: List[str] = [nome]
        scope = _normalize_scope(registo.get("scope"), is_global=registo.get("is_global"))
        if scope == "global":
            partes.append("Global")
        elif scope == "user":
            partes.append("Utilizador")

        linhas_importadas = _coerce_positive_int(registo.get("linhas_importadas"))
        if linhas_importadas is not None:
            suffix = "linha" if linhas_importadas == 1 else "linhas"
            partes.append(f"{linhas_importadas} {suffix}")

        importado_em = str(registo.get("importado_em") or "").strip()
        if importado_em:
            try:
                dt = datetime.fromisoformat(importado_em)
            except Exception:
                partes.append(importado_em)
            else:
                partes.append(dt.strftime("%d-%m-%Y %H:%M"))

        linhas.append(" | ".join(partes))

    return "\n".join(linhas) if linhas else "Nenhum modulo registado neste item."


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


def preparar_linhas_para_importacao(
    rows: Sequence[Mapping[str, Any]],
    imagem_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    linhas: List[Dict[str, Any]] = []
    divisao_token = "DIVISAO INDEPENDENTE"
    for row in rows:
        cleaned = limpar_linha_para_modulo(row)
        cleaned.setdefault("gravar_modulo", False)
        cleaned.pop("_uid", None)
        linhas.append(cleaned)
    if imagem_path:
        for linha in linhas:
            def_peca = linha.get("def_peca") or ""
            try:
                def_token = str(def_peca).strip().casefold()
            except Exception:
                def_token = ""
            if def_token == divisao_token.casefold():
                linha["icon_hint"] = imagem_path
                break
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


def atualizar_modulo_metadata(
    db: Session,
    *,
    modulo_id: int,
    user_id: Optional[int],
    nome: str,
    descricao: Optional[str],
    imagem_path: Optional[str] = None,
    is_global: Optional[bool] = None,
) -> CusteioModulo:
    """Atualiza nome/descrição/imagem de um módulo existente (sem mexer nas linhas)."""
    modulo = db.get(CusteioModulo, modulo_id)
    if modulo is None:
        raise ValueError("Modulo selecionado nao encontrado.")

    nome_limpo = (nome or "").strip()
    if not nome_limpo:
        raise ValueError("O nome do modulo nao pode estar vazio.")

    # Se for módulo de utilizador, apenas o próprio pode atualizar
    if not bool(modulo.is_global):
        if user_id is None or modulo.user_id != user_id:
            raise ValueError("Nao tem permissao para editar este modulo.")

    if is_global is None:
        is_global = bool(modulo.is_global)

    modulo.nome = nome_limpo
    modulo.descricao = descricao
    modulo.imagem_path = imagem_path
    modulo.is_global = bool(is_global)
    modulo.user_id = None if is_global else user_id
    db.flush()
    return modulo


def eliminar_modulo(db: Session, *, modulo_id: int, user_id: Optional[int]) -> None:
    """Elimina um módulo (e as respetivas linhas)."""
    modulo = db.get(CusteioModulo, modulo_id)
    if modulo is None:
        raise ValueError("Modulo selecionado nao encontrado.")

    # Se for módulo de utilizador, apenas o próprio pode eliminar
    if not bool(modulo.is_global):
        if user_id is None or modulo.user_id != user_id:
            raise ValueError("Nao tem permissao para eliminar este modulo.")

    db.delete(modulo)
    db.flush()
