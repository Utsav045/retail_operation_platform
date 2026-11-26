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
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    flag_reason: Mapped[Optional[str]] = mapped_column(String(255))
    raw_file_name: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    
    # Eager batch relationship mapping (lazy="selectin") eliminates N+1 query bottlenecks
    lines: Mapped[List["TransactionLine"]] = relationship(
        "TransactionLine", back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )
    tenders: Mapped[List["TransactionTender"]] = relationship(
        "TransactionTender", back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )
    taxes: Mapped[List["TransactionTax"]] = relationship(
        "TransactionTax", back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )
    gift_cards: Mapped[List["GiftCardActivity"]] = relationship(
        "GiftCardActivity", back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )
    cash_drops: Mapped[List["CashDrop"]] = relationship(
        "CashDrop", back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("store_id", "seq", "business_date", name="uq_store_seq_bdate"),
        Index("ix_trans_store_date", "store_id", "business_date"),
        Index("ix_trans_store_date_status", "store_id", "business_date", "status"),
        Index("ix_trans_device_date", "device_id", "business_date"),
        Index("ix_trans_staff_date", "staff_id", "business_date"),
    )


class TransactionLine(Base):
    __tablename__ = "transaction_lines"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), nullable=False, index=True)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    
    item_code: Mapped[Optional[str]] = mapped_column(String(30), index=True)
    variant: Mapped[Optional[str]] = mapped_column(String(10), default="000")
    description: Mapped[str] = mapped_column(String(150), default="")
    dept: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=Decimal("1.000"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_group: Mapped[str] = mapped_column(String(10), default="T0")
    
    is_void: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    flag_reason: Mapped[Optional[str]] = mapped_column(String(200))
    
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="lines")

    __table_args__ = (
        Index("ix_tx_line_tx_dept", "transaction_id", "dept"),
        Index("ix_tx_line_item_void", "item_code", "is_void"),
    )


class TransactionTender(Base):
    __tablename__ = "transaction_tenders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), nullable=False, index=True)
    
    tender_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # CASH, CARD, MOBILE, GIFT, ACCOUNT
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tendered: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    change: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    
    card_type: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    last4: Mapped[Optional[str]] = mapped_column(String(10))
    auth_code: Mapped[Optional[str]] = mapped_column(String(30))
    wallet: Mapped[Optional[str]] = mapped_column(String(30))
    account_id: Mapped[Optional[str]] = mapped_column(String(30), index=True)
    
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="tenders")

    __table_args__ = (
        Index("ix_tx_tender_type_amount", "tender_type", "amount"),
    )


class TransactionTax(Base):
    __tablename__ = "transaction_taxes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), nullable=False, index=True)
    
    tax_group: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="taxes")


class GiftCardActivity(Base):
    __tablename__ = "gift_card_activities"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), nullable=False, index=True)
    
    line_no: Mapped[int] = mapped_column(Integer, default=1)
    action: Mapped[str] = mapped_column(String(20), default="LOAD", index=True)  # LOAD
    card_last4: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="gift_cards")


class CashDrop(Base):
    __tablename__ = "cash_drops"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), nullable=False, index=True)
    
    envelope: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="OK", index=True)  # OK, CANCELLED
    
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="cash_drops")
