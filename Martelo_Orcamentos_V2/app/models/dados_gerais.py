from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.sql import func

from ..db import Base


class DadosGeraisContextMixin:
    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    ano = Column(String(4), nullable=False, index=True)
    num_orcamento = Column(String(16), nullable=False, index=True)
    versao = Column(String(4), nullable=False, index=True)
    ordem = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DadosGeraisMaterial(DadosGeraisContextMixin, Base):
    __tablename__ = "dados_gerais_materiais"

    grupo_material = Column(String(64), nullable=True)
    descricao = Column(String(255), nullable=True)
    ref_le = Column(String(64), nullable=True, index=True)
    descricao_material = Column(String(255), nullable=True)
    preco_tab = Column(Numeric(12, 4), nullable=True)
    preco_liq = Column(Numeric(12, 4), nullable=True)
    margem = Column(Numeric(8, 6), nullable=True)
    desconto = Column(Numeric(8, 6), nullable=True)
    und = Column(String(12), nullable=True)
    desp = Column(Numeric(8, 6), nullable=True)
    orl_0_4 = Column(String(64), nullable=True)
    orl_1_0 = Column(String(64), nullable=True)
    tipo = Column(String(64), nullable=True)
    familia = Column(String(64), nullable=True)
    comp_mp = Column(Integer, nullable=True)
    larg_mp = Column(Integer, nullable=True)
    esp_mp = Column(Integer, nullable=True)
    id_mp = Column(String(64), ForeignKey("materias_primas.id_mp", ondelete="SET NULL"), nullable=True)
    nao_stock = Column(Boolean, nullable=False, default=False)
    reserva_1 = Column(String(255), nullable=True)
    reserva_2 = Column(String(255), nullable=True)
    reserva_3 = Column(String(255), nullable=True)


class DadosGeraisFerragem(DadosGeraisContextMixin, Base):
    __tablename__ = "dados_gerais_ferragens"

    categoria = Column(String(64), nullable=True)
    descricao = Column(String(255), nullable=True)
    referencia = Column(String(64), nullable=True)
    fornecedor = Column(String(128), nullable=True)
    preco_tab = Column(Numeric(12, 4), nullable=True)
    preco_liq = Column(Numeric(12, 4), nullable=True)
    margem = Column(Numeric(8, 6), nullable=True)
    desconto = Column(Numeric(8, 6), nullable=True)
    und = Column(String(12), nullable=True)
    qt = Column(Numeric(12, 4), nullable=True)
    nao_stock = Column(Boolean, nullable=False, default=False)
    reserva_1 = Column(String(255), nullable=True)
    reserva_2 = Column(String(255), nullable=True)
    reserva_3 = Column(String(255), nullable=True)


class DadosGeraisSistemaCorrer(DadosGeraisContextMixin, Base):
    __tablename__ = "dados_gerais_sistemas_correr"

    categoria = Column(String(64), nullable=True)
    descricao = Column(String(255), nullable=True)
    referencia = Column(String(64), nullable=True)
    fornecedor = Column(String(128), nullable=True)
    preco_tab = Column(Numeric(12, 4), nullable=True)
    preco_liq = Column(Numeric(12, 4), nullable=True)
    margem = Column(Numeric(8, 6), nullable=True)
    desconto = Column(Numeric(8, 6), nullable=True)
    und = Column(String(12), nullable=True)
    qt = Column(Numeric(12, 4), nullable=True)
    nao_stock = Column(Boolean, nullable=False, default=False)
    reserva_1 = Column(String(255), nullable=True)
    reserva_2 = Column(String(255), nullable=True)
    reserva_3 = Column(String(255), nullable=True)


class DadosGeraisAcabamento(DadosGeraisContextMixin, Base):
    __tablename__ = "dados_gerais_acabamentos"

    categoria = Column(String(64), nullable=True)
    descricao = Column(String(255), nullable=True)
    referencia = Column(String(64), nullable=True)
    fornecedor = Column(String(128), nullable=True)
    preco_tab = Column(Numeric(12, 4), nullable=True)
    preco_liq = Column(Numeric(12, 4), nullable=True)
    margem = Column(Numeric(8, 6), nullable=True)
    desconto = Column(Numeric(8, 6), nullable=True)
    und = Column(String(12), nullable=True)
    qt = Column(Numeric(12, 4), nullable=True)
    nao_stock = Column(Boolean, nullable=False, default=False)
    reserva_1 = Column(String(255), nullable=True)
    reserva_2 = Column(String(255), nullable=True)
    reserva_3 = Column(String(255), nullable=True)


class DadosGeraisModelo(Base):
    __tablename__ = "dados_gerais_modelos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    nome_modelo = Column(String(128), nullable=False)
    tipo_menu = Column(String(32), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DadosGeraisModeloItem(Base):
    __tablename__ = "dados_gerais_modelo_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    modelo_id = Column(Integer, ForeignKey("dados_gerais_modelos.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_menu = Column(String(32), nullable=False)
    ordem = Column(Integer, nullable=False, default=0)
    dados = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

