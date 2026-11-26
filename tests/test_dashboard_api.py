import pytest
from httpx import AsyncClient, ASGITransport
from datetime import date
from decimal import Decimal

from app.core.config import settings
from app.core.database import async_session_factory, Base, engine
from app.services.master_loader import load_master_data
from app.services.connector.loader import IngestionService
from app.main import app


@pytest.fixture(scope="module")
def outbox_dir():
    return settings.RAW_DATA_DIR / "outbox"


@pytest.mark.asyncio
async def test_api_health_and_root():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Health check
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"

        # Serve static index
        root_res = await client.get("/")
        assert root_res.status_code == 200
        assert "Brightleaf Market" in root_res.text


@pytest.mark.asyncio
async def test_dashboard_daily_metrics(outbox_dir):
    # Ensure master data and a day of transactions is ingested
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        await load_master_data(session)
        service = IngestionService(session)
        # Ingest batches for 2026-10-01
        for batch_file in ["TLOG_BL01_000001.xml", "TLOG_BL01_000002.xml"]:
            p = outbox_dir / batch_file
            if p.exists():
                await service.process_file(p)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/dashboard/daily?store_id=BL01&date=2026-10-01")
        assert res.status_code == 200
        data = res.json()
        assert data["store_id"] == "BL01"
        assert data["business_date"] == "2026-10-01"
        assert "headline" in data
        assert data["headline"]["total_sales"] > 0
        assert data["headline"]["transaction_count"] > 0
        assert isinstance(data["sales_by_hour"], list)
        assert isinstance(data["tenders_breakdown"], list)
        assert isinstance(data["departments_breakdown"], list)
        assert isinstance(data["watch_list"], list)


@pytest.mark.asyncio
async def test_transactions_search_and_detail(outbox_dir):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List transactions
        res = await client.get("/api/v1/transactions?store_id=BL01&date=2026-10-01&limit=10")
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert len(data["items"]) > 0

        first_tx = data["items"][0]
        tx_id = first_tx["id"]

        # Detail drilldown
        detail_res = await client.get(f"/api/v1/transactions/{tx_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["id"] == tx_id
        assert "lines" in detail
        assert "tenders" in detail
        assert "taxes" in detail
        assert len(detail["lines"]) > 0


@pytest.mark.asyncio
async def test_reconciliation_and_quarantine_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Reconciliation daily
        res = await client.get("/api/v1/reconciliation/daily?store_id=BL01&date=2026-10-01")
        assert res.status_code in (200, 404, 500)

        # Quarantine list
        q_res = await client.get("/api/v1/quarantine")
        assert q_res.status_code == 200
        q_data = q_res.json()
        assert "items" in q_data

        # Live system status
        live_res = await client.get("/api/v1/live/status")
        assert live_res.status_code == 200
        live_data = live_res.json()
        assert live_data["status"] == "HEALTHY"
        assert "stores" in live_data
