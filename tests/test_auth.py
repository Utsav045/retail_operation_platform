import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import async_session_factory
from app.api.v1.auth import ensure_default_user_seeded


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(autouse=True)
async def seed_user():
    async with async_session_factory() as session:
        await ensure_default_user_seeded(session)


@pytest.mark.asyncio
async def test_auth_login_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/auth/login", json={
            "email": "utsavjc@gmail.com",
            "password": "Utsav@123"
        })
        assert res.status_code == 200, res.text
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "utsavjc@gmail.com"
        assert data["user"]["name"] == "Utsav"
        assert data["user"]["role"] == "STORE_MANAGER"


@pytest.mark.asyncio
async def test_auth_login_invalid_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/auth/login", json={
            "email": "utsavjc@gmail.com",
            "password": "WrongPassword999"
        })
        assert res.status_code == 401
        assert "Invalid email or password" in res.json()["detail"]


@pytest.mark.asyncio
async def test_auth_forgot_password_and_otp_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Step 1: Request OTP
        req_res = await ac.post("/api/v1/auth/forgot-password", json={
            "email": "utsavjc@gmail.com"
        })
        assert req_res.status_code == 200
        assert req_res.json()["status"] == "SUCCESS"
        
        # Query generated OTP from DB
        from app.models.user import User
        from sqlalchemy import select
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.email == "utsavjc@gmail.com"))
            user = result.scalar_one()
            otp = user.reset_otp
            assert otp is not None
            assert len(otp) == 6

        # Step 2: Verify wrong OTP fails
        fail_res = await ac.post("/api/v1/auth/verify-otp", json={
            "email": "utsavjc@gmail.com",
            "otp": "000000"
        })
        assert fail_res.status_code == 400

        # Step 3: Verify correct OTP succeeds
        verify_res = await ac.post("/api/v1/auth/verify-otp", json={
            "email": "utsavjc@gmail.com",
            "otp": otp
        })
        assert verify_res.status_code == 200
        assert verify_res.json()["status"] == "VALID"

        # Step 4: Reset Password
        reset_res = await ac.post("/api/v1/auth/reset-password", json={
            "email": "utsavjc@gmail.com",
            "otp": otp,
            "new_password": "Utsav@NewPassword2026"
        })
        assert reset_res.status_code == 200
        assert reset_res.json()["status"] == "SUCCESS"

        # Step 5: Test login with new password
        login_res = await ac.post("/api/v1/auth/login", json={
            "email": "utsavjc@gmail.com",
            "password": "Utsav@NewPassword2026"
        })
        assert login_res.status_code == 200

        # Revert back to Utsav@123
        from app.services.auth.security import hash_password
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.email == "utsavjc@gmail.com"))
            user = result.scalar_one()
            user.hashed_password = hash_password("Utsav@123")
            await session.commit()
