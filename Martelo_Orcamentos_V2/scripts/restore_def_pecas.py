from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
PACKAGE_ROOT = SCRIPT_PATH.parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services import def_pecas as svc_def_pecas


def _default_backup_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return PACKAGE_ROOT / "data" / f"def_pecas_backup_before_restore_{stamp}.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Restaura Definicoes de Pecas a partir do CSV base.")
    parser.add_argument("--csv", type=Path, default=svc_def_pecas.DEFAULT_DEF_PECAS_CSV, help="Caminho do CSV base.")
    parser.add_argument(
        "--no-preserve-existing",
        action="store_true",
        help="Nao preserva valores atuais da base de dados; repoe apenas o CSV base.",
    )
    parser.add_argument(
        "--backup",
        type=Path,
        default=_default_backup_path(),
        help="Caminho do ficheiro JSON onde sera guardado um backup da tabela atual.",
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        atuais = svc_def_pecas.listar_definicoes(session)
        args.backup.parent.mkdir(parents=True, exist_ok=True)
        args.backup.write_text(json.dumps(atuais, ensure_ascii=False, indent=2), encoding="utf-8")

        merged = svc_def_pecas.restaurar_definicoes_a_partir_csv(
            session,
            csv_path=args.csv,
            preservar_existentes=not args.no_preserve_existing,
        )
        print(
            f"Restauro concluido com sucesso. Registos finais: {len(merged)}. "
            f"Backup criado em: {args.backup}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
