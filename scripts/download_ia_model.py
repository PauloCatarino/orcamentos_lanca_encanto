"""
Descarrega o modelo de geração de texto (FLAN-T5 base) para uso offline.
Armazena em data/ia_models/flan-t5-base por defeito.

Uso:
    python scripts/download_ia_model.py
    # ou para outro diretório:
    python scripts/download_ia_model.py --dest data/ia_models/flan-t5-base
"""

from __future__ import annotations

import argparse
from pathlib import Path
import logging

from huggingface_hub import snapshot_download


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("download_ia_model")

DEFAULT_MODEL = "google/flan-t5-base"
DEFAULT_DEST = Path(__file__).resolve().parents[1] / "data" / "ia_models" / "flan-t5-base"


def main():
    parser = argparse.ArgumentParser(description="Download do modelo FLAN-T5 para uso offline.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="ID do modelo (HF Hub).")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST, help="Diretório destino local.")
    args = parser.parse_args()

    dest = args.dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    logger.info("A descarregar modelo '%s' para %s ...", args.model, dest)
    snapshot_download(
        repo_id=args.model,
        local_dir=dest,
        local_dir_use_symlinks=False,
        allow_patterns=None,
    )
    logger.info("Download concluído. Configure 'Pasta Modelo IA (texto)' para: %s", dest)


if __name__ == "__main__":
    main()
