from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint, func, Index

from Martelo_Orcamentos_V2.app.db import Base


class UserFeatureFlag(Base):
    __tablename__ = "user_feature_flags"
    __table_args__ = (
        UniqueConstraint("user_id", "feature_key", name="u_user_feature"),
        Index("idx_user_feature_user", "user_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    feature_key = Column(String(64), nullable=False)
    enabled = Column(Boolean, default=False)

    reservado1 = Column(String(255), nullable=True)
    reservado2 = Column(String(255), nullable=True)
    reservado3 = Column(String(255), nullable=True)
    reservado4 = Column(String(255), nullable=True)
    reservado5 = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
