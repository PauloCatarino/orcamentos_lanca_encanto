from __future__ import annotations

from pathlib import Path
import sys


def resolve_package_asset_path(*relative_parts: str) -> Path:
    package_root = Path(__file__).resolve().parents[2]
    candidates: list[Path] = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        base = Path(meipass)
        candidates.append(base.joinpath(*relative_parts))
        candidates.append(base / "Martelo_Orcamentos_V2" / Path(*relative_parts))

    candidates.append(package_root.joinpath(*relative_parts))

    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except Exception:
            continue
    return package_root.joinpath(*relative_parts)
