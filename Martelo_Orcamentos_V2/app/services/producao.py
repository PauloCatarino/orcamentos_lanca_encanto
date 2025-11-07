from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models.custeio_producao import (
    CusteioProducaoConfig,
    CusteioProducaoValor,
)
from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento
from Martelo_Orcamentos_V2.app.db import SessionLocal


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
    orcamento = session.get(Orcamento, orcamento_id)
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
    config = _config_query(session, ctx)
    if config:
        return config

    config = CusteioProducaoConfig(
        orcamento_id=ctx.orcamento_id,
        cliente_id=ctx.cliente_id,
        user_id=ctx.user_id,
        ano=ctx.ano,
        num_orcamento=ctx.num_orcamento,
        versao=ctx.versao,
        modo="STD",
    )
    session.add(config)
    session.flush()

    valores: List[CusteioProducaoValor] = []
    for ordem, row in enumerate(DEFAULT_PRODUCTION_VALUES, start=1):
        valores.append(
            CusteioProducaoValor(
                config_id=config.id,
                descricao_equipamento=str(row["descricao_equipamento"]),
                abreviatura=str(row["abreviatura"]),
                valor_std=_to_decimal(row["valor_std"]),
                valor_serie=_to_decimal(row["valor_serie"]),
                resumo=str(row.get("resumo") or ""),
                ordem=ordem,
            )
        )
    config.valores = valores
    session.flush()
    return config


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
