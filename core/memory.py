"""Konusma gecmisi (SQLite) - hafiza modulu."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
import structlog

logger = structlog.get_logger(__name__)

# DATA_DIR env'den oku, yoksa "data" kullan
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DB_PATH = DATA_DIR / "memory.db"


class ConversationMemory:
    """Kullanici konusmalarini SQLite'ta saklar."""

    def __init__(self, db_path: str | Path = DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    agent TEXT,
                    sources TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_created ON messages(user_id, created_at DESC)"
            )
            await db.commit()
        logger.info("memory.initialized", db=str(self.db_path))

    async def save_message(
        self,
        user_id: str,
        role: str,
        content: str,
        agent: str | None = None,
        sources: list[dict[str, Any]] | None = None,
    ) -> None:
        sources_json = json.dumps(sources or [], ensure_ascii=False)
        created_at = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO messages (user_id, role, content, agent, sources, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, role, content, agent, sources_json, created_at),
            )
            await db.commit()

    async def get_history(
        self, user_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT role, content, agent, sources, created_at
                FROM messages
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()

        history: list[dict[str, Any]] = []
        for role, content, agent, sources_json, created_at in reversed(rows):
            history.append(
                {
                    "role": role,
                    "content": content,
                    "agent": agent,
                    "sources": json.loads(sources_json) if sources_json else [],
                    "created_at": created_at,
                }
            )
        return history

    async def format_for_llm(self, user_id: str, limit: int = 10) -> str:
        history = await self.get_history(user_id, limit=limit)
        if not history:
            return ""
        lines = ["Onceki konusmalar:"]
        for msg in history:
            role_label = "Kullanici" if msg["role"] == "user" else "Asistan"
            content = msg["content"][:200]
            lines.append(f"{role_label}: {content}")
        return "\n".join(lines)

    async def clear_user(self, user_id: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM messages WHERE user_id = ?", (user_id,)
            )
            await db.commit()
            count = cursor.rowcount
        logger.info("memory.cleared", user_id=user_id, count=count)
        return count

    async def stats(self) -> dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*), COUNT(DISTINCT user_id) FROM messages"
            ) as cursor:
                total, users = await cursor.fetchone()
        return {"total_messages": total, "unique_users": users}


_memory: ConversationMemory | None = None


async def get_memory() -> ConversationMemory:
    global _memory
    if _memory is None:
        _memory = ConversationMemory()
        await _memory.init()
    return _memory