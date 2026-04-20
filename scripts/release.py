from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Martelo_Orcamentos_V2.release_tools import (  # noqa: E402
    DEFAULT_SETUP_PASSWORD,
    bump_semver,
    copy_installer_to_share,
    find_installer_output,
    read_static_app_version,
    resolve_setup_share_path,
    write_static_app_version,
)

LOG_FILE = REPO_ROOT / "installer" / "release_last.log"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Incrementa a versao do Martelo, gera o setup e copia-o para o servidor."
    )
    parser.add_argument(
        "bump",
        nargs="?",
        choices=("patch", "minor", "major"),
        default="patch",
        help="Tipo de incremento da versao semantica. Omissao = patch.",
    )
    parser.add_argument(
        "--set-version",
        dest="set_version",
        help="Define explicitamente a versao final (ex.: 2.3.0).",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("MARTELO_SETUP_PASSWORD") or DEFAULT_SETUP_PASSWORD,
        help="Password do instalador. Omissao = MARTELO_SETUP_PASSWORD ou valor predefinido.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Atualiza apenas a versao no codigo e nao executa o build.",
    )
    parser.add_argument(
        "--skip-copy",
        action="store_true",
        help="Gera o setup localmente mas nao o copia para a pasta do servidor.",
    )
    return parser.parse_args()


def _emit(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _reset_log() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text("", encoding="utf-8")


def _run_build_installer(password: str) -> None:
    env = os.environ.copy()
    env["MARTELO_SETUP_PASSWORD"] = password
    process = subprocess.Popen(
        ["cmd", "/c", str(REPO_ROOT / "build_installer.bat")],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for raw_line in process.stdout:
        line = raw_line.rstrip()
        if line:
            _emit(line)
    exit_code = process.wait()
    if exit_code != 0:
        raise subprocess.CalledProcessError(exit_code, process.args)


def main() -> int:
    _reset_log()
    args = _parse_args()
    current_version = read_static_app_version()
    target_version = args.set_version or bump_semver(current_version, args.bump)
    started = time.perf_counter()

    version_changed = target_version != current_version
    _emit("[1/4] Inicio do processo de release.")
    _emit(f"Versao atual em codigo: {current_version}")
    _emit(f"Versao alvo: {target_version}")
    if version_changed:
        write_static_app_version(target_version)
        _emit(f"Versao atualizada em version.py: {current_version} -> {target_version}")
    else:
        _emit(f"Versao mantida: {target_version}")

    try:
        if args.skip_build:
            _emit("Build ignorado por pedido do utilizador.")
            return 0

        _emit("[2/4] A gerar executavel e instalador local.")
        _run_build_installer(args.password)
        installer_path = find_installer_output(target_version)
        _emit(f"Instalador local criado: {installer_path}")

        if args.skip_copy:
            elapsed = time.perf_counter() - started
            _emit("[3/4] Copia para o servidor ignorada por pedido do utilizador.")
            _emit(f"[4/4] Release concluida com sucesso em {elapsed:.1f}s.")
            return 0

        _emit("[3/4] A copiar instalador para o servidor.")
        share_path = resolve_setup_share_path()
        copied_path = copy_installer_to_share(installer_path, share_path)
        elapsed = time.perf_counter() - started
        _emit(f"Instalador copiado para: {copied_path}")
        _emit(f"[4/4] Release concluida com sucesso em {elapsed:.1f}s.")
        return 0
    except Exception as exc:
        _emit(f"[ERRO] Release falhou: {exc}")
        if version_changed:
            write_static_app_version(current_version)
            _emit(f"A versao em codigo foi reposta para {current_version}.")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
