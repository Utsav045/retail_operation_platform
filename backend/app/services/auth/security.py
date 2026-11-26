import hashlib
import hmac
import os
import secrets
import base64
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "brightleaf_retail_ops_super_secret_jwt_key_2026")
SALT_LENGTH = 16
ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """Hashes a password with a random salt using PBKDF2 HMAC SHA256."""
    salt = os.urandom(SALT_LENGTH)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"{salt.hex()}:{key.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a password against the stored salt:hash string."""
    try:
        salt_hex, key_hex = hashed_password.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        actual_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
        return hmac.compare_digest(actual_key, expected_key)
    except Exception:
        return False


def generate_otp() -> str:
    """Generates a secure 6-digit numeric OTP code."""
    return f"{secrets.randbelow(900000) + 100000:06d}"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed HMAC SHA256 bearer token with expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    
    to_encode.update({"exp": expire.isoformat()})
    payload_bytes = json.dumps(to_encode, sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
    
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    return f"{payload_b64}.{signature}"


def verify_access_token(token: str) -> Optional[dict]:
    """Verifies a signed token and returns the payload if valid and unexpired."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        
        # Verify HMAC signature
        expected_sig = hmac.new(
            SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return None
        
        # Decode payload
        padding = "=" * (4 - (len(payload_b64) % 4)) if len(payload_b64) % 4 != 0 else ""
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        data = json.loads(payload_bytes.decode("utf-8"))
        
        # Check expiry
        if "exp" in data:
            exp_time = datetime.fromisoformat(data["exp"])
            if datetime.utcnow() > exp_time:
                return None
        
        return data
    except Exception:
        return None
