from datetime import datetime, date
from decimal import Decimal
import json
from pathlib import Path
from typing import Union
from lxml import etree

from app.schemas.canonical_summary import (
    CanonicalShiftSummary,
    CanonicalEODSummary,
    SummaryTender,
    SummaryDepartment,
    SummaryTax,
    SummaryExceptions,
)


def _minor_to_decimal(minor_val: Union[int, None]) -> Decimal:
    if minor_val is None:
        return Decimal("0.00")
    return (Decimal(minor_val) / Decimal(100)).quantize(Decimal("0.01"))


class SummaryParser:
    """Universal parser for in-store Hub SHIFT and EOD summaries (XML v2 and JSON v3)."""

    def parse_shift_xml(self, content_or_path: Union[Path, str, bytes]) -> CanonicalShiftSummary:
        if isinstance(content_or_path, Path):
            with open(content_or_path, "rb") as f:
                content = f.read()
            raw_file_name = content_or_path.name
        elif isinstance(content_or_path, str):
            content = content_or_path.encode("utf-8")
            raw_file_name = None
        else:
            content = content_or_path
            raw_file_name = None

        tree = etree.fromstring(content)
        store_id = tree.get("storeId", "")
        bdate_str = tree.get("businessDate", "")
        business_date = datetime.strptime(bdate_str, "%Y-%m-%d").date()
        shift_no = int(tree.get("shiftNo", "1"))
        closed_str = tree.get("closed")
        closed_at = datetime.strptime(closed_str, "%Y-%m-%d %H:%M:%S") if closed_str else None

        # Cash element
        cash_elem = tree.find("Cash")
        opening_float = Decimal(cash_elem.get("openingFloat", "0.00")) if cash_elem is not None else Decimal("0.00")
        counted_cash = Decimal(cash_elem.get("countedCash", "0.00")) if cash_elem is not None else Decimal("0.00")

        # Tenders
        tenders = []
        for tend_el in tree.xpath(".//Tenders/Tender"):
            tenders.append(
                SummaryTender(
                    tender_type=tend_el.get("type", "").upper(),
                    count=int(tend_el.get("count", "0")),
                    amount=Decimal(tend_el.get("amount", "0.00")),
                )
            )

        # GiftCards
        gc_elem = tree.find("GiftCards")
        gift_card_loads = Decimal(gc_elem.get("loadAmount", "0.00")) if gc_elem is not None else Decimal("0.00")

        # CashDrops
        cd_elem = tree.find("CashDrops")
        cash_drops_count = int(cd_elem.get("count", "0")) if cd_elem is not None else 0
        cash_drops_amount = Decimal(cd_elem.get("amount", "0.00")) if cd_elem is not None else Decimal("0.00")

        # Exceptions
        ex_elem = tree.find("Exceptions")
        if ex_elem is not None:
            exceptions = SummaryExceptions(
                line_voids_count=int(ex_elem.get("lineVoids", "0")),
                line_void_amount=Decimal(ex_elem.get("lineVoidAmount", "0.00")),
                cancelled_count=int(ex_elem.get("cancelledTransactions", "0")),
                cancelled_amount=Decimal(ex_elem.get("cancelledAmount", "0.00")),
                refunds_count=int(ex_elem.get("refunds", "0")),
                refund_amount=Decimal(ex_elem.get("refundAmount", "0.00")),
                no_sales_count=int(ex_elem.get("noSales", "0")),
            )
        else:
            exceptions = SummaryExceptions()

        # AccountCharges
        account_charges = []
        for chg_el in tree.xpath(".//AccountCharges/Charge"):
            account_charges.append({
                "account": chg_el.get("account", ""),
                "seq": int(chg_el.get("seq", "0")),
                "amount": Decimal(chg_el.get("amount", "0.00")),
            })

        return CanonicalShiftSummary(
            store_id=store_id,
            business_date=business_date,
            shift_no=shift_no,
            closed_at=closed_at,
            format_version="2.1",
            raw_file_name=raw_file_name,
            opening_float=opening_float,
            counted_cash=counted_cash,
            tenders=tenders,
            gift_card_loads=gift_card_loads,
            cash_drops_count=cash_drops_count,
            cash_drops_amount=cash_drops_amount,
            exceptions=exceptions,
            account_charges=account_charges,
        )

    def parse_shift_json(self, content_or_path: Union[Path, str, bytes]) -> CanonicalShiftSummary:
        if isinstance(content_or_path, Path):
            with open(content_or_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_file_name = content_or_path.name
        elif isinstance(content_or_path, (bytes, bytearray)):
            data = json.loads(content_or_path.decode("utf-8"))
            raw_file_name = None
        else:
            data = json.loads(content_or_path)
            raw_file_name = None

        store_id = data.get("store", "")
        bdate_str = data.get("businessDay", "")
        business_date = datetime.strptime(bdate_str, "%Y-%m-%d").date()
        shift_no = int(data.get("shiftNo", 1))
        closed_str = data.get("closedAt")
        closed_at = datetime.fromisoformat(closed_str).replace(tzinfo=None) if closed_str else None

        cash_data = data.get("cash", {})
        opening_float = _minor_to_decimal(cash_data.get("openingFloatMinor", 0))
        counted_cash = _minor_to_decimal(cash_data.get("countedMinor", 0))

        # Payments -> Tenders
        tenders = []
        for p in data.get("payments", []):
            m = p.get("method", "").upper()
            if m == "GIFT_CARD":
                m = "GIFT"
            tenders.append(
                SummaryTender(
                    tender_type=m,
                    count=int(p.get("count", 0)),
                    amount=_minor_to_decimal(p.get("amountMinor", 0)),
                )
            )

        gc_data = data.get("giftCards", {})
        gift_card_loads = _minor_to_decimal(gc_data.get("loadAmountMinor", 0))

        cd_data = data.get("cashDrops", {})
        cash_drops_count = int(cd_data.get("count", 0))
        cash_drops_amount = _minor_to_decimal(cd_data.get("amountMinor", 0))

        ex_data = data.get("exceptions", {})
        exceptions = SummaryExceptions(
            line_voids_count=int(ex_data.get("lineVoids", 0)),
            line_void_amount=_minor_to_decimal(ex_data.get("lineVoidAmountMinor", 0)),
            cancelled_count=int(ex_data.get("cancelledTransactions", 0)),
            cancelled_amount=_minor_to_decimal(ex_data.get("cancelledAmountMinor", 0)),
            refunds_count=int(ex_data.get("refunds", 0)),
            refund_amount=_minor_to_decimal(ex_data.get("refundAmountMinor", 0)),
            no_sales_count=int(ex_data.get("noSales", 0)),
        )

        account_charges = []
        for chg in data.get("accountCharges", []):
            account_charges.append({
                "account": chg.get("accountId", ""),
                "seq": int(chg.get("sequenceNo", 0)),
                "amount": _minor_to_decimal(chg.get("amountMinor", 0)),
            })

        return CanonicalShiftSummary(
            store_id=store_id,
            business_date=business_date,
            shift_no=shift_no,
            closed_at=closed_at,
            format_version="3.0",
            raw_file_name=raw_file_name,
            opening_float=opening_float,
            counted_cash=counted_cash,
            tenders=tenders,
            gift_card_loads=gift_card_loads,
            cash_drops_count=cash_drops_count,
            cash_drops_amount=cash_drops_amount,
            exceptions=exceptions,
            account_charges=account_charges,
        )

    def parse_eod_xml(self, content_or_path: Union[Path, str, bytes]) -> CanonicalEODSummary:
        if isinstance(content_or_path, Path):
            with open(content_or_path, "rb") as f:
                content = f.read()
            raw_file_name = content_or_path.name
        elif isinstance(content_or_path, str):
            content = content_or_path.encode("utf-8")
            raw_file_name = None
        else:
            content = content_or_path
            raw_file_name = None

        tree = etree.fromstring(content)
        store_id = tree.get("storeId", "")
        bdate_str = tree.get("businessDate", "")
        business_date = datetime.strptime(bdate_str, "%Y-%m-%d").date()
        closed_str = tree.get("closed")
        closed_at = datetime.strptime(closed_str, "%Y-%m-%d %H:%M:%S") if closed_str else None

        # Totals
        tot_el = tree.find("Totals")
        if tot_el is not None:
            reported_txs = int(tot_el.get("transactions", "0"))
            reported_net = Decimal(tot_el.get("netSales", "0.00"))
            reported_tax = Decimal(tot_el.get("tax", "0.00"))
            reported_gc = Decimal(tot_el.get("giftCardLoads", "0.00"))
            reported_grand = Decimal(tot_el.get("grandTotal", "0.00"))
        else:
            reported_txs = 0
            reported_net = Decimal("0.00")
            reported_tax = Decimal("0.00")
            reported_gc = Decimal("0.00")
            reported_grand = Decimal("0.00")

        # Departments
        departments = []
        for d in tree.xpath(".//Departments/Department"):
            code_str = str(d.get("code", "")).lstrip("0") or "0"
            departments.append(
                SummaryDepartment(
                    dept_code=code_str,
                    name=d.get("name", ""),
                    qty=Decimal(d.get("qty", "0.000")),
                    amount=Decimal(d.get("amount", "0.00")),
                )
            )

        # Taxes
        taxes = []
        for t in tree.xpath(".//Taxes/Tax"):
            taxes.append(
                SummaryTax(
                    tax_group=t.get("group", ""),
                    taxable_amount=Decimal(t.get("taxable", "0.00")),
                    tax_amount=Decimal(t.get("amount", "0.00")),
                )
            )

        # Tenders
        tenders = []
        for tend_el in tree.xpath(".//Tenders/Tender"):
            tenders.append(
                SummaryTender(
                    tender_type=tend_el.get("type", "").upper(),
                    count=int(tend_el.get("count", "0")),
                    amount=Decimal(tend_el.get("amount", "0.00")),
                )
            )

        # GiftCards
        gc_elem = tree.find("GiftCards")
        gc_loads = Decimal(gc_elem.get("loadAmount", "0.00")) if gc_elem is not None else Decimal("0.00")

        # CashDrops
        cd_elem = tree.find("CashDrops")
        cd_count = int(cd_elem.get("count", "0")) if cd_elem is not None else 0
        cd_amount = Decimal(cd_elem.get("amount", "0.00")) if cd_elem is not None else Decimal("0.00")

        # Exceptions
        ex_elem = tree.find("Exceptions")
        if ex_elem is not None:
            exceptions = SummaryExceptions(
                line_voids_count=int(ex_elem.get("lineVoids", "0")),
                line_void_amount=Decimal(ex_elem.get("lineVoidAmount", "0.00")),
                cancelled_count=int(ex_elem.get("cancelledTransactions", "0")),
                cancelled_amount=Decimal(ex_elem.get("cancelledAmount", "0.00")),
                refunds_count=int(ex_elem.get("refunds", "0")),
                refund_amount=Decimal(ex_elem.get("refundAmount", "0.00")),
                no_sales_count=int(ex_elem.get("noSales", "0")),
            )
        else:
            exceptions = SummaryExceptions()

        # AccountCharges
        account_charges = []
        for chg_el in tree.xpath(".//AccountCharges/Charge"):
            account_charges.append({
                "account": chg_el.get("account", ""),
                "seq": int(chg_el.get("seq", "0")),
                "amount": Decimal(chg_el.get("amount", "0.00")),
            })

        return CanonicalEODSummary(
            store_id=store_id,
            business_date=business_date,
            closed_at=closed_at,
            format_version="2.1",
            raw_file_name=raw_file_name,
            reported_transactions=reported_txs,
            reported_net_sales=reported_net,
            reported_tax=reported_tax,
            reported_gift_card_loads=reported_gc,
            reported_grand_total=reported_grand,
            departments=departments,
            taxes=taxes,
            tenders=tenders,
            cash_drops_count=cd_count,
            cash_drops_amount=cd_amount,
            exceptions=exceptions,
            account_charges=account_charges,
        )

    def parse_eod_json(self, content_or_path: Union[Path, str, bytes]) -> CanonicalEODSummary:
        if isinstance(content_or_path, Path):
            with open(content_or_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_file_name = content_or_path.name
        elif isinstance(content_or_path, (bytes, bytearray)):
            data = json.loads(content_or_path.decode("utf-8"))
            raw_file_name = None
        else:
            data = json.loads(content_or_path)
            raw_file_name = None

        store_id = data.get("store", "")
        bdate_str = data.get("businessDay", "")
        business_date = datetime.strptime(bdate_str, "%Y-%m-%d").date()
        closed_str = data.get("closedAt")
        closed_at = datetime.fromisoformat(closed_str).replace(tzinfo=None) if closed_str else None

        tot_data = data.get("totals", {})
        reported_txs = int(tot_data.get("transactions", 0))
        reported_net = _minor_to_decimal(tot_data.get("netMinor", 0))
        reported_tax = _minor_to_decimal(tot_data.get("taxMinor", 0))
        reported_gc = _minor_to_decimal(tot_data.get("giftCardLoadsMinor", 0))
        reported_grand = _minor_to_decimal(tot_data.get("grandMinor", 0))

        # Departments
        departments = []
        for d in data.get("departments", []):
            code_str = str(d.get("department", "")).lstrip("0") or "0"
            departments.append(
                SummaryDepartment(
                    dept_code=code_str,
                    name=d.get("name", ""),
                    qty=Decimal(str(d.get("quantity", "0.000"))),
                    amount=_minor_to_decimal(d.get("amountMinor", 0)),
                )
            )

        # Taxes
        taxes = []
        for t in data.get("taxes", []):
            taxes.append(
                SummaryTax(
                    tax_group=t.get("code", ""),
                    taxable_amount=_minor_to_decimal(t.get("taxableMinor", 0)),
                    tax_amount=_minor_to_decimal(t.get("taxMinor", 0)),
                )
            )

        # Payments -> Tenders
        tenders = []
        for p in data.get("payments", []):
            m = p.get("method", "").upper()
            if m == "GIFT_CARD":
                m = "GIFT"
            tenders.append(
                SummaryTender(
                    tender_type=m,
                    count=int(p.get("count", 0)),
                    amount=_minor_to_decimal(p.get("amountMinor", 0)),
                )
            )

        gc_data = data.get("giftCards", {})
        gc_loads = _minor_to_decimal(gc_data.get("loadAmountMinor", 0))

        cd_data = data.get("cashDrops", {})
        cd_count = int(cd_data.get("count", 0))
        cd_amount = _minor_to_decimal(cd_data.get("amountMinor", 0))

        ex_data = data.get("exceptions", {})
        exceptions = SummaryExceptions(
            line_voids_count=int(ex_data.get("lineVoids", 0)),
            line_void_amount=_minor_to_decimal(ex_data.get("lineVoidAmountMinor", 0)),
            cancelled_count=int(ex_data.get("cancelledTransactions", 0)),
            cancelled_amount=_minor_to_decimal(ex_data.get("cancelledAmountMinor", 0)),
            refunds_count=int(ex_data.get("refunds", 0)),
            refund_amount=_minor_to_decimal(ex_data.get("refundAmountMinor", 0)),
            no_sales_count=int(ex_data.get("noSales", 0)),
        )

        account_charges = []
        for chg in data.get("accountCharges", []):
            account_charges.append({
                "account": chg.get("accountId", ""),
                "seq": int(chg.get("sequenceNo", 0)),
                "amount": _minor_to_decimal(chg.get("amountMinor", 0)),
            })

        return CanonicalEODSummary(
            store_id=store_id,
            business_date=business_date,
            closed_at=closed_at,
            format_version="3.0",
            raw_file_name=raw_file_name,
            reported_transactions=reported_txs,
            reported_net_sales=reported_net,
            reported_tax=reported_tax,
            reported_gift_card_loads=reported_gc,
            reported_grand_total=reported_grand,
            departments=departments,
            taxes=taxes,
            tenders=tenders,
            cash_drops_count=cd_count,
            cash_drops_amount=cd_amount,
            exceptions=exceptions,
            account_charges=account_charges,
        )

    def parse_summary_file(self, file_path: Path) -> Union[CanonicalShiftSummary, CanonicalEODSummary]:
        name = file_path.name
        is_json = name.endswith(".json")
        if name.startswith("SHIFT_"):
            return self.parse_shift_json(file_path) if is_json else self.parse_shift_xml(file_path)
        elif name.startswith("EOD_"):
            return self.parse_eod_json(file_path) if is_json else self.parse_eod_xml(file_path)
        else:
            raise ValueError(f"Unknown summary file type: {name}")
