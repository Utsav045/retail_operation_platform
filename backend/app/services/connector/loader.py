import hashlib
import shutil
import traceback
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit import FileImportLog, QuarantinedFile
from app.models.master import Device, Department, Item
from app.models.transaction import (
    Transaction,
    TransactionLine,
    TransactionTender,
    TransactionTax,
    GiftCardActivity,
    CashDrop,
)
from app.services.parsers.xml_v2 import XMLv2Parser
from app.services.parsers.json_v3 import JSONv3Parser
from app.schemas.unified_tlog import CanonicalBatch


def compute_file_hash(path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


class IngestionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.xml_parser = XMLv2Parser()
        self.json_parser = JSONv3Parser()

    async def process_file(self, file_path: Path) -> dict:
        filename = file_path.name
        
        # Only process TLOG batches in this loader
        if not (filename.startswith("TLOG_") and (filename.endswith(".xml") or filename.endswith(".json"))):
            return {"status": "SKIPPED_NOT_TLOG", "file": filename}
            
        file_hash = compute_file_hash(file_path)
        
        # Check if already processed with identical hash
        existing_log = (
            await self.session.execute(select(FileImportLog).where(FileImportLog.file_name == filename))
        ).scalar_one_or_none()
        
        if existing_log and existing_log.file_hash == file_hash and existing_log.status == "PROCESSED":
            return {"status": "ALREADY_PROCESSED", "file": filename}

        file_format = "v2_xml" if filename.endswith(".xml") else "v3_json"
        
        # Parse the batch
        batch: CanonicalBatch
        try:
            if file_format == "v2_xml":
                batch = self.xml_parser.parse(file_path)
            else:
                batch = self.json_parser.parse(file_path)
        except Exception as e:
            # Quarantine corrupted or malformed files safely
            tb = traceback.format_exc()
            quarantine_dest = settings.QUARANTINE_DIR / filename
            try:
                shutil.copy2(file_path, quarantine_dest)
            except Exception:
                pass
                
            reason_msg = f"Parse failure: {str(e)}"
            quarantined_record = QuarantinedFile(
                file_name=filename,
                quarantined_path=str(quarantine_dest),
                reason=reason_msg,
                stack_trace=tb[:1900],
            )
            self.session.add(quarantined_record)
            
            if existing_log:
                existing_log.status = "FAILED"
            else:
                import_log = FileImportLog(
                    file_name=filename,
                    store_id="UNKNOWN",
                    file_format=file_format,
                    file_hash=file_hash,
                    status="FAILED",
                )
                self.session.add(import_log)
                
            await self.session.commit()
            return {"status": "QUARANTINED", "file": filename, "reason": reason_msg}

        # Load reference sets to detect unknown devices, depts, items
        known_devices = set(
            (await self.session.scalars(select(Device.device_id).where(Device.store_id == batch.store_id))).all()
        )
        known_depts = set((await self.session.scalars(select(Department.code))).all())

        records_accepted = 0
        records_skipped = 0
        records_flagged = 0

        for tx_data in batch.transactions:
            # Check for existing transaction (store_id + seq + business_date)
            existing_tx = (
                await self.session.execute(
                    select(Transaction.id).where(
                        Transaction.store_id == batch.store_id,
                        Transaction.seq == tx_data.seq,
                        Transaction.business_date == batch.business_date,
                    )
                )
            ).scalar_one_or_none()

            if existing_tx:
                records_skipped += 1
                continue

            # Flagging logic for unknown device/operator
            is_tx_flagged = False
            flag_reasons = []
            if tx_data.device not in known_devices:
                is_tx_flagged = True
                flag_reasons.append(f"Unknown device: {tx_data.device}")

            db_tx = Transaction(
                store_id=batch.store_id,
                seq=tx_data.seq,
                business_date=batch.business_date,
                batch_seq=batch.batch_seq,
                type=tx_data.type,
                status=tx_data.status,
                device_id=tx_data.device,
                staff_id=tx_data.staff,
                shift=tx_data.shift,
                start_time=tx_data.start_time,
                end_time=tx_data.end_time,
                original_seq=tx_data.original_seq,
                net_amount=tx_data.net_total,
                tax_amount=tx_data.tax_total,
                gift_card_amount=tx_data.gift_card_total,
                grand_total=tx_data.grand_total,
                is_flagged=is_tx_flagged,
                flag_reason="; ".join(flag_reasons) if flag_reasons else None,
                raw_file_name=filename,
            )
            self.session.add(db_tx)
            await self.session.flush()

            # Lines
            for line_data in tx_data.lines:
                is_line_flagged = False
                line_flag_reasons = []
                if line_data.dept not in known_depts:
                    is_line_flagged = True
                    line_flag_reasons.append(f"Unknown dept: {line_data.dept}")

                db_line = TransactionLine(
                    transaction_id=db_tx.id,
                    line_no=line_data.line_no,
                    item_code=line_data.item_code,
                    variant=line_data.variant,
                    description=line_data.description,
                    dept=line_data.dept,
                    qty=line_data.qty,
                    unit_price=line_data.unit_price,
                    amount=line_data.amount,
                    tax_group=line_data.tax_group,
                    is_void=line_data.is_void,
                    is_flagged=is_line_flagged,
                    flag_reason="; ".join(line_flag_reasons) if line_flag_reasons else None,
                )
                self.session.add(db_line)

            # Tenders
            for t_data in tx_data.tenders:
                db_tender = TransactionTender(
                    transaction_id=db_tx.id,
                    tender_type=t_data.tender_type,
                    amount=t_data.amount,
                    tendered=t_data.tendered,
                    change=t_data.change,
                    card_type=t_data.card_type,
                    last4=t_data.last4,
                    auth_code=t_data.auth_code,
                    wallet=t_data.wallet,
                    account_id=t_data.account_id,
                )
                self.session.add(db_tender)

            # Taxes
            for tax_data in tx_data.taxes:
                db_tax = TransactionTax(
                    transaction_id=db_tx.id,
                    tax_group=tax_data.tax_group,
                    taxable_amount=tax_data.taxable_amount,
                    tax_amount=tax_data.tax_amount,
                )
                self.session.add(db_tax)

            # Gift cards
            for gc_data in tx_data.gift_cards:
                db_gc = GiftCardActivity(
                    transaction_id=db_tx.id,
                    line_no=gc_data.line_no,
                    action=gc_data.action,
                    card_last4=gc_data.card_last4,
                    amount=gc_data.amount,
                )
                self.session.add(db_gc)

            # Cash drops
            for cd_data in tx_data.cash_drops:
                db_cd = CashDrop(
                    transaction_id=db_tx.id,
                    envelope=cd_data.envelope,
                    amount=cd_data.amount,
                    status=cd_data.status,
                )
                self.session.add(db_cd)

            if is_tx_flagged:
                records_flagged += 1
            records_accepted += 1

        # Create or update import log
        if existing_log:
            existing_log.file_hash = file_hash
            existing_log.record_count = batch.record_count
            existing_log.records_accepted += records_accepted
            existing_log.records_skipped += records_skipped
            existing_log.records_flagged += records_flagged
            existing_log.status = "PROCESSED"
        else:
            import_log = FileImportLog(
                file_name=filename,
                store_id=batch.store_id,
                file_format=file_format,
                file_hash=file_hash,
                batch_seq=batch.batch_seq,
                record_count=batch.record_count,
                records_accepted=records_accepted,
                records_skipped=records_skipped,
                records_flagged=records_flagged,
                status="PROCESSED",
            )
            self.session.add(import_log)

        await self.session.commit()
        return {
            "status": "PROCESSED",
            "file": filename,
            "accepted": records_accepted,
            "skipped": records_skipped,
            "flagged": records_flagged,
        }
