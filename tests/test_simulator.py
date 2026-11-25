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
