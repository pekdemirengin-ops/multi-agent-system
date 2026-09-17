"""Kalici kullanici deposu - SQLite veya PostgreSQL."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
import bcrypt
import structlog

logger = structlog.get_logger(__name__)

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
SQLITE_PATH = DATA_DIR / "users.db"
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"


def _use_postgres() -> bool:
    return USE_POSTGRES and bool(DATABASE_URL)


def hash_password(password: str) -> str:
    """Sifreyi hash'ler (bcrypt)."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Sifreyi dogrular."""
    try:
        password_bytes = plain_password.encode("utf-8")
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


class UserStore:
    """Kullanicilari SQLite veya PostgreSQL'de saklar."""

    def __init__(self, db_path: str | Path = SQLITE_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.use_postgres = _use_postgres()
        self._pool: Any = None

    async def init(self) -> None:
        if self.use_postgres:
            await self._init_postgres()
        else:
            await self._init_sqlite()
        # Varsayilan admin
        await self.ensure_admin()

    async def _init_sqlite(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                "username TEXT PRIMARY KEY,"
                "password_hash TEXT NOT NULL,"
                "role TEXT NOT NULL DEFAULT 'user',"
                "created_at TEXT NOT NULL,"
                "is_active INTEGER NOT NULL DEFAULT 1)"
            )
            await db.commit()
        logger.info("user_store.initialized", backend="sqlite")

    async def _init_postgres(self) -> None:
        try:
            import asyncpg
        except ImportError as e:
            logger.error("user_store.asyncpg_missing", error=str(e))
            self.use_postgres = False
            await self._init_sqlite()
            return

        try:
            self._pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "CREATE TABLE IF NOT EXISTS users ("
                    "username TEXT PRIMARY KEY,"
                    "password_hash TEXT NOT NULL,"
                    "role TEXT NOT NULL DEFAULT 'user',"
                    "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
                    "is_active BOOLEAN NOT NULL DEFAULT TRUE)"
                )
            logger.info("user_store.initialized", backend="postgres")
        except Exception as e:
            logger.exception("user_store.postgres_init_failed", error=str(e))
            self.use_postgres = False
            await self._init_sqlite()

    async def create_user(
        self,
        username: str,
        password: str,
        role: str = "user",
    ) -> bool:
        """Yeni kullanici olusturur. Basarili ise True."""
        if await self.exists(username):
            return False
        pwd_hash = hash_password(password)
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES ($1, $2, $3)",
                    username, pwd_hash, role,
                )
        else:
            created_at = datetime.now(timezone.utc).isoformat()
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO users (username, password_hash, role, created_at, is_active) "
                    "VALUES (?, ?, ?, ?, 1)",
                    (username, pwd_hash, role, created_at),
                )
                await db.commit()
        logger.info("user_store.user_created", username=username, role=role)
        return True

    async def authenticate(self, username: str, password: str) -> bool:
        """Kullanici adi + sifre dogrular."""
        user = await self.get_user(username)
        if not user or not user.get("is_active", True):
            return False
        return verify_password(password, user["password_hash"])

    async def exists(self, username: str) -> bool:
        return await self.get_user(username) is not None

    async def get_user(self, username: str) -> dict[str, Any] | None:
        """Kullanici bilgisini doner (password_hash dahil)."""
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT username, password_hash, role, created_at, is_active "
                    "FROM users WHERE username = $1",
                    username,
                )
            if not row:
                return None
            return {
                "username": row["username"],
                "password_hash": row["password_hash"],
                "role": row["role"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else "",
                "is_active": bool(row["is_active"]),
            }
        else:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT username, password_hash, role, created_at, is_active "
                    "FROM users WHERE username = ?",
                    (username,),
                ) as cursor:
                    row = await cursor.fetchone()
            if not row:
                return None
            return {
                "username": row[0],
                "password_hash": row[1],
                "role": row[2],
                "created_at": row[3],
                "is_active": bool(row[4]),
            }

    async def list_users(self) -> list[dict[str, Any]]:
        """Tum kullanicilari doner (password_hash HARIC)."""
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT username, role, created_at, is_active FROM users ORDER BY username"
                )
            return [
                {
                    "username": r["username"],
                    "role": r["role"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else "",
                    "is_active": bool(r["is_active"]),
                }
                for r in rows
            ]
        else:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT username, role, created_at, is_active FROM users ORDER BY username"
                ) as cursor:
                    rows = await cursor.fetchall()
            return [
                {
                    "username": r[0],
                    "role": r[1],
                    "created_at": r[2],
                    "is_active": bool(r[3]),
                }
                for r in rows
            ]

    async def delete_user(self, username: str) -> bool:
        """Kullaniciyi siler. admin silinemez."""
        if username == "admin":
            return False
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM users WHERE username = $1", username
                )
            return result.endswith("1")
        else:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM users WHERE username = ?", (username,)
                )
                await db.commit()
                return cursor.rowcount > 0

    async def update_role(self, username: str, role: str) -> bool:
        """Kullanici rolunu gunceller."""
        if role not in ("admin", "user"):
            return False
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE users SET role = $1 WHERE username = $2", role, username
                )
            return result.endswith("1")
        else:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "UPDATE users SET role = ? WHERE username = ?", (role, username)
                )
                await db.commit()
                return cursor.rowcount > 0

    async def set_active(self, username: str, active: bool) -> bool:
        """Kullaniciyi aktif/pasif yapar."""
        if username == "admin" and not active:
            return False
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE users SET is_active = $1 WHERE username = $2", active, username
                )
            return result.endswith("1")
        else:
            val = 1 if active else 0
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "UPDATE users SET is_active = ? WHERE username = ?", (val, username)
                )
                await db.commit()
                return cursor.rowcount > 0

    async def ensure_admin(self) -> None:
        """Varsayilan admin kullanicisini olusturur (yoksa)."""
        if not await self.exists("admin"):
            await self.create_user("admin", "admin123", role="admin")
            logger.info("user_store.default_admin_created")

    async def count(self) -> int:
        """Toplam kullanici sayisi."""
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow("SELECT COUNT(*) as c FROM users")
            return row["c"]
        else:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                    row = await cursor.fetchone()
            return row[0] if row else 0

    def backend_name(self) -> str:
        return "postgresql" if self.use_postgres else "sqlite"


_user_store: UserStore | None = None


async def get_user_store() -> UserStore:
    """Singleton user store."""
    global _user_store
    if _user_store is None:
        _user_store = UserStore()
        await _user_store.init()
    return _user_store