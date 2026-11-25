import pytest
from sqlalchemy import text
from app.core.database import engine, Base


@pytest.mark.asyncio
async def test_database_connection():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT 1"))
        scalar = result.scalar()
        assert scalar == 1
