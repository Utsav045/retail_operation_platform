import asyncio
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import async_session_factory
from app.services.connector.loader import IngestionService

logger = logging.getLogger("outbox_watcher")


class OutboxWatcher:
    """Non-destructive watcher that polls the outbox directory.
    
    CRITICAL RULE: Never deletes, moves, or renames files in outbox/.
    All tracking is done idempotently in the database.
    """
    def __init__(self, outbox_dir: Path | None = None, poll_interval: float = 2.0):
        self.outbox_dir = outbox_dir or settings.OUTBOX_DIR
        self.poll_interval = poll_interval
        self._is_running = False

    async def scan_once(self) -> list[dict]:
        """Scans outbox once and processes any new or pending files in sorted time order."""
        if not self.outbox_dir.exists():
            return []
            
        results = []
        files = sorted(
            [f for f in self.outbox_dir.iterdir() if f.is_file() and not f.name.endswith(".tmp")],
            key=lambda p: (p.stat().st_mtime, p.name),
        )
        
        async with async_session_factory() as session:
            service = IngestionService(session)
            for file_path in files:
                try:
                    res = await service.process_file(file_path)
                    if res.get("status") not in ("SKIPPED_NOT_TLOG", "ALREADY_PROCESSED"):
                        results.append(res)
                except Exception as e:
                    logger.error(f"Error scanning file {file_path.name}: {e}")
                    
        return results

    async def run(self):
        """Continuous background polling loop."""
        self._is_running = True
        logger.info(f"Started OutboxWatcher polling on {self.outbox_dir}")
        while self._is_running:
            await self.scan_once()
            await asyncio.sleep(self.poll_interval)

    def stop(self):
        self._is_running = False
