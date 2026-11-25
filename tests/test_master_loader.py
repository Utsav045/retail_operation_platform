import pytest
from sqlalchemy import select, func
from app.core.database import engine, Base, async_session_factory
from app.models.master import Store, Device, Staff, Department, TaxGroup, Item, BusinessAccount
from app.services.master_loader import load_master_data


@pytest.mark.asyncio
async def test_master_data_loading_and_idempotency():
    # 1. Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    # 2. First load
    async with async_session_factory() as session:
        counts = await load_master_data(session)
        assert counts["stores"] == 2
        assert counts["devices"] == 6
        assert counts["staff"] == 6
        assert counts["business_accounts"] == 6
        assert counts["tax_groups"] == 3
        assert counts["departments"] == 14
        assert counts["items"] > 30

    # 3. Verify exact database rows
    async with async_session_factory() as session:
        stores = (await session.execute(select(func.count(Store.store_id)))).scalar()
        assert stores == 2
        
        devices = (await session.execute(select(func.count(Device.id)))).scalar()
        assert devices == 6
        
        staff_count = (await session.execute(select(func.count(Staff.id)))).scalar()
        assert staff_count == 6
        
        accounts = (await session.execute(select(func.count(BusinessAccount.account_id)))).scalar()
        assert accounts == 6
        
        # Verify decimal precision on an item
        item = (await session.execute(select(Item).limit(1))).scalar_one()
        assert str(item.price).count('.') == 1  # exact decimal representation

    # 4. Idempotency test: second load should insert 0 new items
    async with async_session_factory() as session:
        counts2 = await load_master_data(session)
        assert counts2["stores"] == 0
        assert counts2["devices"] == 0
        assert counts2["staff"] == 0
        assert counts2["business_accounts"] == 0
        assert counts2["items"] == 0
