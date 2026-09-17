"""Auth testleri (JWT + bcrypt)."""
from __future__ import annotations

import pytest
from core.auth import (
    create_access_token,
    decode_token,
    get_user_from_token,
    hash_password,
    verify_password,
)
from core.user_store import get_user_store


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
    """Async UserStore testleri (SQLite fallback)."""

    @pytest.mark.asyncio
    async def test_default_admin_exists(self) -> None:
        store = await get_user_store()
        assert await store.exists("admin") is True

    @pytest.mark.asyncio
    async def test_authenticate_admin(self) -> None:
        store = await get_user_store()
        assert await store.authenticate("admin", "admin123") is True

    @pytest.mark.asyncio
    async def test_wrong_credentials_fail(self) -> None:
        store = await get_user_store()
        assert await store.authenticate("admin", "wrong") is False
        assert await store.authenticate("nobody_xyz", "admin123") is False

    @pytest.mark.asyncio
    async def test_create_user(self) -> None:
        store = await get_user_store()
        # Unique isim (testler arasi cakismasin)
        import uuid
        uname = f"testuser_{uuid.uuid4().hex[:8]}"
        result = await store.create_user(uname, "test123456")
        assert result is True
        assert await store.exists(uname) is True
        assert await store.authenticate(uname, "test123456") is True

    @pytest.mark.asyncio
    async def test_duplicate_user_fails(self) -> None:
        store = await get_user_store()
        import uuid
        uname = f"dupe_{uuid.uuid4().hex[:8]}"
        await store.create_user(uname, "pass1")
        assert await store.create_user(uname, "pass2") is False

    @pytest.mark.asyncio
    async def test_admin_role(self) -> None:
        store = await get_user_store()
        admin = await store.get_user("admin")
        assert admin is not None
        assert admin["role"] == "admin"

    @pytest.mark.asyncio
    async def test_list_users(self) -> None:
        store = await get_user_store()
        users = await store.list_users()
        assert isinstance(users, list)
        assert len(users) >= 1
        # admin her zaman var
        usernames = [u["username"] for u in users]
        assert "admin" in usernames
        # password_hash donmemeli
        for u in users:
            assert "password_hash" not in u

    @pytest.mark.asyncio
    async def test_update_role(self) -> None:
        store = await get_user_store()
        import uuid
        uname = f"roleuser_{uuid.uuid4().hex[:8]}"
        await store.create_user(uname, "pass1234", role="user")
        assert await store.update_role(uname, "admin") is True
        user = await store.get_user(uname)
        assert user is not None
        assert user["role"] == "admin"
        # Temizlik
        await store.delete_user(uname)

    @pytest.mark.asyncio
    async def test_delete_user(self) -> None:
        store = await get_user_store()
        import uuid
        uname = f"deluser_{uuid.uuid4().hex[:8]}"
        await store.create_user(uname, "pass1234")
        assert await store.exists(uname) is True
        assert await store.delete_user(uname) is True
        assert await store.exists(uname) is False

    @pytest.mark.asyncio
    async def test_admin_cannot_be_deleted(self) -> None:
        store = await get_user_store()
        assert await store.delete_user("admin") is False
        assert await store.exists("admin") is True

    @pytest.mark.asyncio
    async def test_role_validation(self) -> None:
        store = await get_user_store()
        # Gecersiz rol
        assert await store.update_role("admin", "superuser") is False