import pytest
from pathlib import Path
from simulator.hub_simulator import HubSimulator
from app.core.config import settings


def test_hub_simulator_emit_and_inbox(tmp_path):
    source_outbox = settings.RAW_DATA_DIR / "outbox"
    live_outbox = tmp_path / "runtime_outbox"
    live_inbox = tmp_path / "runtime_inbox"
    
    sim = HubSimulator(
        source_outbox_dir=source_outbox,
        live_outbox_dir=live_outbox,
        live_inbox_dir=live_inbox,
        store_id="BL01",
    )
    
    # 1. Test chronological file discovery
    files = sim.get_source_files_chronological()
    assert len(files) > 50
    
    # 2. Test emitting a single file
    emitted = sim.emit_file(files[0])
    assert emitted.exists()
    assert (live_outbox / files[0].name).exists()
    
    # 3. Test emitting a damaged file
    corrupt = sim.emit_corrupted_file("TLOG_corrupt_test.xml")
    assert corrupt.exists()
    assert "BAD DATA" in corrupt.read_text(encoding="utf-8")
    
    # 4. Test inbox change file processing with valid item and invalid item
    change_file = live_inbox / "CHG-20261025-0001.xml"
    change_content = """<?xml version="1.0" encoding="UTF-8"?>
<ChangeFile changeId="CHG-20261025-0001" storeId="BL01" created="2026-10-25 06:00:00">
  <Items>
    <Item action="update" code="200000001018" variant="000" price="2.99"/>
    <Item action="update" code="200000001025" variant="" price="4.99"/>
  </Items>
</ChangeFile>
"""
    change_file.write_text(change_content, encoding="utf-8")
    
    ack_path = sim.process_inbox_change_file(change_file)
    assert ack_path is not None
    assert ack_path.exists()
    assert "ACK_BL01_CHG-20261025-0001.xml" in ack_path.name
    
    ack_text = ack_path.read_text(encoding="utf-8")
    assert 'result="PARTIAL"' in ack_text
    assert 'errorCode="E312"' in ack_text  # Variant required
    assert 'action="update" result="APPLIED"' in ack_text
    
    # Verify change file moved to processed/
    assert not change_file.exists()
    assert (live_inbox / "processed" / change_file.name).exists()
    
    # 5. Test whole-file rejection on account maintenance
    account_chg = live_inbox / "CHG-20261025-0002.xml"
    account_content = """<?xml version="1.0" encoding="UTF-8"?>
<ChangeFile changeId="CHG-20261025-0002" storeId="BL01" created="2026-10-25 06:00:00">
  <Accounts>
    <Account id="BA-9999" name="Test"/>
  </Accounts>
</ChangeFile>
"""
    account_chg.write_text(account_content, encoding="utf-8")
    rej_path = sim.process_inbox_change_file(account_chg)
    assert rej_path is not None
    assert rej_path.exists()
    assert "REJ_BL01_CHG-20261025-0002.xml" in rej_path.name
    assert 'errorCode="E410"' in rej_path.read_text(encoding="utf-8")


def test_hub_simulator_validation_error_codes(tmp_path):
    """Test specific in-store hub business rule error codes: E301, E315, E318, E320, E321."""
    sim = HubSimulator(
        source_outbox_dir=tmp_path / "src_outbox",
        live_outbox_dir=tmp_path / "live_outbox",
        live_inbox_dir=tmp_path / "live_inbox",
        store_id="BL01",
    )
    sim.known_depts = {"1", "2", "3"}
    sim.known_tax_groups = {"T1", "T2"}

    # 1. E301 StoreId mismatch
    mismatch_file = sim.live_inbox_dir / "CHG-E301.xml"
    mismatch_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<ChangeFile changeId="CHG-E301" storeId="BL02" created="2026-10-25 06:00:00">
  <Items><Item action="update" code="1001" variant="000" price="5.00"/></Items>
</ChangeFile>""", encoding="utf-8")
    rej_e301 = sim.process_inbox_change_file(mismatch_file)
    assert 'errorCode="E301"' in rej_e301.read_text(encoding="utf-8")

    # 2. E315 Description > 24 chars, E318 Price out of range, E320 Unknown dept, E321 Unknown taxGroup
    rule_file = sim.live_inbox_dir / "CHG-RULES.xml"
    rule_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<ChangeFile changeId="CHG-RULES" storeId="BL01" created="2026-10-25 06:00:00">
  <Items>
    <Item action="update" code="1002" variant="000" description="This description is way too long for hub POS display" price="5.00"/>
    <Item action="update" code="1003" variant="000" price="-10.00"/>
    <Item action="update" code="1004" variant="000" price="5.00" dept="999"/>
    <Item action="update" code="1005" variant="000" price="5.00" taxGroup="T99"/>
  </Items>
</ChangeFile>""", encoding="utf-8")
    ack_rules = sim.process_inbox_change_file(rule_file)
    ack_text = ack_rules.read_text(encoding="utf-8")
    assert 'result="REJECTED"' in ack_text
    assert 'errorCode="E315"' in ack_text
    assert 'errorCode="E318"' in ack_text
    assert 'errorCode="E320"' in ack_text
    assert 'errorCode="E321"' in ack_text

