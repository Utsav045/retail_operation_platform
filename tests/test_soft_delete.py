import pytest
from datetime import date, datetime
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func, text

from app.main import app
from app.core.database import async_session_factory, Base
from app.models.base import SoftDeleteMixin
from app.models.master import Item, Store, Device, Staff, Department, BusinessAccount
from app.models.transaction import Transaction, TransactionLine
from app.models.audit import QuarantinedFile
from app.models.user import User


@pytest.mark.asyncio
async def test_all_models_inherit_soft_delete():
    """Verify that every core business entity inherits SoftDeleteMixin and has soft-delete attributes."""
    models = [
        Store, Device, Staff, Department, Item, BusinessAccount,
        Transaction, TransactionLine, QuarantinedFile, User
    ]
    for m in models:
        assert issubclass(m, SoftDeleteMixin), f"{m.__name__} must inherit SoftDeleteMixin"
        assert hasattr(m, "is_deleted"), f"{m.__name__} must have is_deleted column"
        assert hasattr(m, "deleted_at"), f"{m.__name__} must have deleted_at column"
        assert hasattr(m, "soft_delete"), f"{m.__name__} must have soft_delete method"
        assert hasattr(m, "restore"), f"{m.__name__} must have restore method"


@pytest.mark.asyncio
async def test_soft_delete_and_restore_methods():
    """Verify soft_delete and restore toggle state and timestamp accurately."""
    item = Item(
        code="SOFT_TEST_001",
        variant="000",
        description="Soft Delete Test Item",
        dept="10",
        price=Decimal("4.99")
    )
    assert item.is_deleted is False or item.is_deleted is None
    assert item.deleted_at is None

    # Soft delete
    item.soft_delete()
    assert item.is_deleted is True
    assert isinstance(item.deleted_at, datetime)

    # Restore
    item.restore()
    assert item.is_deleted is False
    assert item.deleted_at is None


@pytest.mark.asyncio
async def test_session_delete_interceptor_prevents_hard_delete():
    """
    CRITICAL: Verify that calling session.delete(obj) is intercepted by the ORM,
    converting it into a non-destructive soft-delete (row remains in database with is_deleted=True).
    """
    async with async_session_factory() as session:
        test_code = "HARD_DEL_PREVENT_001"
        # Create item
        item = Item(
            code=test_code,
            variant="000",
            description="Hard Delete Prevention Item",
            dept="10",
            price=Decimal("9.99")
        )
        session.add(item)
        await session.commit()
        item_id = item.id

    async with async_session_factory() as session:
        # Load and attempt HARD DELETE
        res = await session.execute(select(Item).where(Item.id == item_id))
        loaded_item = res.scalar_one()

        # Hard delete call
        await session.delete(loaded_item)
        await session.commit()

    async with async_session_factory() as session:
        # 1. Standard select should NOT return it (filtered out)
        res_standard = await session.execute(select(Item).where(Item.id == item_id))
        assert res_standard.scalar_one_or_none() is None

        # 2. Raw SQL / include_deleted select MUST prove row still exists in database!
        res_archived = await session.execute(
            select(Item).where(Item.id == item_id).execution_options(include_deleted=True)
        )
        preserved_item = res_archived.scalar_one_or_none()
        assert preserved_item is not None, "Row must NEVER be deleted from SQLite!"
        assert preserved_item.is_deleted is True
        assert preserved_item.deleted_at is not None


@pytest.mark.asyncio
async def test_pricing_api_soft_delete_and_restore():
    """Verify REST endpoint DELETE /api/v1/pricing/items/{code} and POST restore."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create an item in DB directly for test
        async with async_session_factory() as session:
            test_item = Item(
                code="API_SOFT_ITEM_99",
                variant="000",
                description="API Soft Item Test",
                dept="20",
                price=Decimal("3.50")
            )
            session.add(test_item)
            await session.commit()

        # 1. Soft-delete via API
        del_resp = await client.delete("/api/v1/pricing/items/API_SOFT_ITEM_99")
        assert del_resp.status_code == 200
        del_data = del_resp.json()
        assert del_data["status"] == "SUCCESS"
        assert del_data["is_deleted"] is True
        assert del_data["deleted_at"] is not None

        # 2. Verify excluded from active item list
        list_resp = await client.get("/api/v1/pricing/items?search=API Soft Item Test")
        assert list_resp.status_code == 200
        active_items = list_resp.json()["items"]
        assert not any(i["code"] == "API_SOFT_ITEM_99" for i in active_items)

        # 3. Verify present when include_deleted=True
        list_all_resp = await client.get("/api/v1/pricing/items?search=API Soft Item Test&include_deleted=true")
        assert list_all_resp.status_code == 200
        all_items = list_all_resp.json()["items"]
        assert any(i["code"] == "API_SOFT_ITEM_99" and i["is_deleted"] is True for i in all_items)

        # 4. Restore via API
        restore_resp = await client.post("/api/v1/pricing/items/API_SOFT_ITEM_99/restore")
        assert restore_resp.status_code == 200
        restore_data = restore_resp.json()
        assert restore_data["status"] == "SUCCESS"
        assert restore_data["is_deleted"] is False

        # 5. Verify visible in active catalog again
        list_restored = await client.get("/api/v1/pricing/items?search=API Soft Item Test")
        assert any(i["code"] == "API_SOFT_ITEM_99" for i in list_restored.json()["items"])


@pytest.mark.asyncio
async def test_transaction_api_soft_delete_and_restore():
    """Verify REST endpoint DELETE /api/v1/transactions/{id} and POST restore."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create test transaction
        async with async_session_factory() as session:
            tx = Transaction(
                store_id="BL01",
                seq=888801,
                business_date=date(2026, 10, 4),
                type="SALE",
                status="COMPLETED",
                device_id="R1",
                net_amount=Decimal("15.00"),
                grand_total=Decimal("15.00")
            )
            session.add(tx)
            await session.commit()
            tx_id = tx.id

        # 1. Soft delete transaction
        del_resp = await client.delete(f"/api/v1/transactions/{tx_id}")
        assert del_resp.status_code == 200
        del_data = del_resp.json()
        assert del_data["status"] == "SUCCESS"
        assert del_data["is_deleted"] is True

        # 2. Get transaction should now return 404 (excluded from active queries)
        get_resp = await client.get(f"/api/v1/transactions/{tx_id}")
        assert get_resp.status_code == 404

        # 3. Restore transaction
        res_resp = await client.post(f"/api/v1/transactions/{tx_id}/restore")
        assert res_resp.status_code == 200
        assert res_resp.json()["is_deleted"] is False

        # 4. Get transaction should now succeed
        get_restored = await client.get(f"/api/v1/transactions/{tx_id}")
        assert get_restored.status_code == 200
        assert get_restored.json()["id"] == tx_id


@pytest.mark.asyncio
async def test_quarantined_file_api_soft_delete_and_restore():
    """Verify REST endpoint DELETE /api/v1/quarantine/{id} and POST restore."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create quarantined record
        async with async_session_factory() as session:
            qf = QuarantinedFile(
                file_name="corrupt_test_batch_99.xml",
                quarantined_path="runtime_data/quarantine/corrupt_test_batch_99.xml",
                reason="Malformed XML Root",
            )
            session.add(qf)
            await session.commit()
            qf_id = qf.id

        # Soft delete
        del_resp = await client.delete(f"/api/v1/quarantine/{qf_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["is_deleted"] is True

        # Restore
        res_resp = await client.post(f"/api/v1/quarantine/{qf_id}/restore")
        assert res_resp.status_code == 200
        assert res_resp.json()["is_deleted"] is False
