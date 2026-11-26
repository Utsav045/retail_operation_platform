from datetime import date
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.transaction import Transaction, TransactionLine, TransactionTender, TransactionTax, GiftCardActivity, CashDrop
from app.models.summary import ShiftSummary, EndOfDaySummary, ReconciliationReport
from app.models.audit import QuarantinedFile


class ReconciliationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def reconcile_eod(self, store_id: str, business_date: date) -> Dict[str, Any]:
        """
        Recomputes ground truth from transaction logs and compares against EndOfDay summary.
        Evaluates hub self-consistency and performs root-cause diagnostics on any discrepancies.
        """
        # 1. Fetch EOD summary
        eod_summary = (
            await self.session.execute(
                select(EndOfDaySummary).where(
                    EndOfDaySummary.store_id == store_id,
                    EndOfDaySummary.business_date == business_date,
                )
            )
        ).scalar_one_or_none()

        # 2. Check for quarantined files for this store & date
        # Check if any quarantined files match the store or date
        date_str_nodash = business_date.strftime("%Y%m%d")
        quarantined_files = (
            await self.session.execute(
                select(QuarantinedFile.file_name).where(
                    QuarantinedFile.file_name.like(f"%{store_id}%")
                )
            )
        ).scalars().all()
        
        has_quarantined_file = False
        quarantined_matches = []
        for qf in quarantined_files:
            # Check if this quarantined file relates to this business date
            if date_str_nodash in qf:
                has_quarantined_file = True
                quarantined_matches.append(qf)

        # 3. Compute ground truth from transactions
        tx_query = select(Transaction).where(
            Transaction.store_id == store_id,
            Transaction.business_date == business_date,
            Transaction.status == "COMPLETED",
        ).options(
            selectinload(Transaction.lines),
            selectinload(Transaction.tenders),
            selectinload(Transaction.taxes),
            selectinload(Transaction.gift_cards),
            selectinload(Transaction.cash_drops),
        )
        txs = (await self.session.execute(tx_query)).scalars().all()

        computed_transactions = len(txs)
        computed_net_sales = Decimal("0.00")
        computed_tax = Decimal("0.00")
        computed_gift_card_loads = Decimal("0.00")
        computed_grand_total = Decimal("0.00")

        computed_depts: Dict[str, Dict[str, Any]] = {}
        computed_tenders: Dict[str, Decimal] = {}
        computed_taxes: Dict[str, Dict[str, Decimal]] = {}
        voided_lines_list = []

        for tx in txs:
            # Financial sums from transaction level
            computed_net_sales += tx.net_amount
            computed_tax += tx.tax_amount
            computed_gift_card_loads += tx.gift_card_amount
            computed_grand_total += tx.grand_total

            # Line items breakdown
            for line in tx.lines:
                if line.is_void:
                    voided_lines_list.append(line)
                    continue
                dept_code = line.dept.lstrip("0") or "0"
                if dept_code not in computed_depts:
                    computed_depts[dept_code] = {"name": "", "qty": Decimal("0.000"), "amount": Decimal("0.00")}
                computed_depts[dept_code]["qty"] += line.qty
                computed_depts[dept_code]["amount"] += line.amount

            # Tenders breakdown
            for tender in tx.tenders:
                t_type = tender.tender_type.upper()
                if t_type == "GIFT_CARD":
                    t_type = "GIFT"
                computed_tenders[t_type] = computed_tenders.get(t_type, Decimal("0.00")) + tender.amount

            # Taxes breakdown
            for tax in tx.taxes:
                grp = tax.tax_group
                if grp not in computed_taxes:
                    computed_taxes[grp] = {"taxable": Decimal("0.00"), "amount": Decimal("0.00")}
                computed_taxes[grp]["taxable"] += tax.taxable_amount
                computed_taxes[grp]["amount"] += tax.tax_amount

        # Also check all voided lines (even on non-completed sales)
        all_voided_lines = (
            await self.session.execute(
                select(TransactionLine)
                .join(Transaction)
                .where(
                    Transaction.store_id == store_id,
                    Transaction.business_date == business_date,
                    TransactionLine.is_void == True,
                )
            )
        ).scalars().all()
        voided_amount_total = sum((l.amount for l in all_voided_lines), Decimal("0.00"))

        if not eod_summary:
            status = "REVIEW_REQUIRED"
            discrepancy_msg = "EndOfDay summary file not found for this store and business date."
            report = ReconciliationReport(
                store_id=store_id,
                business_date=business_date,
                report_type="DAILY_EOD",
                computed_net_sales=computed_net_sales,
                computed_tax=computed_tax,
                computed_gift_card_loads=computed_gift_card_loads,
                computed_grand_total=computed_grand_total,
                status=status,
                is_consistent=False,
                discrepancy_details=discrepancy_msg,
            )
            self.session.add(report)
            await self.session.commit()
            return {
                "store_id": store_id,
                "business_date": str(business_date),
                "status": status,
                "reason": discrepancy_msg,
            }

        # 4. Compare computed vs reported
        net_diff = (computed_net_sales - eod_summary.reported_net_sales).quantize(Decimal("0.01"))
        tax_diff = (computed_tax - eod_summary.reported_tax).quantize(Decimal("0.01"))
        gc_diff = (computed_gift_card_loads - eod_summary.reported_gift_card_loads).quantize(Decimal("0.01"))
        grand_diff = (computed_grand_total - eod_summary.reported_grand_total).quantize(Decimal("0.01"))
        tx_diff = computed_transactions - eod_summary.reported_transactions

        # 5. Hub Self-Consistency Check
        reported_parts_sum = (
            eod_summary.reported_net_sales + eod_summary.reported_tax + eod_summary.reported_gift_card_loads
        ).quantize(Decimal("0.01"))
        
        # Sum of reported tenders
        reported_tenders = eod_summary.tenders_json or {}
        reported_tender_sum = sum(
            (Decimal(str(v)) for v in reported_tenders.values()), Decimal("0.00")
        ).quantize(Decimal("0.01"))

        # Sum of reported departments
        reported_depts = eod_summary.departments_json or {}
        reported_dept_sum = sum(
            (Decimal(str(v["amount"])) for v in reported_depts.values() if isinstance(v, dict) and "amount" in v),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))

        is_consistent = True
        consistency_errors = []
        if reported_parts_sum != eod_summary.reported_grand_total:
            is_consistent = False
            consistency_errors.append(
                f"Hub parts sum (${reported_parts_sum}) does not equal stated grandTotal (${eod_summary.reported_grand_total})"
            )
        if reported_tender_sum != eod_summary.reported_grand_total:
            is_consistent = False
            consistency_errors.append(
                f"Hub tender sum (${reported_tender_sum}) does not equal stated grandTotal (${eod_summary.reported_grand_total})"
            )

        # 6. Discrepancy Diagnostics & Root Cause Analysis
        discrepancy_reasons = []

        if has_quarantined_file:
            discrepancy_reasons.append(
                f"Corrupted batch file quarantined for this date: {', '.join(quarantined_matches)}. Ground truth TLOG data is incomplete."
            )

        if not is_consistent:
            discrepancy_reasons.extend(consistency_errors)

        if net_diff != Decimal("0.00") or grand_diff != Decimal("0.00") or tax_diff != Decimal("0.00"):
            # Check if diff matches a voided line
            for void_l in all_voided_lines:
                if abs(net_diff) == void_l.amount:
                    discrepancy_reasons.append(
                        f"Reported net sales incorrectly includes voided line: '{void_l.description}' (${void_l.amount}) on line {void_l.line_no}."
                    )
            
            # Check if reported net sales includes gift cards
            if eod_summary.reported_gift_card_loads > Decimal("0.00"):
                if abs(net_diff) == eod_summary.reported_gift_card_loads:
                    discrepancy_reasons.append(
                        f"Reported net sales incorrectly includes gift card load (${eod_summary.reported_gift_card_loads}) as merchandise sales."
                    )

            if tx_diff != 0:
                discrepancy_reasons.append(
                    f"Transaction count mismatch: computed {computed_transactions} vs reported {eod_summary.reported_transactions} (diff: {tx_diff})."
                )

        # Determine Status
        if has_quarantined_file:
            status = "REVIEW_REQUIRED"
        elif net_diff == Decimal("0.00") and tax_diff == Decimal("0.00") and gc_diff == Decimal("0.00") and grand_diff == Decimal("0.00") and is_consistent:
            status = "MATCHED"
        else:
            status = "MISMATCH"

        discrepancy_details = "; ".join(discrepancy_reasons) if discrepancy_reasons else "All totals and breakdowns match ground truth."

        # Save or update report in DB
        existing_report = (
            await self.session.execute(
                select(ReconciliationReport).where(
                    ReconciliationReport.store_id == store_id,
                    ReconciliationReport.business_date == business_date,
                    ReconciliationReport.report_type == "DAILY_EOD",
                )
            )
        ).scalar_one_or_none()

        report_data = {
            "store_id": store_id,
            "business_date": business_date,
            "report_type": "DAILY_EOD",
            "computed_net_sales": computed_net_sales,
            "reported_net_sales": eod_summary.reported_net_sales,
            "net_sales_diff": net_diff,
            "computed_tax": computed_tax,
            "reported_tax": eod_summary.reported_tax,
            "tax_diff": tax_diff,
            "computed_gift_card_loads": computed_gift_card_loads,
            "reported_gift_card_loads": eod_summary.reported_gift_card_loads,
            "gift_card_diff": gc_diff,
            "computed_grand_total": computed_grand_total,
            "reported_grand_total": eod_summary.reported_grand_total,
            "grand_total_diff": grand_diff,
            "status": status,
            "is_consistent": is_consistent,
            "discrepancy_details": discrepancy_details,
        }

        if existing_report:
            for k, v in report_data.items():
                setattr(existing_report, k, v)
        else:
            existing_report = ReconciliationReport(**report_data)
            self.session.add(existing_report)

        await self.session.commit()

        return {
            "store_id": store_id,
            "business_date": str(business_date),
            "status": status,
            "is_consistent": is_consistent,
            "computed": {
                "transactions": computed_transactions,
                "net_sales": str(computed_net_sales),
                "tax": str(computed_tax),
                "gift_card_loads": str(computed_gift_card_loads),
                "grand_total": str(computed_grand_total),
            },
            "reported": {
                "transactions": eod_summary.reported_transactions,
                "net_sales": str(eod_summary.reported_net_sales),
                "tax": str(eod_summary.reported_tax),
                "gift_card_loads": str(eod_summary.reported_gift_card_loads),
                "grand_total": str(eod_summary.reported_grand_total),
            },
            "differences": {
                "net_sales": str(net_diff),
                "tax": str(tax_diff),
                "gift_card_loads": str(gc_diff),
                "grand_total": str(grand_diff),
                "transactions": tx_diff,
            },
            "discrepancy_details": discrepancy_details,
        }

    async def reconcile_shift(self, store_id: str, business_date: date, shift_no: int) -> Dict[str, Any]:
        """
        Reconciles cash drawer for a specific shift:
        expected_cash = opening_float + cash_tenders - cash_refunds - completed_cash_drops.
        Compares expected_cash with counted_cash reported by the hub.
        """
        shift_summary = (
            await self.session.execute(
                select(ShiftSummary).where(
                    ShiftSummary.store_id == store_id,
                    ShiftSummary.business_date == business_date,
                    ShiftSummary.shift_no == shift_no,
                )
            )
        ).scalar_one_or_none()

        if not shift_summary:
            return {
                "store_id": store_id,
                "business_date": str(business_date),
                "shift_no": shift_no,
                "status": "REVIEW_REQUIRED",
                "reason": f"Shift {shift_no} summary not found for store {store_id} on {business_date}",
            }

        # Query all completed transactions for this store, date, shift
        tx_query = select(Transaction).where(
            Transaction.store_id == store_id,
            Transaction.business_date == business_date,
            Transaction.shift == shift_no,
            Transaction.status == "COMPLETED",
        ).options(
            selectinload(Transaction.tenders),
            selectinload(Transaction.cash_drops),
        )
        txs = (await self.session.execute(tx_query)).scalars().all()

        cash_tenders_sum = Decimal("0.00")
        cash_refunds_sum = Decimal("0.00")

        for tx in txs:
            for t in tx.tenders:
                if t.tender_type.upper() == "CASH":
                    if tx.type == "REFUND" or t.amount < Decimal("0.00"):
                        cash_refunds_sum += abs(t.amount)
                    else:
                        cash_tenders_sum += t.amount

        # Completed Cash Drops during shift
        completed_drops_sum = Decimal("0.00")
        for tx in txs:
            for drop in tx.cash_drops:
                if drop.status.upper() in ("OK", "COMPLETED"):
                    completed_drops_sum += drop.amount

        # Also check cash drops logged directly on the summary
        summary_drops = shift_summary.cash_drops_amount or Decimal("0.00")
        # Use transaction cash drops if present, else summary drops
        drops_to_use = completed_drops_sum if completed_drops_sum > Decimal("0.00") else summary_drops

        opening_float = shift_summary.opening_float
        counted_cash = shift_summary.counted_cash

        # Expected Cash Formula:
        # opening_float + cash_tenders - cash_refunds - completed_cash_drops
        expected_cash = (opening_float + cash_tenders_sum - cash_refunds_sum - drops_to_use).quantize(Decimal("0.01"))
        cash_diff = (counted_cash - expected_cash).quantize(Decimal("0.01"))

        if cash_diff == Decimal("0.00"):
            status = "MATCHED"
            reason = "Counted cash exactly equals expected cash."
        elif cash_diff > Decimal("0.00"):
            status = "MISMATCH"
            reason = f"Cash drawer overage of ${cash_diff} (counted ${counted_cash} vs expected ${expected_cash})."
        else:
            status = "MISMATCH"
            reason = f"Cash drawer shortage of ${abs(cash_diff)} (counted ${counted_cash} vs expected ${expected_cash})."

        # Update shift summary with calculated metrics
        shift_summary.expected_cash = expected_cash
        shift_summary.cash_difference = cash_diff

        # Record in ReconciliationReport table
        existing_report = (
            await self.session.execute(
                select(ReconciliationReport).where(
                    ReconciliationReport.store_id == store_id,
                    ReconciliationReport.business_date == business_date,
                    ReconciliationReport.report_type == "SHIFT",
                    ReconciliationReport.shift_no == shift_no,
                )
            )
        ).scalar_one_or_none()

        report_data = {
            "store_id": store_id,
            "business_date": business_date,
            "report_type": "SHIFT",
            "shift_no": shift_no,
            "expected_cash": expected_cash,
            "counted_cash": counted_cash,
            "cash_diff": cash_diff,
            "status": status,
            "is_consistent": True,
            "discrepancy_details": reason,
        }

        if existing_report:
            for k, v in report_data.items():
                setattr(existing_report, k, v)
        else:
            self.session.add(ReconciliationReport(**report_data))

        await self.session.commit()

        return {
            "store_id": store_id,
            "business_date": str(business_date),
            "shift_no": shift_no,
            "opening_float": str(opening_float),
            "cash_taken": str(cash_tenders_sum),
            "cash_refunds": str(cash_refunds_sum),
            "cash_drops": str(drops_to_use),
            "expected_cash": str(expected_cash),
            "counted_cash": str(counted_cash),
            "variance": str(cash_diff),
            "status": status,
            "reason": reason,
        }
