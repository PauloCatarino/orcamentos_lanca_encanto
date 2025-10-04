from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    BigInteger,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.sql import func

from ..db import Base


class DadosGeraisContextMixin:
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    cliente_id = Column(BigInteger, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
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

    grupo_ferragem = Column(String(64), nullable=True)
    descricao = Column(String(255), nullable=True)
    ref_le = Column(String(64), nullable=True, index=True)
    descricao_material = Column(String(255), nullable=True)
    preco_tab = Column(Numeric(12, 4), nullable=True)
    preco_liq = Column(Numeric(12, 4), nullable=True)
    margem = Column(Numeric(8, 6), nullable=True)
    desconto = Column(Numeric(8, 6), nullable=True)
    und = Column(String(12), nullable=True)
    desp = Column(Numeric(8, 6), nullable=True)
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


class DadosGeraisSistemaCorrer(DadosGeraisContextMixin, Base):
    __tablename__ = "dados_gerais_sistemas_correr"

    grupo_sistema = Column(String(64), nullable=True)
    descricao = Column(String(255), nullable=True)
    ref_le = Column(String(64), nullable=True, index=True)
    descricao_material = Column(String(255), nullable=True)
    preco_tab = Column(Numeric(12, 4), nullable=True)
    preco_liq = Column(Numeric(12, 4), nullable=True)
    margem = Column(Numeric(8, 6), nullable=True)
    desconto = Column(Numeric(8, 6), nullable=True)
    und = Column(String(12), nullable=True)
    desp = Column(Numeric(8, 6), nullable=True)
    tipo = Column(String(64), nullable=True)
    familia = Column(String(64), nullable=True)
    comp_mp = Column(Integer, nullable=True)
    larg_mp = Column(Integer, nullable=True)
    esp_mp = Column(Integer, nullable=True)
    orl_0_4 = Column(String(64), nullable=True)
    orl_1_0 = Column(String(64), nullable=True)
    id_mp = Column(String(64), ForeignKey("materias_primas.id_mp", ondelete="SET NULL"), nullable=True)
    nao_stock = Column(Boolean, nullable=False, default=False)
    reserva_1 = Column(String(255), nullable=True)
    reserva_2 = Column(String(255), nullable=True)
    reserva_3 = Column(String(255), nullable=True)


class DadosGeraisAcabamento(DadosGeraisContextMixin, Base):
    __tablename__ = "dados_gerais_acabamentos"

    grupo_acabamento = Column(String(64), nullable=True)
    descricao = Column(String(255), nullable=True)
    ref_le = Column(String(64), nullable=True, index=True)
    descricao_material = Column(String(255), nullable=True)
    preco_tab = Column(Numeric(12, 4), nullable=True)
    preco_liq = Column(Numeric(12, 4), nullable=True)
    margem = Column(Numeric(8, 6), nullable=True)
    desconto = Column(Numeric(8, 6), nullable=True)
    und = Column(String(12), nullable=True)
    desp = Column(Numeric(8, 6), nullable=True)
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


class DadosGeraisModelo(Base):
    __tablename__ = "dados_gerais_modelos"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    nome_modelo = Column(String(128), nullable=False)
    tipo_menu = Column(String(32), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DadosGeraisModeloItem(Base):
    __tablename__ = "dados_gerais_modelo_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    modelo_id = Column(BigInteger, ForeignKey("dados_gerais_modelos.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_menu = Column(String(32), nullable=False)
    ordem = Column(Integer, nullable=False, default=0)
    dados = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DadosItemsContextMixin(DadosGeraisContextMixin):
    item_id = Column(BigInteger, ForeignKey("orcamento_items.id_item", ondelete="CASCADE"), nullable=False, index=True)
    orcamento_id = Column(BigInteger, ForeignKey("orcamentos.id", ondelete="CASCADE"), nullable=False, index=True)


class DadosItemsMaterial(DadosItemsContextMixin, Base):
    __tablename__ = "dados_items_materiais"

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
    linha = Column(Integer, nullable=True, default=1)
    custo_mp_und = Column(Numeric(12, 4), nullable=True)
    custo_mp_total = Column(Numeric(12, 4), nullable=True)
    reserva_1 = Column(String(255), nullable=True)
    reserva_2 = Column(String(255), nullable=True)
    reserva_3 = Column(String(255), nullable=True)


class DadosItemsFerragem(DadosItemsContextMixin, Base):
    __tablename__ = "dados_items_ferragens"

    grupo_ferragem = Column(String(64), nullable=True)
    descricao = Column(String(255), nullable=True)
    ref_le = Column(String(64), nullable=True, index=True)
    descricao_material = Column(String(255), nullable=True)
    preco_tab = Column(Numeric(12, 4), nullable=True)
    preco_liq = Column(Numeric(12, 4), nullable=True)
    margem = Column(Numeric(8, 6), nullable=True)
    desconto = Column(Numeric(8, 6), nullable=True)
    und = Column(String(12), nullable=True)
    desp = Column(Numeric(8, 6), nullable=True)
    tipo = Column(String(64), nullable=True)
    familia = Column(String(64), nullable=True)
    comp_mp = Column(Integer, nullable=True)
    larg_mp = Column(Integer, nullable=True)
    esp_mp = Column(Integer, nullable=True)
    id_mp = Column(String(64), ForeignKey("materias_primas.id_mp", ondelete="SET NULL"), nullable=True)
    nao_stock = Column(Boolean, nullable=False, default=False)
    linha = Column(Integer, nullable=True, default=1)
    spp_ml_und = Column(Numeric(12, 4), nullable=True)
    custo_mp_und = Column(Numeric(12, 4), nullable=True)
    custo_mp_total = Column(Numeric(12, 4), nullable=True)
    reserva_1 = Column(String(255), nullable=True)
    reserva_2 = Column(String(255), nullable=True)
    reserva_3 = Column(String(255), nullable=True)


class DadosItemsSistemaCorrer(DadosItemsContextMixin, Base):
    __tablename__ = "dados_items_sistemas_correr"

    grupo_sistema = Column(String(64), nullable=True)
    descricao = Column(String(255), nullable=True)
    ref_le = Column(String(64), nullable=True, index=True)
    descricao_material = Column(String(255), nullable=True)
    preco_tab = Column(Numeric(12, 4), nullable=True)
    preco_liq = Column(Numeric(12, 4), nullable=True)
    margem = Column(Numeric(8, 6), nullable=True)
    desconto = Column(Numeric(8, 6), nullable=True)
    und = Column(String(12), nullable=True)
    desp = Column(Numeric(8, 6), nullable=True)
    tipo = Column(String(64), nullable=True)
    familia = Column(String(64), nullable=True)
    comp_mp = Column(Integer, nullable=True)
    larg_mp = Column(Integer, nullable=True)
    esp_mp = Column(Integer, nullable=True)
    orl_0_4 = Column(String(64), nullable=True)
    orl_1_0 = Column(String(64), nullable=True)
    id_mp = Column(String(64), ForeignKey("materias_primas.id_mp", ondelete="SET NULL"), nullable=True)
    nao_stock = Column(Boolean, nullable=False, default=False)
    linha = Column(Integer, nullable=True, default=1)
    custo_mp_und = Column(Numeric(12, 4), nullable=True)
    custo_mp_total = Column(Numeric(12, 4), nullable=True)
    reserva_1 = Column(String(255), nullable=True)
    reserva_2 = Column(String(255), nullable=True)
    reserva_3 = Column(String(255), nullable=True)


class DadosItemsAcabamento(DadosItemsContextMixin, Base):
    __tablename__ = "dados_items_acabamentos"

    grupo_acabamento = Column(String(64), nullable=True)
    descricao = Column(String(255), nullable=True)
    ref_le = Column(String(64), nullable=True, index=True)
    descricao_material = Column(String(255), nullable=True)
    preco_tab = Column(Numeric(12, 4), nullable=True)
    preco_liq = Column(Numeric(12, 4), nullable=True)
    margem = Column(Numeric(8, 6), nullable=True)
    desconto = Column(Numeric(8, 6), nullable=True)
    und = Column(String(12), nullable=True)
    desp = Column(Numeric(8, 6), nullable=True)
    tipo = Column(String(64), nullable=True)
    familia = Column(String(64), nullable=True)
    comp_mp = Column(Integer, nullable=True)
    larg_mp = Column(Integer, nullable=True)
    esp_mp = Column(Integer, nullable=True)
    id_mp = Column(String(64), ForeignKey("materias_primas.id_mp", ondelete="SET NULL"), nullable=True)
    nao_stock = Column(Boolean, nullable=False, default=False)
    linha = Column(Integer, nullable=True, default=1)
    custo_acb_und = Column(Numeric(12, 4), nullable=True)
    custo_acb_total = Column(Numeric(12, 4), nullable=True)
    reserva_1 = Column(String(255), nullable=True)
    reserva_2 = Column(String(255), nullable=True)
    reserva_3 = Column(String(255), nullable=True)


class DadosItemsModelo(Base):
    __tablename__ = "dados_items_modelos"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    orcamento_id = Column(BigInteger, ForeignKey("orcamentos.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(BigInteger, ForeignKey("orcamento_items.id_item", ondelete="SET NULL"), nullable=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    nome_modelo = Column(String(128), nullable=False)
    tipo_menu = Column(String(32), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DadosItemsModeloItem(Base):
    __tablename__ = "dados_items_modelo_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    modelo_id = Column(BigInteger, ForeignKey("dados_items_modelos.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_menu = Column(String(32), nullable=False)
    ordem = Column(Integer, nullable=False, default=0)
    dados = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)