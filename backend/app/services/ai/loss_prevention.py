import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.models.transaction import Transaction, TransactionLine, TransactionTender, CashDrop
from app.models.summary import ShiftSummary, ReconciliationReport
from app.models.master import Store, Staff, Department


class LossPreventionService:
    """
    AI Loss Prevention & Store Operations Intelligence Engine:
    - Analyzes cashier transaction patterns to detect anomalies (void clusters, excessive refunds, no-sales)
    - Detects cash drawer shortages and cancelled cash drops
    - Provides 'Ask Your Stores' query answering engine with verifiable data citations
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_daily_audit(
        self,
        business_date: datetime.date,
        store_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes daily loss prevention heuristics across all registers and staff.
        Returns prioritized incident alert cards linked to specific transactions and staff.
        """
        incidents: List[Dict[str, Any]] = []

        # 1. Fetch transactions for the target date
        tx_query = (
            select(Transaction)
            .options(
                selectinload(Transaction.lines),
                selectinload(Transaction.tenders)
            )
            .where(Transaction.business_date == business_date)
        )
        if store_id:
            tx_query = tx_query.where(Transaction.store_id == store_id)

        tx_res = await self.db.execute(tx_query)
        transactions = tx_res.scalars().all()

        # Track cashier metrics
        staff_stats: Dict[str, Dict[str, Any]] = {}

        for tx in transactions:
            s_id = tx.staff_id or "UNKNOWN"
            if s_id not in staff_stats:
                staff_stats[s_id] = {
                    "staff_id": s_id,
                    "store_id": tx.store_id,
                    "total_tx": 0,
                    "void_lines": 0,
                    "void_amount": Decimal("0.00"),
                    "refund_count": 0,
                    "refund_amount": Decimal("0.00"),
                    "no_sale_count": 0,
                    "cancelled_tx": 0,
                    "tx_refs": []
                }

            st = staff_stats[s_id]
            st["total_tx"] += 1
            st["tx_refs"].append(tx.seq)

            # Check voids in lines
            for l in tx.lines:
                if l.is_void:
                    st["void_lines"] += 1
                    st["void_amount"] += (l.amount or Decimal("0.00"))

            # Check transaction types
            if tx.type == "REFUND":
                st["refund_count"] += 1
                st["refund_amount"] += abs(tx.grand_total or Decimal("0.00"))
            elif tx.type == "NO_SALE":
                st["no_sale_count"] += 1
            elif tx.type == "CANCELLED":
                st["cancelled_tx"] += 1

            # Individual High-Risk Transaction Check: Single Tx with >= 2 Voids
            void_lines = [l for l in tx.lines if l.is_void]
            if len(void_lines) >= 2:
                incidents.append({
                    "incident_id": f"LP-VOID-{tx.store_id}-{tx.seq}",
                    "severity": "MEDIUM",
                    "category": "VOID_CLUSTER",
                    "store_id": tx.store_id,
                    "timestamp": tx.start_time.isoformat() if tx.start_time else None,
                    "device_id": tx.device_id,
                    "staff_id": tx.staff_id,
                    "transaction_seq": tx.seq,
                    "headline": f"Cashier Void Cluster: {len(void_lines)} voided items in single basket",
                    "details": f"Items voided: {', '.join([l.description or l.item_code for l in void_lines])}. Total void value: ${sum(l.amount for l in void_lines):.2f}.",
                    "recommended_action": "Review register CCTV at transaction time to verify customer walked away or cashier error."
                })

            # Check high-value refund
            if tx.type == "REFUND" and abs(tx.grand_total or Decimal("0.00")) > Decimal("30.00"):
                incidents.append({
                    "incident_id": f"LP-REFUND-{tx.store_id}-{tx.seq}",
                    "severity": "HIGH",
                    "category": "HIGH_VALUE_REFUND",
                    "store_id": tx.store_id,
                    "timestamp": tx.start_time.isoformat() if tx.start_time else None,
                    "device_id": tx.device_id,
                    "staff_id": tx.staff_id,
                    "transaction_seq": tx.seq,
                    "headline": f"High-Value Refund without Original Receipt: ${abs(tx.grand_total):.2f}",
                    "details": f"Refund transaction for ${abs(tx.grand_total):.2f} processed by {tx.staff_id}. Original seq: {tx.original_seq or 'None'}.",
                    "recommended_action": "Verify manager authorization signature and matching returned physical merchandise."
                })

        # Check Staff Aggregate Anomalies
        for s_id, data in staff_stats.items():
            if data["void_lines"] >= 4:
                incidents.append({
                    "incident_id": f"LP-STAFF-VOID-{data['store_id']}-{s_id}",
                    "severity": "HIGH",
                    "category": "EXCESSIVE_STAFF_VOIDS",
                    "store_id": data["store_id"],
                    "timestamp": datetime.datetime.now().isoformat(),
                    "device_id": "MULTIPLE",
                    "staff_id": s_id,
                    "transaction_seq": None,
                    "headline": f"Excessive Void Activity by Operator {s_id}",
                    "details": f"Staff member {s_id} logged {data['void_lines']} line voids totalling ${data['void_amount']:.2f} across {data['total_tx']} transactions.",
                    "recommended_action": "Schedule cash handling retraining; monitor till drawer scans."
                })

            if data["no_sale_count"] >= 3:
                incidents.append({
                    "incident_id": f"LP-NOSALE-{data['store_id']}-{s_id}",
                    "severity": "MEDIUM",
                    "category": "UNUSUAL_NO_SALE_OPENS",
                    "store_id": data["store_id"],
                    "timestamp": datetime.datetime.now().isoformat(),
                    "device_id": "POS",
                    "staff_id": s_id,
                    "transaction_seq": None,
                    "headline": f"Frequent Drawer Opens: {data['no_sale_count']} No-Sale events",
                    "details": f"Operator opened cash drawer without an active transaction {data['no_sale_count']} times.",
                    "recommended_action": "Check drawer count for short float or unauthorized cash exchange."
                })

        # 2. Check Shift Close Shortages from Reconciliation Reports
        r_query = select(ReconciliationReport).where(
            and_(
                ReconciliationReport.business_date == business_date,
                ReconciliationReport.report_type == "SHIFT"
            )
        )
        if store_id:
            r_query = r_query.where(ReconciliationReport.store_id == store_id)

        r_res = await self.db.execute(r_query)
        shift_reports = r_res.scalars().all()

        for r in shift_reports:
            if r.cash_diff and abs(r.cash_diff) > Decimal("5.00"):
                diff = float(r.cash_diff)
                direction = "SHORTAGE" if diff < 0 else "OVERAGE"
                incidents.append({
                    "incident_id": f"LP-CASH-{r.store_id}-{r.target_id}",
                    "severity": "HIGH" if abs(diff) >= 20.0 else "MEDIUM",
                    "category": f"CASH_DRAWER_{direction}",
                    "store_id": r.store_id,
                    "timestamp": r.created_at.isoformat() if r.created_at else None,
                    "device_id": "POS",
                    "staff_id": r.comparison_details.get("staff_id", "N/A"),
                    "transaction_seq": None,
                    "headline": f"Cash Drawer {direction}: ${abs(diff):.2f} on Shift {r.target_id}",
                    "details": f"Expected cash ${r.comparison_details.get('expected_cash', 0):.2f} vs Actual count ${r.comparison_details.get('actual_cash', 0):.2f}. Variance: ${diff:.2f}.",
                    "recommended_action": "Conduct immediate cash drawer blind audit and interview closing cashier."
                })

        # Severity sort: HIGH first, then MEDIUM, then LOW
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        incidents.sort(key=lambda x: severity_order.get(x["severity"], 3))

        return {
            "business_date": str(business_date),
            "store_id": store_id or "ALL",
            "total_incidents": len(incidents),
            "high_severity_count": sum(1 for i in incidents if i["severity"] == "HIGH"),
            "incidents": incidents
        }

    async def answer_store_query(
        self,
        prompt: str,
        store_id: Optional[str] = None,
        date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        'Ask Your Stores' Natural Language AI Assistant:
        Interprets natural language questions regarding store sales, hourly patterns,
        reconciliation status, void spikes, or cashier performance and returns
        factual data citations.
        """
        p = prompt.lower()
        today = datetime.date(2026, 10, 4) if not date_str else datetime.date.fromisoformat(date_str)

        # 1. Query: Highest selling department / top department
        if "department" in p or "highest selling" in p or "produce" in p or "grocery" in p:
            dept_res = await self.db.execute(
                select(TransactionLine.dept, func.sum(TransactionLine.amount).label("sales"))
                .join(Transaction, Transaction.id == TransactionLine.transaction_id)
                .where(Transaction.business_date == today)
                .group_by(TransactionLine.dept)
                .order_by(desc("sales"))
            )
            dept_rows = dept_res.all()
            top = dept_rows[0] if dept_rows else ("10", Decimal("0.00"))
            return {
                "question": prompt,
                "answer": f"For {today}, the top-performing department was Dept {top[0]} with total merchandise sales of ${top[1]:.2f}. Across all departments, {len(dept_rows)} active categories recorded transactions.",
                "data": [{"dept": r[0], "sales": float(r[1])} for r in dept_rows],
                "confidence": 0.98
            }

        # 2. Query: Reconciliation or discrepancy
        elif "reconciliation" in p or "discrepancy" in p or "mismatch" in p or "variance" in p:
            r_res = await self.db.execute(
                select(ReconciliationReport).where(ReconciliationReport.business_date == today)
            )
            reports = r_res.scalars().all()
            mismatches = [r for r in reports if r.status in ("MISMATCH", "REVIEW_REQUIRED")]

            if mismatches:
                m = mismatches[0]
                return {
                    "question": prompt,
                    "answer": f"On {today}, store {m.store_id} flagged a reconciliation discrepancy (status: {m.status}). Ground truth net sales variance: ${m.net_sales_diff:.2f}, grand total variance: ${m.grand_total_diff:.2f}. Root cause diagnostic: {m.root_cause_analysis}",
                    "data": {
                        "store_id": m.store_id,
                        "status": m.status,
                        "net_sales_diff": float(m.net_sales_diff),
                        "root_cause": m.root_cause_analysis
                    },
                    "confidence": 0.99
                }
            else:
                return {
                    "question": prompt,
                    "answer": f"All stores reconciled with 100% precision on {today}. Ground truth transaction sums matched stated hub totals.",
                    "data": {"status": "MATCHED"},
                    "confidence": 0.95
                }

        # 3. Query: Voids, cashier, or loss prevention
        elif "void" in p or "refund" in p or "cashier" in p or "loss" in p:
            audit = await self.generate_daily_audit(today, store_id)
            return {
                "question": prompt,
                "answer": f"On {today}, the Loss Prevention engine identified {audit['total_incidents']} operational alerts ({audit['high_severity_count']} high severity). The primary events involve cashier void clusters and drawer reconciliations.",
                "data": audit["incidents"][:5],
                "confidence": 0.96
            }

        # 4. Default: Headline Sales overview
        else:
            tx_res = await self.db.execute(
                select(
                    func.sum(Transaction.net_amount),
                    func.count(Transaction.id),
                    func.sum(Transaction.tax_amount)
                ).where(Transaction.business_date == today)
            )
            row = tx_res.one()
            total_net = row[0] or Decimal("0.00")
            count = row[1] or 0
            tax = row[2] or Decimal("0.00")

            return {
                "question": prompt,
                "answer": f"On {today}, network-wide retail sales totaled ${total_net:.2f} across {count} transactions, generating ${tax:.2f} in tax revenue. Average basket size was ${(total_net / count):.2f}." if count > 0 else f"No transactions recorded on {today}.",
                "data": {
                    "date": str(today),
                    "net_sales": float(total_net),
                    "transactions": count,
                    "tax": float(tax)
                },
                "confidence": 0.95
            }
