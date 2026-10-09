"""Authenticated encryption for retrievable credentials (separate from API key hashes)."""

from cryptography.fernet import Fernet

from .config import get_settings


def cipher() -> Fernet:
    key = get_settings().CREDENTIAL_ENCRYPTION_KEY
    if not key:
        raise ValueError("CREDENTIAL_ENCRYPTION_KEY must be configured")
    return Fernet(key.encode())


def encrypt_secret(value: str) -> str:
    return cipher().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    return cipher().decrypt(value.encode()).decode()
