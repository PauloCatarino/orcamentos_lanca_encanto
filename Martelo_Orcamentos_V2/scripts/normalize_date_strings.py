from __future__ import annotations

import argparse

from sqlalchemy import select

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.models import Orcamento, Producao
from Martelo_Orcamentos_V2.app.utils.date_utils import format_date_storage, parse_date_value


def _normalize_field(instance, field_name: str) -> tuple[str, str] | None:
    raw = getattr(instance, field_name, None)
    if raw in (None, ""):
        return None
    parsed = parse_date_value(raw)
    if parsed is None:
        return None
    normalized = format_date_storage(parsed)
    current = str(raw).strip()
    if current == normalized:
        return None
    setattr(instance, field_name, normalized)
    return current, normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Normaliza datas string para ISO (yyyy-mm-dd).")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica as alteracoes na base de dados. Sem esta flag o script corre em dry-run.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        changes: list[str] = []

        for orc in db.execute(select(Orcamento)).scalars().all():
            change = _normalize_field(orc, "data")
            if change:
                before, after = change
                changes.append(f"Orcamento {orc.id} data: {before} -> {after}")

        for proc in db.execute(select(Producao)).scalars().all():
            for field_name in ("data_inicio", "data_entrega"):
                change = _normalize_field(proc, field_name)
                if change:
                    before, after = change
                    changes.append(f"Producao {proc.id} {field_name}: {before} -> {after}")

        if not changes:
            print("Nenhuma data para normalizar.")
            return 0

        print(f"Alteracoes detetadas: {len(changes)}")
        for line in changes[:50]:
            print(line)
        if len(changes) > 50:
            print(f"... e mais {len(changes) - 50} alteracoes.")

        if not args.apply:
            db.rollback()
            print("Dry-run concluido. Use --apply para gravar.")
            return 0

        db.commit()
        print("Normalizacao concluida e gravada com sucesso.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
