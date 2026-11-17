
"""Master-key gate + encrypted storage (AES-256-GCM, scrypt KDF)."""
from __future__ import annotations
import os
import json
import base64
import hashlib
import secrets
from pathlib import Path

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    AESGCM = None

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
VAULT_FILE = DATA_DIR / "vault.enc"
META_FILE = DATA_DIR / "vault.meta.json"


def _ensure_crypto():
    global AESGCM
    if AESGCM is None:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography", "--quiet"])
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _A
        AESGCM = _A


def generate_master_key() -> str:
    """Return a high-entropy key (256-bit) as base32-ish groups for humans."""
    raw = secrets.token_bytes(32)
    # Crockford-like base32 without confusing chars
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    bits = int.from_bytes(raw, "big")
    chars = []
    for _ in range(52):
        chars.append(alphabet[bits % 32])
        bits //= 32
    s = "".join(reversed(chars))
    # groups of 4
    return "-".join(s[i:i+4] for i in range(0, len(s), 4))


def normalize_key(key: str) -> str:
    return "".join(ch for ch in key.upper() if ch.isalnum())


def _derive(key: str, salt: bytes) -> bytes:
    _ensure_crypto()
    # scrypt via hashlib (stdlib)
    return hashlib.scrypt(
        normalize_key(key).encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )


def vault_exists() -> bool:
    return VAULT_FILE.exists() and META_FILE.exists()


def create_vault(master_key: str, initial: dict | None = None) -> None:
    _ensure_crypto()
    salt = os.urandom(16)
    nonce = os.urandom(12)
    aes = AESGCM(_derive(master_key, salt))
    payload = json.dumps(initial or {"accounts": {}}, ensure_ascii=False).encode("utf-8")
    ct = aes.encrypt(nonce, payload, None)
    VAULT_FILE.write_bytes(ct)
    META_FILE.write_text(json.dumps({
        "salt": base64.b64encode(salt).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "kdf": "scrypt",
        "cipher": "AES-256-GCM",
    }), encoding="utf-8")


def unlock_vault(master_key: str) -> dict:
    _ensure_crypto()
    meta = json.loads(META_FILE.read_text(encoding="utf-8"))
    salt = base64.b64decode(meta["salt"])
    nonce = base64.b64decode(meta["nonce"])
    aes = AESGCM(_derive(master_key, salt))
    pt = aes.decrypt(nonce, VAULT_FILE.read_bytes(), None)
    return json.loads(pt.decode("utf-8"))


def save_vault(master_key: str, data: dict) -> None:
    _ensure_crypto()
    meta = json.loads(META_FILE.read_text(encoding="utf-8"))
    salt = base64.b64decode(meta["salt"])
    nonce = os.urandom(12)  # new nonce each save
    aes = AESGCM(_derive(master_key, salt))
    ct = aes.encrypt(nonce, json.dumps(data, ensure_ascii=False).encode("utf-8"), None)
    VAULT_FILE.write_bytes(ct)
    meta["nonce"] = base64.b64encode(nonce).decode()
    META_FILE.write_text(json.dumps(meta), encoding="utf-8")


def export_sync_blob(master_key: str, data: dict) -> str:
    """Encrypted portable blob for phone/PC transfer (same master key)."""
    _ensure_crypto()
    salt = os.urandom(16)
    nonce = os.urandom(12)
    aes = AESGCM(_derive(master_key, salt))
    ct = aes.encrypt(nonce, json.dumps(data, ensure_ascii=False).encode("utf-8"), None)
    blob = {
        "v": 1,
        "salt": base64.b64encode(salt).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "ct": base64.b64encode(ct).decode(),
    }
    return base64.b64encode(json.dumps(blob).encode()).decode()


def import_sync_blob(master_key: str, blob_b64: str) -> dict:
    _ensure_crypto()
    blob = json.loads(base64.b64decode(blob_b64.encode()).decode())
    salt = base64.b64decode(blob["salt"])
    nonce = base64.b64decode(blob["nonce"])
    ct = base64.b64decode(blob["ct"])
    aes = AESGCM(_derive(master_key, salt))
    pt = aes.decrypt(nonce, ct, None)
    return json.loads(pt.decode("utf-8"))
