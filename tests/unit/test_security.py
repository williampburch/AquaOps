from __future__ import annotations

from app.core.security import hash_password, hash_session_token, verify_password


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("a longer test password")

    assert password_hash != "a longer test password"
    assert verify_password("a longer test password", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_session_token_hash_uses_secret_key() -> None:
    token = "session-token"

    first = hash_session_token(token, "first-secret-key")
    second = hash_session_token(token, "second-secret-key")

    assert first != second
    assert first == hash_session_token(token, "first-secret-key")
