from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


INNO_APP_ID = "{D94AEF7B-11A0-48A5-9A65-0F8E5C4AC0B9}"

DEFAULT_SETUP_SHARE_PATH = (
    r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\Instalador_Setup_Martelo"
)
ENV_SETUP_SHARE_PATH = "MARTELO_SETUP_SHARE_PATH"

_VERSION_RE = re.compile(r"(\d+(?:\.\d+)+)")


def get_setup_share_path() -> str:
    value = (os.getenv(ENV_SETUP_SHARE_PATH) or "").strip()
    return value or DEFAULT_SETUP_SHARE_PATH


def parse_version_tuple(version: str) -> Optional[tuple[int, ...]]:
    version = (version or "").strip()
    if not version:
        return None
    m = _VERSION_RE.search(version)
    if not m:
        return None
    try:
        return tuple(int(p) for p in m.group(1).split("."))
    except Exception:
        return None


def parse_version_from_filename(filename: str) -> Optional[tuple[tuple[int, ...], str]]:
    matches = _VERSION_RE.findall(filename or "")
    if not matches:
        return None
    ver_str = matches[-1]
    try:
        ver_tuple = tuple(int(p) for p in ver_str.split("."))
    except Exception:
        return None
    return ver_tuple, ver_str


@dataclass(frozen=True)
class InstallerCandidate:
    version_str: str
    version_tuple: tuple[int, ...]
    path: Path


def find_latest_installer(share_path: str | Path) -> Optional[InstallerCandidate]:
    base = Path(str(share_path))
    try:
        items = list(base.glob("*.exe"))
    except Exception:
        return None

    candidates: list[InstallerCandidate] = []
    for exe_path in items:
        name_lower = exe_path.name.lower()
        if "setup" not in name_lower:
            continue
        if "martelo" not in name_lower:
            continue
        parsed = parse_version_from_filename(exe_path.name)
        if not parsed:
            continue
        ver_tuple, ver_str = parsed
        candidates.append(InstallerCandidate(version_str=ver_str, version_tuple=ver_tuple, path=exe_path))

    if not candidates:
        return None

    return max(candidates, key=lambda c: c.version_tuple)


def get_installed_version(app_id: str = INNO_APP_ID) -> Optional[str]:
    try:
        import winreg  # type: ignore
    except Exception:
        return None

    app_id = (app_id or "").strip()
    if not app_id:
        return None
    if not app_id.startswith("{"):
        app_id = "{" + app_id
    if not app_id.endswith("}"):
        app_id = app_id + "}"

    key_name = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{app_id}_is1"
    views = [0]
    try:
        views = [winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY, 0]
    except Exception:
        views = [0]

    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for view in views:
            try:
                with winreg.OpenKey(root, key_name, 0, winreg.KEY_READ | view) as k:
                    val, _ = winreg.QueryValueEx(k, "DisplayVersion")
                    v = str(val or "").strip()
                    if v:
                        return v
            except FileNotFoundError:
                continue
            except Exception:
                continue
    return None


def get_current_version() -> Optional[str]:
    """
    Versão "atual" do Martelo (o que está a correr nesta máquina).

    Prioridade:
    1) Versão detetada no Windows (Inno Setup / DisplayVersion) — quando instalado via Setup.
    2) Versão definida no código/env (`Martelo_Orcamentos_V2.version`).
    """
    installed = get_installed_version()
    if installed:
        return installed
    try:
        from Martelo_Orcamentos_V2.version import get_app_version

        v = (get_app_version() or "").strip()
        return v or None
    except Exception:
        return None


@dataclass(frozen=True)
class UpdateInfo:
    share_path: str
    installed_version: Optional[str]
    installed_version_tuple: Optional[tuple[int, ...]]
    latest_installer: Optional[InstallerCandidate]
    error: Optional[str] = None

    @property
    def latest_version(self) -> Optional[str]:
        return self.latest_installer.version_str if self.latest_installer else None

    @property
    def latest_version_tuple(self) -> Optional[tuple[int, ...]]:
        return self.latest_installer.version_tuple if self.latest_installer else None

    @property
    def has_update(self) -> bool:
        if not self.latest_installer:
            return False
        if self.installed_version_tuple and self.latest_version_tuple:
            return self.installed_version_tuple < self.latest_version_tuple
        if self.installed_version and self.latest_version:
            return self.installed_version.strip() != self.latest_version.strip()
        return True


def check_for_updates(*, share_path: str | None = None) -> UpdateInfo:
    share = (share_path or "").strip() or get_setup_share_path()
    installed = get_current_version()
    installed_tuple = parse_version_tuple(installed or "")
    try:
        latest = find_latest_installer(share)
        return UpdateInfo(
            share_path=share,
            installed_version=installed,
            installed_version_tuple=installed_tuple,
            latest_installer=latest,
            error=None,
        )
    except Exception as exc:
        return UpdateInfo(
            share_path=share,
            installed_version=installed,
            installed_version_tuple=installed_tuple,
            latest_installer=None,
            error=str(exc),
        )


def stage_installer_to_temp(installer_path: Path) -> Path:
    tmp_dir = Path(tempfile.gettempdir()) / "Martelo_Orcamentos_V2_Update"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    staged = tmp_dir / installer_path.name
    shutil.copy2(installer_path, staged)
    return staged


def launch_installer(installer_path: Path) -> None:
    subprocess.Popen([str(installer_path)], close_fds=True)
