from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
    func,
)

from Martelo_Orcamentos_V2.app.db import Base


class PDFPrintJob(Base):
    __tablename__ = "pdf_print_job"
    __table_args__ = (
        Index("idx_pdf_job_producao", "producao_id"),
        Index("idx_pdf_job_status", "status"),
        Index("idx_pdf_job_category", "category"),
        Index("idx_pdf_job_created_at", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    producao_id = Column(BigInteger, ForeignKey("producao.id", ondelete="CASCADE"), nullable=False, index=True)

    file_path = Column(String(1024), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=True)
    md5_hash = Column(String(32), nullable=True)

    category = Column(String(50), nullable=True)
    priority = Column(Integer, nullable=False, default=8)
    pdf_origin = Column(String(50), nullable=True)

    quantity = Column(Integer, nullable=False, default=1)
    paper_size = Column(String(20), nullable=False, default="A4")
    orientation = Column(String(20), nullable=False, default="vertical")
    page_range = Column(String(50), nullable=True)
    double_sided = Column(Boolean, default=False)
    color_mode = Column(String(20), nullable=False, default="color")

    status = Column(String(50), nullable=False, default="pending")
    print_datetime = Column(DateTime(timezone=True), nullable=True)
    print_duration_ms = Column(Integer, nullable=True)
    print_error_msg = Column(Text, nullable=True)

    reservado1 = Column(String(255), nullable=True)
    reservado2 = Column(String(255), nullable=True)
    reservado3 = Column(String(255), nullable=True)
    reservado4 = Column(String(255), nullable=True)
    reservado5 = Column(String(255), nullable=True)

    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PDFPrintQueue(Base):
    __tablename__ = "pdf_print_queue"
    __table_args__ = (
        Index("idx_pdf_queue_position", "queue_position"),
        Index("idx_pdf_queue_job", "job_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(BigInteger, ForeignKey("pdf_print_job.id", ondelete="CASCADE"), nullable=True, index=True)

    queue_position = Column(Integer, nullable=False)

    file_path = Column(String(1024), nullable=False)
    file_name = Column(String(255), nullable=False)
    priority = Column(Integer, nullable=True)
    category = Column(String(50), nullable=True)

    quantity = Column(Integer, nullable=False, default=1)
    paper_size = Column(String(20), nullable=False, default="A4")
    orientation = Column(String(20), nullable=False, default="vertical")

    reservado1 = Column(String(255), nullable=True)
    reservado2 = Column(String(255), nullable=True)
    reservado3 = Column(String(255), nullable=True)
    reservado4 = Column(String(255), nullable=True)
    reservado5 = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PDFPrintConfig(Base):
    __tablename__ = "pdf_print_config"
    __table_args__ = (
        Index("idx_pdf_config_category", "category"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False, unique=True)

    default_quantity = Column(Integer, nullable=False, default=1)
    default_paper_size = Column(String(20), nullable=False, default="A4")
    default_orientation = Column(String(20), nullable=False, default="vertical")
    default_double_sided = Column(Boolean, default=False)
    default_color_mode = Column(String(20), nullable=False, default="color")

    reservado1 = Column(String(255), nullable=True)
    reservado2 = Column(String(255), nullable=True)
    reservado3 = Column(String(255), nullable=True)
    reservado4 = Column(String(255), nullable=True)
    reservado5 = Column(String(255), nullable=True)

    display_name = Column(String(100), nullable=True)
    icon_path = Column(String(512), nullable=True)
    priority = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
