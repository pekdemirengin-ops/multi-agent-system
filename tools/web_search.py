"""DuckDuckGo tabanli web arama araci (ddgs paketi)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import structlog
from ddgs import DDGS

logger = structlog.get_logger(__name__)


def search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """DuckDuckGo'da arama yapar. Sonuclari onem sirasina gore dondurur."""
    results = _do_search(query, max_results)

    # Sonuclari puanla (tarih + anahtar kelime)
    scored = [(r, _score_result(r, query)) for r in results]
    scored.sort(key=lambda x: x[1], reverse=True)

    return [r for r, _ in scored]


def _do_search(query: str, max_results: int) -> list[dict[str, Any]]:
    """Tek bir arama yapar."""
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


def _score_result(result: dict[str, Any], query: str) -> float:
    """Sonucu puanlar (yuksek = daha alakali/guncel)."""
    score = 0.0
    text = (result.get("title", "") + " " + result.get("snippet", "")).lower()
    query_lower = query.lower()

    # 1) Sorgu kelimeleri eslesmesi
    query_words = [w for w in query_lower.split() if len(w) > 3]
    for w in query_words:
        if w in text:
            score += 1.0

    # 2) Guncel yil eslesmesi (2026 > 2025 > 2024)
    current_year = datetime.now().year
    for year_offset in range(0, 4):
        year = current_year - year_offset
        if str(year) in text:
            score += (4 - year_offset) * 2.0
            break

    # 3) "Yeni", "son", "seçildi" gibi guncel kelimeler
    fresh_keywords = ["yeni", "son", "seçildi", "seçim", "2026", "guncel", "şu an"]
    for kw in fresh_keywords:
        if kw in text:
            score += 1.5

    # 4) Eski yillar (2024 ve oncesi) -> puan dusur
    for old_year in ["2023", "2022", "2021", "2020"]:
        if old_year in text:
            score -= 2.0

    return score


def format_results(results: list[dict[str, Any]]) -> str:
    """Arama sonuclarini LLM'e verilecek metne cevirir."""
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
    for test_query in [
        "Fenerbahce baskani kim?",
        "2026 Dunya Kupasi sampiyonu kim?",
        "Python nedir?",
    ]:
        print(f"\n=== {test_query} ===")
        res = search(test_query, max_results=3)
        for r in res:
            print(f"  - {r['title']}")
            print(f"    {r['snippet'][:100]}")