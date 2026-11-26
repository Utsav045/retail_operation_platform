import pytest
from decimal import Decimal
from pathlib import Path
import time
from sqlalchemy import select

from app.core.database import async_session_factory, Base, engine
from app.services.master_loader import load_master_data
from app.services.pricing.manager import PricingService
from app.models.master import Item
from simulator.hub_simulator import HubSimulator


async def init_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as session:
        await load_master_data(session)
        await session.commit()


def test_rounding_rules():
    # ROUND_UP_9: nearest price ending in 9 cents
    assert PricingService.apply_rounding_rule(Decimal("4.12"), "ROUND_UP_9") == Decimal("4.19")
    assert PricingService.apply_rounding_rule(Decimal("4.19"), "ROUND_UP_9") == Decimal("4.19")
    assert PricingService.apply_rounding_rule(Decimal("4.91"), "ROUND_UP_9") == Decimal("4.99")
    assert PricingService.apply_rounding_rule(Decimal("10.00"), "ROUND_UP_9") == Decimal("10.09")

    # ROUND_99: nearest .99
    assert PricingService.apply_rounding_rule(Decimal("4.12"), "ROUND_99") == Decimal("4.99")
    assert PricingService.apply_rounding_rule(Decimal("4.99"), "ROUND_99") == Decimal("4.99")


@pytest.mark.asyncio
async def test_bulk_price_adjustment_preview():
    await init_test_db()
    async with async_session_factory() as session:
        service = PricingService(session)
        preview = await service.preview_bulk_adjustment(pct_change=5.0, dept="20", rounding_rule="ROUND_UP_9")
        assert len(preview) > 0
        for itm in preview:
            assert itm["dept"] == "20"
            assert itm["new_price"] >= itm["old_price"]
            assert str(itm["new_price"]).endswith("9") or str(itm["new_price"]).endswith(".99")


@pytest.mark.asyncio
async def test_change_file_generation_and_simulator_ack(tmp_path):
    await init_test_db()
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)

    async with async_session_factory() as session:
        service = PricingService(session, inbox_dir=inbox, outbox_dir=outbox)

        # 1. Generate XML change file
        items_to_update = [
            {"code": "049000000443", "variant": None, "price": "2.49", "description": "Cola 20oz", "dept": "20", "tax_group": "T1", "age_restricted": 0},
            {"code": "028400000116", "variant": None, "price": "1.99", "description": "Chips Sea Salt", "dept": "20", "tax_group": "T1", "age_restricted": 0}
        ]
        cf_res = service.generate_change_file(store_id="BL01", items=items_to_update, change_id="TEST_CHG_001")
        assert cf_res["file_name"] == "TEST_CHG_001.xml"
        assert Path(cf_res["file_path"]).exists()

        # 2. Simulator picks up change file from inbox and validates rules
        sim = HubSimulator(source_outbox_dir=outbox, live_outbox_dir=outbox, live_inbox_dir=inbox, store_id="BL01")
        ack_file = sim.process_inbox_change_file(Path(cf_res["file_path"]))

        assert ack_file is not None
        assert ack_file.exists()
        assert ack_file.name.startswith("ACK_BL01_TEST_CHG_001")

        # 3. PricingService inspects sync status
        sync_records = service.inspect_sync_status()
        assert len(sync_records) > 0
        ack_record = [r for r in sync_records if r["change_id"] == "TEST_CHG_001"][0]
        assert ack_record["status"] == "APPLIED"
        assert len(ack_record["items"]) == 2


@pytest.mark.asyncio
async def test_change_file_rejection_rules(tmp_path):
    await init_test_db()
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)

    async with async_session_factory() as session:
        service = PricingService(session, inbox_dir=inbox, outbox_dir=outbox)

        # Generate invalid change file violating rule E410 (Account maintenance inside change file)
        from lxml import etree
        root = etree.Element("ChangeFile", changeId="CHG_BAD_E410", storeId="BL01")
        etree.SubElement(root, "Account", id="ACC-999", name="Hacked Account")
        xml_bytes = etree.tostring(root, xml_declaration=True, encoding="UTF-8")

        bad_file = inbox / "CHG_BAD_E410.xml"
        with open(bad_file, "wb") as f:
            f.write(xml_bytes)

        sim = HubSimulator(source_outbox_dir=outbox, live_outbox_dir=outbox, live_inbox_dir=inbox, store_id="BL01")
        rej_file = sim.process_inbox_change_file(bad_file)

        assert rej_file is not None
        assert rej_file.name.startswith("REJ_BL01_CHG_BAD_E410")

        sync_records = service.inspect_sync_status()
        rej_record = [r for r in sync_records if r["change_id"] == "CHG_BAD_E410"][0]
        assert rej_record["status"] == "REJECTED"
        assert rej_record["error_code"] == "E410"


@pytest.mark.asyncio
async def test_commercial_account_billing_statement():
    await init_test_db()
    async with async_session_factory() as session:
        service = PricingService(session)
        statement = await service.generate_commercial_statement(account_id="BA-0001", month="2026-10")
        assert statement["account_id"] == "BA-0001"
        assert "business_name" in statement
        assert "credit_limit" in statement
        assert "payment_due_date" in statement
        assert isinstance(statement["total_charges"], float)
