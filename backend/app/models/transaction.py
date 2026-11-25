from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    String,
    Numeric,
    Integer,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Transaction(Base):
    __tablename__ = "transactions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    batch_seq: Mapped[int] = mapped_column(Integer, default=0)
    
    type: Mapped[str] = mapped_column(String(20), nullable=False)    # SALE, REFUND, NO_SALE, CASH_DROP
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # COMPLETED, CANCELLED
    device_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    staff_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    shift: Mapped[int] = mapped_column(Integer, default=1)
    
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    original_seq: Mapped[Optional[int]] = mapped_column(Integer)     # On refunds: referenced sale seq
    
    # Financial fields - Exact Decimal
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    gift_card_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    
    # Audit & flags
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[Optional[str]] = mapped_column(String(255))
    raw_file_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    lines: Mapped[List["TransactionLine"]] = relationship("TransactionLine", back_populates="transaction", cascade="all, delete-orphan")
    tenders: Mapped[List["TransactionTender"]] = relationship("TransactionTender", back_populates="transaction", cascade="all, delete-orphan")
    taxes: Mapped[List["TransactionTax"]] = relationship("TransactionTax", back_populates="transaction", cascade="all, delete-orphan")
    gift_cards: Mapped[List["GiftCardActivity"]] = relationship("GiftCardActivity", back_populates="transaction", cascade="all, delete-orphan")
    cash_drops: Mapped[List["CashDrop"]] = relationship("CashDrop", back_populates="transaction", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("store_id", "seq", "business_date", name="uq_store_seq_bdate"),
        Index("ix_trans_store_date", "store_id", "business_date"),
    )


class TransactionLine(Base):
    __tablename__ = "transaction_lines"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), nullable=False, index=True)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    
    item_code: Mapped[Optional[str]] = mapped_column(String(30))
    variant: Mapped[Optional[str]] = mapped_column(String(10), default="000")
    description: Mapped[str] = mapped_column(String(150), default="")
    dept: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=Decimal("1.000"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_group: Mapped[str] = mapped_column(String(10), default="T0")
    
    is_void: Mapped[bool] = mapped_column(Boolean, default=False)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[Optional[str]] = mapped_column(String(200))
    
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="lines")


class TransactionTender(Base):
    __tablename__ = "transaction_tenders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), nullable=False, index=True)
    
    tender_type: Mapped[str] = mapped_column(String(20), nullable=False)  # CASH, CARD, MOBILE, GIFT, ACCOUNT
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tendered: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    change: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    
    card_type: Mapped[Optional[str]] = mapped_column(String(20))
    last4: Mapped[Optional[str]] = mapped_column(String(10))
    auth_code: Mapped[Optional[str]] = mapped_column(String(30))
    wallet: Mapped[Optional[str]] = mapped_column(String(30))
    account_id: Mapped[Optional[str]] = mapped_column(String(30))
    
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="tenders")


class TransactionTax(Base):
    __tablename__ = "transaction_taxes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), nullable=False, index=True)
    
    tax_group: Mapped[str] = mapped_column(String(10), nullable=False)
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="taxes")


class GiftCardActivity(Base):
    __tablename__ = "gift_card_activities"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), nullable=False, index=True)
    
    line_no: Mapped[int] = mapped_column(Integer, default=1)
    action: Mapped[str] = mapped_column(String(20), default="LOAD")  # LOAD
    card_last4: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="gift_cards")


class CashDrop(Base):
    __tablename__ = "cash_drops"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), nullable=False, index=True)
    
    envelope: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="OK")  # OK, CANCELLED
    
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="cash_drops")
