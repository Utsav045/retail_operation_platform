import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import text, select
from app.core.database import engine, Base, async_session_factory
from app.models.master import Store, Device, Staff, Department, TaxGroup, Item, BusinessAccount
from app.models.transaction import Transaction, TransactionLine, TransactionTender


@pytest.mark.asyncio
async def test_database_connection():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT 1"))
        scalar = result.scalar()
        assert scalar == 1


@pytest.mark.asyncio
async def test_database_decimal_precision():
    """Verify that financial values are stored and retrieved with exact Decimal(12,2) precision."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        # Create test store
        store = Store(store_id="TEST01", store_name="Precision Test Store")
        session.add(store)
        await session.flush()

        # Create a transaction with decimal amounts
        tx = Transaction(
            store_id="TEST01",
            batch_seq=999,
            seq=99901,
            business_date=date(2026, 10, 25),
            type="SALE",
            status="COMPLETED",
            device_id="R1",
            staff_id=101,
            net_amount=Decimal("19.99"),
            tax_amount=Decimal("1.60"),
            grand_total=Decimal("21.59"),
        )
        session.add(tx)
        await session.flush()

        line1 = TransactionLine(
            transaction_id=tx.id,
            line_no=1,
            item_code="100000000001",
            variant="000",
            description="Item 1",
            dept="01",
            qty=Decimal("1.000"),
            unit_price=Decimal("19.99"),
            amount=Decimal("19.99"),
            tax_group="T1",
        )
        session.add(line1)

        tender1 = TransactionTender(
            transaction_id=tx.id,
            tender_type="CASH",
            amount=Decimal("20.00"),
            change=Decimal("1.59"),
        )
        session.add(tender1)
        await session.commit()

        # Retrieve and verify exact Decimal types
        saved_tx = (await session.execute(select(Transaction).where(Transaction.id == tx.id))).scalar_one()
        assert isinstance(saved_tx.net_amount, Decimal)
        assert saved_tx.net_amount == Decimal("19.99")
        assert saved_tx.tax_amount == Decimal("1.60")
        assert saved_tx.grand_total == Decimal("21.59")
        assert saved_tx.net_amount + saved_tx.tax_amount == saved_tx.grand_total

