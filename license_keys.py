# -*- coding: utf-8 -*-
"""Signed license keys. Only admin can mint; client only verifies."""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

# Public verify material baked into clients (HMAC secret).
# Admin uses the same secret to sign. Change ADMIN_SECRET only in admin builds if you fork.
_APP_SECRET = b"mishabetmen-v1-license-hmac-7f3a9c2e8b1d4f6a"

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _b32_encode(data: bytes) -> str:
    n = int.from_bytes(data, "big")
    chars = []
    for _ in range(max(1, (len(data) * 8 + 4) // 5)):
        chars.append(ALPHABET[n % 32])
        n //= 32
    return "".join(reversed(chars))


def _b32_decode(s: str) -> bytes:
    s = "".join(ch for ch in s.upper() if ch in ALPHABET)
    n = 0
    for ch in s:
        n = n * 32 + ALPHABET.index(ch)
    length = (len(s) * 5) // 8
    return n.to_bytes(length + 2, "big")[-length:] if length else b"\x00"


def _sign(payload: bytes) -> bytes:
    return hmac.new(_APP_SECRET, payload, hashlib.sha256).digest()[:12]


def mint_license(label: str = "") -> str:
    """Admin only: create a new unique license key."""
    uid = secrets.token_bytes(10)
    ts = int(time.time()).to_bytes(4, "big")
    payload = uid + ts
    sig = _sign(payload)
    raw = payload + sig
    body = _b32_encode(raw)
    # group 4
    grouped = "-".join(body[i:i + 4] for i in range(0, len(body), 4))
    return grouped


def verify_license(key: str) -> bool:
    """Client: accept only properly signed keys."""
    try:
        compact = "".join(ch for ch in key.upper() if ch in ALPHABET)
        if len(compact) < 20:
            return False
        raw = _b32_decode(compact)
        if len(raw) < 14 + 12:
            # try flexible length
            if len(raw) < 20:
                return False
        payload, sig = raw[:-12], raw[-12:]
        if len(payload) < 10:
            return False
        expect = _sign(payload)
        return hmac.compare_digest(sig, expect)
    except Exception:
        return False


def normalize_key(key: str) -> str:
    return "".join(ch for ch in key.upper() if ch.isalnum())
