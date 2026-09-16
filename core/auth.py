"""JWT authentication modulu."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import structlog
from jose import JWTError, jwt

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
# Sifre hash'leme (dogrudan bcrypt)
# ============================================================

def hash_password(password: str) -> str:
    """Sifreyi hash'ler (dogrudan bcrypt)."""
    password_bytes = password.encode("utf-8")
    # bcrypt 72 byte siniri
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Sifreyi dogrular (dogrudan bcrypt)."""
    try:
        password_bytes = plain_password.encode("utf-8")
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


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
    logger.info("auth.token_created", sub=data.get("sub"))
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


# ============================================================
# Basit in-memory kullanici deposu
# ============================================================

class UserStore:
    """Basit in-memory kullanici deposu."""

    def __init__(self) -> None:
        self._users: dict[str, dict[str, str]] = {}

    def create_user(self, username: str, password: str) -> bool:
        if username in self._users:
            return False
        self._users[username] = {
            "username": username,
            "password_hash": hash_password(password),
        }
        logger.info("auth.user_created", username=username)
        return True

    def authenticate(self, username: str, password: str) -> bool:
        user = self._users.get(username)
        if not user:
            return False
        return verify_password(password, user["password_hash"])

    def exists(self, username: str) -> bool:
        return username in self._users

    def count(self) -> int:
        return len(self._users)


user_store = UserStore()


# Ilk kullanici (default)
if not user_store.exists("admin"):
    user_store.create_user("admin", "admin123")
    logger.info("auth.default_user_created", username="admin", password="admin123")