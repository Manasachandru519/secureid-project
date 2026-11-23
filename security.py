import os, json, hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def _key() -> bytes:
    secret = os.getenv("SECRET_KEY", "secureid-local-demo-change-this-secret")
    return hashlib.sha256(secret.encode("utf-8")).digest()  # 32 bytes = AES-256

def encrypt_json(data: dict) -> str:
    nonce = os.urandom(12)
    encrypted = AESGCM(_key()).encrypt(nonce, json.dumps(data).encode("utf-8"), None)
    return (nonce + encrypted).hex()

def decrypt_json(payload: str) -> dict:
    raw = bytes.fromhex(payload)
    plain = AESGCM(_key()).decrypt(raw[:12], raw[12:], None)
    return json.loads(plain.decode("utf-8"))
