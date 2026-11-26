from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import SoftDeleteMixin


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FileImportLog(Base, SoftDeleteMixin):
    """Log of all ingested transaction batches with SHA256 integrity hash."""
    __tablename__ = "file_import_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # v2_xml, v3_json
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    batch_seq: Mapped[int] = mapped_column(Integer, default=0)
    
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    records_accepted: Mapped[int] = mapped_column(Integer, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0)
    records_flagged: Mapped[int] = mapped_column(Integer, default=0)
    
    status: Mapped[str] = mapped_column(String(20), default="PROCESSED", index=True)  # PROCESSED, PARTIAL, FAILED
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)

    __table_args__ = (
        Index("ix_file_import_store_date", "store_id", "imported_at"),
    )


class QuarantinedFile(Base, SoftDeleteMixin):
    """Isolated corrupt or unparseable batches preserving ground-truth ledger integrity."""
    __tablename__ = "quarantined_files"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    quarantined_path: Mapped[str] = mapped_column(String(300), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(String(2000))
    quarantined_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)


class SecurityAuditLog(Base, SoftDeleteMixin):
    """Immutable security audit log tracking logins, failed attempts, OTP requests, and privileged actions."""
    __tablename__ = "security_audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    actor_email: Mapped[str] = mapped_column(String(120), default="anonymous", index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255))
    details: Mapped[Optional[str]] = mapped_column(Text)
    
    __table_args__ = (
        Index("ix_sec_audit_event_time", "event_type", "timestamp"),
        Index("ix_sec_audit_actor_time", "actor_email", "timestamp"),
    )
