from __future__ import annotations

from pathlib import Path
import re
from typing import Dict, Optional


_PRODUCER_RE = re.compile(r"/Producer\s*\((.*?)\)", re.IGNORECASE | re.DOTALL)
_CREATOR_RE = re.compile(r"/Creator\s*\((.*?)\)", re.IGNORECASE | re.DOTALL)
_MEDIA_BOX_RE = re.compile(
    r"/MediaBox\s*\[\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*\]",
    re.IGNORECASE,
)


def _read_pdf_text(path: Path, max_bytes: int = 512 * 1024) -> str:
    try:
        with path.open("rb") as fh:
            chunk = fh.read(max_bytes)
        return chunk.decode("latin-1", errors="ignore")
    except Exception:
        return ""


def extract_metadata(file_path: str | Path) -> Dict[str, str]:
    path = Path(file_path)
    text = _read_pdf_text(path)
    metadata: Dict[str, str] = {}

    producer = _first_match(_PRODUCER_RE, text)
    if producer:
        metadata["producer"] = producer

    creator = _first_match(_CREATOR_RE, text)
    if creator:
        metadata["creator"] = creator

    return metadata


def detect_origin(file_path: str | Path) -> str:
    path = Path(file_path)
    text = _read_pdf_text(path)
    if not text:
        return "unknown"

    low = text.lower()
    if "autocad" in low or "imos" in low:
        return "autocad"
    if "/predictor" in low:
        return "autocad"
    if "excel" in low or "microsoft" in low:
        return "excel"
    return "unknown"


def detect_page_size(file_path: str | Path) -> Optional[str]:
    path = Path(file_path)
    text = _read_pdf_text(path)
    if not text:
        return None
    match = _MEDIA_BOX_RE.search(text)
    if not match:
        return None
    try:
        x1, y1, x2, y2 = (float(match.group(i)) for i in range(1, 5))
    except Exception:
        return None
    width = abs(x2 - x1)
    height = abs(y2 - y1)
    short = min(width, height)
    long = max(width, height)
    if _approx_size(short, long, 595, 842):
        return "A4"
    if _approx_size(short, long, 842, 1191):
        return "A3"
    return None


def _first_match(regex: re.Pattern[str], text: str) -> Optional[str]:
    match = regex.search(text)
    if not match:
        return None
    value = match.group(1).strip()
    return value.replace("\x00", " ")


def _approx_size(short: float, long: float, target_short: float, target_long: float, tol: float = 12.0) -> bool:
    return abs(short - target_short) <= tol and abs(long - target_long) <= tol
