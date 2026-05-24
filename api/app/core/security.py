import secrets
import hashlib
import hmac
from datetime import datetime, timezone
from .config import get_settings

settings = get_settings()


def generate_api_key() -> tuple[str, str]:
    """Return (raw_key, hashed_key). Store only the hash."""
    raw = settings.API_KEY_PREFIX + secrets.token_urlsafe(32)
    hashed = _hash_key(raw)
    return raw, hashed


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    return hmac.compare_digest(_hash_key(raw_key), stored_hash)


def generate_webhook_secret() -> str:
    return secrets.token_hex(32)


def sign_webhook_payload(payload: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def verify_webhook_signature(payload: bytes, secret: str, signature: str) -> bool:
    expected = sign_webhook_payload(payload, secret)
    return hmac.compare_digest(expected, signature)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
