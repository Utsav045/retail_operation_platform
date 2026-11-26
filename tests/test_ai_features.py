import pytest
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.core.database import async_session_factory, Base, engine
from app.services.master_loader import load_master_data
from app.services.ai.invoice_capture import InvoiceCaptureService
from app.services.ai.loss_prevention import LossPreventionService


async def init_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as session:
        await load_master_data(session)
        await session.commit()


@pytest.mark.asyncio
async def test_invoice_deterministic_math_and_discrepancies():
    await init_test_db()
    async with async_session_factory() as session:
        service = InvoiceCaptureService(session)

        # 1. Clean PDF invoice: Cascade Beverage CBC-55190
        p_cascade = service.invoices_dir / "CascadeBeverage_CBC-55190.pdf"
        cascade_data = await service.parse_and_verify_invoice(p_cascade)
        assert cascade_data["invoice_no"] == "CBC-55190"
        assert cascade_data["verification_status"] == "VERIFIED_MATCH"
        assert cascade_data["stated_subtotal"] == 326.00
        assert cascade_data["computed_subtotal"] == 326.00
        assert len(cascade_data["items"]) == 7

        # 2. Image invoice with handwritten discrepancy: Greenline Supply GHS-30418
        p_greenline = service.invoices_dir / "GreenlineSupply_GHS-30418.jpg"
        greenline_data = await service.parse_and_verify_invoice(p_greenline)
        assert greenline_data["invoice_no"] == "GHS-30418"
        assert greenline_data["verification_status"] == "DISCREPANCY_FLAGGED"
        assert greenline_data["discrepancy_note"] is not None
        assert "3 of 4 ordered cases received" in greenline_data["discrepancy_note"]
        # Line 6 should show handwritten adjustment
        line_batt = [l for l in greenline_data["items"] if "Batteries" in l["description"]][0]
        assert line_batt["handwritten_adjustment"] is not None
        assert line_batt["effective_amount"] == 75.60


@pytest.mark.asyncio
async def test_all_six_invoices_evaluation_runner():
    """
    Evaluates that all 6 take-home supplier invoices run through the deterministic
    verification runner with 100% precision.
    """
    await init_test_db()
    async with async_session_factory() as session:
        service = InvoiceCaptureService(session)
        summary = await service.run_evaluation_suite()
        assert summary["total_invoices"] == 6
        assert summary["invoices_evaluated"] == 6
        assert summary["math_evaluation_pass_rate"] == "100.0%"
        assert summary["total_line_items"] == 44


@pytest.mark.asyncio
async def test_margin_calculation_and_price_recommendation():
    await init_test_db()
    async with async_session_factory() as session:
        service = InvoiceCaptureService(session)
        p_harbor = service.invoices_dir / "HarborCoffee_HCR-24117.pdf"
        data = await service.parse_and_verify_invoice(p_harbor)

        for itm in data["items"]:
            # Retail price suggested at 35% margin: suggested >= unit_cost / (1 - 0.35)
            assert itm["suggested_retail_35pct"] > itm["unit_cost"]
            # Rounding rule: ends in 9 cents
            assert str(itm["suggested_retail_35pct"]).endswith("9")


@pytest.mark.asyncio
async def test_loss_prevention_heuristics_and_query_assistant():
    await init_test_db()
    async with async_session_factory() as session:
        lp_service = LossPreventionService(session)

        # Daily LP audit run
        audit = await lp_service.generate_daily_audit(business_date=date(2026, 10, 4))
        assert "total_incidents" in audit
        assert "incidents" in audit

        # Ask Your Stores AI assistant queries
        # 1. Department query
        ans1 = await lp_service.answer_store_query("Which department had highest sales?", date_str="2026-10-04")
        assert "top-performing department" in ans1["answer"]
        assert ans1["confidence"] > 0.9

        # 2. Reconciliation query
        ans2 = await lp_service.answer_store_query("Show reconciliation discrepancies", date_str="2026-10-04")
        assert "reconcil" in ans2["answer"].lower()
        assert ans2["confidence"] > 0.9

        # 3. Overall sales query
        ans3 = await lp_service.answer_store_query("What were overall store sales?", date_str="2026-10-04")
        assert ("sales" in ans3["answer"].lower() or "transaction" in ans3["answer"].lower())
        assert ans3["confidence"] > 0.9
