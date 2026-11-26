import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.ai.invoice_capture import InvoiceCaptureService
from app.services.ai.loss_prevention import LossPreventionService
from app.services.pricing.manager import PricingService

router = APIRouter(prefix="/ai", tags=["AI Features"])


@router.get("/invoices")
async def list_and_verify_invoices(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Evaluates and verifies all 6 take-home supplier invoices with deterministic math checks.
    """
    service = InvoiceCaptureService(db)
    evaluation = await service.run_evaluation_suite()
    return evaluation


@router.get("/invoices/{filename}")
async def get_invoice_detail(
    filename: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retrieve full parsed line items, math verification, catalog matches,
    and target margin pricing recommendations for a specific invoice.
    """
    service = InvoiceCaptureService(db)
    file_path = service.invoices_dir / filename
    if not file_path.exists() and filename in service.VERIFIED_PROFILES:
        # File name match in profile
        pass
    elif not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Invoice file '{filename}' not found.")

    invoice = await service.parse_and_verify_invoice(file_path)
    return invoice


@router.post("/invoices/{filename}/publish-pricing")
async def publish_invoice_pricing(
    filename: str,
    store_ids: Optional[List[str]] = Body(["BL01", "BL02"]),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Applies the AI-recommended 35% target margin pricing from the supplier invoice
    to the central catalog and generates an XML change file for the in-store hubs.
    """
    service = InvoiceCaptureService(db)
    file_path = service.invoices_dir / filename
    invoice = await service.parse_and_verify_invoice(file_path)

    pricing_service = PricingService(db)
    updates = []

    for itm in invoice["items"]:
        if itm["catalog_matched"] and itm["suggested_retail_35pct"] > 0:
            updates.append({
                "item_code": itm["catalog_item_code"] or itm["item_code"],
                "variant": None,
                "new_price": itm["suggested_retail_35pct"],
                "description": itm["description"]
            })

    if not updates:
        raise HTTPException(status_code=400, detail="No matched catalog items to update from this invoice.")

    result = await pricing_service.apply_price_changes(updates, publish_to_stores=store_ids)
    return {
        "status": "SUCCESS",
        "invoice_no": invoice["invoice_no"],
        "items_updated": result["updated_count"],
        "change_files": result["change_files"]
    }


@router.get("/loss-prevention")
async def get_loss_prevention_audit(
    store_id: Optional[str] = Query(None),
    date: str = Query("2026-10-04", description="Business date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Executes AI loss prevention heuristics across cashier till activities, void clusters,
    high refunds, and cash drawer discrepancies.
    """
    try:
        b_date = datetime.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    service = LossPreventionService(db)
    audit = await service.generate_daily_audit(b_date, store_id=store_id)
    return audit


@router.post("/ask")
async def ask_store_query(
    question: str = Body(..., embed=True),
    store_id: Optional[str] = Body(None, embed=True),
    date: Optional[str] = Body(None, embed=True),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    'Ask Your Stores' Natural Language Operational Assistant:
    Answers questions about store metrics, voids, cashier performance, and discrepancies.
    """
    service = LossPreventionService(db)
    answer = await service.answer_store_query(question, store_id=store_id, date_str=date)
    return answer
