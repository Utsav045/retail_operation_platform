import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.transaction import Transaction, TransactionLine, TransactionTender, TransactionTax, GiftCardActivity

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def _to_float(val: Any) -> float:
    if val is None:
        return 0.0
    return float(val)


@router.get("")
async def list_transactions(
    store_id: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    dept: Optional[str] = Query(None),
    tender_type: Optional[str] = Query(None),
    tx_type: Optional[str] = Query(None, alias="type"),
    device_id: Optional[str] = Query(None),
    staff_id: Optional[str] = Query(None),
    is_flagged: Optional[bool] = Query(None),
    has_voids: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search and filter transactions across stores, date ranges, departments, tenders, and exception types.
    """
    filters = []

    if store_id:
        filters.append(Transaction.store_id == store_id)
    if date:
        try:
            filters.append(Transaction.business_date == datetime.date.fromisoformat(date))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    if start_date:
        try:
            filters.append(Transaction.business_date >= datetime.date.fromisoformat(start_date))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format.")
    if end_date:
        try:
            filters.append(Transaction.business_date <= datetime.date.fromisoformat(end_date))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format.")
    if tx_type:
        filters.append(Transaction.type == tx_type.upper())
    if device_id:
        filters.append(Transaction.device_id == device_id)
    if staff_id:
        filters.append(Transaction.staff_id == staff_id)
    if is_flagged is not None:
        filters.append(Transaction.is_flagged == is_flagged)

    # Department filter requires joining TransactionLine
    if dept:
        filters.append(Transaction.id.in_(
            select(TransactionLine.transaction_id).where(TransactionLine.dept == dept.upper())
        ))

    # Tender filter requires joining TransactionTender
    if tender_type:
        filters.append(Transaction.id.in_(
            select(TransactionTender.transaction_id).where(TransactionTender.tender_type == tender_type.upper())
        ))

    # Void filter
    if has_voids is True:
        filters.append(Transaction.id.in_(
            select(TransactionLine.transaction_id).where(TransactionLine.is_void == True)
        ))

    # Count query
    count_query = select(func.count(Transaction.id)).where(and_(*filters)) if filters else select(func.count(Transaction.id))
    total_count = (await db.execute(count_query)).scalar() or 0

    # Data query
    data_query = (
        select(Transaction)
        .options(
            selectinload(Transaction.lines),
            selectinload(Transaction.tenders),
            selectinload(Transaction.taxes)
        )
        .order_by(desc(Transaction.business_date), desc(Transaction.start_time), desc(Transaction.seq))
        .offset(offset)
        .limit(limit)
    )
    if filters:
        data_query = data_query.where(and_(*filters))

    res = await db.execute(data_query)
    records = res.scalars().all()

    items = []
    for tx in records:
        void_count = sum(1 for l in tx.lines if l.is_void)
        items.append({
            "id": tx.id,
            "store_id": tx.store_id,
            "seq": tx.seq,
            "business_date": str(tx.business_date),
            "start_time": tx.start_time.strftime("%H:%M:%S") if tx.start_time else None,
            "type": tx.type,
            "status": tx.status,
            "device_id": tx.device_id,
            "staff_id": tx.staff_id,
            "shift": tx.shift,
            "net_amount": _to_float(tx.net_amount),
            "tax_amount": _to_float(tx.tax_amount),
            "gift_card_amount": _to_float(tx.gift_card_amount),
            "grand_total": _to_float(tx.grand_total),
            "item_count": len([l for l in tx.lines if not l.is_void]),
            "void_count": void_count,
            "is_flagged": tx.is_flagged,
            "flag_reason": tx.flag_reason,
            "tenders": [t.tender_type for t in tx.tenders]
        })

    return {
        "total": total_count,
        "offset": offset,
        "limit": limit,
        "items": items
    }


@router.get("/{tx_id}")
async def get_transaction_detail(
    tx_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retrieve full transaction receipt detail including line items, taxes, tenders, and gift card records.
    """
    query = (
        select(Transaction)
        .options(
            selectinload(Transaction.lines),
            selectinload(Transaction.tenders),
            selectinload(Transaction.taxes),
            selectinload(Transaction.gift_cards)
        )
        .where(Transaction.id == tx_id)
    )
    res = await db.execute(query)
    tx = res.scalar_one_or_none()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    return {
        "id": tx.id,
        "store_id": tx.store_id,
        "seq": tx.seq,
        "business_date": str(tx.business_date),
        "start_time": tx.start_time.isoformat() if tx.start_time else None,
        "end_time": tx.end_time.isoformat() if tx.end_time else None,
        "type": tx.type,
        "status": tx.status,
        "device_id": tx.device_id,
        "staff_id": tx.staff_id,
        "shift": tx.shift,
        "original_seq": tx.original_seq,
        "net_amount": _to_float(tx.net_amount),
        "tax_amount": _to_float(tx.tax_amount),
        "gift_card_amount": _to_float(tx.gift_card_amount),
        "grand_total": _to_float(tx.grand_total),
        "is_flagged": tx.is_flagged,
        "flag_reason": tx.flag_reason,
        "raw_file_name": tx.raw_file_name,
        "lines": [
            {
                "line_no": l.line_no,
                "item_code": l.item_code,
                "variant": l.variant,
                "description": l.description,
                "dept": l.dept,
                "qty": _to_float(l.qty),
                "unit_price": _to_float(l.unit_price),
                "amount": _to_float(l.amount),
                "tax_group": l.tax_group,
                "is_void": l.is_void,
                "is_flagged": l.is_flagged,
                "flag_reason": l.flag_reason
            }
            for l in sorted(tx.lines, key=lambda x: x.line_no)
        ],
        "tenders": [
            {
                "tender_type": t.tender_type,
                "amount": _to_float(t.amount),
                "tendered": _to_float(t.tendered),
                "change": _to_float(t.change),
                "card_type": t.card_type,
                "last4": t.last4,
                "auth_code": t.auth_code,
                "wallet": t.wallet,
                "account_id": t.account_id
            }
            for t in tx.tenders
        ],
        "taxes": [
            {
                "tax_group": x.tax_group,
                "taxable_amount": _to_float(x.taxable_amount),
                "tax_amount": _to_float(x.tax_amount)
            }
            for x in tx.taxes
        ],
        "gift_cards": [
            {
                "card_number_masked": g.card_number_masked,
                "activity_type": g.activity_type,
                "amount": _to_float(g.amount),
                "auth_code": g.auth_code
            }
            for g in tx.gift_cards
        ]
    }
