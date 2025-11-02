import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine
from Martelo_Orcamentos_V2.app.config import settings

# Logging básico
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Base declarativa do ORM
Base = declarative_base()

# Engine
engine = create_engine(settings.DB_URI, pool_pre_ping=True, echo=False)
#engine = create_engine(settings.DB_URI, echo=True, future=True)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Gerador de sessão para uso em serviços/GUI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Cria as tabelas se não existirem via ORM.
    Se falhar (ex.: ordem de FKs), aplica o script SQL completo uma vez.
    """
    try:
        # Importar modelos para registar as tabelas
        try:
            from .models import (
                user,
                client,
                orcamento,
                item_children,
                app_setting,
                materia_prima,
                dados_gerais,
                custeio,
                custeio_producao,
            )  # noqa: F401
            
            # Drop custeio_items table if it exists to force recreation with new schema
            if custeio.CusteioItem.__table__.exists(engine):
                custeio.CusteioItem.__table__.drop(engine)
                logger.info("Tabela 'custeio_items' removida para recriação.")

        except Exception:
            pass
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelas criadas/atualizadas com sucesso (ORM).")
    except SQLAlchemyError as e:
        logger.error("Erro ao criar as tabelas (ORM): %s", e)
        # Fallback: executar script SQL uma vez
        try:
            script_path = "Martelo_Orcamentos_V2/scripts/001_init_schema.sql"
            with open(script_path, "r", encoding="utf-8") as f:
                sql = f.read()
            with engine.begin() as conn:
                for stmt in sql.split(";\n"):
                    s = stmt.strip()
                    if s:
                        conn.execute(text(s))
            logger.info("Schema criado via script SQL de fallback.")
        except Exception as ee:
            logger.error("Falha ao aplicar script SQL: %s", ee)
            raise


def test_connection():
    try:
        with engine.connect() as connection:
            res = connection.execute(text("SELECT 1"))
            logger.info("Ligação MySQL OK. Resultado: %s", res.scalar())
    except SQLAlchemyError as e:
        logger.error("Falha na ligação: %s", e)
        raise


