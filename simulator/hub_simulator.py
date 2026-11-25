import argparse
import asyncio
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from lxml import etree

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("HubSimulator")


class HubSimulator:
    def __init__(
        self,
        source_outbox_dir: Path,
        live_outbox_dir: Path,
        live_inbox_dir: Path,
        speed_factor: float = 1.0,  # 1.0 = normal, higher = faster
        store_id: str = "BL01",
    ):
        self.source_outbox_dir = source_outbox_dir
        self.live_outbox_dir = live_outbox_dir
        self.live_inbox_dir = live_inbox_dir
        self.speed_factor = speed_factor
        self.store_id = store_id
        
        self.processed_inbox_dir = live_inbox_dir / "processed"
        self.processed_inbox_dir.mkdir(parents=True, exist_ok=True)
        self.live_outbox_dir.mkdir(parents=True, exist_ok=True)
        
        self.known_depts = {"10", "11", "12", "13", "20", "21", "22", "23", "30", "40", "41", "50", "51", "99"}
        self.known_tax_groups = {"T0", "T1", "T2"}
        self.applied_change_ids: set[str] = set()

    def get_source_files_chronological(self) -> list[Path]:
        """Returns all batch files from source outbox sorted by modification time or sequence."""
        files = [
            f for f in self.source_outbox_dir.iterdir()
            if f.is_file() and not f.name.endswith(".tmp")
        ]
        return sorted(files, key=lambda p: (p.stat().st_mtime, p.name))

    def emit_file(self, src_file: Path) -> Path:
        """Copies a file from source to live outbox."""
        dest = self.live_outbox_dir / src_file.name
        shutil.copy2(src_file, dest)
        logger.info(f"[OUTBOX EMIT] Emitted {src_file.name} to {dest}")
        return dest

    def emit_corrupted_file(self, filename: str = "TLOG_BL01_999999_corrupted.xml") -> Path:
        """Emits a damaged XML file to test platform quarantine handling."""
        dest = self.live_outbox_dir / filename
        with open(dest, "w", encoding="utf-8") as f:
            f.write("<TransactionLog formatVersion='2.1' storeId='BL01'><Transaction seq='999999'>BAD DATA WITHOUT CLOSING TAG")
        logger.warning(f"[CORRUPT EMIT] Emitted damaged file {filename}")
        return dest

    def re_emit_file(self, filename: str) -> Path | None:
        """Re-emits an already-sent file to test platform idempotency."""
        src = self.source_outbox_dir / filename
        if not src.exists():
            logger.error(f"Cannot re-emit: {src} does not exist")
            return None
        dest = self.live_outbox_dir / filename
        shutil.copy2(src, dest)
        # Touch timestamp to simulate modified/re-sent file
        os.utime(dest, None)
        logger.info(f"[RE-EMIT DUPLICATE] Re-emitted {filename}")
        return dest

    def process_inbox_change_file(self, change_file: Path) -> Path | None:
        """Reads a change file from inbox, validates rules, updates state, and writes ACK/REJ."""
        if change_file.name.endswith(".tmp"):
            return None  # Ignore temporary files being written
            
        logger.info(f"[INBOX PICKUP] Processing {change_file.name}")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            tree = etree.parse(str(change_file))
            root = tree.getroot()
        except Exception:
            # Whole file error E302
            rej_name = f"REJ_{self.store_id}_UNKNOWN_{int(time.time())}.xml"
            dest = self.live_outbox_dir / rej_name
            with open(dest, "w", encoding="utf-8") as f:
                f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<ChangeReject changeId="UNKNOWN" storeId="{self.store_id}" processed="{now_str}" errorCode="E302" message="Malformed XML"/>\n')
            shutil.move(str(change_file), str(self.processed_inbox_dir / change_file.name))
            return dest

        change_id = root.get("changeId", "UNKNOWN")
        file_store_id = root.get("storeId", "")

        # Check whole-file rule E410 (Account maintenance not allowed through change files)
        if root.find(".//Accounts") is not None or root.find(".//Account") is not None:
            rej_name = f"REJ_{self.store_id}_{change_id}.xml"
            dest = self.live_outbox_dir / rej_name
            with open(dest, "w", encoding="utf-8") as f:
                f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<ChangeReject changeId="{change_id}" storeId="{file_store_id}" processed="{now_str}" errorCode="E410" message="Account maintenance is not accepted. Create and edit business accounts at the hub terminal."/>\n')
            shutil.move(str(change_file), str(self.processed_inbox_dir / change_file.name))
            logger.warning(f"[REJ WRITTEN] Whole-file rejection E410 written to {rej_name}")
            return dest

        # Check storeId match E301
        if file_store_id and file_store_id != self.store_id:
            rej_name = f"REJ_{self.store_id}_{change_id}.xml"
            dest = self.live_outbox_dir / rej_name
            with open(dest, "w", encoding="utf-8") as f:
                f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<ChangeReject changeId="{change_id}" storeId="{file_store_id}" processed="{now_str}" errorCode="E301" message="StoreId mismatch"/>\n')
            shutil.move(str(change_file), str(self.processed_inbox_dir / change_file.name))
            return dest

        # Check if already applied
        if change_id in self.applied_change_ids:
            ack_name = f"ACK_{self.store_id}_{change_id}.xml"
            dest = self.live_outbox_dir / ack_name
            with open(dest, "w", encoding="utf-8") as f:
                f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<ChangeAck changeId="{change_id}" storeId="{self.store_id}" processed="{now_str}" result="ALREADY_APPLIED"/>\n')
            shutil.move(str(change_file), str(self.processed_inbox_dir / change_file.name))
            return dest

        # Validate item-level rules
        item_results = []
        has_applied = False
        has_rejected = False

        for item in root.xpath("//Item"):
            code = item.get("code", "")
            variant = item.get("variant")
            action = item.get("action", "update")
            desc = item.get("description", "")
            price = item.get("price")
            dept = item.get("dept")
            tax_group = item.get("taxGroup")

            # E312: variant required
            if not variant:
                item_results.append(f'<ItemResult code="{code}" variant="" action="{action}" result="REJECTED" errorCode="E312" message="Variant is required. Send 000 for the base item."/>')
                has_rejected = True
                continue

            # E315: description <= 24 characters
            if desc and len(desc) > 24:
                item_results.append(f'<ItemResult code="{code}" variant="{variant}" action="{action}" result="REJECTED" errorCode="E315" message="Description longer than 24 characters."/>')
                has_rejected = True
                continue

            # E318: price > 0.00 and <= 999.99
            if price:
                try:
                    p_val = float(price)
                    if p_val <= 0.0 or p_val > 999.99:
                        item_results.append(f'<ItemResult code="{code}" variant="{variant}" action="{action}" result="REJECTED" errorCode="E318" message="Price out of range (0.01 to 999.99)."/>')
                        has_rejected = True
                        continue
                except ValueError:
                    item_results.append(f'<ItemResult code="{code}" variant="{variant}" action="{action}" result="REJECTED" errorCode="E318" message="Invalid price format."/>')
                    has_rejected = True
                    continue

            # E320: dept must exist
            if dept and dept not in self.known_depts:
                item_results.append(f'<ItemResult code="{code}" variant="{variant}" action="{action}" result="REJECTED" errorCode="E320" message="Department {dept} does not exist on hub."/>')
                has_rejected = True
                continue

            # E321: taxGroup must exist
            if tax_group and tax_group not in self.known_tax_groups:
                item_results.append(f'<ItemResult code="{code}" variant="{variant}" action="{action}" result="REJECTED" errorCode="E321" message="TaxGroup {tax_group} does not exist on hub."/>')
                has_rejected = True
                continue

            # Otherwise applied
            item_results.append(f'<ItemResult code="{code}" variant="{variant}" action="{action}" result="APPLIED"/>')
            has_applied = True

        overall_result = "APPLIED"
        if has_applied and has_rejected:
            overall_result = "PARTIAL"
        elif not has_applied and has_rejected:
            overall_result = "REJECTED"

        ack_name = f"ACK_{self.store_id}_{change_id}.xml"
        dest = self.live_outbox_dir / ack_name
        with open(dest, "w", encoding="utf-8") as f:
            f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<ChangeAck changeId="{change_id}" storeId="{self.store_id}" processed="{now_str}" result="{overall_result}">\n')
            for res_line in item_results:
                f.write(f"  {res_line}\n")
            f.write("</ChangeAck>\n")

        self.applied_change_ids.add(change_id)
        shutil.move(str(change_file), str(self.processed_inbox_dir / change_file.name))
        logger.info(f"[ACK WRITTEN] Emitted {ack_name} with result={overall_result}")
        return dest

    async def run_loop(self, delay_per_file: float = 1.0, max_files: int | None = None):
        """Replays files sequentially and checks inbox continuously."""
        all_files = self.get_source_files_chronological()
        emitted_count = 0
        logger.info(f"HubSimulator starting playback of {len(all_files)} files at {delay_per_file}s interval...")

        for src_file in all_files:
            if max_files and emitted_count >= max_files:
                break
                
            self.emit_file(src_file)
            emitted_count += 1
            
            # Check inbox
            for inbox_file in self.live_inbox_dir.iterdir():
                if inbox_file.is_file() and not inbox_file.name.endswith(".tmp"):
                    self.process_inbox_change_file(inbox_file)
                    
            await asyncio.sleep(delay_per_file)
            
        logger.info("HubSimulator finished file replay. Still monitoring inbox...")
        while True:
            for inbox_file in self.live_inbox_dir.iterdir():
                if inbox_file.is_file() and not inbox_file.name.endswith(".tmp"):
                    self.process_inbox_change_file(inbox_file)
            await asyncio.sleep(2.0)


def main():
    parser = argparse.ArgumentParser(description="Brightleaf Hub Simulator")
    parser.add_argument("--source", type=str, default=r"Full Stack_Hiring_Task_Zygeist\data_package\outbox")
    parser.add_argument("--outbox", type=str, default=r"retail_operations_platform\runtime_data\outbox")
    parser.add_argument("--inbox", type=str, default=r"retail_operations_platform\runtime_data\inbox")
    parser.add_argument("--speed", type=float, default=1.0, help="Seconds delay between emitted batches")
    parser.add_argument("--re-emit", type=str, help="Re-emit a specific file")
    parser.add_argument("--emit-corrupt", action="store_true", help="Emit a damaged XML file")
    args = parser.parse_args()

    sim = HubSimulator(
        source_outbox_dir=Path(args.source),
        live_outbox_dir=Path(args.outbox),
        live_inbox_dir=Path(args.inbox),
    )

    if args.re_emit:
        sim.re_emit_file(args.re_emit)
        return

    if args.emit_corrupt:
        sim.emit_corrupted_file()
        return

    asyncio.run(sim.run_loop(delay_per_file=args.speed))


if __name__ == "__main__":
    main()
