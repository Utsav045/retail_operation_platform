import json
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Union

from app.schemas.unified_tlog import (
    CanonicalBatch,
    CanonicalTransaction,
    CanonicalLine,
    CanonicalTender,
    CanonicalTax,
    CanonicalGiftCard,
    CanonicalCashDrop,
)
from app.services.parsers.base import BaseTLOGParser


def _minor_to_decimal(minor_val: int | float | None) -> Decimal:
    if minor_val is None:
        return Decimal("0.00")
    return (Decimal(minor_val) / Decimal(100)).quantize(Decimal("0.01"))


class JSONv3Parser(BaseTLOGParser):
    def parse(self, file_path_or_content: Union[Path, str, bytes]) -> CanonicalBatch:
        if isinstance(file_path_or_content, Path):
            with open(file_path_or_content, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif isinstance(file_path_or_content, (bytes, bytearray)):
            data = json.loads(file_path_or_content.decode("utf-8"))
        else:
            data = json.loads(file_path_or_content)

        store_id = data.get("store", "")
        bdate_str = data.get("businessDay", "")
        business_date = datetime.strptime(bdate_str, "%Y-%m-%d").date()
        
        batch_info = data.get("batch", {})
        batch_seq = int(batch_info.get("seq", 0))
        created_str = batch_info.get("createdAt")
        # Handle ISO with timezone like '2026-10-11T09:00:34-07:00'
        if created_str:
            try:
                created_at = datetime.fromisoformat(created_str)
            except ValueError:
                created_at = None
        else:
            created_at = None
            
        record_count = int(batch_info.get("records", 0))
        format_version = data.get("schema", "tlog/3.0")
        
        transactions: list[CanonicalTransaction] = []
        
        for tx_data in data.get("transactions", []):
            seq = int(tx_data.get("sequenceNo"))
            tx_type = tx_data.get("kind", "sale").upper()
            status = tx_data.get("state", "completed").upper()
            device = tx_data.get("terminal", "")
            staff = int(tx_data.get("operator", "0"))
            shift = int(tx_data.get("shiftNo", 1))
            
            started_str = tx_data.get("startedAt")
            started_at = datetime.fromisoformat(started_str) if started_str else None
            ended_str = tx_data.get("endedAt")
            ended_at = datetime.fromisoformat(ended_str) if ended_str else None
            
            orig_seq = tx_data.get("referenceSequenceNo")
            original_seq = int(orig_seq) if orig_seq else None
            
            # Totals
            totals_data = tx_data.get("totals", {})
            net_total = _minor_to_decimal(totals_data.get("netMinor", 0))
            tax_total = _minor_to_decimal(totals_data.get("taxMinor", 0))
            gift_card_total = _minor_to_decimal(totals_data.get("giftCardLoadsMinor", 0))
            grand_total = _minor_to_decimal(totals_data.get("grandMinor", 0))
            
            # Lines and Gift cards
            lines: list[CanonicalLine] = []
            gift_cards: list[CanonicalGiftCard] = []
            for line_data in tx_data.get("lines", []):
                line_type = line_data.get("lineType", "item").lower()
                line_no = int(line_data.get("lineNo", 1))
                
                if line_type == "item":
                    dept_str = str(line_data.get("department", "99")).lstrip("0") or "0"
                    lines.append(
                        CanonicalLine(
                            line_no=line_no,
                            item_code=line_data.get("sku"),
                            variant=line_data.get("variant", "000"),
                            description=line_data.get("text", ""),
                            dept=dept_str,
                            qty=Decimal(str(line_data.get("quantity", "1"))),
                            unit_price=_minor_to_decimal(line_data.get("unitPriceMinor", 0)),
                            amount=_minor_to_decimal(line_data.get("extendedMinor", 0)),
                            tax_group=line_data.get("taxCode", "T0"),
                            is_void=bool(line_data.get("voided", False)),
                        )
                    )
                elif line_type in ("giftcard", "gift_card"):
                    gift_cards.append(
                        CanonicalGiftCard(
                            line_no=line_no,
                            action=line_data.get("action", "load").upper(),
                            card_last4=str(line_data.get("cardSuffix", "")),
                            amount=_minor_to_decimal(line_data.get("amountMinor", 0)),
                        )
                    )
                    
            # Tenders / Payments
            tenders: list[CanonicalTender] = []
            for p_data in tx_data.get("payments", []):
                amount = _minor_to_decimal(p_data.get("amountMinor", 0))
                tendered = _minor_to_decimal(p_data.get("tenderedMinor")) if "tenderedMinor" in p_data else None
                change = _minor_to_decimal(p_data.get("changeMinor")) if "changeMinor" in p_data else None
                method = p_data.get("method", "cash").upper()
                if method == "GIFT_CARD":
                    method = "GIFT"
                    
                tenders.append(
                    CanonicalTender(
                        tender_type=method,
                        amount=amount,
                        tendered=tendered,
                        change=change,
                        card_type=p_data.get("network"),
                        last4=p_data.get("panSuffix"),
                        auth_code=p_data.get("approval"),
                        wallet=p_data.get("wallet"),
                        account_id=p_data.get("accountId"),
                    )
                )
                
            # Taxes
            taxes: list[CanonicalTax] = []
            for tax_data in tx_data.get("taxes", []):
                taxes.append(
                    CanonicalTax(
                        tax_group=tax_data.get("code", "T0"),
                        taxable_amount=_minor_to_decimal(tax_data.get("taxableMinor", 0)),
                        tax_amount=_minor_to_decimal(tax_data.get("taxMinor", 0)),
                    )
                )
                
            # Cash Drops
            cash_drops: list[CanonicalCashDrop] = []
            if "drop" in tx_data:
                drop_data = tx_data["drop"]
                cancelled = bool(drop_data.get("cancelled", False))
                cash_drops.append(
                    CanonicalCashDrop(
                        envelope=str(drop_data.get("envelopeNo", "")),
                        amount=_minor_to_decimal(drop_data.get("amountMinor", 0)),
                        status="CANCELLED" if cancelled else "OK",
                    )
                )
                
            transactions.append(
                CanonicalTransaction(
                    seq=seq,
                    type=tx_type,
                    status=status,
                    device=device,
                    staff=staff,
                    shift=shift,
                    start_time=started_at.replace(tzinfo=None) if started_at else None,
                    end_time=ended_at.replace(tzinfo=None) if ended_at else None,
                    original_seq=original_seq,
                    net_total=net_total,
                    tax_total=tax_total,
                    gift_card_total=gift_card_total,
                    grand_total=grand_total,
                    lines=lines,
                    tenders=tenders,
                    taxes=taxes,
                    gift_cards=gift_cards,
                    cash_drops=cash_drops,
                )
            )
            
        return CanonicalBatch(
            format_version=format_version,
            store_id=store_id,
            business_date=business_date,
            batch_seq=batch_seq,
            created_at=created_at.replace(tzinfo=None) if created_at else None,
            record_count=record_count or len(transactions),
            transactions=transactions,
        )
