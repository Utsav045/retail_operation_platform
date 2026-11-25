import csv
from decimal import Decimal
from pathlib import Path
from lxml import etree
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.master import Store, Device, Staff, Department, TaxGroup, Item, BusinessAccount


async def load_master_data(session: AsyncSession, raw_data_dir: Path | None = None) -> dict[str, int]:
    base_dir = raw_data_dir or settings.RAW_DATA_DIR
    counts = {
        "stores": 0,
        "devices": 0,
        "staff": 0,
        "business_accounts": 0,
        "tax_groups": 0,
        "departments": 0,
        "items": 0,
    }
    
    # 1. Stores
    stores_file = base_dir / "master" / "stores.csv"
    if stores_file.exists():
        with open(stores_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                store_id = row["store_id"].strip()
                existing = await session.get(Store, store_id)
                if not existing:
                    store = Store(
                        store_id=store_id,
                        store_name=row["store_name"].strip(),
                        address=row.get("address", "").strip(),
                        city=row.get("city", "").strip(),
                        state=row.get("state", "").strip(),
                        timezone=row.get("timezone", "America/Los_Angeles").strip(),
                    )
                    session.add(store)
                    counts["stores"] += 1
        await session.flush()

    # 2. Devices
    devices_file = base_dir / "master" / "devices.csv"
    if devices_file.exists():
        with open(devices_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                store_id = row["store_id"].strip()
                device_id = row["device_id"].strip()
                query = select(Device).where(Device.store_id == store_id, Device.device_id == device_id)
                res = await session.execute(query)
                if not res.scalar_one_or_none():
                    dev = Device(
                        store_id=store_id,
                        device_id=device_id,
                        device_type=row["device_type"].strip(),
                        display_name=row["display_name"].strip(),
                    )
                    session.add(dev)
                    counts["devices"] += 1
        await session.flush()

    # 3. Staff
    staff_file = base_dir / "master" / "staff.csv"
    if staff_file.exists():
        with open(staff_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                store_id = row["store_id"].strip()
                staff_id = int(row["staff_id"].strip())
                query = select(Staff).where(Staff.store_id == store_id, Staff.staff_id == staff_id)
                res = await session.execute(query)
                if not res.scalar_one_or_none():
                    staff = Staff(
                        store_id=store_id,
                        staff_id=staff_id,
                        name=row["name"].strip(),
                        role=row["role"].strip(),
                    )
                    session.add(staff)
                    counts["staff"] += 1
        await session.flush()

    # 4. Business Accounts
    accounts_file = base_dir / "business_accounts.csv"
    if accounts_file.exists():
        with open(accounts_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                acc_id = row["account_id"].strip()
                existing = await session.get(BusinessAccount, acc_id)
                if not existing:
                    account = BusinessAccount(
                        account_id=acc_id,
                        business_name=row["business_name"].strip(),
                        home_store=row["home_store"].strip(),
                        credit_limit=Decimal(row["credit_limit"].strip()),
                        terms=row.get("terms", "NET30").strip(),
                        status=row.get("status", "ACTIVE").strip(),
                    )
                    session.add(account)
                    counts["business_accounts"] += 1
        await session.flush()

    # Pre-populate existing tax groups, departments, and items to memory sets
    existing_tax_groups = set((await session.scalars(select(TaxGroup.code))).all())
    existing_depts = set((await session.scalars(select(Department.code))).all())
    existing_items = set(
        (await session.execute(select(Item.code, Item.variant))).all()
    )

    # 5. Price List XML (Departments, TaxGroups, Items)
    for store_code in ["BL01", "BL02"]:
        pricelist_file = base_dir / "outbox" / f"PRICELIST_{store_code}.xml"
        if pricelist_file.exists():
            tree = etree.parse(str(pricelist_file))
            root = tree.getroot()
            
            # Tax Groups
            for tg in root.xpath("//TaxGroup"):
                code = tg.get("code")
                if code and code not in existing_tax_groups:
                    tax_group = TaxGroup(
                        code=code,
                        rate_percent=Decimal(tg.get("ratePercent", "0.00")),
                        description=tg.get("description", ""),
                    )
                    session.add(tax_group)
                    existing_tax_groups.add(code)
                    counts["tax_groups"] += 1
            
            # Departments
            for dept in root.xpath("//Department"):
                code = dept.get("code")
                if code and code not in existing_depts:
                    department = Department(
                        code=code,
                        name=dept.get("name", ""),
                        default_tax_group=dept.get("defaultTaxGroup", "T1"),
                        min_age=int(dept.get("minAge", "0")),
                    )
                    session.add(department)
                    existing_depts.add(code)
                    counts["departments"] += 1

            # Items
            for item_elem in root.xpath("//Item"):
                code = item_elem.get("code")
                variant = item_elem.get("variant", "000")
                key = (code, variant)
                if code and key not in existing_items:
                    item = Item(
                        code=code,
                        variant=variant,
                        description=item_elem.get("description", ""),
                        dept=item_elem.get("dept", "99"),
                        price=Decimal(item_elem.get("price", "0.00")),
                        tax_group=item_elem.get("taxGroup", "T1"),
                        min_age=int(item_elem.get("minAge", "0")),
                        unit=item_elem.get("unit", "EA"),
                        containers=int(item_elem.get("containers", "0")),
                        active=item_elem.get("active", "Y") == "Y",
                    )
                    session.add(item)
                    existing_items.add(key)
                    counts["items"] += 1

    await session.commit()
    return counts
