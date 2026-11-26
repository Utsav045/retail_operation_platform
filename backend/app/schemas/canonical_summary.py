from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class SummaryTender(BaseModel):
    tender_type: str
    count: int = 0
    amount: Decimal = Decimal("0.00")


class SummaryDepartment(BaseModel):
    dept_code: str
    name: str = ""
    qty: Decimal = Decimal("0.000")
    amount: Decimal = Decimal("0.00")


class SummaryTax(BaseModel):
    tax_group: str
    taxable_amount: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")


class SummaryExceptions(BaseModel):
    line_voids_count: int = 0
    line_void_amount: Decimal = Decimal("0.00")
    cancelled_count: int = 0
    cancelled_amount: Decimal = Decimal("0.00")
    refunds_count: int = 0
    refund_amount: Decimal = Decimal("0.00")
    no_sales_count: int = 0


class CanonicalShiftSummary(BaseModel):
    store_id: str
    business_date: date
    shift_no: int
    closed_at: Optional[datetime] = None
    format_version: str = "2.1"
    raw_file_name: Optional[str] = None

    opening_float: Decimal = Decimal("0.00")
    counted_cash: Decimal = Decimal("0.00")
    
    tenders: List[SummaryTender] = Field(default_factory=list)
    gift_card_loads: Decimal = Decimal("0.00")
    cash_drops_count: int = 0
    cash_drops_amount: Decimal = Decimal("0.00")
    exceptions: SummaryExceptions = Field(default_factory=SummaryExceptions)
    account_charges: List[Dict[str, Any]] = Field(default_factory=list)


class CanonicalEODSummary(BaseModel):
    store_id: str
    business_date: date
    closed_at: Optional[datetime] = None
    format_version: str = "2.1"
    raw_file_name: Optional[str] = None

    reported_transactions: int = 0
    reported_net_sales: Decimal = Decimal("0.00")
    reported_tax: Decimal = Decimal("0.00")
    reported_gift_card_loads: Decimal = Decimal("0.00")
    reported_grand_total: Decimal = Decimal("0.00")

    departments: List[SummaryDepartment] = Field(default_factory=list)
    taxes: List[SummaryTax] = Field(default_factory=list)
    tenders: List[SummaryTender] = Field(default_factory=list)
    cash_drops_count: int = 0
    cash_drops_amount: Decimal = Decimal("0.00")
    exceptions: SummaryExceptions = Field(default_factory=SummaryExceptions)
    account_charges: List[Dict[str, Any]] = Field(default_factory=list)
