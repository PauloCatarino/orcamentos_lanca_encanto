"""
Pesquisa local (RAG simples) sobre os documentos curados ingestados.

Pré-requisitos:
  - Executar scripts/ingest_profundo.py para popular MySQL e índice FAISS.
  - Dependências: sentence-transformers, faiss-cpu.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import create_engine, text

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover - opcional
    faiss = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - opcional
    SentenceTransformer = None

# Garantir que o pacote Martelo_Orcamentos_V2 está no sys.path quando o script é corrido diretamente
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Martelo_Orcamentos_V2.app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("search_profundo")

DEFAULT_BASE = (
    r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Compras\Tabela e Catalogos_Fornecedores\Tabelas Preços\Pesquisa_Profunda_IA"
)
DEFAULT_EMBEDDINGS_DIR = Path(
    r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\Base_Dados_Orcamento\Pesquisa_IA_Martelo"
)
META_FILENAME = "faiss_meta.jsonl"
FAISS_FILENAME = "faiss.index"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def load_meta(meta_path: Path) -> List[dict]:
    if not meta_path.exists():
        logger.error("Meta de FAISS não encontrada: %s", meta_path)
        return []
    entries: List[dict] = []
    with meta_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    return entries


def load_index(index_path: Path) -> Optional[object]:
    if faiss is None:
        logger.error("faiss não instalado.")
        return None
    if not index_path.exists():
        logger.error("Índice FAISS não encontrado: %s", index_path)
        return None
    try:
        idx = faiss.read_index(str(index_path))
    except Exception as exc:
        logger.error("Falha ao carregar índice FAISS: %s", exc)
        return None
    if getattr(idx, "ntotal", 0) == 0:
        logger.error("Índice FAISS vazio (ntotal=0) em %s", index_path)
        return None
    return idx


def load_model() -> Optional[SentenceTransformer]:
    if SentenceTransformer is None:
        logger.error("sentence-transformers não instalado.")
        return None
    try:
        return SentenceTransformer(MODEL_NAME)
    except Exception as exc:
        logger.error("Falha ao carregar modelo %s: %s", MODEL_NAME, exc)
        return None


def search(query: str, top_k: int, base_path: Path, embeddings_dir: Path) -> None:
    index_path = embeddings_dir / FAISS_FILENAME
    meta_path = embeddings_dir / META_FILENAME

    meta = load_meta(meta_path)
    index = load_index(index_path)
    model = load_model()

    if not meta or index is None or model is None:
        logger.error("Requisitos em falta; abortando pesquisa.")
        return

    vector = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    scores, positions = index.search(vector, top_k)
    scores = scores[0]
    positions = positions[0]

    results: List[Tuple[int, float]] = []
    for pos, score in zip(positions, scores):
        if pos < 0 or pos >= len(meta):
            continue
        chunk_id = meta[pos].get("chunk_id")
        if chunk_id:
            results.append((int(chunk_id), float(score)))

    if not results:
        logger.info("Sem resultados para: %s", query)
        return

    chunk_ids = [cid for cid, _ in results]
    engine = create_engine(settings.DB_URI, pool_pre_ping=True, echo=False)
    from sqlalchemy import bindparam

    with engine.begin() as conn:
        stmt = text(
            """
            SELECT c.id, c.text, c.page, c.document_id, d.path, d.filename, d.supplier
            FROM ia_chunks c
            JOIN ia_documents d ON d.id = c.document_id
            WHERE c.id IN :ids
            """
        ).bindparams(bindparam("ids", expanding=True))
        rows = conn.execute(stmt, {"ids": chunk_ids}).fetchall()

    row_map = {row.id: row for row in rows}

    for idx, (cid, score) in enumerate(results, start=1):
        row = row_map.get(cid)
        if not row:
            continue
        snippet = (row.text or "").strip().replace("\n", " ")
        if len(snippet) > 220:
            snippet = snippet[:220] + "..."
        print(f"[{idx}] score={score:.4f} | fornecedor={row.supplier} | ficheiro={row.filename} | página={row.page}")
        print(f"     caminho: {row.path}")
        print(f"     texto: {snippet}\n")


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Pesquisa IA local sobre documentos curados.")
    parser.add_argument("query", type=str, help="Texto a pesquisar.")
    parser.add_argument("--top", type=int, default=5, help="Número de resultados (default: 5).")
    parser.add_argument(
        "--base",
        type=Path,
        default=Path(DEFAULT_BASE),
        help="Pasta base Pesquisa_Profunda_IA (default: caminho UNC configurado).",
    )
    parser.add_argument(
        "--embeddings",
        type=Path,
        default=DEFAULT_EMBEDDINGS_DIR,
        help="Pasta onde está o índice FAISS/meta (default: share UNC configurado).",
    )
    args = parser.parse_args(argv)

    embeddings_dir = args.embeddings.resolve()
    search(args.query, args.top, args.base, embeddings_dir)


if __name__ == "__main__":
    main()
