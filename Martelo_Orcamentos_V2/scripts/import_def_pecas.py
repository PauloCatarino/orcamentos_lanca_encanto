from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Dict, Optional

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
PACKAGE_ROOT = SCRIPT_PATH.parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services import def_pecas as svc_def_pecas


CSV_PATH = PACKAGE_ROOT / "data" / "def_pecas.csv"


def _clean_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = value.strip()
    return text or None


def load_rows() -> list[Dict[str, Optional[str]]]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Não foi possível encontrar o ficheiro de origem: {CSV_PATH}")

    rows: list[Dict[str, Optional[str]]] = []
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for raw_row in reader:
            normalized: Dict[str, Optional[str]] = {}
            for key, value in raw_row.items():
                if key is None:
                    continue
                normalized[key.lower()] = _clean_value(value)
            rows.append(normalized)
    return rows


def main() -> None:
    rows = load_rows()
    if not rows:
        print("Nenhum registo encontrado no ficheiro. Nada foi importado.")
        return

    session = SessionLocal()
    try:
        svc_def_pecas.guardar_definicoes(session, rows)
        print(f"Importacao concluida com sucesso: {len(rows)} registos atualizados.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
