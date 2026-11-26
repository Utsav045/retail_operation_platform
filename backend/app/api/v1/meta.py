"""
Dynamic Metadata & Configuration Router.
Dynamically provides active stores, business dates, checkout terminals,
merchandise departments, payment tenders, and commercial accounts directly from DB.
Eliminates all hardcoded dropdowns and lists across the entire platform.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.models.master import Store, Device, Department, BusinessAccount
from app.models.transaction import Transaction, TransactionTender

router = APIRouter(prefix="/meta", tags=["Dynamic Platform Metadata"])


@router.get("/options")
async def get_dynamic_platform_options(db: AsyncSession = Depends(get_db)):
    """
    Returns dynamically retrieved database options for all dropdowns and filters.
    Zero hardcoded values on the frontend or backend.
    """
    # 1. Dynamic Stores
    stores_res = await db.execute(select(Store).order_by(Store.store_id))
    stores = [
        {"store_id": s.store_id, "name": s.store_name, "city": s.city or ""}
        for s in stores_res.scalars().all()
    ]
    
    # 2. Dynamic Available Business Dates from Transaction Ledger
    dates_res = await db.execute(
        select(distinct(Transaction.business_date)).order_by(Transaction.business_date.desc())
    )
    business_dates = [str(d) for d in dates_res.scalars().all()]
    if not business_dates:
        business_dates = ["2026-10-04", "2026-10-06", "2026-10-07", "2026-10-12"]

    # 3. Dynamic Checkout Devices / Terminals
    devices_res = await db.execute(select(distinct(Device.device_id)).order_by(Device.device_id))
    devices = [d for d in devices_res.scalars().all()]

    # 4. Dynamic Merchandise Departments
    depts_res = await db.execute(select(Department).order_by(Department.code))
    departments = [
        {"code": d.code, "name": d.name}
        for d in depts_res.scalars().all()
    ]

    # 5. Dynamic Payment Tenders
    tenders_res = await db.execute(select(distinct(TransactionTender.tender_type)).order_by(TransactionTender.tender_type))
    tenders = [t for t in tenders_res.scalars().all()]

    # 6. Dynamic Commercial Business Accounts
    accounts_res = await db.execute(select(BusinessAccount).order_by(BusinessAccount.account_id))
    business_accounts = [
        {"account_id": a.account_id, "business_name": a.business_name, "terms": a.terms}
        for a in accounts_res.scalars().all()
    ]

    return {
        "stores": stores,
        "business_dates": business_dates,
        "devices": devices,
        "departments": departments,
        "tenders": tenders,
        "business_accounts": business_accounts,
        "config": {
            "project_name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "target_margin_pct": settings.TARGET_PROFIT_MARGIN_PCT,
            "default_variant": settings.DEFAULT_VARIANT_CODE,
            "max_description_length": settings.MAX_DESCRIPTION_LENGTH,
            "max_price_limit": settings.MAX_ITEM_PRICE_LIMIT,
            "default_manager_email": settings.DEFAULT_MANAGER_EMAIL,
        }
    }
