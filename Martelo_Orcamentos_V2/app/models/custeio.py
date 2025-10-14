from __future__ import annotations

from sqlalchemy import (
    BigInteger,
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


class CusteioContextMixin:
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    orcamento_id = Column(BigInteger, ForeignKey("orcamentos.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(BigInteger, ForeignKey("orcamento_items.id_item", ondelete="CASCADE"), nullable=False, index=True)
    cliente_id = Column(BigInteger, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    ano = Column(String(4), nullable=False)
    num_orcamento = Column(String(16), nullable=False)
    versao = Column(String(4), nullable=False)
    ordem = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CusteioItem(CusteioContextMixin, Base):
    __tablename__ = "custeio_items"

    descricao_livre = Column(Text, nullable=True)
    def_peca = Column(String(128), nullable=True)
    descricao = Column(String(255), nullable=True)
    qt_mod = Column(Numeric(18, 4), nullable=True)
    qt_und = Column(Numeric(18, 4), nullable=True)
    comp = Column(Numeric(18, 4), nullable=True)
    larg = Column(Numeric(18, 4), nullable=True)
    esp = Column(Numeric(18, 4), nullable=True)
    mps = Column(Boolean, nullable=False, default=False)
    mo = Column(Boolean, nullable=False, default=False)
    orla = Column(Boolean, nullable=False, default=False)
    blk = Column(Boolean, nullable=False, default=False)
    nst = Column(Boolean, nullable=False, default=False)
    mat_default = Column(String(128), nullable=True)
    qt_total = Column(Numeric(18, 4), nullable=True)
    comp_res = Column(Numeric(18, 4), nullable=True)
    larg_res = Column(Numeric(18, 4), nullable=True)
    esp_res = Column(Numeric(18, 4), nullable=True)
    ref_le = Column(String(64), nullable=True)
    descricao_no_orcamento = Column(String(255), nullable=True)
    pliq = Column(Numeric(18, 4), nullable=True)
    und = Column(String(16), nullable=True)
    desp = Column(Numeric(18, 4), nullable=True)
    orl_0_4 = Column(String(64), nullable=True)
    orl_1_0 = Column(String(64), nullable=True)
    tipo = Column(String(64), nullable=True)
    familia = Column(String(64), nullable=True)
    comp_mp = Column(Numeric(18, 4), nullable=True)
    larg_mp = Column(Numeric(18, 4), nullable=True)
    esp_mp = Column(Numeric(18, 4), nullable=True)
    orl_c1 = Column(Numeric(18, 4), nullable=True)
    orl_c2 = Column(Numeric(18, 4), nullable=True)
    orl_l1 = Column(Numeric(18, 4), nullable=True)
    orl_l2 = Column(Numeric(18, 4), nullable=True)
    ml_orl_c1 = Column(Numeric(18, 4), nullable=True)
    ml_orl_c2 = Column(Numeric(18, 4), nullable=True)
    ml_orl_l1 = Column(Numeric(18, 4), nullable=True)
    ml_orl_l2 = Column(Numeric(18, 4), nullable=True)
    custo_orl_c1 = Column(Numeric(18, 4), nullable=True)
    custo_orl_c2 = Column(Numeric(18, 4), nullable=True)
    custo_orl_l1 = Column(Numeric(18, 4), nullable=True)
    custo_orl_l2 = Column(Numeric(18, 4), nullable=True)
    gravar_modulo = Column(Boolean, nullable=False, default=False)
    custo_total_orla = Column(Numeric(18, 4), nullable=True)
    soma_total_ml_orla = Column(Numeric(18, 4), nullable=True)
    area_m2_und = Column(Numeric(18, 4), nullable=True)
    spp_ml_und = Column(Numeric(18, 4), nullable=True)
    cp01_sec = Column(Numeric(18, 4), nullable=True)
    cp01_sec_und = Column(Numeric(18, 4), nullable=True)
    cp02_orl = Column(Numeric(18, 4), nullable=True)
    cp02_orl_und = Column(Numeric(18, 4), nullable=True)
    cp03_cnc = Column(Numeric(18, 4), nullable=True)
    cp03_cnc_und = Column(Numeric(18, 4), nullable=True)
    cp04_abd = Column(Numeric(18, 4), nullable=True)
    cp04_abd_und = Column(Numeric(18, 4), nullable=True)
    cp05_prensa = Column(Numeric(18, 4), nullable=True)
    cp05_prensa_und = Column(Numeric(18, 4), nullable=True)
    cp06_esquad = Column(Numeric(18, 4), nullable=True)
    cp06_esquad_und = Column(Numeric(18, 4), nullable=True)
    cp07_embalagem = Column(Numeric(18, 4), nullable=True)
    cp07_embalagem_und = Column(Numeric(18, 4), nullable=True)
    cp08_mao_de_obra = Column(Numeric(18, 4), nullable=True)
    cp08_mao_de_obra_und = Column(Numeric(18, 4), nullable=True)
    custo_mp_und = Column(Numeric(18, 4), nullable=True)
    custo_mp_total = Column(Numeric(18, 4), nullable=True)
    soma_custo_orla_total = Column(Numeric(18, 4), nullable=True)
    soma_custo_und = Column(Numeric(18, 4), nullable=True)
    soma_custo_total = Column(Numeric(18, 4), nullable=True)
    soma_custo_acb = Column(Numeric(18, 4), nullable=True)
