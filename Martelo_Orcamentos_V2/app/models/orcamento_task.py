from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func

from ..db import Base


class OrcamentoTask(Base):
    __tablename__ = "orcamento_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    orcamento_id = Column(BigInteger, ForeignKey("orcamentos.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    texto = Column(Text, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    status = Column(String(24), nullable=False, default="Pendente", index=True)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
