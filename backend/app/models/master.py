from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, Integer, Boolean, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import SoftDeleteMixin


class Store(Base, SoftDeleteMixin):
    """Store locations and regional configuration."""
    __tablename__ = "stores"
    
    store_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    store_name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(200))
    city: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    state: Mapped[Optional[str]] = mapped_column(String(10))
    timezone: Mapped[str] = mapped_column(String(50), default="America/Los_Angeles")


class Device(Base, SoftDeleteMixin):
    """In-store checkout terminals, cashier registers, and self-checkouts."""
    __tablename__ = "devices"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    device_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # COUNTER or SELF_CHECKOUT
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    __table_args__ = (
        UniqueConstraint("store_id", "device_id", name="uq_store_device"),
        Index("ix_device_store_type", "store_id", "device_type"),
    )


class Staff(Base, SoftDeleteMixin):
    """Store employees, cashiers, supervisors, and store managers."""
    __tablename__ = "staff"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    staff_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    __table_args__ = (
        UniqueConstraint("store_id", "staff_id", name="uq_store_staff"),
        Index("ix_staff_store_role", "store_id", "role"),
    )


class Department(Base, SoftDeleteMixin):
    """Merchandise category departments (Produce, Bakery, Dairy, Deli, etc.)."""
    __tablename__ = "departments"
    
    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    default_tax_group: Mapped[str] = mapped_column(String(10), default="T1")
    min_age: Mapped[int] = mapped_column(Integer, default=0)


class TaxGroup(Base, SoftDeleteMixin):
    """Tax classification categories and jurisdiction percentages."""
    __tablename__ = "tax_groups"
    
    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(100), nullable=False)


class Item(Base, SoftDeleteMixin):
    """Central product catalog with variant SKUs, department mapping, and retail shelf prices."""
    __tablename__ = "items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    variant: Mapped[str] = mapped_column(String(10), default="000", nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    dept: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, index=True)
    tax_group: Mapped[str] = mapped_column(String(10), default="T1")
    min_age: Mapped[int] = mapped_column(Integer, default=0)
    unit: Mapped[str] = mapped_column(String(10), default="EA")
    containers: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    __table_args__ = (
        UniqueConstraint("code", "variant", name="uq_item_variant"),
        Index("ix_item_code_variant", "code", "variant"),
        Index("ix_item_dept_price", "dept", "price"),
    )


class BusinessAccount(Base, SoftDeleteMixin):
    """Commercial credit accounts for local wholesale customers (cafes, caterers, bakeries)."""
    __tablename__ = "business_accounts"
    
    account_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    business_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    home_store: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    terms: Mapped[str] = mapped_column(String(20), default="NET30")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    
    __table_args__ = (
        Index("ix_biz_acc_store_status", "home_store", "status"),
    )
