import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_dynamic_meta_options():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/meta/options")
        assert res.status_code == 200, res.text
        data = res.json()
        
        # Verify dynamic lists
        assert "stores" in data
        assert len(data["stores"]) >= 2
        assert any(s["store_id"] == "BL01" for s in data["stores"])
        
        assert "business_dates" in data
        assert len(data["business_dates"]) > 0
        
        assert "departments" in data
        assert len(data["departments"]) >= 6
        
        assert "devices" in data
        assert len(data["devices"]) >= 2
        
        assert "tenders" in data
        assert "CASH" in data["tenders"] or "CARD" in data["tenders"]
        
        assert "business_accounts" in data
        assert len(data["business_accounts"]) >= 4
        
        assert "config" in data
        assert data["config"]["target_margin_pct"] == 35.0
        assert data["config"]["default_variant"] == "000"
