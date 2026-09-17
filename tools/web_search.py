"""DuckDuckGo tabanli web arama araci (akilli puanlama)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import structlog
from ddgs import DDGS

logger = structlog.get_logger(__name__)


# Guncel yil
CURRENT_YEAR = datetime.now().year


def search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """DuckDuckGo'da arama yapar. Sonuclari puanlayip siralar."""
    results = _do_search(query, max_results * 2)  # 2x al, sonra filtrele

    # Puanla
    scored = []
    for r in results:
        score = _score_result(r, query)
        scored.append((r, score))

    # Puana gore sirala (yuksek once)
    scored.sort(key=lambda x: x[1], reverse=True)

    # Negatif puanlilari at
    filtered = [r for r, s in scored if s > 0]

    # Yeterli sonuc yoksa hepsini don
    if len(filtered) < max_results:
        filtered = [r for r, _ in scored]

    return filtered[:max_results]


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
    """Sonucu puanlar (yuksek = daha guncel/alakali)."""
    score = 0.0
    text = (result.get("title", "") + " " + result.get("snippet", "") + " " + result.get("url", "")).lower()
    query_lower = query.lower()

    # 1) Sorgu kelimeleri eslesmesi
    query_words = [w for w in query_lower.split() if len(w) > 3]
    for w in query_words:
        if w in text:
            score += 1.0

    # 2) GUNCEL YIL (cok guclu)
    if str(CURRENT_YEAR) in text:  # 2026
        score += 10.0
    elif str(CURRENT_YEAR - 1) in text:  # 2025
        score -= 5.0
    elif str(CURRENT_YEAR - 2) in text:  # 2024
        score -= 8.0

    # 3) Guncel kelimeler
    fresh_kw = ["görevdeki", "mevcut başkan", "şu anki", "yeni başkan", "seçildi", "yeniden başkan"]
    for kw in fresh_kw:
        if kw in text:
            score += 5.0

    # 4) Eski bilgiler (negatif)
    old_kw = ["2025 seçim", "sadettin saran", "ali koç dönemi", "eski başkan"]
    for kw in old_kw:
        if kw in text:
            score -= 8.0

    # 5) Vikipedi "görevdeki" ifadesi
    if "görevdeki" in text:
        score += 5.0

    # 6) Haber siteleri vs blog
    trusted_domains = ["wikipedia.org", "sabah.com.tr", "ntv.com.tr", "aa.com.tr", "cnnturk.com"]
    for d in trusted_domains:
        if d in result.get("url", ""):
            score += 2.0

    # 7) Tarih bilgisi (snippet basinda "Jun 8, 2026" gibi)
    date_match = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2},?\s+(\d{4})", text, re.IGNORECASE)
    if date_match:
        year = int(date_match.group(2))
        if year == CURRENT_YEAR:
            score += 8.0
        elif year == CURRENT_YEAR - 1:
            score -= 3.0

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