"""Arastirma agent'i - web arama + LLM ozetleme (RAG)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient
from tools.web_search import format_results, search

logger = structlog.get_logger(__name__)


RESEARCHER_SYSTEM_PROMPT = """Sen bir arastirmacisin. Sana web arama sonuclari veriliyor.

GOREVIN: Sana verilen arama sonuclarini kullanarak kullanicinin sorusunu cevaplamak.

MUTLAK KURALLAR (HICBIRINI IHLAL ETME):
1. SADECE sana verilen arama sonuclarindaki bilgileri kullan.
2. Kendi ic bilgini KULLANMA. Kendi bildiklerini UNUT.
3. Arama sonuclari senin bildiginle CELISSE BILE, arama sonuclarina GUVEN.
4. "Bu bilgi yok", "bilmiyorum", "henuz oynanmadi", "yeterli bilgi bulamadim" 
   gibi ifadeler KESINLIKLE YASAK.
5. Arama sonuclarinda bilgi VARSA, MUTLAKA onu kullan ve net cevap ver.
6. Eger arama sonuclari gercekten tamamen bos veya hatali ise 
   (bu cok nadirdir), "arama sonuclarinda bilgi bulunamadi" diyebilirsin.
7. Bugunun tarihi: {today}. Bu tarihe kadar olan tum olaylar GERCEKLESMIS olabilir.
   Yani 2024, 2025, 2026 yilinda olmus olaylar GERCEKTIR.
8. Cevabini Turkce ver. Maddeler halinde, net ve kisa.
9. En fazla 5 madde kullan.
10. Cevabin sonunda kaynaklari belirt.

ORNEK DOGRU DAVRANIS:
- Soru: "2026 Dunya Kupasi sampiyonu kim?"
- Arama sonucu: "Ispanya 2026 Dunya Kupasi'nda sampiyon oldu, finalde Arjantin'i 1-0 yendi"
- DOGRU CEVAP: "2026 Dunya Kupasi'ni Ispanya kazandi. Finalde Arjantin'i 1-0 yendi."

ORNEK YANLIS DAVRANIS (YAPMA!):
- "2026 Dunya Kupasi henuz oynanmadi" (YANLIS - senin eski bilgin!)
- "Bu bilgi arama sonuclarinda yok" (YANLIS - varsa kullan!)
"""


class ResearcherAgent(BaseAgent):
    """Web'de arastirir, LLM ile ozetler, kaynaklari doner."""

    def __init__(
        self,
        name: str,
        bus: Any,
        model: str | None = None,
        max_search_results: int = 5,
    ) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model=model)
        self.max_search_results = max_search_results

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        query = str(message.content)
        logger.info("researcher.start", query=query[:80])

        try:
            sources = search(query, max_results=self.max_search_results)
            logger.info("researcher.search_done", count=len(sources))

            if not sources:
                logger.warning("researcher.no_sources")
                fallback = self.llm.chat(
                    prompt=f"Soru: {query}\n\nKisa ve net cevap ver.",
                    system=f"Sen yardimci bir asistansin. Bugun: {datetime.now().strftime('%Y-%m-%d')}. Turkce cevap ver.",
                )
                await self.send(
                    message.sender,
                    {
                        "research": fallback,
                        "sources": [],
                        "query": query,
                        "source_count": 0,
                    },
                    msg_type="result",
                )
                return

            context = format_results(sources)
            today = datetime.now().strftime("%Y-%m-%d")
            system_with_date = RESEARCHER_SYSTEM_PROMPT.replace("{today}", today)

            # Cok net prompt: kendi bilgini unut, sadece arama sonuclarini kullan
            prompt = (
                f"KULLANICI SORUSU: {query}\n\n"
                f"ARAMA SONUCLARI (bugun {today} itibariyle):\n{context}\n\n"
                f"GOREV: Yukaridaki arama sonuclarini kullanarak soruyu cevapla.\n"
                f"KENDI BILGINI KULLANMA. Sadece yukaridaki arama sonuclarina guven.\n"
                f"Arama sonuclarinda cevap VARSA mutlaka kullan.\n"
                f"Cevap:"
            )

            summary = self.llm.chat(prompt=prompt, system=system_with_date)

            await self.send(
                message.sender,
                {
                    "research": summary,
                    "sources": [{"title": s["title"], "url": s["url"]} for s in sources],
                    "query": query,
                    "source_count": len(sources),
                },
                msg_type="result",
            )
            logger.info("researcher.done", sources=len(sources), summary_len=len(summary))

        except Exception as e:
            logger.exception("researcher.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<ResearcherAgent name={self.name!r}>"