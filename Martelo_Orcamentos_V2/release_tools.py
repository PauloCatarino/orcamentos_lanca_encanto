from __future__ import annotations

import re
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = Path(__file__).resolve().parent / "version.py"
INSTALLER_OUTPUT_DIR = REPO_ROOT / "installer" / "Output"
DEFAULT_SETUP_PASSWORD = "Martelo_V2"

_APP_VERSION_RE = re.compile(
    r'^(?P<prefix>\s*APP_VERSION\s*=\s*")(?P<version>\d+\.\d+\.\d+)(?P<suffix>".*)$',
    re.MULTILINE,
)


def parse_semver(version: str) -> tuple[int, int, int]:
    text = (version or "").strip()
    parts = text.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError(f"Versao invalida: {version!r}")
    return int(parts[0]), int(parts[1]), int(parts[2])


def bump_semver(version: str, part: str) -> str:
    major, minor, patch = parse_semver(version)
    key = (part or "").strip().lower()
    if key == "major":
        return f"{major + 1}.0.0"
    if key == "minor":
        return f"{major}.{minor + 1}.0"
    if key == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Tipo de incremento invalido: {part!r}")


def read_static_app_version(version_file: Path = VERSION_FILE) -> str:
    text = version_file.read_text(encoding="utf-8")
    match = _APP_VERSION_RE.search(text)
    if not match:
        raise ValueError(f"Nao encontrei APP_VERSION em {version_file}")
    return match.group("version")


def write_static_app_version(new_version: str, version_file: Path = VERSION_FILE) -> str:
    parse_semver(new_version)
    text = version_file.read_text(encoding="utf-8")
    match = _APP_VERSION_RE.search(text)
    if not match:
        raise ValueError(f"Nao encontrei APP_VERSION em {version_file}")
    updated = _APP_VERSION_RE.sub(
        rf'\g<prefix>{new_version}\g<suffix>',
        text,
        count=1,
    )
    version_file.write_text(updated, encoding="utf-8")
    return new_version


def find_installer_output(
    app_version: str,
    output_dir: Path = INSTALLER_OUTPUT_DIR,
) -> Path:
    candidates = sorted(
        output_dir.glob(f"Setup_*_{app_version}.exe"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            f"Nao encontrei o instalador da versao {app_version} em {output_dir}"
        )
    return candidates[0]


def resolve_setup_share_path() -> Path:
    from Martelo_Orcamentos_V2.utils_version import get_setup_share_path

    return Path(get_setup_share_path())


def copy_installer_to_share(installer_path: Path, share_path: Path) -> Path:
    share_path.mkdir(parents=True, exist_ok=True)
    destination = share_path / installer_path.name
    shutil.copy2(installer_path, destination)
    return destination
