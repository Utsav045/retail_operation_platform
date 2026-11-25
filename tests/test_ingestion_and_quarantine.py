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
