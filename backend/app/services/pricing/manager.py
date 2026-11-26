import os
import uuid
import time
import math
import datetime
from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING
from pathlib import Path
from typing import List, Dict, Any, Optional
from lxml import etree
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update

from app.models.master import Item, Store, BusinessAccount
from app.models.transaction import Transaction, TransactionLine, TransactionTender


class PricingService:
    """
    Manages central price book updates, bulk pricing rules,
    XML ChangeFile generation for in-store hubs, and ACK/REJ processing.
    """

    def __init__(self, db: AsyncSession, inbox_dir: Optional[Path] = None, outbox_dir: Optional[Path] = None):
        self.db = db
        self.inbox_dir = inbox_dir or Path("runtime_data/inbox")
        self.outbox_dir = outbox_dir or Path("runtime_data/outbox")
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def apply_rounding_rule(price: Decimal, rule: str = "ROUND_UP_9") -> Decimal:
        """
        Applies retail pricing rounding rules:
        - ROUND_UP_9: Rounds up to nearest value ending in .99 or nearest 9 cents (e.g. 4.12 -> 4.19, 4.91 -> 4.99)
        - ROUND_99: Rounds up to nearest .99 (e.g. 4.12 -> 4.99)
        - ROUND_STANDARD: Standard 2-decimal half-up rounding
        """
        if rule == "ROUND_99":
            cents = int(price * 100)
            base_dollars = cents // 100
            current_cents = cents % 100
            if current_cents > 99:
                return Decimal(f"{base_dollars + 1}.99")
            return Decimal(f"{base_dollars}.99")
        elif rule == "ROUND_UP_9":
            # Round up to nearest price ending in 9 cents (e.g. .09, .19, .29, ..., .99)
            cents = int(math.ceil(float(price * 100)))
            remainder = cents % 10
            if remainder <= 9:
                cents += (9 - remainder)
            return Decimal(cents) / Decimal(100)
        else:
            return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    async def preview_bulk_adjustment(
        self,
        pct_change: float,
        dept: Optional[str] = None,
        rounding_rule: str = "ROUND_UP_9"
    ) -> List[Dict[str, Any]]:
        """
        Previews price adjustments for items in a department or across the catalog
        without committing changes to the database.
        """
        query = select(Item)
        if dept:
            query = query.where(Item.dept == dept)
        res = await self.db.execute(query)
        items = res.scalars().all()

        multiplier = Decimal(str(1 + (pct_change / 100.0)))
        preview = []

        for item in items:
            raw_new_price = item.price * multiplier
            new_price = self.apply_rounding_rule(raw_new_price, rounding_rule)
            diff = new_price - item.price
            pct_actual = (diff / item.price * 100) if item.price > 0 else Decimal("0.00")

            preview.append({
                "code": item.code,
                "variant": item.variant,
                "description": item.description,
                "dept": item.dept,
                "old_price": float(item.price),
                "new_price": float(new_price),
                "diff": float(diff),
                "pct_change": float(round(pct_actual, 2)),
                "tax_group": item.tax_group,
                "min_age": item.min_age
            })

        return preview

    async def apply_price_changes(
        self,
        updates: List[Dict[str, Any]],
        publish_to_stores: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Updates item records in the master database and optionally generates
        atomic XML ChangeFile batches in store inbox directories.
        """
        updated_items = []

        for u in updates:
            code = u.get("code") or u.get("item_code")
            variant = u.get("variant")
            new_price = Decimal(str(u["new_price"]))

            stmt = (
                update(Item)
                .where(and_(Item.code == code, Item.variant == variant, Item.is_deleted == False))
                .values(price=new_price)
            )
            await self.db.execute(stmt)
            updated_items.append({
                "code": code,
                "variant": variant or "000",
                "price": str(new_price),
                "description": u.get("description", "")[:24],  # Max 24 chars for E315
                "dept": u.get("dept", "20"),
                "tax_group": u.get("tax_group", "T1"),
                "min_age": u.get("min_age", 0)
            })

        await self.db.commit()

        change_files = []
        if publish_to_stores:
            for store_id in publish_to_stores:
                cf = self.generate_change_file(store_id, updated_items)
                change_files.append(cf)

        return {
            "status": "SUCCESS",
            "updated_count": len(updated_items),
            "change_files": change_files
        }

    def generate_change_file(
        self,
        store_id: str,
        items: List[Dict[str, Any]],
        change_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a specification-compliant XML change file for the in-store hub.
        Adheres to atomic write protocol (.tmp -> .xml) in store inbox.
        Ensures variant is set (000 if base) and description is <= 24 characters.
        """
        c_id = change_id or f"CHG_{store_id}_{int(time.time())}_{uuid.uuid4().hex[:4].upper()}"
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        root = etree.Element("ChangeFile", changeId=c_id, storeId=store_id, generated=now_str)
        items_elem = etree.SubElement(root, "Items")

        for itm in items:
            code = itm.get("code") or itm.get("item_code", "")
            variant = itm.get("variant") or "000"  # Required by E312
            desc = (itm.get("description") or "")[:24]  # Max 24 chars for E315
            price_val = Decimal(str(itm["price"]))

            etree.SubElement(
                items_elem,
                "Item",
                action="UPDATE",
                code=code,
                variant=variant,
                description=desc,
                dept=itm.get("dept", "20"),
                price=f"{price_val:.2f}",
                taxGroup=itm.get("tax_group", "T1"),
                ageRestricted=str(itm.get("min_age", 0))
            )

        xml_bytes = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")

        # Atomic write: write to .tmp then rename
        tmp_filename = f"{c_id}.tmp"
        final_filename = f"{c_id}.xml"

        tmp_path = self.inbox_dir / tmp_filename
        final_path = self.inbox_dir / final_filename

        with open(tmp_path, "wb") as f:
            f.write(xml_bytes)

        os.replace(tmp_path, final_path)

        return {
            "change_id": c_id,
            "store_id": store_id,
            "file_name": final_filename,
            "file_path": str(final_path),
            "item_count": len(items)
        }

    def inspect_sync_status(self) -> List[Dict[str, Any]]:
        """
        Scans outbox directory for ACK and REJ files emitted by in-store hubs.
        Returns status summary for each change file.
        """
        results = []
        if not self.outbox_dir.exists():
            return results

        for p in self.outbox_dir.glob("*.xml"):
            if not (p.name.startswith("ACK_") or p.name.startswith("REJ_")):
                continue

            try:
                tree = etree.parse(str(p))
                root = tree.getroot()
                tag = root.tag

                if tag == "ChangeReject":
                    results.append({
                        "file_name": p.name,
                        "status": "REJECTED",
                        "change_id": root.get("changeId"),
                        "store_id": root.get("storeId"),
                        "error_code": root.get("errorCode"),
                        "message": root.get("message"),
                        "processed_at": root.get("processed")
                    })
                elif tag == "ChangeAck":
                    item_results = []
                    for itm in root.xpath(".//Item | .//ItemResult"):
                        item_results.append({
                            "code": itm.get("code"),
                            "result": itm.get("result"),
                            "error_code": itm.get("errorCode"),
                            "reason": itm.get("reason")
                        })
                    results.append({
                        "file_name": p.name,
                        "status": root.get("result", "APPLIED"),
                        "change_id": root.get("changeId"),
                        "store_id": root.get("storeId"),
                        "processed_at": root.get("processed"),
                        "items": item_results
                    })
            except Exception:
                continue

        return results

    async def generate_commercial_statement(
        self,
        account_id: str,
        month: str  # YYYY-MM
    ) -> Dict[str, Any]:
        """
        Generates a commercial business account monthly billing statement.
        Aggregates account transactions, itemized lines, and payment due terms.
        """
        acc_res = await self.db.execute(select(BusinessAccount).where(BusinessAccount.account_id == account_id))
        acc = acc_res.scalar_one_or_none()
        if not acc:
            raise ValueError(f"Business account '{account_id}' not found.")

        # Date range for the billing month
        year, m = map(int, month.split("-"))
        start_date = datetime.date(year, m, 1)
        next_month = datetime.date(year + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)

        # Find transactions tendered to this account
        tender_subquery = (
            select(TransactionTender.transaction_id)
            .where(
                and_(
                    TransactionTender.tender_type == "COMMERCIAL_ACCOUNT",
                    TransactionTender.account_id == account_id
                )
            )
        )
        tx_query = (
            select(Transaction)
            .where(
                and_(
                    Transaction.id.in_(tender_subquery),
                    Transaction.business_date >= start_date,
                    Transaction.business_date < next_month
                )
            )
            .order_by(Transaction.business_date, Transaction.seq)
        )
        tx_res = await self.db.execute(tx_query)
        transactions = tx_res.scalars().all()

        total_charges = Decimal("0.00")
        statement_lines = []

        for tx in transactions:
            total_charges += (tx.grand_total or Decimal("0.00"))
            statement_lines.append({
                "date": str(tx.business_date),
                "store_id": tx.store_id,
                "invoice_ref": f"TX-{tx.store_id}-{tx.seq}",
                "amount": float(tx.grand_total or Decimal("0.00")),
                "type": tx.type
            })

        terms_days = 30
        if "15" in (acc.terms or ""):
            terms_days = 15

        due_date = next_month + datetime.timedelta(days=terms_days)

        return {
            "account_id": acc.account_id,
            "business_name": acc.business_name,
            "home_store": acc.home_store,
            "credit_limit": float(acc.credit_limit or Decimal("0.00")),
            "terms": acc.terms or "NET30",
            "billing_period": month,
            "statement_date": str(next_month),
            "payment_due_date": str(due_date),
            "total_charges": float(total_charges),
            "transactions_count": len(statement_lines),
            "transactions": statement_lines
        }
