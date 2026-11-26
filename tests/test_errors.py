import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_unified_error_format_on_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/transactions/99999999")
        assert res.status_code == 404
        data = res.json()
        assert "error" in data
        err = data["error"]
        assert err["code"] == "NOT_FOUND"
        assert "message" in err
        assert "user_action" in err
        assert err["status_code"] == 404


@pytest.mark.asyncio
async def test_unified_error_format_on_validation_failure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Invalid payload (missing required email and password)
        res = await ac.post("/api/v1/auth/login", json={})
        assert res.status_code == 422
        data = res.json()
        assert "error" in data
        err = data["error"]
        assert err["code"] == "FORM_VALIDATION_FAILED"
        assert "Field" in err["message"]
        assert "user_action" in err


@pytest.mark.asyncio
async def test_unified_error_format_on_auth_failure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/auth/login", json={
            "email": "utsavjc@gmail.com",
            "password": "WrongPasswordXYZ"
        })
        assert res.status_code == 401
        data = res.json()
        assert "error" in data
        err = data["error"]
        assert err["code"] == "UNAUTHORIZED"
        assert "Invalid email or password" in err["message"]
        assert "user_action" in err


@pytest.mark.asyncio
async def test_hub_error_translation_dictionary():
    from app.core.errors import HUB_ERROR_TRANSLATIONS
    assert "E301" in HUB_ERROR_TRANSLATIONS
    assert "E312" in HUB_ERROR_TRANSLATIONS
    assert "E315" in HUB_ERROR_TRANSLATIONS
    assert "E318" in HUB_ERROR_TRANSLATIONS
    
    # Verify simplified explanations
    assert "variant" in HUB_ERROR_TRANSLATIONS["E312"]["message"].lower()
    assert "24-character" in HUB_ERROR_TRANSLATIONS["E315"]["message"]
    assert "safety limit" in HUB_ERROR_TRANSLATIONS["E318"]["message"].lower()
