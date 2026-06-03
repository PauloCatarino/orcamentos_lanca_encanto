# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


ROOT = Path(".").resolve()
PKG = ROOT / "Martelo_Orcamentos_V2"
ICON = ROOT / "martelo.ico"
BUILD_PROFILE = os.getenv("MARTELO_BUILD_PROFILE", "full").strip().lower() or "full"

if BUILD_PROFILE not in {"full", "lean"}:
    raise ValueError(f"Perfil de build invalido: {BUILD_PROFILE}")

datas = [
    (str(PKG / "ui" / "forms"), "Martelo_Orcamentos_V2/ui/forms"),
]

assets_dir = PKG / "ui" / "assets"
if assets_dir.exists():
    datas.append((str(assets_dir), "Martelo_Orcamentos_V2/ui/assets"))

if ICON.exists():
    datas += [
        (str(ICON), "."),
        (str(ICON), "Martelo_Orcamentos_V2"),
    ]

# ReportLab precisa de ficheiros de dados/fonte, mas nao de todos os submodulos.
datas += collect_data_files("reportlab")

binaries = []
hiddenimports = [
    "passlib.handlers.bcrypt",
    "win32com.client",
    "pythoncom",
    "pywintypes",
    "win32clipboard",
    "win32con",
    "win32gui",
    "win32process",
    "pywinauto",
    "pywinauto.application",
    "pywinauto.mouse",
    "pywinauto.controls.uia_controls",
    "pywinauto.controls.win32_controls",
    "comtypes",
    "PySide6.QtPdf",
    "PySide6.QtUiTools",
    "pypdf",
]

excludes = [
    "_pytest",
    "pytest",
    "pytest_asyncio",
    "PySide6.scripts.deploy_lib",
    "pysqlite2",
    "MySQLdb",
    "psycopg2",
    "tensorboard",
]

if BUILD_PROFILE == "lean":
    excludes += [
        "faiss",
        "sentence_transformers",
        "transformers",
        "tokenizers",
        "safetensors",
        "torch",
        "sklearn",
        "scipy",
        "huggingface_hub",
    ]


a = Analysis(
    [str(PKG / "run_dev.py")],
    pathex=[str(PKG)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Martelo_Orcamentos_V2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ICON)] if ICON.exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Martelo_Orcamentos_V2",
)
