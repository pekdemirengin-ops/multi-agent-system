"""DuckDuckGo tabanli web arama araci (ddgs paketi)."""
from __future__ import annotations

from typing import Any

import structlog
from ddgs import DDGS

logger = structlog.get_logger(__name__)


# Arama stratejileri (sirali denenecek)
SEARCH_BACKENDS = ["auto", "google", "bing", "duckduckgo"]


def search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """DuckDuckGo'da arama yapar. Birden fazla strateji dener."""
    results: list[dict[str, Any]] = []

    # 1) Direkt Turkce arama
    results = _do_search(query, max_results)
    if _has_good_results(results, query):
        return results

    # 2) Ingilizce cevirerek dene
    english_query = _translate_query(query)
    if english_query != query:
        logger.info("web_search.english_fallback", english_query=english_query)
        eng_results = _do_search(english_query, max_results)
        if _has_good_results(eng_results, english_query):
            return eng_results

    # 3) Sonuc yoksa mevcut sonuclari dondur
    return results


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


def _has_good_results(results: list[dict[str, Any]], query: str) -> bool:
    """Sonuclarin sorguyla alakali olup olmadigini kontrol eder."""
    if not results:
        return False

    # Sorgudaki anahtar kelimeler
    query_words = [w.lower() for w in query.split() if len(w) > 3]
    if not query_words:
        return True

    # En az 1 anahtar kelime sonuclarda gecmeli
    for r in results:
        text = (r.get("title", "") + " " + r.get("snippet", "")).lower()
        for w in query_words:
            if w in text:
                return True

    logger.warning("web_search.irrelevant_results", query=query[:50])
    return False


def _translate_query(query: str) -> str:
    """Basit Turkce->Ingilizce ceviri (anahtar kelimeler)."""
    translations = {
        "dunya kupasi": "World Cup",
        "sampiyonu": "champion winner",
        "kim": "who",
        "ne zaman": "when",
        "nedir": "what is",
        "nobel": "Nobel",
        "odulu": "Prize",
        "2026": "2026",
        "2025": "2025",
        "2024": "2024",
    }
    english = query.lower()
    for tr, en in translations.items():
        english = english.replace(tr, en)
    return english.strip()


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
    # Test
    for test_query in [
        "2026 Dunya Kupasi sampiyonu kim?",
        "Python nedir?",
        "2024 Nobel Odulu kime verildi?",
    ]:
        print(f"\n=== {test_query} ===")
        res = search(test_query, max_results=3)
        for r in res:
            print(f"  - {r['title']}")