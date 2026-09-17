"""Arastirma agent'i - web arama + LLM ozetleme."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient
from tools.web_search import search

logger = structlog.get_logger(__name__)


SUMMARY_PROMPT = """Web arama sonuclarindan KISA cevap cikar.

MUTLAK KURALLAR:
- MAKSIMUM 2-3 CUMLE. Asla 4 cumleyi gecme.
- Ilk cumlede dogrudan cevabi ver.
- Detay, tarihce, gerekce YAZMA.
- SADECE kaynaklardaki bilgiyi kullan. Uydurma YAPMA.
- URL, markdown, basli sayilar YAZMA.
- Sayilari ve ozel isimleri oldugu gibi koru.

BAGLAM KONTROLU (KRITIK):
- Soru bir KULUPTEN bahsediyorsa (Al-Nassr, Galatasaray, Real Madrid), o kulubun bilgisini kullan. MILLI TAKIM bilgisini kullanma.
- Soru bir MILLI TAKIMDAN bahsediyorsa (Portekiz, Turkiye), o milli takimin bilgisini kullan. Kulup bilgisini kullanma.
- Ornek: "Ronaldo hangi takimda ve teknik direktoru kim?"
  -> Ronaldo'nun KULUBU (Al-Nassr) ve o kulubun teknik direktoru lazim.
  -> Portekiz milli takimi hocasi DEGIL.
- Ornek: "Ronaldo'nun milli takim teknik direktoru kim?"
  -> Portekiz milli takiminin hocasi lazim.

COKLU BILGI:
- Soruda "ve" varsa, her iki parcayi da cevapla.
- "X kim ve Y nerede" -> iki ayri cumle.

Ornek 1 (tek bilgi):
Soru: Kozan belediye baskani kim?
Kaynaklar: [Mustafa Atli, 2024 MHP]
Cevap: Kozan Belediye Baskani Mustafa Atli'dir.

Ornek 2 (kulup baglami):
Soru: Cristiano Ronaldo hangi takimda ve teknik direktoru kim?
Kaynaklar: [Ronaldo Al-Nassr'da. Al-Nassr teknik direktorluk gorevine Ange Postecoglou getirildi. Portekiz milli takiminin hocasi Jorge Jesus.]
Cevap: Cristiano Ronaldo Al-Nassr'da oynamaktadir. Al-Nassr'in teknik direktoru Ange Postecoglou'dur.

Ornek 3 (milli takim baglami):
Soru: Cristiano Ronaldo'nun milli takim teknik direktoru kim?
Kaynaklar: [Portekiz milli takimi. Jorge Jesus teknik direktor. Al-Nassr'da Ange Postecoglou.]
Cevap: Cristiano Ronaldo'nun milli takim teknik direktoru Jorge Jesus'tur.
"""


class ResearcherAgent(BaseAgent):
    """Web'de arastirir, LLM ile ozetler."""

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
        self.llm = GroqLLMClient() if use_llm_summary else None

    def _enrich_query(self, query: str) -> str:
        """Sorguyu zenginlestirir (yil ekler)."""
        current_year = datetime.now().year
        if any(str(y) in query for y in range(current_year - 2, current_year + 2)):
            return query
        keywords = ["kim", "ne zaman", "guncel", "son", "yeni", "su an", "simdi"]
        if any(k in query.lower() for k in keywords):
            return f"{query} {current_year}"
        return query

    def _summarize_with_llm(self, query: str, sources: list[dict]) -> str:
        """Web sonuclarini LLM ile ozetler."""
        if not self.llm or not sources:
            return ""

        # Kaynaklari birlestir
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

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        query = str(message.content)
        enriched = self._enrich_query(query)
        logger.info("researcher.start", query=query[:80], enriched=enriched[:80])

        try:
            sources = search(enriched, max_results=self.max_search_results)

            if not sources:
                answer = "Bu konuda web'de guvenilir bir sonuc bulunamadi."
            else:
                # LLM ile ozetle
                summary = self._summarize_with_llm(query, sources)

                if summary:
                    answer = summary
                else:
                    # LLM ozetleme basarisizsa ham sonucu goster (eski davranis)
                    today = datetime.now().strftime("%Y-%m-%d")
                    lines = [
                        f"{today} itibariyle web arama sonuclari:",
                        f"Sorgu: {enriched}",
                        "",
                    ]
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
                    "enriched_query": enriched,
                    "source_count": len(sources),
                    "summarized": bool(self.llm and sources),
                },
                msg_type="result",
            )
            logger.info("researcher.done", sources=len(sources), summarized=bool(self.llm))

        except Exception as e:
            logger.exception("researcher.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<ResearcherAgent name={self.name!r} (llm-summary={self.use_llm_summary})>"