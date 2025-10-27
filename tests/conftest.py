import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Martelo_Orcamentos_V2.app.db import Base


@pytest.fixture(scope="function")
def db_session(tmp_path):
    """Cria uma DB SQLite em memória e devolve uma Session limpa por teste.

    Usa scope function para isolar cada teste.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    try:
        yield sess
    finally:
        sess.close()
