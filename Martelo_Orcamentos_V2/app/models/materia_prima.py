from sqlalchemy import Column, String, Numeric, Text, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from ..db import Base


class MateriaPrima(Base):
    __tablename__ = "materias_primas"

    id_mp = Column(String(64), primary_key=True)
    ref_phc = Column(String(64), index=True, nullable=True)
    ref_fornecedor = Column(String(64), index=True, nullable=True)
    ref_le = Column(String(64), index=True, nullable=True)
    descricao_phc = Column(Text, nullable=True)
    descricao_orcamento = Column(Text, nullable=True)
    preco_tabela = Column(Numeric(14, 4), nullable=True)
    margem = Column(Numeric(10, 4), nullable=True)
    desconto = Column(Numeric(10, 4), nullable=True)
    pliq = Column(Numeric(14, 4), nullable=True)
    und = Column(String(16), nullable=True)
    desp = Column(Numeric(10, 4), nullable=True)
    comp_mp = Column(Numeric(14, 4), nullable=True)
    larg_mp = Column(Numeric(14, 4), nullable=True)
    esp_mp = Column(Numeric(14, 4), nullable=True)
    tipo = Column(String(64), nullable=True)
    familia = Column(String(64), nullable=True)
    cor = Column(String(64), nullable=True)
    orl_0_4 = Column(Numeric(10, 4), nullable=True)
    orl_1_0 = Column(Numeric(10, 4), nullable=True)
    cor_ref_material = Column(String(128), nullable=True)
    nome_fornecedor = Column(String(128), nullable=True)
    nome_fabricante = Column(String(128), nullable=True)
    data_ultimo_preco = Column(String(32), nullable=True)
    aplicacao = Column(String(128), nullable=True)
    stock = Column(Numeric(14, 4), nullable=True)
    notas_2 = Column(Text, nullable=True)
    notas_3 = Column(Text, nullable=True)
    notas_4 = Column(Text, nullable=True)


class MateriaPrimaPreference(Base):
    __tablename__ = "materia_prima_preferences"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    columns = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

