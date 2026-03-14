from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

from Martelo_Orcamentos_V2.app.services import pdf_analyzer, pdf_categorizer


EXCLUDED_DIRS = {"mails", "imagens", "excels"}


def scan_folder(
    folder_path: str | Path,
    *,
    nome_plano_cut_rite: Optional[str] = None,
    nome_enc_imos_ix: Optional[str] = None,
    recursive: bool = False,
) -> List[Dict[str, object]]:
    base = Path(folder_path)
    if not base.exists() or not base.is_dir():
        return []

    files = _list_pdfs(base, recursive=recursive)
    rows: List[Dict[str, object]] = []
    for path in files:
        origin = pdf_analyzer.detect_origin(path)
        page_size = pdf_analyzer.detect_page_size(path)
        category, priority = pdf_categorizer.categorize_file(
            path.name,
            nome_plano_cut_rite=nome_plano_cut_rite,
            nome_enc_imos_ix=nome_enc_imos_ix,
            origin=origin,
        )
        defaults = pdf_categorizer.default_config(category)
        rows.append(
            {
                "selected": True,
                "priority": int(priority),
                "file_name": path.name,
                "file_path": str(path),
                "category": category,
                "origin": origin,
                "page_size": page_size,
                "quantity": int(defaults.get("quantity", 1)),
                "paper_size": str(defaults.get("paper_size", "A4")),
                "orientation": str(defaults.get("orientation", "vertical")),
                "page_range": "all",
                "double_sided": False,
                "color_mode": "color",
                "file_size": _safe_size(path),
            }
        )
    rows.sort(key=lambda r: (int(r.get("priority", 99)), str(r.get("file_name", "")).casefold()))
    return rows


def _list_pdfs(base: Path, *, recursive: bool) -> Iterable[Path]:
    if not recursive:
        for entry in base.iterdir():
            if entry.is_file() and entry.suffix.lower() == ".pdf":
                yield entry
        return

    for root, dirs, files in _walk(base):
        for name in files:
            if name.lower().endswith(".pdf"):
                yield Path(root) / name


def _walk(base: Path):
    for root, dirs, files in __import__("os").walk(base):
        dirs[:] = [d for d in dirs if d.casefold() not in EXCLUDED_DIRS]
        yield root, dirs, files


def _safe_size(path: Path) -> int:
    try:
        return int(path.stat().st_size)
    except Exception:
        return 0
