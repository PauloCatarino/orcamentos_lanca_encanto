from __future__ import annotations

from pathlib import Path
import os
import subprocess
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.services.settings import get_setting


KEY_SUMATRA_PATH = "pdf_sumatra_path"

DEFAULT_SUMATRA_PATHS = (
    r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
    r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
)


def resolve_sumatra_path(db: Optional[Session]) -> Optional[str]:
    if db is not None:
        configured = (get_setting(db, KEY_SUMATRA_PATH, "") or "").strip()
        if configured and Path(configured).is_file():
            return configured
    for path in DEFAULT_SUMATRA_PATHS:
        if Path(path).is_file():
            return path
    return None


def print_pdf_batch(
    file_rows: Iterable[dict],
    *,
    db: Optional[Session] = None,
) -> None:
    sumatra = resolve_sumatra_path(db)
    for row in file_rows:
        file_path = str(row.get("file_path", "") or "")
        if not file_path:
            continue
        copies = int(row.get("quantity") or 1)
        paper_size = str(row.get("paper_size") or "A4")
        orientation = str(row.get("orientation") or "vertical")
        double_sided = bool(row.get("double_sided"))
        page_size = str(row.get("page_size") or "").upper()
        need_fit = bool(page_size and page_size != str(paper_size).upper())
        if sumatra:
            _print_with_sumatra(
                sumatra,
                file_path,
                copies=copies,
                paper_size=paper_size,
                orientation=orientation,
                double_sided=double_sided,
                fit_to_page=need_fit,
            )
        else:
            _print_with_default_app(file_path, copies=copies)


def _print_with_sumatra(
    sumatra_path: str,
    file_path: str,
    *,
    copies: int,
    paper_size: str,
    orientation: str,
    double_sided: bool,
    fit_to_page: bool,
) -> None:
    settings = []
    if paper_size:
        settings.append(f"paper={paper_size}")
    if orientation.lower().startswith("h"):
        settings.append("landscape")
    else:
        settings.append("portrait")
    if fit_to_page:
        settings.append("fit")
    if double_sided:
        settings.append("duplex")
    settings_arg = ",".join(settings)

    for _ in range(max(1, copies)):
        cmd = [
            sumatra_path,
            "-print-to-default",
            "-silent",
            "-exit-when-done",
        ]
        if settings_arg:
            cmd.extend(["-print-settings", settings_arg])
        cmd.append(file_path)
        subprocess.run(cmd, check=False)


def _print_with_default_app(file_path: str, *, copies: int) -> None:
    for _ in range(max(1, copies)):
        try:
            os.startfile(file_path, "print")
        except Exception:
            break
