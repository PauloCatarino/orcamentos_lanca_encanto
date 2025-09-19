from sqlalchemy import BigInteger, Column, String, DateTime, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from ..db import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nome = Column(String(255), nullable=False, index=True)
    morada = Column(Text, nullable=True)
    email = Column(String(255), nullable=True)
    telefone = Column(String(64), nullable=True)
    num_cliente_phc = Column(String(64), nullable=True, index=True)
    notas = Column(Text, nullable=True)
    extras = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

