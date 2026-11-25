from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class CanonicalLine(BaseModel):
    line_no: int
    item_code: Optional[str] = None
    variant: Optional[str] = "000"
    description: str = ""
    dept: str
    qty: Decimal = Decimal("1.000")
    unit_price: Decimal = Decimal("0.00")
    amount: Decimal = Decimal("0.00")
    tax_group: str = "T0"
    is_void: bool = False


class CanonicalTender(BaseModel):
    tender_type: str
    amount: Decimal
    tendered: Optional[Decimal] = None
    change: Optional[Decimal] = None
    card_type: Optional[str] = None
    last4: Optional[str] = None
    auth_code: Optional[str] = None
    wallet: Optional[str] = None
    account_id: Optional[str] = None


class CanonicalTax(BaseModel):
    tax_group: str
    taxable_amount: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")


class CanonicalGiftCard(BaseModel):
    line_no: int = 1
    action: str = "LOAD"
    card_last4: str
    amount: Decimal = Decimal("0.00")


class CanonicalCashDrop(BaseModel):
    envelope: str
    amount: Decimal = Decimal("0.00")
    status: str = "OK"


class CanonicalTransaction(BaseModel):
    seq: int
    type: str = "SALE"          # SALE, REFUND, NO_SALE, CASH_DROP
    status: str = "COMPLETED"   # COMPLETED, CANCELLED
    device: str
    staff: int = 0
    shift: int = 1
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    original_seq: Optional[int] = None
    
    net_total: Decimal = Decimal("0.00")
    tax_total: Decimal = Decimal("0.00")
    gift_card_total: Decimal = Decimal("0.00")
    grand_total: Decimal = Decimal("0.00")
    
    lines: List[CanonicalLine] = Field(default_factory=list)
    tenders: List[CanonicalTender] = Field(default_factory=list)
    taxes: List[CanonicalTax] = Field(default_factory=list)
    gift_cards: List[CanonicalGiftCard] = Field(default_factory=list)
    cash_drops: List[CanonicalCashDrop] = Field(default_factory=list)


class CanonicalBatch(BaseModel):
    format_version: str
    store_id: str
    business_date: date
    batch_seq: int
    created_at: Optional[datetime] = None
    record_count: int = 0
    transactions: List[CanonicalTransaction] = Field(default_factory=list)
