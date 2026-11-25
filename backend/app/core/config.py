from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Brightleaf Retail Operations Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Base directory is retail_operations_platform/
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    
    # Path to original task data package
    RAW_DATA_DIR: Path = BASE_DIR.parent / "Full Stack_Hiring_Task_Zygeist" / "data_package"
    
    # Runtime directories for active hub exchange
    RUNTIME_DIR: Path = BASE_DIR / "runtime_data"
    OUTBOX_DIR: Path = BASE_DIR / "runtime_data" / "outbox"
    INBOX_DIR: Path = BASE_DIR / "runtime_data" / "inbox"
    QUARANTINE_DIR: Path = BASE_DIR / "runtime_data" / "quarantine"
    
    # Database configuration
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/retail_ops.db"
    
    # Polling & Hub timing
    WATCHER_POLL_INTERVAL_SECONDS: float = 2.0
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# Ensure runtime directories exist
settings.RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
settings.INBOX_DIR.mkdir(parents=True, exist_ok=True)
settings.QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
