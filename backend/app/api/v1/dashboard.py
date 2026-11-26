import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.transaction import Transaction, TransactionLine, TransactionTender, CashDrop
from app.models.master import Store, Device, Department

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _to_float(val: Any) -> float:
    if val is None:
        return 0.0
    return float(val)


@router.get("/daily")
async def get_daily_dashboard(
    store_id: Optional[str] = Query(None, description="Store identifier (e.g. BL01, BL02)"),
    date: Optional[str] = Query(None, description="Business date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Returns comprehensive daily dashboard metrics:
    - Headline figures: Total sales, Counter sales, Self-checkout sales, Transaction count, Avg basket, Gift card loads
    - Hourly sales breakdown
    - Tenders breakdown
    - Department breakdown
    - Watch list (voids, cancellations, refunds, no-sales, cash drops)
    """
    # Parse target date
    if date:
        try:
            target_date = datetime.date.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        latest_res = await db.execute(select(func.max(Transaction.business_date)))
        max_date = latest_res.scalar()
        target_date = max_date if max_date else datetime.date.today()

    # Base query filter
    tx_filters = [Transaction.business_date == target_date]
    if store_id:
        tx_filters.append(Transaction.store_id == store_id)

    # 1. Headline metrics: Fetch all transactions for this date & store
    query = (
        select(Transaction)
        .options(
            selectinload(Transaction.lines),
            selectinload(Transaction.tenders),
            selectinload(Transaction.taxes),
            selectinload(Transaction.cash_drops)
        )
        .where(and_(*tx_filters))
    )
    res = await db.execute(query)
    transactions: List[Transaction] = list(res.scalars().all())

    # Load devices to categorize Counter vs Self-checkout
    dev_query = select(Device)
    if store_id:
        dev_query = dev_query.where(Device.store_id == store_id)
    dev_res = await db.execute(dev_query)
    device_map = {d.device_id: d.device_type.upper() for d in dev_res.scalars().all()}

    total_sales = Decimal("0.00")
    counter_sales = Decimal("0.00")
    sco_sales = Decimal("0.00")
    sale_tx_count = 0
    gift_card_loads = Decimal("0.00")

    hourly_sales: Dict[int, Dict[str, Any]] = {h: {"hour": h, "sales": Decimal("0.00"), "tx_count": 0} for h in range(6, 23)}
    tenders_dict: Dict[str, Dict[str, Any]] = {}
    depts_dict: Dict[str, Dict[str, Any]] = {}
    watch_list: List[Dict[str, Any]] = []

    for tx in transactions:
        # Process gift card load
        if tx.gift_card_amount and tx.gift_card_amount > 0:
            gift_card_loads += tx.gift_card_amount

        # Sales and refunds count toward net turnover
        if tx.type in ("SALE", "REFUND"):
            net = tx.net_amount or Decimal("0.00")
            total_sales += net
            sale_tx_count += 1

            # Categorize device
            dev_type = device_map.get(tx.device_id, "POS")
            if "SCO" in dev_type or "SELF" in dev_type:
                sco_sales += net
            else:
                counter_sales += net

            # Hourly distribution
            if tx.start_time:
                hour = tx.start_time.hour
                if hour not in hourly_sales:
                    hourly_sales[hour] = {"hour": hour, "sales": Decimal("0.00"), "tx_count": 0}
                hourly_sales[hour]["sales"] += net
                hourly_sales[hour]["tx_count"] += 1

        # Tenders breakdown
        for tender in tx.tenders:
            t_type = (tender.tender_type or "OTHER").upper()
            if t_type not in tenders_dict:
                tenders_dict[t_type] = {"tender_type": t_type, "total_amount": Decimal("0.00"), "count": 0}
            tenders_dict[t_type]["total_amount"] += (tender.amount or Decimal("0.00"))
            tenders_dict[t_type]["count"] += 1

        # Department breakdown from lines (exclude void lines)
        for line in tx.lines:
            if not line.is_void:
                d_code = line.dept or "GENERAL"
                if d_code not in depts_dict:
                    depts_dict[d_code] = {"dept": d_code, "total_sales": Decimal("0.00"), "item_count": 0}
                depts_dict[d_code]["total_sales"] += (line.amount or Decimal("0.00"))
                depts_dict[d_code]["item_count"] += int(line.qty or 1)

        # Watch list exceptions
        is_exception = False
        reason = None
        if tx.type == "REFUND":
            is_exception = True
            reason = f"Refund processed: ${abs(tx.grand_total):.2f}"
        elif tx.type == "CANCELLED":
            is_exception = True
            reason = "Transaction cancelled by operator"
        elif tx.type == "NO_SALE":
            is_exception = True
            reason = "No Sale / Drawer Open event"
        elif any(l.is_void for l in tx.lines):
            is_exception = True
            void_count = sum(1 for l in tx.lines if l.is_void)
            reason = f"{void_count} item void(s) in transaction"

        if is_exception:
            watch_list.append({
                "id": tx.id,
                "store_id": tx.store_id,
                "seq": tx.seq,
                "time": tx.start_time.strftime("%H:%M:%S") if tx.start_time else "N/A",
                "type": tx.type,
                "device_id": tx.device_id,
                "staff_id": tx.staff_id,
                "amount": _to_float(tx.grand_total),
                "reason": reason
            })

        # Safe Cash Drops
        for cd in tx.cash_drops:
            watch_list.append({
                "id": tx.id,
                "store_id": tx.store_id,
                "seq": tx.seq,
                "time": tx.start_time.strftime("%H:%M:%S") if tx.start_time else "N/A",
                "type": "CASH_DROP",
                "device_id": tx.device_id,
                "staff_id": tx.staff_id,
                "amount": _to_float(cd.amount),
                "reason": f"Safe Cash Drop ({cd.status or 'COMPLETED'}) - Envelope: {cd.envelope or 'N/A'}"
            })

    # Sort watch list by time descending
    watch_list.sort(key=lambda x: x["time"], reverse=True)

    # Average basket
    avg_basket = (total_sales / sale_tx_count) if sale_tx_count > 0 else Decimal("0.00")

    return {
        "store_id": store_id or "ALL",
        "business_date": str(target_date),
        "headline": {
            "total_sales": _to_float(total_sales),
            "counter_sales": _to_float(counter_sales),
            "self_checkout_sales": _to_float(sco_sales),
            "transaction_count": sale_tx_count,
            "average_basket": _to_float(round(avg_basket, 2)),
            "gift_card_loads": _to_float(gift_card_loads),
        },
        "sales_by_hour": [
            {"hour": f"{h:02d}:00", "sales": _to_float(data["sales"]), "tx_count": data["tx_count"]}
            for h, data in sorted(hourly_sales.items())
        ],
        "tenders_breakdown": [
            {"tender_type": k, "total_amount": _to_float(v["total_amount"]), "count": v["count"]}
            for k, v in tenders_dict.items()
        ],
        "departments_breakdown": [
            {"dept": k, "total_sales": _to_float(v["total_sales"]), "item_count": v["item_count"]}
            for k, v in depts_dict.items()
        ],
        "watch_list": watch_list[:50]
    }
