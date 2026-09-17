"""Arastirma agent'i - coklu arama + baglam + LLM ozetleme."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient
from tools.web_search import search

logger = structlog.get_logger(__name__)


# ============================================================
# Sistem promptu - "uzman arastirmaci" gibi dusun
# ============================================================
SUMMARY_PROMPT = """Sen uzman bir arastirma asistanisin. Web arama sonuclarindan
EKSIKSIZ, HIZLI ve DOGRU cevap vereceksin.

ADIM ADIM DUSUN (kafandan, cevaba yazma):

ADIM 1: Soruyu parcala
- "Ronaldo kim, hangi takim, hoca kim" = 3 bilgi
- Her bilgi icin ayri dusun

ADIM 2: Her parca icin kaynaga bak
- Kaynaklari TEK TEK oku
- Her parca icin EN ACIK kaynagi bul
- Ornek: "Al-Nassr teknik direktoru" -> Transfermarkt'ta "Ange Postecoglou" yaziyor

ADIM 3: Cevabi yaz
- Her parca icin ayri cumle
- MAKSIMUM 4 cumle
- SADECE kaynaktaki bilgi
- UYDURMA YOK

MUTLAK KURALLAR:
- Sorudaki HER parca icin cevap ver
- Kaynaklarda olan bilgiyi ATLAMA (ornek: Al-Nassr, Postecoglou)
- Kaynaklarda OLMAYAN bilgiyi YAZMA (ornek: forma numarasi)
- Baglam: "Ronaldo'nun kulubu" -> Al-Nassr. "Portekiz milli takimi" -> ayri.
- Bilgi yoksa: "X bilgisi kaynaklarda yer almamaktadir"

ORNEK (dogru):
Soru: Cristiano Ronaldo kim, hangi takimda, hoca kim?
Kaynaklar:
  1. "Ronaldo 1985 Portekiz, Al-Nassr forvet"
  2. "Al-Nassr hocasi Ange Postecoglou, 3 Temmuz 2026"
Cevap: Cristiano Ronaldo, 1985 dogumlu Portekizli forvet oyuncusudur. Al-Nassr kulubunde oynamaktadir. Al-Nassr'in teknik direktoru Ange Postecoglou'dur.

ORNEK (yanlis - yapma):
Cevap: Ronaldo Portekiz milli takiminda 0 numarali formayi giyiyor. 
   ^^^ YANLIS: milli takim degil, kulup soruluyor. 0 numara UYDURMA.

Simdi sen cevapla:"""


class ResearcherAgent(BaseAgent):
    """Web'de arastirir, coklu arama yapar, LLM ile ozetler."""

    def __init__(
        self,
        name: str,
        bus: Any,
        max_search_results: int = 5,
        use_llm_summary: bool = True,
    ) -> None:
        super().__init__(name, bus)
        self.max_search_results = max_search_results
        self.use_llm_summary = use_llm_summary
        self.llm = GroqLLMClient(model="llama-3.1-8b-instant") if use_llm_summary else None

    def _split_query(self, query: str) -> list[str]:
        """Soruyu alt sorulara boler. 've' ile ayrilanlari ayirir."""
        lower = query.lower()
        parts = []
        # " ve " ile bol
        if " ve " in lower:
            raw_parts = re.split(r"\s+ve\s+", query, flags=re.IGNORECASE)
            parts = [p.strip() for p in raw_parts if p.strip()]
        # " , " ile bol (virgul + ve olmadan)
        elif query.count(",") >= 1:
            raw_parts = [p.strip() for p in query.split(",") if p.strip()]
            if len(raw_parts) >= 2:
                parts = raw_parts
        else:
            parts = [query]

        # 1'den azsa, ana sorgu
        if len(parts) < 2:
            return [query]

        # Son parcaya baglam ekle (ilk parcanin konusu)
        # Ornek: "Ronaldo kim, hangi takimda, hoca kim" -> 3 parca
        # Ilk parcayi referans olarak kullan
        return parts

    def _enrich_query(self, query: str) -> str:
        """Yil ekler (guncel bilgi icin)."""
        current_year = datetime.now().year
        if any(str(y) in query for y in range(current_year - 2, current_year + 2)):
            return query
        keywords = ["kim", "ne zaman", "guncel", "son", "yeni", "su an", "simdi"]
        if any(k in query.lower() for k in keywords):
            return f"{query} {current_year}"
        return query

    def _summarize_with_llm(self, query: str, sources: list) -> str:
        """Kaynaklari LLM ile ozetler."""
        if not self.llm or not sources:
            return ""
        context_lines = []
        for i, s in enumerate(sources, 1):
            context_lines.append(f"Kaynak {i}: {s['title']}")
            context_lines.append(f"Icerik: {s['snippet']}")
            context_lines.append("")
        context = "\n".join(context_lines)
        prompt = f"Soru: {query}\n\nKaynaklar:\n{context}\n\nCevap:"
        try:
            answer = self.llm.chat(prompt=prompt, system=SUMMARY_PROMPT)
            return answer.strip()
        except Exception as e:
            logger.exception("researcher.summary_failed", error=str(e))
            return ""

    def _collect_sources(self, query: str) -> tuple[list[dict], int]:
        """Tek veya coklu arama yapar, kaynaklari doner."""
        sub_queries = self._split_query(query)
        all_sources = []

        if len(sub_queries) > 1:
            logger.info("researcher.multi_search", count=len(sub_queries), queries=sub_queries)
            # Her alt soru icin ayri arama
            for sq in sub_queries:
                enriched = self._enrich_query(sq)
                found = search(enriched, max_results=3)
                all_sources.extend(found)
        else:
            enriched = self._enrich_query(query)
            all_sources = search(enriched, max_results=self.max_search_results)

        # Tekrarlari temizle (URL bazli)
        seen_urls = set()
        unique_sources = []
        for s in all_sources:
            if s["url"] not in seen_urls:
                seen_urls.add(s["url"])
                unique_sources.append(s)

        # Max 8 kaynak
        return unique_sources[:8], len(sub_queries)

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        query = str(message.content)
        logger.info("researcher.start", query=query[:80])

        try:
            sources, sub_count = self._collect_sources(query)

            if not sources:
                answer = "Bu konuda web'de guvenilir bir sonuc bulunamadi."
            else:
                summary = self._summarize_with_llm(query, sources)
                if summary:
                    answer = summary
                else:
                    # LLM yoksa ham sonuc
                    today = datetime.now().strftime("%Y-%m-%d")
                    lines = [f"{today} itibariyle web arama sonuclari:", f"Sorgu: {query}", ""]
                    for i, s in enumerate(sources, 1):
                        lines.append(f"{i}. {s['title']}")
                        lines.append(f"   {s['snippet']}")
                        lines.append("")
                    answer = "\n".join(lines)

            await self.send(
                message.sender,
                {
                    "answer": answer,
                    "research": answer,
                    "sources": [{"title": s["title"], "url": s["url"]} for s in sources],
                    "query": query,
                    "source_count": len(sources),
                    "summarized": bool(self.llm and sources),
                    "multi_search": sub_count > 1,
                },
                msg_type="result",
            )
            logger.info("researcher.done", sources=len(sources), multi_search=sub_count > 1)

        except Exception as e:
            logger.exception("researcher.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<ResearcherAgent name={self.name!r} (multi-search, llm-summary)>"