from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union
from app.schemas.unified_tlog import CanonicalBatch


class BaseTLOGParser(ABC):
    @abstractmethod
    def parse(self, file_path_or_content: Union[Path, str, bytes]) -> CanonicalBatch:
        """Parses raw transaction log into a canonical normalized batch."""
        pass
