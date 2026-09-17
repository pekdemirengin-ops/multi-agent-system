"""Auth testleri (JWT + bcrypt)."""
from __future__ import annotations

import pytest
from core.auth import (
    create_access_token,
    decode_token,
    get_user_from_token,
    hash_password,
    user_store,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self) -> None:
        password = "test123456"
        hashed = hash_password(password)
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt format
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self) -> None:
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_long_password_truncated(self) -> None:
        # bcrypt 72 byte siniri
        long_password = "a" * 100
        hashed = hash_password(long_password)
        assert verify_password("a" * 72, hashed) is True
        assert verify_password("a" * 100, hashed) is True

    def test_different_hashes_same_password(self) -> None:
        # Her hash'leme farkli salt kullanmali
        h1 = hash_password("test")
        h2 = hash_password("test")
        assert h1 != h2
        assert verify_password("test", h1) is True
        assert verify_password("test", h2) is True


class TestJWT:
    def test_create_and_decode(self) -> None:
        token = create_access_token({"sub": "testuser"})
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # header.payload.signature

        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert "exp" in payload
        assert "iat" in payload

    def test_get_user_from_token(self) -> None:
        token = create_access_token({"sub": "admin"})
        user = get_user_from_token(token)
        assert user == "admin"

    def test_invalid_token_returns_none(self) -> None:
        assert decode_token("invalid.token.here") is None
        assert decode_token("") is None
        assert get_user_from_token("bad.token") is None

    def test_tampered_token_returns_none(self) -> None:
        token = create_access_token({"sub": "admin"})
        # Token'i degistir
        parts = token.split(".")
        parts[1] = "dGFtcGVyZWQ"  # "tampered" base64
        tampered = ".".join(parts)
        assert decode_token(tampered) is None


class TestUserStore:
    def test_default_admin_exists(self) -> None:
        assert user_store.exists("admin") is True

    def test_authenticate_admin(self) -> None:
        assert user_store.authenticate("admin", "admin123") is True

    def test_wrong_credentials_fail(self) -> None:
        assert user_store.authenticate("admin", "wrong") is False
        assert user_store.authenticate("nobody", "admin123") is False

    def test_create_user(self) -> None:
        result = user_store.create_user("testuser_auth", "test123456")
        assert result is True
        assert user_store.exists("testuser_auth") is True
        assert user_store.authenticate("testuser_auth", "test123456") is True

    def test_duplicate_user_fails(self) -> None:
        user_store.create_user("dupe_user", "pass1")
        assert user_store.create_user("dupe_user", "pass2") is False