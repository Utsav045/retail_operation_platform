import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.core.database import get_db
from app.models.summary import ReconciliationReport, EndOfDaySummary, ShiftSummary
from app.services.reconciliation.engine import ReconciliationService

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


def _to_float(val: Any) -> float:
    if val is None:
        return 0.0
    return float(val)


@router.get("/daily")
async def get_daily_reconciliation(
    store_id: str = Query(..., description="Store identifier (e.g. BL01, BL02)"),
    date: str = Query(..., description="Business date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the end-of-day reconciliation report for a store and date.
    If no report has been generated yet, runs reconciliation dynamically.
    """
    try:
        b_date = datetime.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Check for existing persisted report
    query = select(ReconciliationReport).where(
        and_(
            ReconciliationReport.store_id == store_id,
            ReconciliationReport.business_date == b_date,
            ReconciliationReport.report_type == "EOD"
        )
    ).order_by(desc(ReconciliationReport.created_at))
    res = await db.execute(query)
    report = res.scalars().first()

    if not report:
        # Run reconciliation on the fly
        service = ReconciliationService(db)
        try:
            report_result = await service.reconcile_eod(store_id, b_date)
            await db.commit()
            if isinstance(report_result, dict):
                return report_result
            report = report_result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Reconciliation error: {str(e)}")

    if isinstance(report, dict):
        return report

    return {
        "id": report.id,
        "store_id": report.store_id,
        "business_date": str(report.business_date),
        "report_type": report.report_type,
        "target_id": report.target_id,
        "status": report.status,
        "net_sales_diff": _to_float(report.net_sales_diff),
        "tax_diff": _to_float(report.tax_diff),
        "grand_total_diff": _to_float(report.grand_total_diff),
        "cash_diff": _to_float(report.cash_diff),
        "comparison_details": report.comparison_details,
        "root_cause_analysis": report.root_cause_analysis,
        "created_at": report.created_at.isoformat() if report.created_at else None
    }


@router.get("/shifts")
async def get_shift_reconciliations(
    store_id: str = Query(..., description="Store identifier (e.g. BL01, BL02)"),
    date: str = Query(..., description="Business date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get all shift close reconciliation reports for a store and date.
    """
    try:
        b_date = datetime.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Find shift summaries for this store and date
    s_query = select(ShiftSummary).where(
        and_(
            ShiftSummary.store_id == store_id,
            ShiftSummary.business_date == b_date
        )
    ).order_by(ShiftSummary.shift_no, ShiftSummary.device_id)
    s_res = await db.execute(s_query)
    shifts = s_res.scalars().all()

    reports = []
    service = ReconciliationService(db)

    for shift in shifts:
        # Look for report
        r_query = select(ReconciliationReport).where(
            and_(
                ReconciliationReport.store_id == store_id,
                ReconciliationReport.business_date == b_date,
                ReconciliationReport.report_type == "SHIFT",
                ReconciliationReport.target_id == shift.shift_id
            )
        )
        r_res = await db.execute(r_query)
        r = r_res.scalars().first()

        if not r:
            try:
                r = await service.reconcile_shift(shift.shift_id)
                await db.commit()
            except Exception:
                continue

        if r:
            reports.append({
                "id": r.id,
                "shift_id": shift.shift_id,
                "shift_no": shift.shift_no,
                "device_id": shift.device_id,
                "staff_id": shift.staff_id,
                "opening_float": _to_float(shift.opening_float),
                "closing_cash": _to_float(shift.closing_cash_actual),
                "status": r.status,
                "cash_diff": _to_float(r.cash_diff),
                "details": r.comparison_details,
                "root_cause_analysis": r.root_cause_analysis
            })

    return reports
