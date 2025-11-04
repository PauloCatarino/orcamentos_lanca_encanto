from __future__ import annotations

from sqlalchemy import Column, Integer, Numeric, String, UniqueConstraint

from ..db import Base


class DefinicaoPeca(Base):
    __tablename__ = "definicoes_pecas"
    __table_args__ = (
        UniqueConstraint("nome_da_peca", name="u_definicoes_pecas_nome"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_peca_principal = Column(String(64), nullable=False)
    subgrupo_peca = Column(String(128), nullable=True)
    nome_da_peca = Column(String(255), nullable=False)

    cp01_sec = Column(Numeric(12, 4), nullable=True)
    cp02_orl = Column(Numeric(12, 4), nullable=True)
    cp03_cnc = Column(Numeric(12, 4), nullable=True)
    cp04_abd = Column(Numeric(12, 4), nullable=True)
    cp05_prensa = Column(Numeric(12, 4), nullable=True)
    cp06_esquad = Column(Numeric(12, 4), nullable=True)
    cp07_embalagem = Column(Numeric(12, 4), nullable=True)
    cp08_mao_de_obra = Column(Numeric(12, 4), nullable=True)

