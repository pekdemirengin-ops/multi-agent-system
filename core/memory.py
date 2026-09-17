"""Konusma gecmisi - SQLite veya PostgreSQL."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
import structlog

logger = structlog.get_logger(__name__)

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
SQLITE_PATH = DATA_DIR / "memory.db"
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"


def _use_postgres() -> bool:
    return USE_POSTGRES and bool(DATABASE_URL)


class ConversationMemory:
    """Kullanici konusmalarini SQLite veya PostgreSQL'de saklar."""

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

    async def _init_sqlite(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS messages ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "user_id TEXT NOT NULL,"
                "role TEXT NOT NULL,"
                "content TEXT NOT NULL,"
                "agent TEXT,"
                "sources TEXT,"
                "created_at TEXT NOT NULL)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_created ON messages(user_id, created_at DESC)"
            )
            await db.commit()
        logger.info("memory.initialized", backend="sqlite")

    async def _init_postgres(self) -> None:
        try:
            import asyncpg
        except ImportError as e:
            logger.error("memory.asyncpg_missing", error=str(e))
            self.use_postgres = False
            await self._init_sqlite()
            return

        try:
            self._pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "CREATE TABLE IF NOT EXISTS messages ("
                    "id SERIAL PRIMARY KEY,"
                    "user_id TEXT NOT NULL,"
                    "role TEXT NOT NULL,"
                    "content TEXT NOT NULL,"
                    "agent TEXT,"
                    "sources JSONB,"
                    "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
                )
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_user_created ON messages(user_id, created_at DESC)"
                )
            logger.info("memory.initialized", backend="postgres")
        except Exception as e:
            logger.exception("memory.postgres_init_failed", error=str(e))
            self.use_postgres = False
            await self._init_sqlite()

    async def save_message(
        self,
        user_id: str,
        role: str,
        content: str,
        agent: str | None = None,
        sources: list[dict[str, Any]] | None = None,
    ) -> None:
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO messages (user_id, role, content, agent, sources) VALUES ($1, $2, $3, $4, $5)",
                    user_id, role, content, agent, json.dumps(sources or []),
                )
        else:
            sources_json = json.dumps(sources or [], ensure_ascii=False)
            created_at = datetime.now(timezone.utc).isoformat()
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO messages (user_id, role, content, agent, sources, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, role, content, agent, sources_json, created_at),
                )
                await db.commit()

    async def get_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT role, content, agent, sources, created_at FROM messages "
                    "WHERE user_id = $1 ORDER BY id DESC LIMIT $2",
                    user_id, limit,
                )
            history: list[dict[str, Any]] = []
            for row in reversed(rows):
                sources = row["sources"]
                if isinstance(sources, str):
                    sources = json.loads(sources)
                history.append({
                    "role": row["role"],
                    "content": row["content"],
                    "agent": row["agent"],
                    "sources": sources or [],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else "",
                })
            return history
        else:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT role, content, agent, sources, created_at FROM messages "
                    "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                    (user_id, limit),
                ) as cursor:
                    rows = await cursor.fetchall()
            history2: list[dict[str, Any]] = []
            for role, content, agent, sources_json, created_at in reversed(rows):
                history2.append({
                    "role": role,
                    "content": content,
                    "agent": agent,
                    "sources": json.loads(sources_json) if sources_json else [],
                    "created_at": created_at,
                })
            return history2

    async def format_for_llm(self, user_id: str, limit: int = 10) -> str:
        history = await self.get_history(user_id, limit=limit)
        if not history:
            return ""
        lines = ["Onceki konusmalar:"]
        for msg in history:
            role_label = "Kullanici" if msg["role"] == "user" else "Asistan"
            lines.append(f"{role_label}: {msg['content'][:200]}")
        return "\n".join(lines)

    async def clear_user(self, user_id: str) -> int:
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                result = await conn.execute("DELETE FROM messages WHERE user_id = $1", user_id)
                count = int(result.split()[-1]) if result else 0
        else:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
                await db.commit()
                count = cursor.rowcount
        logger.info("memory.cleared", user_id=user_id, count=count)
        return count

    async def stats(self) -> dict[str, Any]:
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT COUNT(*) as total, COUNT(DISTINCT user_id) as users FROM messages"
                )
                return {"total_messages": row["total"], "unique_users": row["users"]}
        else:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT COUNT(*), COUNT(DISTINCT user_id) FROM messages"
                ) as cursor:
                    total, users = await cursor.fetchone()
            return {"total_messages": total, "unique_users": users}

    def backend_name(self) -> str:
        return "postgresql" if self.use_postgres else "sqlite"


_memory: ConversationMemory | None = None


async def get_memory() -> ConversationMemory:
    global _memory
    if _memory is None:
        _memory = ConversationMemory()
        await _memory.init()
    return _memory