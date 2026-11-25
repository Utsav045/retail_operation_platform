from pathlib import Path
from decimal import Decimal
from app.services.parsers.xml_v2 import XMLv2Parser
from app.services.parsers.json_v3 import JSONv3Parser
from app.core.config import settings


def test_xml_v2_parser():
    xml_path = settings.RAW_DATA_DIR / "outbox" / "TLOG_BL01_000001.xml"
    assert xml_path.exists(), f"Missing test file: {xml_path}"
    
    parser = XMLv2Parser()
    batch = parser.parse(xml_path)
    
    assert batch.store_id == "BL01"
    assert str(batch.business_date) == "2026-10-01"
    assert batch.batch_seq == 1
    assert len(batch.transactions) == 40
    
    first_tx = batch.transactions[0]
    assert first_tx.seq == 100001
    assert first_tx.type == "SALE"
    assert first_tx.device == "R1"
    assert first_tx.staff == 201
    assert len(first_tx.lines) == 1
    assert first_tx.lines[0].item_code == "200000001513"
    assert first_tx.lines[0].amount == Decimal("3.75")
    assert first_tx.net_total == Decimal("3.75")
    assert first_tx.tax_total == Decimal("0.36")
    assert first_tx.grand_total == Decimal("4.11")
    assert len(first_tx.tenders) == 1
    assert first_tx.tenders[0].tender_type == "CASH"
    assert first_tx.tenders[0].amount == Decimal("4.11")


def test_json_v3_parser():
    json_path = settings.RAW_DATA_DIR / "outbox" / "TLOG_BL01_000071.json"
    assert json_path.exists(), f"Missing test file: {json_path}"
    
    parser = JSONv3Parser()
    batch = parser.parse(json_path)
    
    assert batch.store_id == "BL01"
    assert str(batch.business_date) == "2026-10-11"
    assert batch.batch_seq == 71
    assert len(batch.transactions) == 45
    
    first_tx = batch.transactions[0]
    assert first_tx.seq == 102209
    assert first_tx.type == "SALE"
    assert first_tx.device == "R1"
    assert first_tx.staff == 201
    assert len(first_tx.lines) == 2
    assert first_tx.lines[0].item_code == "200000001513"
    assert first_tx.lines[0].amount == Decimal("3.75")
    assert first_tx.net_total == Decimal("6.00")
    assert first_tx.tax_total == Decimal("0.57")
    assert first_tx.grand_total == Decimal("6.57")
    assert len(first_tx.tenders) == 1
    assert first_tx.tenders[0].tender_type == "MOBILE"
    assert first_tx.tenders[0].amount == Decimal("6.57")
