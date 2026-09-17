"""JWT authentication modulu."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from jose import JWTError, jwt

from core.user_store import (
    UserStore,
    get_user_store,
    hash_password,
    verify_password,
)

logger = structlog.get_logger(__name__)


# ============================================================
# Ayarlar
# ============================================================

SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "dev-secret-key-change-in-production-please-1234567890",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 gun


# ============================================================
# JWT token olusturma / dogrulama
# ============================================================

def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """JWT access token olusturur."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info("auth.token_created", sub=data.get("sub"), role=data.get("role"))
    return encoded


def decode_token(token: str) -> dict[str, Any] | None:
    """Token'i decode eder."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning("auth.invalid_token", error=str(e))
        return None


def get_user_from_token(token: str) -> str | None:
    """Token'dan kullanici adini cikarir."""
    payload = decode_token(token)
    if payload is None:
        return None
    return payload.get("sub")


def get_user_info_from_token(token: str) -> dict[str, Any] | None:
    """Token'dan kullanici bilgisi (sub + role) cikarir."""
    payload = decode_token(token)
    if payload is None:
        return None
    return {
        "username": payload.get("sub"),
        "role": payload.get("role", "user"),
    }


# ============================================================
# Backward compatibility (eski kod user_store kullaniyordu)
# ============================================================

# NOT: user_store artik async. Eski senkron kod icin bir wrapper.
# Yeni kod get_user_store() kullanmali.
class _SyncUserStoreWrapper:
    """Eski senkron API'yi async store'a kopru yapar (DEPRECATED)."""

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, str]] = {}

    def exists(self, username: str) -> bool:
        # Senkron varsayim: cache'e bak
        return username in self._cache or username == "admin"

    def create_user(self, username: str, password: str) -> bool:
        if username in self._cache:
            return False
        self._cache[username] = {
            "username": username,
            "password_hash": hash_password(password),
        }
        return True

    def authenticate(self, username: str, password: str) -> bool:
        user = self._cache.get(username)
        if not user:
            return False
        return verify_password(password, user["password_hash"])

    def count(self) -> int:
        return len(self._cache) + (1 if "admin" in self._cache else 0)


# DEPRECATED: yeni kod get_user_store() kullansin
user_store = _SyncUserStoreWrapper()