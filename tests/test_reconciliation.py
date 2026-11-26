from datetime import date
from decimal import Decimal
from pathlib import Path
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory, Base, engine
from app.services.master_loader import load_master_data
from app.services.connector.loader import IngestionService
from app.services.parsers.summary_parser import SummaryParser
from app.services.reconciliation.engine import ReconciliationService
from app.models.summary import ShiftSummary, EndOfDaySummary, ReconciliationReport


@pytest.fixture(scope="module")
def outbox_dir():
    return settings.RAW_DATA_DIR / "outbox"


def test_summary_parser_xml_and_json(outbox_dir):
    parser = SummaryParser()
    
    # 1. XML ShiftClose
    shift_xml = parser.parse_summary_file(outbox_dir / "SHIFT_BL01_20261001_1.xml")
    assert shift_xml.store_id == "BL01"
    assert shift_xml.business_date == date(2026, 10, 1)
    assert shift_xml.shift_no == 1
    assert shift_xml.opening_float == Decimal("300.00")
    assert shift_xml.counted_cash == Decimal("383.68")
    assert len(shift_xml.tenders) == 5
    
    # 2. JSON ShiftClose
    shift_json = parser.parse_summary_file(outbox_dir / "SHIFT_BL01_20261011_1.json")
    assert shift_json.store_id == "BL01"
    assert shift_json.business_date == date(2026, 10, 11)
    assert shift_json.opening_float == Decimal("300.00")
    assert shift_json.counted_cash == Decimal("407.34")
    
    # 3. XML EndOfDay
    eod_xml = parser.parse_summary_file(outbox_dir / "EOD_BL01_20261001.xml")
    assert eod_xml.store_id == "BL01"
    assert eod_xml.reported_transactions == 214
    assert eod_xml.reported_net_sales == Decimal("2495.14")
    assert eod_xml.reported_tax == Decimal("165.83")
    assert eod_xml.reported_gift_card_loads == Decimal("50.00")
    assert eod_xml.reported_grand_total == Decimal("2710.97")
    assert len(eod_xml.departments) == 14
    
    # 4. JSON EndOfDay
    eod_json = parser.parse_summary_file(outbox_dir / "EOD_BL01_20261011.json")
    assert eod_json.store_id == "BL01"
    assert eod_json.reported_net_sales == Decimal("2724.61")
    assert eod_json.reported_grand_total == Decimal("3029.75")
    assert len(eod_json.departments) == 14


@pytest.mark.asyncio
async def test_eod_reconciliation_matched_day(outbox_dir):
    """Verify that on a clean day (BL01 2026-10-01), all computed totals match reported EOD with status MATCHED."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        await load_master_data(session)
        loader = IngestionService(session)
        
        # Load batches 1 to 7 for BL01 on 2026-10-01
        for b in range(1, 8):
            f = outbox_dir / f"TLOG_BL01_{b:06d}.xml"
            if f.exists():
                await loader.process_file(f)
                
        # Load EOD summary
        await loader.process_file(outbox_dir / "EOD_BL01_20261001.xml")
        
        # Reconcile
        rec_service = ReconciliationService(session)
        result = await rec_service.reconcile_eod("BL01", date(2026, 10, 1))
        
        assert result["status"] == "MATCHED"
        assert result["is_consistent"] is True
        assert result["computed"]["net_sales"] == "2495.14"
        assert result["computed"]["tax"] == "165.83"
        assert result["computed"]["gift_card_loads"] == "50.00"
        assert result["computed"]["grand_total"] == "2710.97"
        assert result["differences"]["grand_total"] == "0.00"


@pytest.mark.asyncio
async def test_shift_cash_reconciliation_exact_match(outbox_dir):
    """Verify expected cash calculation: opening_float + cash_taken - cash_refunds - completed_cash_drops."""
    async with async_session_factory() as session:
        loader = IngestionService(session)
        await loader.process_file(outbox_dir / "SHIFT_BL01_20261001_1.xml")
        
        rec_service = ReconciliationService(session)
        shift_res = await rec_service.reconcile_shift("BL01", date(2026, 10, 1), 1)
        
        assert shift_res["status"] == "MATCHED"
        assert shift_res["opening_float"] == "300.00"
        assert shift_res["counted_cash"] == "383.68"
        assert shift_res["expected_cash"] == "383.68"
        assert shift_res["variance"] == "0.00"


@pytest.mark.asyncio
async def test_eod_reconciliation_gift_card_misclassification(outbox_dir):
    """
    Verify intentional dataset flaw detection on BL02 2026-10-03:
    The hub mistakenly included $25.00 gift card load into department net sales.
    Reconciliation flags MISMATCH and pinpoints the root cause.
    """
    async with async_session_factory() as session:
        loader = IngestionService(session)
        # Load BL02 batches for 2026-10-03 (batches 15 to 21)
        for b in range(15, 22):
            f = outbox_dir / f"TLOG_BL02_{b:06d}.xml"
            if f.exists():
                await loader.process_file(f)
                
        await loader.process_file(outbox_dir / "EOD_BL02_20261003.xml")
        
        rec_service = ReconciliationService(session)
        result = await rec_service.reconcile_eod("BL02", date(2026, 10, 3))
        
        assert result["status"] == "MISMATCH"
        assert result["differences"]["net_sales"] == "-25.00"
        assert result["differences"]["grand_total"] == "0.00"  # Grand total still matches
        assert "gift card load ($25.00)" in result["discrepancy_details"]


@pytest.mark.asyncio
async def test_eod_reconciliation_hub_self_inconsistency(outbox_dir):
    """
    Verify intentional dataset flaw detection on BL01 2026-10-04:
    Hub's reported parts ($3099.59) do not equal its stated grandTotal ($3109.59).
    Reconciliation detects inconsistency and reports delta of $10.00.
    """
    async with async_session_factory() as session:
        loader = IngestionService(session)
        # Load BL01 batches for 2026-10-04 (batches 22 to 28)
        for b in range(22, 29):
            f = outbox_dir / f"TLOG_BL01_{b:06d}.xml"
            if f.exists():
                await loader.process_file(f)
                
        await loader.process_file(outbox_dir / "EOD_BL01_20261004.xml")
        
        rec_service = ReconciliationService(session)
        result = await rec_service.reconcile_eod("BL01", date(2026, 10, 4))
        
        assert result["is_consistent"] is False
        assert result["status"] == "MISMATCH"
        assert result["differences"]["grand_total"] == "-10.00"
        assert "does not equal stated grandTotal" in result["discrepancy_details"]


@pytest.mark.asyncio
async def test_eod_reconciliation_void_line_leakage(outbox_dir):
    """
    Verify intentional dataset flaw detection on BL01 2026-10-06:
    Hub mistakenly included voided line Honey 12oz ($6.49) into reported net sales.
    Reconciliation detects exact $6.49 delta and isolates the voided line.
    """
    async with async_session_factory() as session:
        loader = IngestionService(session)
        # Load BL01 batches for 2026-10-06 (batches 36 to 42)
        for b in range(36, 43):
            f = outbox_dir / f"TLOG_BL01_{b:06d}.xml"
            if f.exists():
                await loader.process_file(f)
                
        await loader.process_file(outbox_dir / "EOD_BL01_20261006.xml")
        
        rec_service = ReconciliationService(session)
        result = await rec_service.reconcile_eod("BL01", date(2026, 10, 6))
        
        assert result["status"] == "MISMATCH"
        assert result["differences"]["net_sales"] == "-6.49"
        assert "Honey 12oz" in result["discrepancy_details"]
        assert "$6.49" in result["discrepancy_details"]
