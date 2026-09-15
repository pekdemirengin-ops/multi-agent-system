"""DuckDuckGo tabanli web arama araci (ddgs paketi)."""
from __future__ import annotations

from typing import Any

import structlog
from ddgs import DDGS

logger = structlog.get_logger(__name__)


def search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """DuckDuckGo'da arama yapar.

    Args:
        query: Arama sorgusu
        max_results: Maksimum sonuç sayısı (1-10)

    Returns:
        [{"title": str, "url": str, "snippet": str}, ...]
    """
    results: list[dict[str, Any]] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    }
                )
        logger.info("web_search.done", query=query[:50], count=len(results))
    except Exception as e:
        logger.exception("web_search.error", query=query, error=str(e))
    return results


def format_results(results: list[dict[str, Any]]) -> str:
    """Arama sonuçlarını LLM'e verilecek metne çevirir."""
    if not results:
        return "(Sonuc bulunamadi)"
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   URL: {r['url']}")
        lines.append(f"   {r['snippet']}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    res = search("Python asyncio nedir", max_results=3)
    print(format_results(res))