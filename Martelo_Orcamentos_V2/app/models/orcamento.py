
from sqlalchemy import (
    BigInteger,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Numeric,
    Boolean,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from ..db import Base


class Orcamento(Base):
    __tablename__ = "orcamentos"
    __table_args__ = (
        UniqueConstraint("ano", "num_orcamento", "versao", name="u_orc_ano_num_ver"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ano = Column(String(4), nullable=False, index=True)
    num_orcamento = Column(String(16), nullable=False, index=True)
    versao = Column(String(2), nullable=False, default="00", index=True)
    client_id = Column(BigInteger, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(32), nullable=True)  # Falta Orçamentar; Enviado; Adjudicado; Sem Interesse; Não Adjudicado
    data = Column(String(10), nullable=True)  # dd-mm-aaaa
    preco_total = Column(Numeric(14, 2), nullable=True)
    ref_cliente = Column(String(64), nullable=True)
    enc_phc = Column(String(64), nullable=True)
    obra = Column(String(255), nullable=True)
    descricao_orcamento = Column(Text, nullable=True)
    localizacao = Column(String(255), nullable=True)
    info_1 = Column(Text, nullable=True)
    info_2 = Column(Text, nullable=True)
    notas = Column(Text, nullable=True)
    extras = Column(JSON, nullable=True)
    reservado1 = Column(String(255), nullable=True)
    reservado2 = Column(String(255), nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    items = relationship("OrcamentoItem", back_populates="orcamento", cascade="all, delete-orphan")


class OrcamentoItem(Base):
    __tablename__ = "orcamento_items"
    __table_args__ = (
        Index("ix_item_ord", "id_orcamento", "item_ord"),
    )

    id_item = Column(BigInteger, primary_key=True, autoincrement=True)
    id_orcamento = Column(BigInteger, ForeignKey("orcamentos.id", ondelete="CASCADE"), nullable=False)
    item_ord = Column(Integer, nullable=False, default=1)  # apenas ordenação visual

    item_nome = Column("item", String(255), nullable=True)

    codigo = Column(String(64), nullable=True)
    descricao = Column(Text, nullable=True)
    altura = Column(Numeric(10, 2), nullable=True, default=0)
    largura = Column(Numeric(10, 2), nullable=True, default=0)
    profundidade = Column(Numeric(10, 2), nullable=True, default=0)
    und = Column(String(16), nullable=True, default="und")
    qt = Column(Numeric(10, 2), nullable=True, default=1)

    preco_unitario = Column(Numeric(14, 2), nullable=True, default=0)
    preco_total = Column(Numeric(14, 2), nullable=True, default=0)
    custo_produzido = Column(Numeric(14, 2), nullable=True, default=0)
    ajuste = Column(Numeric(14, 2), nullable=True, default=0)
    custo_total_orlas = Column(Numeric(14, 2), nullable=True, default=0)
    custo_total_mao_obra = Column(Numeric(14, 2), nullable=True, default=0)
    custo_total_materia_prima = Column(Numeric(14, 2), nullable=True, default=0)
    custo_total_acabamentos = Column(Numeric(14, 2), nullable=True, default=0)

    margem_lucro_perc = Column(Numeric(6, 4), nullable=True, default=0)  # fração 0..1
    valor_margem = Column(Numeric(14, 2), nullable=True, default=0)
    custos_admin_perc = Column(Numeric(6, 4), nullable=True, default=0)
    valor_custos_admin = Column(Numeric(14, 2), nullable=True, default=0)
    margem_acabamentos_perc = Column(Numeric(6, 4), nullable=True, default=0)
    valor_acabamentos = Column(Numeric(14, 2), nullable=True, default=0)
    margem_mp_orlas_perc = Column(Numeric(6, 4), nullable=True, default=0)
    valor_mp_orlas = Column(Numeric(14, 2), nullable=True, default=0)
    margem_mao_obra_perc = Column(Numeric(6, 4), nullable=True, default=0)
    valor_mao_obra = Column(Numeric(14, 2), nullable=True, default=0)

    notas = Column(Text, nullable=True)
    extras = Column(JSON, nullable=True)
    reservado_1 = Column(String(255), nullable=True)
    reservado_2 = Column(String(255), nullable=True)
    reservado_3 = Column(String(255), nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    orcamento = relationship("Orcamento", back_populates="items")
