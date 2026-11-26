import hashlib
from pathlib import Path
import shutil
import traceback
from typing import Dict, Any, Union
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.master import Device, Department
from app.models.transaction import (
    Transaction,
    TransactionLine,
    TransactionTender,
    TransactionTax,
    GiftCardActivity,
    CashDrop,
)
from app.models.summary import ShiftSummary, EndOfDaySummary
from app.models.audit import FileImportLog, QuarantinedFile
from app.services.parsers.xml_v2 import XMLv2Parser
from app.services.parsers.json_v3 import JSONv3Parser
from app.services.parsers.summary_parser import SummaryParser
from app.schemas.unified_tlog import CanonicalBatch


def _decimal_to_str(obj: Any) -> Any:
    """Recursively converts Decimal objects to str for JSON serialization."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_str(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_str(v) for v in obj]
    return obj


def compute_file_hash(file_path: Path) -> str:
    """Computes SHA-256 checksum for a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class IngestionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.xml_parser = XMLv2Parser()
        self.json_parser = JSONv3Parser()
        self.summary_parser = SummaryParser()

    async def process_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Safely processes an incoming hub file (TLOG, SHIFT, EOD) in a non-destructive,
        idempotent manner. Never deletes or locks the source file.
        """
        filename = file_path.name
        
        # Check supported file types
        is_tlog = filename.startswith("TLOG_") and (filename.endswith(".xml") or filename.endswith(".json"))
        is_shift = filename.startswith("SHIFT_") and (filename.endswith(".xml") or filename.endswith(".json"))
        is_eod = filename.startswith("EOD_") and (filename.endswith(".xml") or filename.endswith(".json"))
        
        if not (is_tlog or is_shift or is_eod):
            return {"status": "SKIPPED_UNSUPPORTED", "file": filename}
            
        file_hash = compute_file_hash(file_path)
        
        # Check if already processed with identical hash
        existing_log = (
            await self.session.execute(select(FileImportLog).where(FileImportLog.file_name == filename))
        ).scalar_one_or_none()
        
        if existing_log and existing_log.file_hash == file_hash and existing_log.status == "PROCESSED":
            return {"status": "ALREADY_PROCESSED", "file": filename}

        file_format = "v2_xml" if filename.endswith(".xml") else "v3_json"
        
        try:
            if is_tlog:
                return await self._process_tlog(file_path, filename, file_hash, file_format, existing_log)
            elif is_shift:
                return await self._process_shift(file_path, filename, file_hash, file_format, existing_log)
            elif is_eod:
                return await self._process_eod(file_path, filename, file_hash, file_format, existing_log)
        except Exception as e:
            return await self._quarantine_file(file_path, filename, file_hash, file_format, existing_log, e)

        return {"status": "SKIPPED", "file": filename}

    async def _quarantine_file(
        self,
        file_path: Path,
        filename: str,
        file_hash: str,
        file_format: str,
        existing_log: Any,
        exc: Exception,
    ) -> Dict[str, Any]:
        """Quarantine corrupted or malformed files safely without touching outbox/."""
        tb = traceback.format_exc()
        quarantine_dest = settings.QUARANTINE_DIR / filename
        try:
            shutil.copy2(file_path, quarantine_dest)
        except Exception:
            pass
            
        reason_msg = f"Parse failure: {str(exc)}"
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

    async def _process_tlog(
        self,
        file_path: Path,
        filename: str,
        file_hash: str,
        file_format: str,
        existing_log: Any,
    ) -> Dict[str, Any]:
        """Parses and ingests a TLOG transaction batch."""
        if file_format == "v2_xml":
            batch = self.xml_parser.parse(file_path)
        else:
            batch = self.json_parser.parse(file_path)

        # Load reference sets to detect unknown devices
        known_devices = set(
            (await self.session.scalars(select(Device.device_id).where(Device.store_id == batch.store_id))).all()
        )

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

            # Flagging logic for unknown device
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
                flag_reason="; ".join(flag_reasons) if is_tx_flagged else None,
                raw_file_name=filename,
            )
            self.session.add(db_tx)
            await self.session.flush()

            # Lines
            for line_data in tx_data.lines:
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
                )
                self.session.add(db_line)

            # Tenders
            for tend_data in tx_data.tenders:
                db_tender = TransactionTender(
                    transaction_id=db_tx.id,
                    tender_type=tend_data.tender_type,
                    amount=tend_data.amount,
                    tendered=tend_data.tendered,
                    change=tend_data.change,
                    card_type=tend_data.card_type,
                    last4=tend_data.last4,
                    auth_code=tend_data.auth_code,
                    wallet=tend_data.wallet,
                    account_id=tend_data.account_id,
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

    async def _process_shift(
        self,
        file_path: Path,
        filename: str,
        file_hash: str,
        file_format: str,
        existing_log: Any,
    ) -> Dict[str, Any]:
        """Parses and ingests a ShiftClose summary."""
        shift = self.summary_parser.parse_summary_file(file_path)

        # Check existing shift summary
        existing_shift = (
            await self.session.execute(
                select(ShiftSummary).where(
                    ShiftSummary.store_id == shift.store_id,
                    ShiftSummary.business_date == shift.business_date,
                    ShiftSummary.shift_no == shift.shift_no,
                )
            )
        ).scalar_one_or_none()

        tenders_dict = {t.tender_type: str(t.amount) for t in shift.tenders}
        exceptions_dict = _decimal_to_str(shift.exceptions.model_dump() if hasattr(shift.exceptions, "model_dump") else shift.exceptions.dict())

        if existing_shift:
            existing_shift.opening_float = shift.opening_float
            existing_shift.counted_cash = shift.counted_cash
            existing_shift.tenders_json = tenders_dict
            existing_shift.gift_card_loads = shift.gift_card_loads
            existing_shift.cash_drops_amount = shift.cash_drops_amount
            existing_shift.exceptions_json = exceptions_dict
            existing_shift.raw_file_name = filename
        else:
            db_shift = ShiftSummary(
                store_id=shift.store_id,
                business_date=shift.business_date,
                shift_no=shift.shift_no,
                opening_float=shift.opening_float,
                counted_cash=shift.counted_cash,
                tenders_json=tenders_dict,
                gift_card_loads=shift.gift_card_loads,
                cash_drops_amount=shift.cash_drops_amount,
                exceptions_json=exceptions_dict,
                raw_file_name=filename,
            )
            self.session.add(db_shift)

        # Import audit log
        if existing_log:
            existing_log.file_hash = file_hash
            existing_log.status = "PROCESSED"
        else:
            import_log = FileImportLog(
                file_name=filename,
                store_id=shift.store_id,
                file_format=file_format,
                file_hash=file_hash,
                record_count=1,
                records_accepted=1,
                status="PROCESSED",
            )
            self.session.add(import_log)

        await self.session.commit()
        return {"status": "PROCESSED", "file": filename, "type": "SHIFT", "shift_no": shift.shift_no}

    async def _process_eod(
        self,
        file_path: Path,
        filename: str,
        file_hash: str,
        file_format: str,
        existing_log: Any,
    ) -> Dict[str, Any]:
        """Parses and ingests an EndOfDay summary."""
        eod = self.summary_parser.parse_summary_file(file_path)

        existing_eod = (
            await self.session.execute(
                select(EndOfDaySummary).where(
                    EndOfDaySummary.store_id == eod.store_id,
                    EndOfDaySummary.business_date == eod.business_date,
                )
            )
        ).scalar_one_or_none()

        depts_dict = {d.dept_code: {"name": d.name, "qty": str(d.qty), "amount": str(d.amount)} for d in eod.departments}
        taxes_dict = {t.tax_group: {"taxable": str(t.taxable_amount), "amount": str(t.tax_amount)} for t in eod.taxes}
        tenders_dict = {t.tender_type: str(t.amount) for t in eod.tenders}
        exceptions_dict = _decimal_to_str(eod.exceptions.model_dump() if hasattr(eod.exceptions, "model_dump") else eod.exceptions.dict())

        if existing_eod:
            existing_eod.reported_transactions = eod.reported_transactions
            existing_eod.reported_net_sales = eod.reported_net_sales
            existing_eod.reported_tax = eod.reported_tax
            existing_eod.reported_gift_card_loads = eod.reported_gift_card_loads
            existing_eod.reported_grand_total = eod.reported_grand_total
            existing_eod.departments_json = depts_dict
            existing_eod.taxes_json = taxes_dict
            existing_eod.tenders_json = tenders_dict
            existing_eod.exceptions_json = exceptions_dict
            existing_eod.raw_file_name = filename
        else:
            db_eod = EndOfDaySummary(
                store_id=eod.store_id,
                business_date=eod.business_date,
                reported_transactions=eod.reported_transactions,
                reported_net_sales=eod.reported_net_sales,
                reported_tax=eod.reported_tax,
                reported_gift_card_loads=eod.reported_gift_card_loads,
                reported_grand_total=eod.reported_grand_total,
                departments_json=depts_dict,
                taxes_json=taxes_dict,
                tenders_json=tenders_dict,
                exceptions_json=exceptions_dict,
                raw_file_name=filename,
            )
            self.session.add(db_eod)

        # Import audit log
        if existing_log:
            existing_log.file_hash = file_hash
            existing_log.status = "PROCESSED"
        else:
            import_log = FileImportLog(
                file_name=filename,
                store_id=eod.store_id,
                file_format=file_format,
                file_hash=file_hash,
                record_count=1,
                records_accepted=1,
                status="PROCESSED",
            )
            self.session.add(import_log)

        await self.session.commit()
        return {"status": "PROCESSED", "file": filename, "type": "EOD"}
