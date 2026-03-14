from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.sql import func

from Martelo_Orcamentos_V2.app.db import Base


class Producao(Base):
    """
    Processo produtivo (obra adjudicada ou criada livremente).
    Codigo AA.NNNN_VV_PP:
      - AA: ultimos 2 digitos do ano
      - NNNN: num. encomenda PHC (4 digitos, zero-fill)
      - VV: versao da obra (2 digitos)
      - PP: versao do plano de corte (2 digitos)
    """

    __tablename__ = "producao"
    __table_args__ = (
        UniqueConstraint("codigo_processo", name="u_producao_codigo"),
        UniqueConstraint("ano", "num_enc_phc", "versao_obra", "versao_plano", name="u_producao_chave"),
        Index("ix_producao_estado", "estado"),
        Index("ix_producao_cliente", "nome_cliente"),
        Index("ix_producao_data_entrega", "data_entrega"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    codigo_processo = Column(String(32), nullable=False, index=True)
    ano = Column(String(4), nullable=False, index=True)
    num_enc_phc = Column(String(16), nullable=False, index=True)
    versao_obra = Column(String(2), nullable=False, default="01")
    versao_plano = Column(String(2), nullable=False, default="01")

    orcamento_id = Column(BigInteger, ForeignKey("orcamentos.id", ondelete="SET NULL"), nullable=True, index=True)
    client_id = Column(BigInteger, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)

    responsavel = Column(String(100), nullable=True)
    estado = Column(String(50), nullable=True)

    nome_cliente = Column(String(255), nullable=True)
    nome_cliente_simplex = Column(String(255), nullable=True)
    num_cliente_phc = Column(String(64), nullable=True)
    ref_cliente = Column(String(64), nullable=True)

    num_orcamento = Column(String(16), nullable=True)
    versao_orc = Column(String(2), nullable=True)

    obra = Column(String(255), nullable=True)
    localizacao = Column(String(255), nullable=True)
    descricao_orcamento = Column(Text, nullable=True)

    data_entrega = Column(String(10), nullable=True)  # dd-mm-aaaa
    data_inicio = Column(String(10), nullable=True)   # dd-mm-aaaa
    preco_total = Column(Numeric(14, 2), nullable=True)
    qt_artigos = Column(Integer, nullable=True)

    descricao_artigos = Column(Text, nullable=True)
    materias_usados = Column(Text, nullable=True)
    descricao_producao = Column(Text, nullable=True)

    notas1 = Column(Text, nullable=True)
    notas2 = Column(Text, nullable=True)
    notas3 = Column(Text, nullable=True)

    imagem_path = Column(String(1024), nullable=True)
    pasta_servidor = Column(String(1024), nullable=True)
    tipo_pasta = Column(String(64), nullable=True)  # Encomenda de Cliente | Encomenda de Cliente Final

    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
