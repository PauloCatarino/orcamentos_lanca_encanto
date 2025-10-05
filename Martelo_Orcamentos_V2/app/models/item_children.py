from sqlalchemy import BigInteger, Column, String, Text, DateTime, Numeric, Integer
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db import Base


class _ChildBase:
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # NOTA: FK removida temporariamente para evitar problemas de criação em alguns ambientes.
    # A coluna mantém o mesmo nome e tipo para reativar a FK numa fase posterior.
    id_item_fk = Column(BigInteger, nullable=False, index=True)
    notas = Column(Text, nullable=True)
    extras = Column(JSON, nullable=True)
    reservado1 = Column(String(255), nullable=True)
    reservado2 = Column(String(255), nullable=True)
    reservado3 = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DadosModuloMedidas(Base, _ChildBase):
    __tablename__ = "dados_modulo_medidas"

    H = Column(Numeric(10, 2), default=0)
    L = Column(Numeric(10, 2), default=0)
    P = Column(Numeric(10, 2), default=0)
    H1 = Column(Numeric(10, 2), default=0)
    L1 = Column(Numeric(10, 2), default=0)
    P1 = Column(Numeric(10, 2), default=0)
    H2 = Column(Numeric(10, 2), default=0)
    L2 = Column(Numeric(10, 2), default=0)
    P2 = Column(Numeric(10, 2), default=0)
    H3 = Column(Numeric(10, 2), default=0)
    L3 = Column(Numeric(10, 2), default=0)
    P3 = Column(Numeric(10, 2), default=0)
    H4 = Column(Numeric(10, 2), default=0)
    L4 = Column(Numeric(10, 2), default=0)
    P4 = Column(Numeric(10, 2), default=0)


class DadosDefPecas(Base, _ChildBase):
    __tablename__ = "dados_def_pecas"

    descricao_livre = Column(Text)
    def_peca = Column(String(255))
    descricao = Column(Text)
    qt_mod = Column(String(64))
    qt_und = Column(Numeric(10, 2))
    comp = Column(String(255))
    larg = Column(String(255))
    esp = Column(String(255))
    mps = Column(Integer)  # boolean int
    mo = Column(Integer)
    orla = Column(Integer)
    blk = Column(Integer)
    mat_default = Column(String(100))
    tab_default = Column(String(100))
    ref_le = Column(String(100))
    descricao_no_orcamento = Column(Text)
    ptab = Column(Numeric(12, 2))
    pliq = Column(Numeric(12, 2))
    des1plus = Column(Numeric(6, 2))
    des1minus = Column(Numeric(6, 2))
    und = Column(String(20))
    desp = Column(Numeric(6, 4))
    corres_orla_0_4 = Column(String(50))
    corres_orla_1_0 = Column(String(50))
    tipo = Column(String(50))
    familia = Column(String(50))
    comp_mp = Column(Numeric(10, 2))
    larg_mp = Column(Numeric(10, 2))
    esp_mp = Column(Numeric(10, 2))
    mp = Column(Integer)
    orla_c1 = Column(Numeric(10, 2))
    orla_c2 = Column(Numeric(10, 2))
    orla_l1 = Column(Numeric(10, 2))
    orla_l2 = Column(Numeric(10, 2))
    ml_c1 = Column(Numeric(12, 2))
    ml_c2 = Column(Numeric(12, 2))
    ml_l1 = Column(Numeric(12, 2))
    ml_l2 = Column(Numeric(12, 2))
    custo_ml_c1 = Column(Numeric(12, 2))
    custo_ml_c2 = Column(Numeric(12, 2))
    custo_ml_l1 = Column(Numeric(12, 2))
    custo_ml_l2 = Column(Numeric(12, 2))
    qt_total = Column(Numeric(12, 2))
    comp_res = Column(Numeric(10, 2))
    larg_res = Column(Numeric(10, 2))
    esp_res = Column(Numeric(10, 2))
    area_m2_und = Column(Numeric(12, 4))
    spp_ml_und = Column(Numeric(12, 4))
    cp09_custo_mp = Column(Numeric(12, 2))
    custo_mp_und = Column(Numeric(12, 2))
    custo_mp_total = Column(Numeric(12, 2))
    soma_custo_und = Column(Numeric(12, 2))
    soma_custo_total = Column(Numeric(12, 2))
    soma_custo_acb = Column(Numeric(12, 2))


