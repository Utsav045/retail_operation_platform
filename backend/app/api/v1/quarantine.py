import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.audit import QuarantinedFile

router = APIRouter(prefix="/quarantine", tags=["Quarantine"])


@router.get("")
async def list_quarantined_files(
    store_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    List all quarantined corrupt, invalid, or damaged files with error reason, store, timestamp, and original payload.
    """
    query = select(QuarantinedFile).order_by(desc(QuarantinedFile.quarantined_at))
    if store_id:
        query = query.where(QuarantinedFile.store_id == store_id)

    query = query.offset(offset).limit(limit)
    res = await db.execute(query)
    items = res.scalars().all()

    return {
        "total": len(items),
        "items": [
            {
                "id": f.id,
                "file_name": f.file_name,
                "store_id": f.store_id,
                "file_hash": f.file_hash,
                "quarantine_reason": f.quarantine_reason,
                "error_details": f.error_details,
                "quarantined_at": f.quarantined_at.isoformat() if f.quarantined_at else None,
                "payload_preview": f.raw_payload[:1000] if f.raw_payload else None
            }
            for f in items
        ]
    }


@router.get("/{file_id}")
async def get_quarantined_file(
    file_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retrieve full payload of a quarantined file for root-cause diagnosis.
    """
    query = select(QuarantinedFile).where(QuarantinedFile.id == file_id)
    res = await db.execute(query)
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Quarantined record not found.")

    return {
        "id": f.id,
        "file_name": f.file_name,
        "store_id": f.store_id,
        "file_hash": f.file_hash,
        "quarantine_reason": f.quarantine_reason,
        "error_details": f.error_details,
        "quarantined_at": f.quarantined_at.isoformat() if f.quarantined_at else None,
        "raw_payload": f.raw_payload
    }


@router.delete("/{file_id}")
async def soft_delete_quarantined_file(
    file_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Soft-delete a quarantined file entry from view.
    Preserves audit data and payload in database.
    """
    query = select(QuarantinedFile).where(QuarantinedFile.id == file_id)
    res = await db.execute(query)
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Quarantined record not found.")

    f.soft_delete()
    await db.commit()
    return {
        "status": "SUCCESS",
        "message": f"Quarantined record {f.file_name} soft-deleted. Audit file preserved.",
        "id": f.id,
        "is_deleted": f.is_deleted,
        "deleted_at": f.deleted_at.isoformat() if f.deleted_at else None
    }


@router.post("/{file_id}/restore")
async def restore_quarantined_file(
    file_id: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Restore a soft-deleted quarantined file entry.
    """
    query = select(QuarantinedFile).where(QuarantinedFile.id == file_id).execution_options(include_deleted=True)
    res = await db.execute(query)
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Quarantined record not found.")

    f.restore()
    await db.commit()
    return {
        "status": "SUCCESS",
        "message": f"Quarantined record {f.file_name} restored.",
        "id": f.id,
        "is_deleted": f.is_deleted
    }
