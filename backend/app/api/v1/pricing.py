from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.master import Item, Store, BusinessAccount
from app.services.pricing.manager import PricingService

router = APIRouter(prefix="/pricing", tags=["Price List & Hub Sync"])


@router.get("/items")
async def list_items(
    dept: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    List items from central catalog with code, variant, description, department, price, tax group, and age restriction.
    """
    query = select(Item)
    if dept:
        query = query.where(Item.dept == dept.upper())
    if search:
        query = query.where(Item.description.ilike(f"%{search}%"))

    res = await db.execute(query.offset(offset).limit(limit))
    items = res.scalars().all()

    return {
        "total": len(items),
        "items": [
            {
                "id": itm.id,
                "code": itm.code,
                "variant": itm.variant,
                "description": itm.description,
                "dept": itm.dept,
                "price": float(itm.price),
                "tax_group": itm.tax_group,
                "min_age": itm.min_age
            }
            for itm in items
        ]
    }


@router.post("/preview-bulk")
async def preview_bulk_pricing(
    pct_change: float = Body(..., embed=True),
    dept: Optional[str] = Body(None, embed=True),
    rounding_rule: str = Body("ROUND_UP_9", embed=True),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Preview bulk price updates (e.g. +5% rounded to end in 9 cents) before committing.
    """
    service = PricingService(db)
    preview = await service.preview_bulk_adjustment(
        pct_change=pct_change,
        dept=dept,
        rounding_rule=rounding_rule
    )
    return {
        "pct_change": pct_change,
        "dept": dept or "ALL",
        "rounding_rule": rounding_rule,
        "items_affected": len(preview),
        "preview": preview
    }


@router.post("/apply-and-publish")
async def apply_and_publish_pricing(
    updates: List[Dict[str, Any]] = Body(...),
    publish_to_stores: Optional[List[str]] = Body(["BL01", "BL02"]),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Commit price updates to the database and generate XML change files for in-store hubs.
    """
    service = PricingService(db)
    result = await service.apply_price_changes(updates, publish_to_stores=publish_to_stores)
    return result


@router.get("/sync-status")
async def get_sync_status(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Inspects ACK and REJ responses from in-store hubs in runtime_data/outbox.
    """
    service = PricingService(db)
    records = service.inspect_sync_status()
    return {
        "total": len(records),
        "results": records
    }


@router.get("/commercial-statement")
async def get_commercial_statement(
    account_id: str = Query(..., description="Business account ID e.g. BA-0001"),
    month: str = Query("2026-10", description="Billing month YYYY-MM"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate commercial business account monthly billing statement.
    """
    service = PricingService(db)
    try:
        stmt = await service.generate_commercial_statement(account_id, month)
        return stmt
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
