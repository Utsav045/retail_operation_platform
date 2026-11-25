from datetime import date
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, Integer, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
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
    
    raw_file_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    __table_args__ = (
        UniqueConstraint("store_id", "business_date", "shift_no", name="uq_shift_summary"),
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
    
    raw_file_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    __table_args__ = (
        UniqueConstraint("store_id", "business_date", name="uq_eod_summary"),
    )
