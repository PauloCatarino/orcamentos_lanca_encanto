from sqlalchemy import BigInteger, Column, String, DateTime, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from ..db import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nome = Column(String(255), nullable=False, index=True)
    nome_simplex = Column(String(255), nullable=True, index=True)
    morada = Column(Text, nullable=True)
    email = Column(String(255), nullable=True)
    web_page = Column(String(255), nullable=True)
    telefone = Column(String(64), nullable=True)
    telemovel = Column(String(64), nullable=True)
    num_cliente_phc = Column(String(64), nullable=True, index=True)
    info_1 = Column(Text, nullable=True)
    info_2 = Column(Text, nullable=True)
    notas = Column(Text, nullable=True)  # campo livre adicional
    extras = Column(JSON, nullable=True)
    reservado1 = Column(String(255), nullable=True)
    reservado2 = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
