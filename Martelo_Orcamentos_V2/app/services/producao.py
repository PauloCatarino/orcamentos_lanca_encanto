from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import time
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models.custeio_producao import (
    CusteioProducaoConfig,
    CusteioProducaoValor,
)
from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento
from Martelo_Orcamentos_V2.app.db import SessionLocal
import logging

logger = logging.getLogger(__name__)


DEFAULT_PRODUCTION_VALUES: Sequence[Mapping[str, object]] = (
    {
        "descricao_equipamento": "VALOR_SECCIONADORA",
        "abreviatura": "SEC",
        "valor_std": Decimal("0.45"),
        "valor_serie": Decimal("0.35"),
        "resumo": "€/ML para a máquina Seccionadora",
    },
    {
        "descricao_equipamento": "VALOR_ORLADORA",
        "abreviatura": "ORL",
        "valor_std": Decimal("0.65"),
        "valor_serie": Decimal("0.50"),
        "resumo": "€/ML para a máquina Orladora",
    },
    {
        "descricao_equipamento": "CNC_PRECO_PECA_BAIXO",
        "abreviatura": "CNC",
        "valor_std": Decimal("0.75"),
        "valor_serie": Decimal("0.60"),
        "resumo": "€/peça se AREA_M2_und ≤ 0.7",
    },
    {
        "descricao_equipamento": "CNC_PRECO_PECA_MEDIO",
        "abreviatura": "CNC",
        "valor_std": Decimal("1.25"),
        "valor_serie": Decimal("1.00"),
        "resumo": "€/peça se 0.7 < AREA_M2_und < 1",
    },
    {
        "descricao_equipamento": "CNC_PRECO_PECA_ALTO",
        "abreviatura": "CNC",
        "valor_std": Decimal("1.75"),
        "valor_serie": Decimal("1.50"),
        "resumo": "€/peça se AREA_M2_und ≥ 1",
    },
    {
        "descricao_equipamento": "VALOR_ABD",
        "abreviatura": "ABD",
        "valor_std": Decimal("0.60"),
        "valor_serie": Decimal("0.50"),
        "resumo": "€/peça para a máquina ABD",
    },
    {
        "descricao_equipamento": "EUROS_HORA_CNC",
        "abreviatura": "CNC",
        "valor_std": Decimal("55"),
        "valor_serie": Decimal("55"),
        "resumo": "€/hora para a máquina CNC",
    },
    {
        "descricao_equipamento": "EUROS_HORA_PRENSA",
        "abreviatura": "PRENSA",
        "valor_std": Decimal("50"),
        "valor_serie": Decimal("40"),
        "resumo": "€/hora para a máquina Prensa",
    },
    {
        "descricao_equipamento": "EUROS_HORA_ESQUAD",
        "abreviatura": "ESQUAD",
        "valor_std": Decimal("20"),
        "valor_serie": Decimal("20"),
        "resumo": "€/hora para a máquina Esquadrejadora",
    },
    {
        "descricao_equipamento": "EUROS_EMBALAGEM_M3",
        "abreviatura": "EMBALAGEM",
        "valor_std": Decimal("50"),
        "valor_serie": Decimal("40"),
        "resumo": "€/M³ para Embalagem",
    },
    {
        "descricao_equipamento": "EUROS_HORA_MO",
        "abreviatura": "MO",
        "valor_std": Decimal("17.5"),
        "valor_serie": Decimal("17.5"),
        "resumo": "€/hora para Mão de Obra",
    },
    {
        "descricao_equipamento": "COLAGEM/REVESTIMENTO",
        "abreviatura": "COLAGEM",
        "valor_std": Decimal("3"),
        "valor_serie": Decimal("2.5"),
        "resumo": "€/M2 para Colagem/Revestimento por face",
    },
)

_COLAGEM_LEGACY_NAMES: Tuple[str, ...] = (
    "SERVICOS COLAGEM",
    "COLAGEM SANDWICH (M2)",
    "SERVICOS COLAGEM (M2)",
)
_COLAGEM_TARGET_NAME = "COLAGEM/REVESTIMENTO"
_COLAGEM_TARGET_ABBR = "COLAGEM"
_COLAGEM_STD = Decimal("3")
_COLAGEM_SERIE = Decimal("2.5")
_COLAGEM_RESUMO = "€/M2 para Colagem/Revestimento por face"
_COLAGEM_MIGRATION_DONE = False


@dataclass(frozen=True)
class ProducaoContext:
    orcamento_id: int
    versao: str
    user_id: int
    ano: str
    num_orcamento: str
    cliente_id: Optional[int]


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _normalize_versao(value: Optional[str]) -> str:
    if not value:
        return "01"
    text = str(value).strip()
    if text.isdigit() and len(text) <= 2:
        return f"{int(text):02d}"
    return text


def build_context(session: Session, orcamento_id: int, user_id: int, versao: Optional[str] = None) -> ProducaoContext:
    try:
        session.expire_all()
    except Exception:
        pass
    logger.debug("build_context: tentando session.get Orcamento id=%s", orcamento_id)
    orcamento = session.get(Orcamento, orcamento_id)
    if orcamento is None:
        try:
            session.rollback()
            session.expire_all()
            orcamento = session.get(Orcamento, orcamento_id)
        except Exception:
            pass
    if orcamento is None:
        # tenta com uma nova sessão para evitar caches/ligação com problema
        try:
            logger.debug("build_context: orcamento nao encontrado na sessao principal, tentando nova sessao id=%s", orcamento_id)
            with SessionLocal() as tmp:
                orcamento = tmp.get(Orcamento, orcamento_id)
                logger.debug("build_context: resultado nova sessao orcamento=%s", bool(orcamento))
                if orcamento is None:
                    # tentativa adicional com SQL crua para diagnostico
                    try:
                        res = tmp.execute("SELECT id, ano, num_orcamento, versao FROM orcamento WHERE id = :id", {"id": orcamento_id}).fetchone()
                        logger.debug("build_context: raw select result=%s", res)
                    except Exception as e:
                        logger.exception("build_context: falha ao executar raw select para orcamento %s: %s", orcamento_id, e)
        except Exception:
            logger.exception("build_context: erro ao tentar nova sessao para orcamento %s", orcamento_id)
    if orcamento is None:
        raise ValueError(f"Orçamento {orcamento_id} não encontrado.")
    versao_norm = _normalize_versao(versao or orcamento.versao)
    cliente_id = getattr(orcamento, "client_id", None)
    return ProducaoContext(
        orcamento_id=orcamento_id,
        versao=versao_norm,
        user_id=user_id,
        ano=str(getattr(orcamento, "ano", "") or ""),
        num_orcamento=str(getattr(orcamento, "num_orcamento", "") or ""),
        cliente_id=cliente_id,
    )


def _config_query(session: Session, ctx: ProducaoContext):
    return session.execute(
        select(CusteioProducaoConfig).where(
            CusteioProducaoConfig.orcamento_id == ctx.orcamento_id,
            CusteioProducaoConfig.versao == ctx.versao,
            CusteioProducaoConfig.user_id == ctx.user_id,
        )
    ).scalar_one_or_none()


def ensure_config(session: Session, ctx: ProducaoContext) -> CusteioProducaoConfig:
    """
    Garante que existe config para (orcamento, versao, user) evitando locks longos.
    Usa INSERT IGNORE numa sessao curta e recarrega na sessao principal.
    """
    try:
        session.rollback()
        session.execute(text("SET innodb_lock_wait_timeout=5"))
    except Exception:
        pass

    existing = _config_query(session, ctx)
    if existing:
        return existing

    # Confirmar que o orcamento existe (sessao independente para evitar cache suja)
    with SessionLocal() as chk:
        if chk.get(Orcamento, ctx.orcamento_id) is None:
            raise ValueError(f"Orcamento {ctx.orcamento_id} nao encontrado.")

    insert_cfg_sql = text(
        """
        INSERT IGNORE INTO custeio_producao_config (orcamento_id, cliente_id, user_id, ano, num_orcamento, versao, modo)
        VALUES (:orcamento_id, :cliente_id, :user_id, :ano, :num_orcamento, :versao, :modo)
        """
    )
    insert_val_sql = text(
        """
        INSERT IGNORE INTO custeio_producao_valores
        (config_id, descricao_equipamento, abreviatura, valor_std, valor_serie, resumo, ordem)
        VALUES (:config_id, :descricao_equipamento, :abreviatura, :valor_std, :valor_serie, :resumo, :ordem)
        """
    )
    params_cfg = {
        "orcamento_id": ctx.orcamento_id,
        "cliente_id": ctx.cliente_id,
        "user_id": ctx.user_id,
        "ano": ctx.ano,
        "num_orcamento": ctx.num_orcamento,
        "versao": ctx.versao,
        "modo": "STD",
    }

    created_id: Optional[int] = None
    with SessionLocal() as iso:
        try:
            try:
                iso.execute(text("SET innodb_lock_wait_timeout=5"))
            except Exception:
                pass
            iso.execute(insert_cfg_sql, params_cfg)
            iso.commit()
            existing_iso = _config_query(iso, ctx)
            created_id = existing_iso.id if existing_iso else None
            if created_id:
                for ordem, row in enumerate(DEFAULT_PRODUCTION_VALUES, start=1):
                    iso.execute(
                        insert_val_sql,
                        {
                            "config_id": created_id,
                            "descricao_equipamento": str(row["descricao_equipamento"]),
                            "abreviatura": str(row["abreviatura"]),
                            "valor_std": _to_decimal(row["valor_std"]),
                            "valor_serie": _to_decimal(row["valor_serie"]),
                            "resumo": str(row.get("resumo") or ""),
                            "ordem": ordem,
                        },
                    )
                iso.commit()
        except Exception:
            iso.rollback()
            created_id = None

    session.expire_all()
    config = session.get(CusteioProducaoConfig, created_id) if created_id else _config_query(session, ctx)
    if config:
        return config

    # fallback: tentar criar na sessao atual (sem INSERT IGNORE) antes de falhar
    try:
        cfg_obj = CusteioProducaoConfig(
            orcamento_id=ctx.orcamento_id,
            cliente_id=ctx.cliente_id,
            user_id=ctx.user_id,
            ano=ctx.ano,
            num_orcamento=ctx.num_orcamento,
            versao=ctx.versao,
            modo="STD",
        )
        session.add(cfg_obj)
        session.flush()
        for ordem, row in enumerate(DEFAULT_PRODUCTION_VALUES, start=1):
            session.add(
                CusteioProducaoValor(
                    config_id=cfg_obj.id,
                    descricao_equipamento=str(row["descricao_equipamento"]),
                    abreviatura=str(row["abreviatura"]),
                    valor_std=_to_decimal(row["valor_std"]),
                    valor_serie=_to_decimal(row["valor_serie"]),
                    resumo=str(row.get("resumo") or ""),
                    ordem=ordem,
                )
            )
        session.flush()
        return cfg_obj
    except IntegrityError:
        # Outro processo/sessão gravou no intervalo; tentar recuperar
        try:
            session.rollback()
        except Exception:
            pass
        existing = _config_query(session, ctx)
        if existing:
            return existing
        raise
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
        raise ValueError(
            f"Falha ao garantir config de producao para orcamento {ctx.orcamento_id} versao {ctx.versao} user {ctx.user_id}"
        )


def load_config(session: Session, ctx: ProducaoContext) -> CusteioProducaoConfig:
    config = ensure_config(session, ctx)
    ensure_default_values(session, config)
    return config


def ensure_default_values(session: Session, config: CusteioProducaoConfig) -> bool:
    if _migrate_colagem_records_once():
        for valor in config.valores:
            if valor.descricao_equipamento in _COLAGEM_LEGACY_NAMES:
                session.expire(
                    valor,
                    attribute_names=[
                        "descricao_equipamento",
                        "abreviatura",
                        "valor_std",
                        "valor_serie",
                        "resumo",
                    ],
                )
    existing: Dict[str, CusteioProducaoValor] = {
        valor.descricao_equipamento: valor for valor in config.valores
    }
    ordem_counter = max((valor.ordem or 0 for valor in config.valores), default=0) + 1
    added = False
    updated = False

    def _decimal_equals(value: Optional[Decimal], target: str) -> bool:
        try:
            return Decimal(value or 0) == Decimal(str(target))
        except Exception:
            return False

    colagem_entry = existing.get("COLAGEM/REVESTIMENTO")
    legacy_entry = existing.get("SERVICOS COLAGEM")
    target_entry = colagem_entry or legacy_entry
    if target_entry:
        needs_update = False
        if target_entry.descricao_equipamento != "COLAGEM/REVESTIMENTO":
            target_entry.descricao_equipamento = "COLAGEM/REVESTIMENTO"
            needs_update = True
            existing["COLAGEM/REVESTIMENTO"] = target_entry
            if legacy_entry:
                existing.pop("SERVICOS COLAGEM", None)
        if (target_entry.abreviatura or "").strip().upper() != "COLAGEM":
            target_entry.abreviatura = "COLAGEM"
            needs_update = True
        # Ajusta apenas quando ainda está com os valores antigos (10/8)
        if (
            _decimal_equals(target_entry.valor_std, "10")
            and _decimal_equals(target_entry.valor_serie, "8")
        ):
            target_entry.valor_std = _to_decimal("3")
            target_entry.valor_serie = _to_decimal("2.5")
            needs_update = True
        if needs_update:
            target_entry.resumo = "€/M2 para Colagem/Revestimento por face"
            session.add(target_entry)
            updated = True

    for row in DEFAULT_PRODUCTION_VALUES:
        desc = str(row["descricao_equipamento"])
        if desc in existing:
            continue
        valor = CusteioProducaoValor(
            config_id=config.id,
            descricao_equipamento=desc,
            abreviatura=str(row["abreviatura"]),
            valor_std=_to_decimal(row["valor_std"]),
            valor_serie=_to_decimal(row["valor_serie"]),
            resumo=str(row.get("resumo") or ""),
            ordem=ordem_counter,
        )
        ordem_counter += 1
        session.add(valor)
        config.valores.append(valor)
        added = True
    if added or updated:
        session.flush()
    return added or updated


def _migrate_colagem_records_once() -> bool:
    global _COLAGEM_MIGRATION_DONE
    if _COLAGEM_MIGRATION_DONE:
        return False
    _COLAGEM_MIGRATION_DONE = True

    session = SessionLocal()
    try:
        registros = (
            session.query(CusteioProducaoValor)
            .filter(CusteioProducaoValor.descricao_equipamento.in_(_COLAGEM_LEGACY_NAMES))
            .all()
        )
        if not registros:
            session.commit()
            return False
        changed = False
        for registro in registros:
            registro.descricao_equipamento = _COLAGEM_TARGET_NAME
            registro.abreviatura = _COLAGEM_TARGET_ABBR
            registro.valor_std = _COLAGEM_STD
            registro.valor_serie = _COLAGEM_SERIE
            registro.resumo = _COLAGEM_RESUMO
            changed = True
        session.commit()
        return changed
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()


def load_values(session: Session, ctx: ProducaoContext) -> List[dict]:
    config = load_config(session, ctx)
    return [
        {
            "descricao_equipamento": valor.descricao_equipamento,
            "abreviatura": valor.abreviatura,
            "valor_std": float(valor.valor_std or 0),
            "valor_serie": float(valor.valor_serie or 0),
            "resumo": valor.resumo or "",
            "ordem": valor.ordem,
        }
        for valor in sorted(config.valores, key=lambda v: v.ordem)
    ]


def save_values(session: Session, ctx: ProducaoContext, valores: Iterable[Mapping[str, object]]) -> None:
    config = load_config(session, ctx)
    existing = {valor.descricao_equipamento: valor for valor in config.valores}
    ordem_counter = 1
    for entrada in valores:
        chave = str(entrada.get("descricao_equipamento") or "").strip()
        if not chave:
            continue
        registro = existing.get(chave)
        if registro is None:
            registro = CusteioProducaoValor(
                config_id=config.id,
                descricao_equipamento=chave,
                abreviatura=str(entrada.get("abreviatura") or ""),
            )
        registro.valor_std = _to_decimal(entrada.get("valor_std"))
        registro.valor_serie = _to_decimal(entrada.get("valor_serie"))
        registro.resumo = str(entrada.get("resumo") or "")
        registro.ordem = ordem_counter
        ordem_counter += 1
        session.add(registro)
    session.flush()


def reset_values(session: Session, ctx: ProducaoContext) -> None:
    config = load_config(session, ctx)
    session.query(CusteioProducaoValor).filter(CusteioProducaoValor.config_id == config.id).delete(synchronize_session=False)
    session.flush()
    ensure_default_values(session, config)


def get_mode(session: Session, ctx: ProducaoContext) -> str:
    config = load_config(session, ctx)
    modo = (config.modo or "STD").upper()
    if modo not in {"STD", "SERIE"}:
        return "STD"
    return modo


def set_mode(session: Session, ctx: ProducaoContext, modo: str) -> None:
    modo_norm = (modo or "").upper()
    if modo_norm not in {"STD", "SERIE"}:
        raise ValueError("Modo inválido. Utilize 'STD' ou 'SERIE'.")
    config = load_config(session, ctx)
    config.modo = modo_norm
    session.add(config)
    session.flush()
