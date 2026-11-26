import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Brightleaf Retail Operations Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
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
    
    # Authentication & Session Security
    AUTH_SECRET_KEY: str = "brightleaf_retail_ops_super_secret_jwt_key_2026"
    AUTH_TOKEN_EXPIRE_DAYS: int = 7
    OTP_EXPIRE_MINUTES: int = 15
    DEFAULT_MANAGER_EMAIL: str = "utsavjc@gmail.com"
    DEFAULT_MANAGER_NAME: str = "Utsav"
    DEFAULT_MANAGER_PASSWORD: str = "Utsav@123"
    DEFAULT_MANAGER_ROLE: str = "STORE_MANAGER"
    
    # Gmail & SMTP Dispatch Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_TIMEOUT_SECONDS: int = 10
    
    # Retail Business Logic & Rules
    TARGET_PROFIT_MARGIN_PCT: float = 35.0
    DEFAULT_VARIANT_CODE: str = "000"
    MAX_DESCRIPTION_LENGTH: int = 24
    MAX_ITEM_PRICE_LIMIT: float = 999.99
    DEFAULT_ROUNDING_RULE: str = "ROUND_UP_9"
    EOD_TOLERANCE_THRESHOLD: float = 5.00
    
    # CORS Trusted Origins
    CORS_ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure runtime directories exist
settings.RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
settings.INBOX_DIR.mkdir(parents=True, exist_ok=True)
settings.QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
