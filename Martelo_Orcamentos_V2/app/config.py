import sys
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


def _resolve_env_file() -> str:
    """
    Resolve o caminho do .env de forma robusta:
    - em executável (PyInstaller): ao lado do .exe
    - em dev: no CWD ou na raiz do repositório
    """
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        try:
            candidates.append(Path(sys.executable).resolve().parent / ".env")
        except Exception:
            pass
    try:
        candidates.append(Path.cwd() / ".env")
    except Exception:
        pass
    try:
        # .../Martelo_Orcamentos_V2/app/config.py -> raiz repo = parents[3]
        candidates.append(Path(__file__).resolve().parents[3] / ".env")
    except Exception:
        pass

    for path in candidates:
        try:
            if path.is_file():
                return str(path)
        except Exception:
            continue
    return ".env"


class Settings(BaseSettings):
    # --- APP ---
    APP_NAME: str = "Martelo_Orcamentos_V2"

    # --- DATABASE ---
    DB_USER: str = "orc_user"
    DB_PASSWORD: str = "senha_forte"
    DB_HOST: str = "192.168.5.201"
    DB_PORT: int = 3306
    DB_NAME: str = "orcamentos_v2"
    DB_CHARSET: str = "utf8mb4"
    DB_URI: str = ""

    # --- EMAIL ---
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 465
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_SSL: bool = True

    # --- PRODUCAO ---
    PRODUCAO_BASE_PATH: str = r"\\SERVER_LE_Lanca_Encanto\LancaEncanto\Dep_Producao"
    PRODUCAO_PASTA_ENCOMENDA: str = "Encomenda de Cliente"
    PRODUCAO_PASTA_ENCOMENDA_FINAL: str = "Encomenda de Cliente Final"

    # --- PERSONALIZAÇÃO ---
    NOME_UTILIZADOR: str = "Utilizador"
    ASSINATURA_HTML: str | None = None

    # --- IA / OPENAI ---
    OPENAI_API_KEY: str | None = None

    # --- PHC (SQL Server, read-only) ---
    PHC_SQL_SERVER: str | None = None
    PHC_SQL_DATABASE: str | None = None
    PHC_SQL_USER: str | None = None
    PHC_SQL_PASSWORD: str | None = None
    PHC_SQL_TRUSTED: bool = False
    PHC_SQL_TRUST_SERVER_CERTIFICATE: bool = True

    # --- STREAMLIT (SQL Server, read-only) ---
    STREAMLIT_SQL_SERVER: str | None = None
    STREAMLIT_SQL_DATABASE: str | None = None
    STREAMLIT_SQL_USER: str | None = None
    STREAMLIT_SQL_PASSWORD: str | None = None
    STREAMLIT_SQL_TRUSTED: bool = False
    STREAMLIT_SQL_TRUST_SERVER_CERTIFICATE: bool = True

    model_config = ConfigDict(env_file=_resolve_env_file(), case_sensitive=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Se DB_URI não estiver definido no .env, monta automaticamente
        if not self.DB_URI:
            self.DB_URI = (
                f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset={self.DB_CHARSET}"
            )

    def __repr__(self):
        """Esconde info sensível quando imprimido"""
        return (
            f"<Settings APP_NAME={self.APP_NAME} "
            f"DB_URI={self.DB_URI.replace(self.DB_PASSWORD, '****')} "
            f"SMTP_USER={self.SMTP_USER} SMTP_SSL={self.SMTP_SSL}>"
        )


settings = Settings()
