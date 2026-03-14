from __future__ import annotations

import os

ENV_APP_VERSION = "MARTELO_APP_VERSION"

# Atualize este valor quando fizer release.
# Nota: também pode definir a variável de ambiente MARTELO_APP_VERSION (ex.: no .env) para sobrepor.
APP_VERSION = "2.2.1"


def get_app_version() -> str:
    return (os.getenv(ENV_APP_VERSION) or "").strip() or APP_VERSION

