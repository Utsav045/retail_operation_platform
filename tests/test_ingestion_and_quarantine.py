import pytest
from pathlib import Path
from sqlalchemy import select, func
from app.core.config import settings
from app.core.database import async_session_factory, Base, engine
from app.models.audit import FileImportLog, QuarantinedFile
from app.models.transaction import Transaction, TransactionLine
from app.services.connector.loader import IngestionService
from app.services.master_loader import load_master_data


@pytest.mark.asyncio
async def test_ingestion_idempotency_and_quarantine(tmp_path):
    # Reset and seed database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    async with async_session_factory() as session:
        await load_master_data(session)

    # 1. Ingest an XML file
    xml_source = settings.RAW_DATA_DIR / "outbox" / "TLOG_BL01_000001.xml"
    test_outbox = tmp_path / "outbox"
    test_outbox.mkdir()
    
    xml_copy = test_outbox / "TLOG_BL01_000001.xml"
    xml_copy.write_bytes(xml_source.read_bytes())
    
    async with async_session_factory() as session:
        service = IngestionService(session)
        res1 = await service.process_file(xml_copy)
        assert res1["status"] == "PROCESSED"
        assert res1["accepted"] == 40
        assert res1["skipped"] == 0

    # Verify rows in DB
    async with async_session_factory() as session:
        tx_count = (await session.execute(select(func.count(Transaction.id)))).scalar()
        assert tx_count == 40
        lines_count = (await session.execute(select(func.count(TransactionLine.id)))).scalar()
        assert lines_count > 40

    # 2. Re-ingest the exact same file -> IDEMPOTENCY TEST
    async with async_session_factory() as session:
        service = IngestionService(session)
        res2 = await service.process_file(xml_copy)
        assert res2["status"] == "ALREADY_PROCESSED"

    # Verify no duplicate transactions were added
    async with async_session_factory() as session:
        tx_count_after = (await session.execute(select(func.count(Transaction.id)))).scalar()
        assert tx_count_after == 40

    # 3. Test Quarantine of a Corrupted File
    corrupt_file = test_outbox / "TLOG_BL01_000999_corrupt.xml"
    corrupt_file.write_text("<TransactionLog storeId='BL01'><Transaction seq='999'>unclosed tag", encoding="utf-8")
    
    async with async_session_factory() as session:
        service = IngestionService(session)
        res_corrupt = await service.process_file(corrupt_file)
        assert res_corrupt["status"] == "QUARANTINED"
        assert "Parse failure" in res_corrupt["reason"]

    # Verify quarantine database record
    async with async_session_factory() as session:
        q_record = (
            await session.execute(select(QuarantinedFile).where(QuarantinedFile.file_name == corrupt_file.name))
        ).scalar_one_or_none()
        assert q_record is not None
        assert "Parse failure" in q_record.reason
        assert q_record.stack_trace is not None
        
        # Verify original file was NOT deleted
        assert corrupt_file.exists()
        assert xml_copy.exists()


@pytest.mark.asyncio
async def test_transaction_level_deduplication(tmp_path):
    """Verify that if two different files contain overlapping transactions, duplicates are skipped at transaction level."""
    test_outbox = tmp_path / "outbox2"
    test_outbox.mkdir()

    # Batch 1 with transaction 9901 and 9902
    xml_batch1 = """<?xml version="1.0" encoding="UTF-8"?>
<TransactionLog storeId="BL01" businessDate="2026-10-25" batchSeq="101">
    <Transaction seq="9901" type="SALE" device="R1" staff="201" timestamp="2026-10-25T09:00:00">
        <Line lineNo="1" item="200000001018" desc="Coffee" qty="1" unitPrice="3.00" amount="3.00"/>
        <Tender seq="1" type="CASH" amount="3.00"/>
    </Transaction>
    <Transaction seq="9902" type="SALE" device="R1" staff="201" timestamp="2026-10-25T09:05:00">
        <Line lineNo="1" item="200000001018" desc="Coffee" qty="1" unitPrice="3.00" amount="3.00"/>
        <Tender seq="1" type="CASH" amount="3.00"/>
    </Transaction>
</TransactionLog>"""
    f1 = test_outbox / "TLOG_BL01_000101.xml"
    f1.write_text(xml_batch1, encoding="utf-8")

    # Batch 2 with transaction 9902 (duplicate) and 9903 (new)
    xml_batch2 = """<?xml version="1.0" encoding="UTF-8"?>
<TransactionLog storeId="BL01" businessDate="2026-10-25" batchSeq="102">
    <Transaction seq="9902" type="SALE" device="R1" staff="201" timestamp="2026-10-25T09:05:00">
        <Line lineNo="1" item="200000001018" desc="Coffee" qty="1" unitPrice="3.00" amount="3.00"/>
        <Tender seq="1" type="CASH" amount="3.00"/>
    </Transaction>
    <Transaction seq="9903" type="SALE" device="R1" staff="201" timestamp="2026-10-25T09:10:00">
        <Line lineNo="1" item="200000001018" desc="Coffee" qty="1" unitPrice="3.00" amount="3.00"/>
        <Tender seq="1" type="CASH" amount="3.00"/>
    </Transaction>
</TransactionLog>"""
    f2 = test_outbox / "TLOG_BL01_000102.xml"
    f2.write_text(xml_batch2, encoding="utf-8")

    async with async_session_factory() as session:
        service = IngestionService(session)
        res1 = await service.process_file(f1)
        assert res1["status"] == "PROCESSED"
        assert res1["accepted"] == 2
        assert res1["skipped"] == 0

        res2 = await service.process_file(f2)
        assert res2["status"] == "PROCESSED"
        assert res2["accepted"] == 1
        assert res2["skipped"] == 1  # 9902 was safely skipped

