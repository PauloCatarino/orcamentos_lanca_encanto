import logging
from sqlalchemy import create_engine, text, event, inspect
from typing import Callable
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session as _Session
from sqlalchemy.orm import declarative_base, sessionmaker
from Martelo_Orcamentos_V2.app.config import settings

# Logging básico
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Base declarativa do ORM
Base = declarative_base()

# --------------------
# Resiliência DB
# --------------------

_DISCONNECT_HINTS = (
    "server has gone away",
    "lost connection",
    "is closed",
    "connection was killed",
    "connection reset",
    "broken pipe",
    "not connected",
    "can't connect",
    "timed out",
)

_DISCONNECT_HANDLERS: list[Callable[[BaseException], None]] = []


def register_disconnect_handler(handler: Callable[[BaseException], None]) -> None:
    if handler and handler not in _DISCONNECT_HANDLERS:
        _DISCONNECT_HANDLERS.append(handler)


def _notify_disconnect(exc: BaseException) -> None:
    for handler in list(_DISCONNECT_HANDLERS):
        try:
            handler(exc)
        except Exception:
            continue


def is_disconnect_error(exc: BaseException) -> bool:
    """
    Heurística para detetar perdas de ligação ao MySQL/PyMySQL.

    Nota: SQLAlchemy marca muitos casos em `DBAPIError.connection_invalidated`,
    mas também fazemos fallback por mensagem/códigos comuns.
    """
    if isinstance(exc, DBAPIError) and getattr(exc, "connection_invalidated", False):
        return True

    root = getattr(exc, "orig", None) or exc
    args = getattr(root, "args", None)
    try:
        if isinstance(args, tuple) and args and isinstance(args[0], int):
            # Códigos típicos MySQL/PyMySQL:
            # 2006: MySQL server has gone away
            # 2013: Lost connection to MySQL server during query
            # 2003: Can't connect to MySQL server
            if int(args[0]) in (2003, 2006, 2013):
                return True
    except Exception:
        pass

    msg = str(exc).casefold()
    return any(h in msg for h in _DISCONNECT_HINTS)


class ResilientSession(_Session):
    """
    Session que tenta recuperar de ligações caídas:
    - em `execute()`: faz rollback/close + dispose() do engine e repete 1x.
    - em `commit()`: faz rollback/close e propaga o erro (não faz retry).
    """

    def _invalidate(self) -> None:
        try:
            super().rollback()
        except Exception:
            pass
        try:
            super().close()
        except Exception:
            pass
        try:
            engine.dispose()
        except Exception:
            pass

    def execute(self, *args, **kwargs):  # type: ignore[override]
        try:
            return super().execute(*args, **kwargs)
        except (DBAPIError, OperationalError) as exc:
            if is_disconnect_error(exc):
                _notify_disconnect(exc)
                self._invalidate()
                try:
                    return super().execute(*args, **kwargs)
                except (DBAPIError, OperationalError) as exc2:
                    if is_disconnect_error(exc2):
                        _notify_disconnect(exc2)
                        self._invalidate()
                    raise
            raise

    def commit(self) -> None:  # type: ignore[override]
        try:
            return super().commit()
        except (DBAPIError, OperationalError) as exc:
            if is_disconnect_error(exc):
                _notify_disconnect(exc)
                self._invalidate()
            raise

# Engine
engine = create_engine(
    settings.DB_URI,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        # reduz bloqueios na UI quando o servidor está indisponível
        "connect_timeout": 5,
        # em PyMySQL estes timeouts aplicam-se a leitura/escrita no socket
        "read_timeout": 30,
        "write_timeout": 30,
    },
    echo=False,
)


def _ensure_runtime_columns() -> None:
    """Add small backward-compatible columns that `create_all()` cannot add."""
    try:
        inspector = inspect(engine)
        if "custeio_items" not in inspector.get_table_names():
            return
        existing_columns = {col["name"] for col in inspector.get_columns("custeio_items")}
        if "qt_manual_override" not in existing_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE custeio_items "
                        "ADD COLUMN qt_manual_override BOOLEAN NOT NULL DEFAULT 0"
                    )
                )
            logger.info("Coluna custeio_items.qt_manual_override adicionada com sucesso.")
    except Exception as exc:
        logger.warning("Nao foi possivel verificar/adicionar colunas runtime: %s", exc)

@event.listens_for(engine, "handle_error")
def _on_engine_error(context) -> None:
    try:
        exc = getattr(context, "original_exception", None) or getattr(context, "exception", None)
        if exc is None:
            return
        if getattr(context, "is_disconnect", False) or is_disconnect_error(exc):
            _notify_disconnect(exc)
    except Exception:
        pass


@event.listens_for(engine.pool, "invalidate")
def _on_pool_invalidate(_dbapi_conn, _conn_record, exception) -> None:
    try:
        if exception is not None and is_disconnect_error(exception):
            _notify_disconnect(exception)
    except Exception:
        pass

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=ResilientSession)


def get_db():
    """Gerador de sessão para uso em serviços/GUI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Cria as tabelas se não existirem via ORM.

    O arranque nunca deve recriar automaticamente uma base que já tenha dados.
    """
    try:
        # Importar modelos para registar as tabelas
        try:
            from .models import (
                user,
                client,
                cliente_temporario,
                orcamento,
                orcamento_task,
                item_children,
                app_setting,
                materia_prima,
                dados_gerais,
                custeio,
                custeio_producao,
                producao,
                modulo,
                pdf_manager,
                user_feature_flag,
            )  # noqa: F401
        except Exception:
            pass
        Base.metadata.create_all(bind=engine)
        _ensure_runtime_columns()
        logger.info("Tabelas criadas/atualizadas com sucesso (ORM).")
    except SQLAlchemyError as e:
        logger.error("Erro ao criar as tabelas (ORM): %s", e)
        try:
            existing_tables = inspect(engine).get_table_names()
        except Exception:
            existing_tables = []

        if existing_tables:
            logger.error(
                "Fallback SQL automatico bloqueado para proteger dados existentes. "
                "Tabelas detectadas: %s",
                ", ".join(sorted(existing_tables)),
            )
        else:
            logger.error(
                "Nao foi possivel inicializar o schema via ORM e o fallback automatico foi desativado "
                "por seguranca. Execute a criacao/migracao manualmente."
            )
        raise


def test_connection():
    try:
        with engine.connect() as connection:
            res = connection.execute(text("SELECT 1"))
            logger.info("Ligação MySQL OK. Resultado: %s", res.scalar())
    except SQLAlchemyError as e:
        logger.error("Falha na ligação: %s", e)
        raise



