from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Union
from lxml import etree

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


class XMLv2Parser(BaseTLOGParser):
    def parse(self, file_path_or_content: Union[Path, str, bytes]) -> CanonicalBatch:
        if isinstance(file_path_or_content, Path):
            with open(file_path_or_content, "rb") as f:
                content = f.read()
        elif isinstance(file_path_or_content, str):
            content = file_path_or_content.encode("utf-8")
        else:
            content = file_path_or_content

        tree = etree.fromstring(content)
        
        # Batch root attributes
        store_id = tree.get("storeId", "")
        bdate_str = tree.get("businessDate", "")
        business_date = datetime.strptime(bdate_str, "%Y-%m-%d").date()
        batch_seq = int(tree.get("batchSeq", "0"))
        created_str = tree.get("created")
        created_at = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S") if created_str else None
        record_count = int(tree.get("recordCount", "0"))
        format_version = tree.get("formatVersion", "2.1")
        
        transactions: list[CanonicalTransaction] = []
        
        for tx_elem in tree.xpath("./Transaction"):
            seq = int(tx_elem.get("seq"))
            tx_type = tx_elem.get("type", "SALE").upper()
            status = tx_elem.get("status", "COMPLETED").upper()
            device = tx_elem.get("device", "")
            staff = int(tx_elem.get("staff", "0"))
            shift = int(tx_elem.get("shift", "1"))
            
            start_str = tx_elem.get("start")
            start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S") if start_str else None
            end_str = tx_elem.get("end")
            end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S") if end_str else None
            
            orig_seq = tx_elem.get("originalSeq")
            original_seq = int(orig_seq) if orig_seq else None
            
            # Totals
            total_elem = tx_elem.find("Total")
            if total_elem is not None:
                net_total = Decimal(total_elem.get("net", "0.00"))
                tax_total = Decimal(total_elem.get("tax", "0.00"))
                gift_card_total = Decimal(total_elem.get("giftCardLoads", "0.00"))
                grand_total = Decimal(total_elem.get("total", "0.00"))
            else:
                net_total = Decimal("0.00")
                tax_total = Decimal("0.00")
                gift_card_total = Decimal("0.00")
                grand_total = Decimal("0.00")
            
            # Lines
            lines: list[CanonicalLine] = []
            for item_elem in tx_elem.xpath("./ItemLine"):
                line_no = int(item_elem.get("line", "1"))
                is_void = item_elem.get("status") == "VOID"
                line = CanonicalLine(
                    line_no=line_no,
                    item_code=item_elem.get("itemCode"),
                    variant=item_elem.get("variant", "000"),
                    description=item_elem.get("desc", ""),
                    dept=str(item_elem.get("dept", "99")).zfill(2),
                    qty=Decimal(item_elem.get("qty", "1")),
                    unit_price=Decimal(item_elem.get("unitPrice", "0.00")),
                    amount=Decimal(item_elem.get("amount", "0.00")),
                    tax_group=item_elem.get("taxGroup", "T0"),
                    is_void=is_void,
                )
                lines.append(line)
                
            # Tenders
            tenders: list[CanonicalTender] = []
            for tend_elem in tx_elem.xpath("./Tender"):
                tend_amount = Decimal(tend_elem.get("amount", "0.00"))
                tendered = Decimal(tend_elem.get("tendered")) if tend_elem.get("tendered") else None
                change = Decimal(tend_elem.get("change")) if tend_elem.get("change") else None
                tender = CanonicalTender(
                    tender_type=tend_elem.get("type", "CASH").upper(),
                    amount=tend_amount,
                    tendered=tendered,
                    change=change,
                    card_type=tend_elem.get("cardType"),
                    last4=tend_elem.get("last4"),
                    auth_code=tend_elem.get("auth"),
                    wallet=tend_elem.get("wallet"),
                    account_id=tend_elem.get("account"),
                )
                tenders.append(tender)
                
            # Taxes
            taxes: list[CanonicalTax] = []
            for tax_elem in tx_elem.xpath("./Tax"):
                taxes.append(
                    CanonicalTax(
                        tax_group=tax_elem.get("group", "T0"),
                        taxable_amount=Decimal(tax_elem.get("taxable", "0.00")),
                        tax_amount=Decimal(tax_elem.get("amount", "0.00")),
                    )
                )
                
            # Gift cards
            gift_cards: list[CanonicalGiftCard] = []
            for gc_elem in tx_elem.xpath("./GiftCardLine"):
                gift_cards.append(
                    CanonicalGiftCard(
                        line_no=int(gc_elem.get("line", "1")),
                        action=gc_elem.get("action", "LOAD"),
                        card_last4=gc_elem.get("cardLast4", ""),
                        amount=Decimal(gc_elem.get("amount", "0.00")),
                    )
                )
                
            # Cash Drops
            cash_drops: list[CanonicalCashDrop] = []
            for cd_elem in tx_elem.xpath("./CashDrop"):
                cash_drops.append(
                    CanonicalCashDrop(
                        envelope=cd_elem.get("envelope", ""),
                        amount=Decimal(cd_elem.get("amount", "0.00")),
                        status=cd_elem.get("status", "OK"),
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
                    start_time=start_time,
                    end_time=end_time,
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
            created_at=created_at,
            record_count=record_count or len(transactions),
            transactions=transactions,
        )
