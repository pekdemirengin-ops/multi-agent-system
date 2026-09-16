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
Bu sonuclari kullanarak kullanicinin sorusunu YANITLAMAK ZORUNDASIN.

ONEMLI KURALLAR:
1. Sana verilen arama sonuclarina KESINLIKLE GUVEN.
2. Kendi ic bilginle celisse bile, arama sonuclarini TEK DOGRU KAYNAK kabul et.
3. ASLA "henuz oynanmadi", "bilmiyorum", "yeterli bilgi bulamadim" DEME.
4. Arama sonuclarinda bilgi varsa, onu kullan ve net bir cevap ver.
5. Bugunun tarihi: {today}. Bu tarihten sonra olan olaylar GERCEKLESMIS olabilir.
6. Cevabini Turkce, maddeler halinde ve net ver.
7. En fazla 5 madde kullan.
8. Kaynaklari referans olarak goster.

Eger arama sonuclari tamamen alakasizsa (ornegin bos veya hata varsa),
o zaman "bu konuda net bir bilgi bulamadim" diyebilirsin. Ama bu cok nadir olmali.
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

            prompt = (
                f"Kullanici sorusu: {query}\n\n"
                f"Web arama sonuclari:\n{context}\n\n"
                f"YUKARIDAKI ARAMA SONUCLARINA GORE soruyu yanitla. "
                f"Arama sonuclari bugun ({today}) itibariyle gunceldir. "
                f"Kendi eski bilgini KULLANMA, sadece arama sonuclarini kullan."
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