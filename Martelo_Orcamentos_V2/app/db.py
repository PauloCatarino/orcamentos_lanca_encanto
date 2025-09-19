import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from Martelo_Orcamentos_V2.app.config import settings

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Base declarativa do ORM
Base = declarative_base()

# Criar engine SQLAlchemy usando a URI do .env
engine = create_engine(
    settings.DB_URI,
    pool_pre_ping=True,   # evita erros de "MySQL server has gone away"
    echo=False            # podes pôr True para debug detalhado das queries
)

# Criar sessão (SessionLocal será usada em todo o projeto)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Função geradora para obter e fechar sessão automaticamente."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Cria as tabelas no banco de dados, se não existirem."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelas criadas/atualizadas com sucesso (ORM).")
    except SQLAlchemyError as e:
        logger.error("Erro ao criar as tabelas: %s", e)
        raise


def test_connection():
    """Testa a ligação com a base de dados."""
    try:
        with engine.connect() as connection:
            # IMPORTANTE: usar text() para queries no SQLAlchemy 2.0+
            result = connection.execute(text("SELECT 1"))
            logger.info("Ligação à base de dados bem-sucedida! Resultado: %s", result.scalar())
    except SQLAlchemyError as e:
        logger.error("Falha na ligação ao MySQL: %s", e)
        raise
