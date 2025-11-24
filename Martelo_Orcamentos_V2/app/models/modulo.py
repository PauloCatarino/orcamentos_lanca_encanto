from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from Martelo_Orcamentos_V2.app.db import Base


class CusteioModulo(Base):
    __tablename__ = "custeio_modulos"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nome = Column(String(255), nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    imagem_path = Column(String(1024), nullable=True)
    is_global = Column(Boolean, nullable=False, default=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    extras = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    linhas = relationship("CusteioModuloLinha", back_populates="modulo", cascade="all, delete-orphan")


class CusteioModuloLinha(Base):
    __tablename__ = "custeio_modulo_linhas"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    modulo_id = Column(BigInteger, ForeignKey("custeio_modulos.id", ondelete="CASCADE"), nullable=False, index=True)
    ordem = Column(Integer, nullable=False, default=0)
    dados = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    modulo = relationship("CusteioModulo", back_populates="linhas")
