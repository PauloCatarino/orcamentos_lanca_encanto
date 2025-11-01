from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..db import Base


class CusteioProducaoConfig(Base):
    __tablename__ = "custeio_producao_config"
    __table_args__ = (
        UniqueConstraint(
            "orcamento_id",
            "versao",
            "user_id",
            name="u_custeio_producao_config_ctx",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    orcamento_id = Column(BigInteger, ForeignKey("orcamentos.id", ondelete="CASCADE"), nullable=False, index=True)
    cliente_id = Column(BigInteger, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    ano = Column(String(4), nullable=False)
    num_orcamento = Column(String(16), nullable=False)
    versao = Column(String(4), nullable=False)
    modo = Column(String(8), nullable=False, default="STD")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    valores = relationship(
        "CusteioProducaoValor",
        back_populates="config",
        cascade="all, delete-orphan",
        order_by="CusteioProducaoValor.ordem",
    )


class CusteioProducaoValor(Base):
    __tablename__ = "custeio_producao_valores"
    __table_args__ = (
        UniqueConstraint(
            "config_id",
            "descricao_equipamento",
            name="u_custeio_producao_valor_desc",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    config_id = Column(BigInteger, ForeignKey("custeio_producao_config.id", ondelete="CASCADE"), nullable=False, index=True)
    descricao_equipamento = Column(String(128), nullable=False)
    abreviatura = Column(String(16), nullable=False)
    valor_std = Column(Numeric(18, 4), nullable=False)
    valor_serie = Column(Numeric(18, 4), nullable=False)
    resumo = Column(String(255), nullable=True)
    ordem = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    config = relationship("CusteioProducaoConfig", back_populates="valores")
