from pathlib import Path
from decimal import Decimal
import tempfile
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


def test_xml_v2_cash_drop_and_void():
    """Verify parsing non-sale events like CASH_DROP and VOID flags."""
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<TransactionLog storeId="BL01" businessDate="2026-10-01" batchSeq="5">
    <Transaction seq="100099" type="CASH_DROP" device="R1" staff="201" start="2026-10-01 14:00:00">
        <CashDrop amount="150.00" envelope="ENV-001" status="OK"/>
    </Transaction>
    <Transaction seq="100100" type="SALE" status="CANCELLED" device="R2" staff="202" start="2026-10-01 14:05:00">
        <ItemLine line="1" itemCode="200000001018" desc="Coffee" qty="1" unitPrice="2.50" amount="2.50" taxGroup="T1" status="VOID"/>
        <Total net="2.50" tax="0.20" total="2.70"/>
        <Tender type="CASH" amount="2.70"/>
    </Transaction>
</TransactionLog>"""
    with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as f:
        f.write(sample_xml)
        temp_path = Path(f.name)
    
    try:
        parser = XMLv2Parser()
        batch = parser.parse(temp_path)
        assert len(batch.transactions) == 2
        
        # Check cash drop
        tx_drop = batch.transactions[0]
        assert tx_drop.type == "CASH_DROP"
        assert len(tx_drop.cash_drops) == 1
        assert tx_drop.cash_drops[0].amount == Decimal("150.00")
        assert tx_drop.cash_drops[0].envelope == "ENV-001"
        
        # Check voided sale
        tx_void = batch.transactions[1]
        assert tx_void.status == "CANCELLED"
        assert tx_void.lines[0].is_void is True
        assert tx_void.grand_total == Decimal("2.70")
    finally:
        temp_path.unlink()


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


def test_json_v3_minor_unit_conversion():
    """Verify conversion of minor unit integers (cents) to exact Decimal dollar amounts."""
    sample_json = """{
        "schema": "tlog/3.0",
        "store": "BL02",
        "businessDay": "2026-10-15",
        "batch": {
            "seq": 105
        },
        "transactions": [
            {
                "sequenceNo": 200500,
                "kind": "sale",
                "state": "completed",
                "terminal": "SCO1",
                "operator": "305",
                "startedAt": "2026-10-15T10:30:00Z",
                "lines": [
                    {
                        "lineNo": 1,
                        "lineType": "item",
                        "sku": "100000000005",
                        "text": "Organic Milk",
                        "quantity": "1",
                        "unitPriceMinor": 1250,
                        "extendedMinor": 1250,
                        "taxCode": "T1"
                    }
                ],
                "taxes": [
                    {
                        "code": "T1",
                        "taxableMinor": 1250,
                        "taxMinor": 103
                    }
                ],
                "payments": [
                    {
                        "method": "CREDIT_CARD",
                        "amountMinor": 1353
                    }
                ],
                "totals": {
                    "netMinor": 1250,
                    "taxMinor": 103,
                    "giftCardLoadsMinor": 0,
                    "grandMinor": 1353
                }
            }
        ]
    }"""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(sample_json)
        temp_path = Path(f.name)
    
    try:
        parser = JSONv3Parser()
        batch = parser.parse(temp_path)
        tx = batch.transactions[0]
        assert tx.net_total == Decimal("12.50")
        assert tx.tax_total == Decimal("1.03")
        assert tx.grand_total == Decimal("13.53")
        assert tx.lines[0].unit_price == Decimal("12.50")
        assert tx.lines[0].amount == Decimal("12.50")
        assert tx.tenders[0].amount == Decimal("13.53")
    finally:
        temp_path.unlink()

