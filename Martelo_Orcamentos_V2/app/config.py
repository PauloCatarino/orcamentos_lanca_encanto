from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- APP ---
    APP_NAME: str = "Martelo_Orcamentos_V2"

    # --- DATABASE ---
    DB_USER: str = "root"
    DB_PASSWORD: str = "admin"
    DB_HOST: str = "localhost"
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

    # --- PERSONALIZAÇÃO ---
    NOME_UTILIZADOR: str = "Utilizador"
    ASSINATURA_HTML: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False

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
