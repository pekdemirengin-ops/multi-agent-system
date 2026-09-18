"""Pipeline gecmisi - bellek ici son 50 calistirma."""
from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Son 50 calistirmayi tut (FIFO)
_history: deque[dict[str, Any]] = deque(maxlen=50)


def add_result(
    pipeline_name: str,
    query: str,
    success: bool,
    duration_ms: int,
    step_count: int,
    final_answer: str = "",
    error: str | None = None,
    user: str = "anonymous",
) -> dict[str, Any]:
    """Pipeline sonucunu gecmise ekler."""
    entry = {
        "id": len(_history) + 1,
        "pipeline": pipeline_name,
        "query": query[:200],
        "success": success,
        "duration_ms": duration_ms,
        "step_count": step_count,
        "final_answer": final_answer[:500] if final_answer else "",
        "error": error,
        "user": user,
        "timestamp": datetime.now().isoformat(),
    }
    _history.append(entry)
    logger.info("pipeline.history_added",
                pipeline=pipeline_name,
                success=success,
                total=len(_history))
    return entry


def get_history(limit: int = 20, user: str | None = None) -> list[dict[str, Any]]:
    """Gecmisi doner (en yeni once)."""
    items = list(_history)
    if user:
        items = [i for i in items if i.get("user") == user]
    # En yeni once
    items.reverse()
    return items[:limit]


def get_stats() -> dict[str, Any]:
    """Gecmis istatistikleri."""
    if not _history:
        return {
            "total": 0,
            "success": 0,
            "failed": 0,
            "success_rate": 0.0,
            "by_pipeline": {},
        }

    total = len(_history)
    success = sum(1 for i in _history if i["success"])
    failed = total - success

    by_pipeline: dict[str, int] = {}
    for i in _history:
        p = i["pipeline"]
        by_pipeline[p] = by_pipeline.get(p, 0) + 1

    return {
        "total": total,
        "success": success,
        "failed": failed,
        "success_rate": round(success / total * 100, 1) if total > 0 else 0.0,
        "by_pipeline": by_pipeline,
    }


def clear_history() -> int:
    """Gecmisi temizler."""
    count = len(_history)
    _history.clear()
    logger.info("pipeline.history_cleared", count=count)
    return count
