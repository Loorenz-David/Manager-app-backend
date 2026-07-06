from cryptography.fernet import Fernet

from beyo_manager.config import settings


def encrypt_field(plaintext: str) -> str:
    key = _get_key()
    return Fernet(key).encrypt(plaintext.encode()).decode()


def decrypt_field(ciphertext: str) -> str:
    key = _get_key()
    return Fernet(key).decrypt(ciphertext.encode()).decode()


def _get_key() -> bytes:
    if not settings.field_encryption_key:
        raise RuntimeError("FIELD_ENCRYPTION_KEY is not set in environment config.")
    return settings.field_encryption_key.encode()
