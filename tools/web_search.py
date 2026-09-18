"""Web arama - Tavily API (keyless + keyed mode)."""
from __future__ import annotations

import os
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


def search_with_answer(query: str, max_results: int = 5) -> dict[str, Any]:
    """Tavily ile arama + dogrudan cevap doner."""
    try:
        from tavily import TavilyClient

        if TAVILY_API_KEY and not TAVILY_API_KEY.startswith("keyless"):
            client = TavilyClient(api_key=TAVILY_API_KEY)
        else:
            client = TavilyClient()

        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
            include_answer=True,
        )

        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
                "score": r.get("score", 0),
            })

        logger.info("web_search.done", count=len(results), query=query[:50])

        return {
            "results": results,
            "answer": response.get("answer", ""),
        }

    except Exception as e:
        logger.exception("web_search.error", error=str(e))
        return {"results": [], "answer": ""}


def search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Geriye uyumlu: sadece sonuclari doner."""
    result = search_with_answer(query, max_results)
    return result["results"]


def format_results(results: list[dict[str, Any]]) -> str:
    """Sonuclari formatlar (URL dahil)."""
    if not results:
        return "Sonuc bulunamadi."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   {r.get('url', '')}")  # URL EKLENDI
        lines.append(f"   {r['snippet']}")
        lines.append("")
    return "\n".join(lines)
