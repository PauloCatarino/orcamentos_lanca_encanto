# db.py
"""Camada de acesso à base de dados usando SQLAlchemy.

Este módulo encapsula a criação de engine e fornece uma função simples
para carregar tabelas da base *MySQL* para ``pandas.DataFrame``.
Está a criar o mapeamento de dados das tabelas orcamentos + orcaemnto_items + dados_def_pecas 
  estes dados vão ser mapeados para o ficheiro exel de onde vão ser feitos os resumos para apresentar no programa em formato dashborad
"""
from __future__ import annotations

from sqlalchemy import create_engine
import pandas as pd

# URI de ligação; ajuste conforme as suas credenciais de acesso
DB_URI = "mysql+pymysql://orcamentos_le:admin@localhost:3306/orcamentos"

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

def carregar_orcamento(num_orcamento: str, versao: str) -> pd.DataFrame:
    """
    Lê os itens de um orçamento, filtrando por num_orcamento e versao
    na tabela principal `orcamentos`.

    Parâmetros:
    -----------
    num_orcamento : str
        O código do orçamento (coluna num_orcamento em orcamentos).
    versao : str
        A versão do orçamento (coluna versao em orcamentos).

    Retorna:
    --------
    pd.DataFrame
        Todos os campos da tabela orcamento_items para aquele
        orçamento/version.
    """
    query = f"""
    SELECT i.*
    FROM `orcamento_items` AS i
    JOIN `orcamentos`      AS o
      ON i.id_orcamento = o.id
    WHERE o.num_orcamento = {num_orcamento!r}
      AND o.versao        = {versao!r};
    """
    return pd.read_sql(query, engine)


if __name__ == "__main__":
    # Exemplo rápido de utilização
    items = carregar_tabela("orcamento_items")
    print(items.head())
