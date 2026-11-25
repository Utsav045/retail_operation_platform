from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, Integer, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Store(Base):
    __tablename__ = "stores"
    
    store_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    store_name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(200))
    city: Mapped[Optional[str]] = mapped_column(String(50))
    state: Mapped[Optional[str]] = mapped_column(String(10))
    timezone: Mapped[str] = mapped_column(String(50), default="America/Los_Angeles")


class Device(Base):
    __tablename__ = "devices"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(String(10), nullable=False)
    device_id: Mapped[str] = mapped_column(String(10), nullable=False)
    device_type: Mapped[str] = mapped_column(String(20), nullable=False)  # COUNTER or SELF_CHECKOUT
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    __table_args__ = (UniqueConstraint("store_id", "device_id", name="uq_store_device"),)


class Staff(Base):
    __tablename__ = "staff"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(String(10), nullable=False)
    staff_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    
    __table_args__ = (UniqueConstraint("store_id", "staff_id", name="uq_store_staff"),)


class Department(Base):
    __tablename__ = "departments"
    
    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    default_tax_group: Mapped[str] = mapped_column(String(10), default="T1")
    min_age: Mapped[int] = mapped_column(Integer, default=0)


class TaxGroup(Base):
    __tablename__ = "tax_groups"
    
    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(100), nullable=False)


class Item(Base):
    __tablename__ = "items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    variant: Mapped[str] = mapped_column(String(10), default="000", nullable=False)
    description: Mapped[str] = mapped_column(String(100), nullable=False)
    dept: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_group: Mapped[str] = mapped_column(String(10), default="T1")
    min_age: Mapped[int] = mapped_column(Integer, default=0)
    unit: Mapped[str] = mapped_column(String(10), default="EA")
    containers: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    __table_args__ = (UniqueConstraint("code", "variant", name="uq_item_variant"),)


class BusinessAccount(Base):
    __tablename__ = "business_accounts"
    
    account_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    business_name: Mapped[str] = mapped_column(String(100), nullable=False)
    home_store: Mapped[str] = mapped_column(String(10), nullable=False)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    terms: Mapped[str] = mapped_column(String(20), default="NET30")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
