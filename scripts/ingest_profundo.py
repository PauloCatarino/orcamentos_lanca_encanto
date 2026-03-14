"""
Ingestão de documentos curados (Pesquisa_Profunda_IA) para MySQL + FAISS.

Fluxo:
1) Varrer a pasta base (definida por SEARCH_IA_BASE_PATH ou valor por defeito).
2) Extrair texto (PDF, TXT, DOCX, XLSX/CSV) e dividir em chunks.
3) Criar/atualizar tabelas ia_documents, ia_chunks, ia_tables no MySQL.
4) Gerar embeddings (se sentence-transformers + faiss estiverem instalados) e guardar índice em disco.

Requisitos recomendados:
  pip install pdfplumber python-docx pandas sentence-transformers faiss-cpu rapidfuzz
  # Para OCR de scans: pip install pytesseract pdf2image; instalar Tesseract + Poppler no SO.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
import sys
from typing import Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import text, create_engine

try:
    import pdfplumber
except Exception:  # pragma: no cover - opcional
    pdfplumber = None

try:
    import pandas as pd
except Exception:  # pragma: no cover - opcional
    pd = None

try:
    import docx  # type: ignore
except Exception:  # pragma: no cover - opcional
    docx = None

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
logger = logging.getLogger("ingest_profundo")


# ----------------------- Configs -----------------------
DEFAULT_BASE = (
    r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Compras\Tabela e Catalogos_Fornecedores\Tabelas Preços\Pesquisa_Profunda_IA"
)
# Por defeito, guardar embeddings num share UNC (partilhado) para funcionar em qualquer PC.
DEFAULT_EMBEDDINGS_DIR = Path(
    r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\Base_Dados_Orcamento\Pesquisa_IA_Martelo"
)
META_FILENAME = "faiss_meta.jsonl"
FAISS_FILENAME = "faiss.index"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# ----------------------- Helpers -----------------------

def _path_is_ascii(path: Path) -> bool:
    try:
        return str(path).isascii()
    except Exception:
        return False


def compute_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 200) -> List[Tuple[int, int, str]]:
    """
    Divide texto em blocos. Retorna lista de (start, end, chunk_text).
    """
    text = text or ""
    n = len(text)
    if n == 0:
        return []
    chunks: List[Tuple[int, int, str]] = []
    start = 0
    while start < n:
        end = min(n, start + chunk_size)
        chunk = text[start:end]
        chunks.append((start, end, chunk))
        if end == n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def extract_text_from_pdf(path: Path) -> List[Tuple[int, str]]:
    if not pdfplumber:
        logger.warning("pdfplumber não instalado; PDF será ignorado: %s", path)
        return []
    pages: List[Tuple[int, str]] = []
    with pdfplumber.open(path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text:
                pages.append((idx, text))
    return pages


def extract_text_from_docx(path: Path) -> List[Tuple[int, str]]:
    if not docx:
        logger.warning("python-docx não instalado; DOCX será ignorado: %s", path)
        return []
    document = docx.Document(str(path))
    text = "\n".join(p.text for p in document.paragraphs)
    return [(1, text)]


def extract_text_from_xlsx(path: Path) -> List[Tuple[int, str]]:
    if not pd:
        logger.warning("pandas não instalado; XLSX/CSV será ignorado: %s", path)
        return []
    pages: List[Tuple[int, str]] = []
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        pages.append((1, df.to_csv(index=False)))
        return pages
    try:
        sheets = pd.read_excel(path, sheet_name=None, dtype=str, keep_default_na=False)
    except Exception:
        return []
    for idx, (sheet_name, df) in enumerate(sheets.items(), start=1):
        text = f"Sheet: {sheet_name}\n" + df.to_csv(index=False)
        pages.append((idx, text))
    return pages


def extract_text_from_txt(path: Path) -> List[Tuple[int, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        text = ""
    return [(1, text)]


def extract_text(path: Path) -> List[Tuple[int, str]]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    if ext in {".docx"}:
        return extract_text_from_docx(path)
    if ext in {".xlsx", ".xlsm", ".xls", ".csv"}:
        return extract_text_from_xlsx(path)
    if ext in {".txt", ".md"}:
        return extract_text_from_txt(path)
    return []


def ensure_schema(engine) -> None:
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS ia_documents (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            path TEXT NOT NULL,
            filename VARCHAR(512),
            ext VARCHAR(16),
            size_bytes BIGINT,
            modified_at DATETIME NULL,
            checksum VARCHAR(64),
            supplier VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_ia_documents_checksum (checksum)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS ia_chunks (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            document_id BIGINT NOT NULL,
            chunk_index INT NOT NULL,
            page INT NULL,
            start_char INT NULL,
            end_char INT NULL,
            text LONGTEXT,
            vector_index BIGINT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_ia_chunks_doc (document_id),
            CONSTRAINT fk_ia_chunks_doc FOREIGN KEY (document_id) REFERENCES ia_documents(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS ia_tables (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            document_id BIGINT NOT NULL,
            source_page INT NULL,
            table_index INT NULL,
            table_json LONGTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_ia_tables_doc (document_id),
            CONSTRAINT fk_ia_tables_doc FOREIGN KEY (document_id) REFERENCES ia_documents(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))
    logger.info("Esquema ia_* verificado/criado.")


def load_embedding_model() -> Optional[SentenceTransformer]:
    if SentenceTransformer is None:
        logger.warning("sentence-transformers não instalado; embeddings não serão gerados.")
        return None
    try:
        model = SentenceTransformer(MODEL_NAME)
    except Exception as exc:  # pragma: no cover - download ou path
        logger.error("Falha ao carregar modelo %s: %s", MODEL_NAME, exc)
        return None
    return model


def load_faiss(index_path: Path, dim: int) -> Optional[object]:
    if faiss is None:
        logger.warning("faiss não instalado; índice vetorial não será usado.")
        return None
    if index_path.exists():
        index = faiss.read_index(str(index_path))
        if index.d != dim:
            logger.warning("Dimensão do índice (%s) difere do modelo (%s); recriando.", index.d, dim)
            index = faiss.IndexFlatIP(dim)
    else:
        index = faiss.IndexFlatIP(dim)
    return index


def append_meta(meta_path: Path, metas: Sequence[dict]) -> None:
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with meta_path.open("a", encoding="utf-8") as f:
        for entry in metas:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def rebuild_meta_from_db(engine, meta_path: Path) -> None:
    """
    Reconstrói o ficheiro de meta a partir de ia_chunks ordenados por vector_index.
    Útil quando o índice FAISS existe mas o meta foi perdido.
    """
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT c.id AS chunk_id, c.document_id, c.page, c.chunk_index
                FROM ia_chunks c
                WHERE c.vector_index IS NOT NULL
                ORDER BY c.vector_index ASC
                """
            )
        ).fetchall()
    if not rows:
        logger.warning("Não foi possível reconstruir meta: nenhum chunk com vector_index encontrado.")
        return
    metas = [
        {
            "chunk_id": row.chunk_id,
            "document_id": row.document_id,
            "page": row.page,
            "chunk_index": row.chunk_index,
        }
        for row in rows
    ]
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with meta_path.open("w", encoding="utf-8") as f:
        for entry in metas:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logger.info("Meta reconstruído a partir da BD: %s (entradas: %s)", meta_path, len(metas))


def rebuild_index_from_db(engine, model: SentenceTransformer, embed_dim: int, index_path: Path, meta_path: Path) -> None:
    """
    Recria o índice FAISS e o meta a partir de todos os ia_chunks.
    Útil quando o índice está vazio mas já existem vetores/textos na BD.
    """
    if faiss is None or model is None:
        logger.warning("Não foi possível reconstruir índice: faiss/model ausentes.")
        return
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT c.id, c.text, c.page, c.chunk_index
                FROM ia_chunks c
                ORDER BY c.id
                """
            )
        ).fetchall()
    if not rows:
        logger.warning("Reconstrução ignorada: nenhum chunk encontrado na BD.")
        return

    index = faiss.IndexFlatIP(embed_dim)
    metas: List[dict] = []
    batch_size = 256
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        texts = [r.text or "" for r in batch]
        vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        index.add(vectors)
        for pos, r in enumerate(batch, start=index.ntotal - len(batch)):
            metas.append(
                {
                    "chunk_id": r.id,
                    "document_id": None,
                    "page": r.page,
                    "chunk_index": r.chunk_index,
                }
            )

    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with meta_path.open("w", encoding="utf-8") as f:
        for entry in metas:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logger.info("Índice FAISS reconstruído (%s vetores) e meta gravado em %s", index.ntotal, index_path)


def ingest(base_path: Path, embeddings_dir: Path) -> None:
    engine = create_engine(settings.DB_URI, pool_pre_ping=True, echo=False)
    ensure_schema(engine)

    model = load_embedding_model()
    embed_dim = model.get_sentence_embedding_dimension() if model else None

    embeddings_dir.mkdir(parents=True, exist_ok=True)
    index_path = embeddings_dir / FAISS_FILENAME
    meta_path = embeddings_dir / META_FILENAME

    faiss_index = load_faiss(index_path, embed_dim) if (model and embed_dim) else None
    # Se já existe índice mas não temos meta, tentar reconstruir a partir da BD
    if faiss_index is not None and not meta_path.exists():
        rebuild_meta_from_db(engine, meta_path)
    # Se o índice existe mas está vazio, tentar reconstruir a partir da BD
    if faiss_index is not None and getattr(faiss_index, "ntotal", 0) == 0 and model is not None and embed_dim:
        rebuild_index_from_db(engine, model, embed_dim, index_path, meta_path)
        faiss_index = load_faiss(index_path, embed_dim)

    allowed_exts = {".pdf", ".docx", ".xlsx", ".xlsm", ".xls", ".csv", ".txt", ".md"}
    files = [p for p in base_path.rglob("*") if p.is_file() and p.suffix.lower() in allowed_exts]
    if not files:
        logger.info("Nenhum ficheiro encontrado em %s", base_path)
        return

    processed = 0
    skipped_existing = 0

    with engine.begin() as conn:
        for file_path in files:
            checksum = compute_checksum(file_path)
            res = conn.execute(
                text("SELECT id FROM ia_documents WHERE checksum = :chk"),
                {"chk": checksum},
            ).first()
            if res:
                skipped_existing += 1
                continue

            stat = file_path.stat()
            supplier = file_path.parent.name
            doc_res = conn.execute(
                text(
                    """
                    INSERT INTO ia_documents (path, filename, ext, size_bytes, modified_at, checksum, supplier)
                    VALUES (:path, :filename, :ext, :size_bytes, :modified_at, :checksum, :supplier)
                    """
                ),
                {
                    "path": str(file_path),
                    "filename": file_path.name,
                    "ext": file_path.suffix.lower(),
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime),
                    "checksum": checksum,
                    "supplier": supplier,
                },
            )
            doc_id = doc_res.lastrowid

            pages = extract_text(file_path)
            chunk_records: List[dict] = []
            for page_num, page_text in pages:
                chunks = chunk_text(page_text)
                for idx, (start, end, chunk_txt) in enumerate(chunks):
                    chunk_records.append(
                        {
                            "document_id": doc_id,
                            "chunk_index": idx,
                            "page": page_num,
                            "start_char": start,
                            "end_char": end,
                            "text": chunk_txt,
                        }
                    )

            if not chunk_records:
                logger.info("Sem texto extraído: %s", file_path)
                processed += 1
                continue

            # Insert chunks
            inserted_ids: List[int] = []
            for rec in chunk_records:
                res_chunk = conn.execute(
                    text(
                        """
                        INSERT INTO ia_chunks (document_id, chunk_index, page, start_char, end_char, text)
                        VALUES (:document_id, :chunk_index, :page, :start_char, :end_char, :text)
                        """
                    ),
                    rec,
                )
                inserted_ids.append(res_chunk.lastrowid)

            # Embeddings
            if model and faiss_index is not None:
                texts = [rec["text"] for rec in chunk_records]
                vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
                start_pos = faiss_index.ntotal
                faiss_index.add(vectors)
                # Atualizar vector_index em lote
                for idx, chunk_id in enumerate(inserted_ids):
                    vec_idx = start_pos + idx
                    conn.execute(
                        text("UPDATE ia_chunks SET vector_index = :vec_idx WHERE id = :cid"),
                        {"vec_idx": vec_idx, "cid": chunk_id},
                    )
                # Append metas
                metas = []
                for idx, chunk_id in enumerate(inserted_ids):
                    metas.append(
                        {
                            "chunk_id": chunk_id,
                            "document_id": doc_id,
                            "page": chunk_records[idx]["page"],
                            "chunk_index": chunk_records[idx]["chunk_index"],
                        }
                    )
                append_meta(meta_path, metas)

            processed += 1
            logger.info("Ingerido: %s (chunks: %s)", file_path, len(chunk_records))

    # Persist index
    if faiss_index is not None and model:
        faiss.write_index(faiss_index, str(index_path))
        logger.info("Índice FAISS guardado em %s", index_path)

    logger.info("Concluído. Novos: %s | Ignorados (já existiam): %s", processed, skipped_existing)


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Ingestão de documentos curados para IA local.")
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
        help="Pasta para guardar índice FAISS/meta (default: share UNC configurado).",
    )
    args = parser.parse_args(argv)

    base_path = args.base
    if not base_path.exists():
        logger.error("Pasta base não existe: %s", base_path)
        return

    embeddings_dir = args.embeddings.resolve()
    if not _path_is_ascii(embeddings_dir):
        fallback_dir = DEFAULT_EMBEDDINGS_DIR
        try:
            fallback_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        if fallback_dir.exists():
            logger.warning(
                "Embeddings path has non-ASCII chars; using shared path: %s",
                fallback_dir,
            )
            embeddings_dir = fallback_dir
    try:
        embeddings_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        logger.error("Falha ao criar pasta de embeddings %s: %s", embeddings_dir, exc)
        return

    ingest(base_path, embeddings_dir)


if __name__ == "__main__":
    main()
