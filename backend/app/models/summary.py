from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlalchemy import String, Numeric, Integer, Date, DateTime, Boolean, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.sqlite import JSON
from app.core.database import Base


class ShiftSummary(Base):
    __tablename__ = "shift_summaries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    shift_no: Mapped[int] = mapped_column(Integer, nullable=False)
    
    opening_float: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    counted_cash: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    expected_cash: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    cash_difference: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    
    tenders_json: Mapped[Optional[Any]] = mapped_column(JSON)
    gift_card_loads: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    cash_drops_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    exceptions_json: Mapped[Optional[Any]] = mapped_column(JSON)
    
    raw_file_name: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("store_id", "business_date", "shift_no", name="uq_shift_summary"),
        Index("ix_shift_store_date", "store_id", "business_date"),
    )


class EndOfDaySummary(Base):
    __tablename__ = "end_of_day_summaries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    reported_transactions: Mapped[int] = mapped_column(Integer, default=0)
    reported_net_sales: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    reported_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    reported_gift_card_loads: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    reported_grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    
    departments_json: Mapped[Optional[Any]] = mapped_column(JSON)
    taxes_json: Mapped[Optional[Any]] = mapped_column(JSON)
    tenders_json: Mapped[Optional[Any]] = mapped_column(JSON)
    exceptions_json: Mapped[Optional[Any]] = mapped_column(JSON)
    
    raw_file_name: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("store_id", "business_date", name="uq_eod_summary"),
        Index("ix_eod_store_date", "store_id", "business_date"),
    )


class ReconciliationReport(Base):
    __tablename__ = "reconciliation_reports"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)  # DAILY_EOD or SHIFT
    shift_no: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Financial metrics
    computed_net_sales: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    reported_net_sales: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    net_sales_diff: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    
    computed_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    reported_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_diff: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    
    computed_gift_card_loads: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    reported_gift_card_loads: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    gift_card_diff: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    
    computed_grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    reported_grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    grand_total_diff: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    
    # Cash metrics (for shift)
    expected_cash: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    counted_cash: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    cash_diff: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    
    # Audit status
    status: Mapped[str] = mapped_column(String(30), nullable=False)  # MATCHED, MISMATCH, REVIEW_REQUIRED
    is_consistent: Mapped[bool] = mapped_column(Boolean, default=True)
    discrepancy_details: Mapped[Optional[str]] = mapped_column(Text)
    detailed_diffs_json: Mapped[Optional[Any]] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_rec_store_date_type", "store_id", "business_date", "report_type"),
    )
