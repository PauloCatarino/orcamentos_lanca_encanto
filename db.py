# db.py
"""Camada de acesso à base de dados usando SQLAlchemy.

Este módulo encapsula a criação de engine e fornece uma função simples
para carregar tabelas da base *MySQL* para ``pandas.DataFrame``.
"""
from __future__ import annotations

from sqlalchemy import create_engine
import pandas as pd

# URI de ligação; ajuste conforme as suas credenciais de acesso
DB_URI = "mysql+pymysql://user:senha@localhost:3306/orcamentos_lanca_encanto"

# Criação do engine SQLAlchemy
engine = create_engine(DB_URI)


def carregar_tabela(nome_tabela: str) -> pd.DataFrame:
    """Lê toda a tabela ``nome_tabela`` para um ``DataFrame``.

    Parameters
    ----------
    nome_tabela : str
        Nome da tabela ou view existente na base ``orcamentos_lanca_encanto``.

    Returns
    -------
    pandas.DataFrame
        DataFrame com os dados da tabela solicitada.
    """
    query = f"SELECT * FROM {nome_tabela}"
    return pd.read_sql(query, engine)


if __name__ == "__main__":
    # Exemplo rápido de utilização
    items = carregar_tabela("orcamento_items")
    print(items.head())
