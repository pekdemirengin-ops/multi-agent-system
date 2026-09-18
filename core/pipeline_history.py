"""Pipeline gecmisi - PostgreSQL veya SQLite (kalici)."""
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
SQLITE_PATH = DATA_DIR / "pipeline_history.db"
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"


def _use_postgres() -> bool:
    return USE_POSTGRES and bool(DATABASE_URL)


class PipelineHistory:
    """Kalici pipeline gecmisi."""

    def __init__(self) -> None:
        self.db_path = SQLITE_PATH
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
                "CREATE TABLE IF NOT EXISTS pipeline_history ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "pipeline TEXT NOT NULL,"
                "query TEXT NOT NULL,"
                "success INTEGER NOT NULL,"
                "duration_ms INTEGER NOT NULL,"
                "step_count INTEGER NOT NULL,"
                "final_answer TEXT,"
                "error TEXT,"
                "user TEXT,"
                "created_at TEXT NOT NULL)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_pipeline_created "
                "ON pipeline_history(created_at DESC)"
            )
            await db.commit()
        logger.info("pipeline_history.initialized", backend="sqlite")

    async def _init_postgres(self) -> None:
        try:
            import asyncpg
        except ImportError as e:
            logger.error("pipeline_history.asyncpg_missing", error=str(e))
            self.use_postgres = False
            await self._init_sqlite()
            return

        try:
            self._pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "CREATE TABLE IF NOT EXISTS pipeline_history ("
                    "id SERIAL PRIMARY KEY,"
                    "pipeline TEXT NOT NULL,"
                    "query TEXT NOT NULL,"
                    "success BOOLEAN NOT NULL,"
                    "duration_ms INTEGER NOT NULL,"
                    "step_count INTEGER NOT NULL,"
                    "final_answer TEXT,"
                    "error TEXT,"
                    "user_id TEXT,"
                    "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
                )
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_pipeline_created "
                    "ON pipeline_history(created_at DESC)"
                )
            logger.info("pipeline_history.initialized", backend="postgres")
        except Exception as e:
            logger.exception("pipeline_history.postgres_init_failed", error=str(e))
            self.use_postgres = False
            await self._init_sqlite()

    async def add(
        self,
        pipeline_name: str,
        query: str,
        success: bool,
        duration_ms: int,
        step_count: int,
        final_answer: str = "",
        error: str | None = None,
        user: str = "anonymous",
    ) -> dict[str, Any]:
        """Yeni kayit ekler."""
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "INSERT INTO pipeline_history "
                    "(pipeline, query, success, duration_ms, step_count, final_answer, error, user_id) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id, created_at",
                    pipeline_name, query[:500], success, duration_ms,
                    step_count, final_answer[:2000] if final_answer else "",
                    error, user,
                )
            entry_id = row["id"]
            created_at = row["created_at"].isoformat()
        else:
            created_at = datetime.now(timezone.utc).isoformat()
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "INSERT INTO pipeline_history "
                    "(pipeline, query, success, duration_ms, step_count, final_answer, error, user, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (pipeline_name, query[:500], int(success), duration_ms,
                     step_count, final_answer[:2000] if final_answer else "",
                     error, user, created_at),
                )
                await db.commit()
                entry_id = cursor.lastrowid

        logger.info("pipeline_history.added",
                    id=entry_id, pipeline=pipeline_name, success=success)

        return {
            "id": entry_id,
            "pipeline": pipeline_name,
            "query": query[:200],
            "success": success,
            "duration_ms": duration_ms,
            "step_count": step_count,
            "final_answer": final_answer[:500] if final_answer else "",
            "error": error,
            "user": user,
            "timestamp": created_at,
        }

    async def get(self, limit: int = 20, user: str | None = None) -> list[dict[str, Any]]:
        """Gecmisi doner (en yeni once)."""
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                if user and user != "anonymous":
                    rows = await conn.fetch(
                        "SELECT id, pipeline, query, success, duration_ms, "
                        "step_count, final_answer, error, user_id, created_at "
                        "FROM pipeline_history WHERE user_id = $1 "
                        "ORDER BY id DESC LIMIT $2",
                        user, limit,
                    )
                else:
                    rows = await conn.fetch(
                        "SELECT id, pipeline, query, success, duration_ms, "
                        "step_count, final_answer, error, user_id, created_at "
                        "FROM pipeline_history ORDER BY id DESC LIMIT $1",
                        limit,
                    )
            return [
                {
                    "id": r["id"],
                    "pipeline": r["pipeline"],
                    "query": r["query"],
                    "success": bool(r["success"]),
                    "duration_ms": r["duration_ms"],
                    "step_count": r["step_count"],
                    "final_answer": r["final_answer"] or "",
                    "error": r["error"],
                    "user": r["user_id"] or "anonymous",
                    "timestamp": r["created_at"].isoformat() if r["created_at"] else "",
                }
                for r in rows
            ]
        else:
            async with aiosqlite.connect(self.db_path) as db:
                if user and user != "anonymous":
                    cursor = await db.execute(
                        "SELECT id, pipeline, query, success, duration_ms, "
                        "step_count, final_answer, error, user, created_at "
                        "FROM pipeline_history WHERE user = ? "
                        "ORDER BY id DESC LIMIT ?",
                        (user, limit),
                    )
                else:
                    cursor = await db.execute(
                        "SELECT id, pipeline, query, success, duration_ms, "
                        "step_count, final_answer, error, user, created_at "
                        "FROM pipeline_history ORDER BY id DESC LIMIT ?",
                        (limit,),
                    )
                rows = await cursor.fetchall()

            return [
                {
                    "id": r[0], "pipeline": r[1], "query": r[2],
                    "success": bool(r[3]), "duration_ms": r[4],
                    "step_count": r[5], "final_answer": r[6] or "",
                    "error": r[7], "user": r[8] or "anonymous",
                    "timestamp": r[9],
                }
                for r in rows
            ]

    async def stats(self) -> dict[str, Any]:
        """Istatistikler."""
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                total = await conn.fetchval("SELECT COUNT(*) FROM pipeline_history")
                success = await conn.fetchval(
                    "SELECT COUNT(*) FROM pipeline_history WHERE success = TRUE"
                )
                by_pipeline = await conn.fetch(
                    "SELECT pipeline, COUNT(*) as c FROM pipeline_history "
                    "GROUP BY pipeline ORDER BY c DESC"
                )
            return {
                "total": total,
                "success": success,
                "failed": total - success,
                "success_rate": round(success / total * 100, 1) if total > 0 else 0.0,
                "by_pipeline": {r["pipeline"]: r["c"] for r in by_pipeline},
            }
        else:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT COUNT(*) FROM pipeline_history") as c:
                    total = (await c.fetchone())[0]
                async with db.execute(
                    "SELECT COUNT(*) FROM pipeline_history WHERE success = 1"
                ) as c:
                    success = (await c.fetchone())[0]
                async with db.execute(
                    "SELECT pipeline, COUNT(*) FROM pipeline_history "
                    "GROUP BY pipeline ORDER BY COUNT(*) DESC"
                ) as c:
                    by_pipeline = {r[0]: r[1] for r in await c.fetchall()}
            return {
                "total": total,
                "success": success,
                "failed": total - success,
                "success_rate": round(success / total * 100, 1) if total > 0 else 0.0,
                "by_pipeline": by_pipeline,
            }

    async def clear(self) -> int:
        """Tum gecmisi siler."""
        if self.use_postgres:
            async with self._pool.acquire() as conn:
                result = await conn.execute("DELETE FROM pipeline_history")
            count = int(result.split()[-1]) if result else 0
        else:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("DELETE FROM pipeline_history")
                await db.commit()
                count = cursor.rowcount
        logger.info("pipeline_history.cleared", count=count)
        return count

    def backend_name(self) -> str:
        return "postgresql" if self.use_postgres else "sqlite"


# Singleton
_history: PipelineHistory | None = None


async def get_history_store() -> PipelineHistory:
    """Singleton history store."""
    global _history
    if _history is None:
        _history = PipelineHistory()
        await _history.init()
    return _history


# Kolaylik icin async wrapper'lar
async def add_result(**kwargs) -> dict[str, Any]:
    store = await get_history_store()
    return await store.add(**kwargs)


async def get_history(limit: int = 20, user: str | None = None) -> list[dict[str, Any]]:
    store = await get_history_store()
    return await store.get(limit=limit, user=user)


async def get_stats() -> dict[str, Any]:
    store = await get_history_store()
    return await store.stats()


async def clear_history() -> int:
    store = await get_history_store()
    return await store.clear()
