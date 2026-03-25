"""字段级加密工具，用于保护 secret_key 等敏感字段"""
import base64
import os
from cryptography.fernet import Fernet
from app.core.config import settings

def _get_fernet() -> Fernet:
    import hashlib
    key_bytes = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)

def encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()
