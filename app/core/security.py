from __future__ import annotations

import hashlib
import hmac
import secrets

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_session_token(token: str, secret_key: str) -> str:
    digest = hmac.new(
        secret_key.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest
