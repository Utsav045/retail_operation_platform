from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FileImportLog(Base):
    __tablename__ = "file_import_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False)  # v2_xml, v3_json
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    batch_seq: Mapped[int] = mapped_column(Integer, default=0)
    
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    records_accepted: Mapped[int] = mapped_column(Integer, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0)
    records_flagged: Mapped[int] = mapped_column(Integer, default=0)
    
    status: Mapped[str] = mapped_column(String(20), default="PROCESSED")  # PROCESSED, PARTIAL, FAILED
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class QuarantinedFile(Base):
    __tablename__ = "quarantined_files"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    quarantined_path: Mapped[str] = mapped_column(String(300), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    stack_trace: Mapped[Optional[str]] = mapped_column(String(2000))
    quarantined_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
