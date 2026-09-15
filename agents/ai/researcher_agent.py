"""Arastirma agent'i — web arama + LLM ozetleme (RAG)."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient
from tools.web_search import format_results, search

logger = structlog.get_logger(__name__)


RESEARCHER_SYSTEM_PROMPT = """Sen bir arastirmacisin. Sana verilen web arama
sonuclarini kullanarak kullanicinin sorusunu yanitlarsin.

Kurallar:
- Sadece sana verilen kaynaklardaki bilgileri kullan
- Bilgi yoksa "Bu konuda yeterli bilgi bulamadim" de
- Maddeler halinde, oz ve net yanit ver
- En fazla 5 madde
"""


class ResearcherAgent(BaseAgent):
    """Web'de arastirir, LLM ile ozetler, kaynaklari ile birlikte dondurur."""

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
            # 1) Web'de ara
            sources = search(query, max_results=self.max_search_results)

            if not sources:
                logger.warning("researcher.no_sources", query=query[:80])
                await self.send(
                    message.sender,
                    {
                        "research": "Bu konuda web'de sonuc bulunamadi.",
                        "sources": [],
                        "query": query,
                    },
                    msg_type="result",
                )
                return

            # 2) Sonuclari LLM'e ver, ozetlettir
            context = format_results(sources)
            prompt = (
                f"Kullanici sorusu: {query}\n\n"
                f"Web arama sonuclari:\n{context}\n\n"
                f"Bu kaynaklara dayanarak soruyu yanitla."
            )

            summary = self.llm.chat(prompt=prompt, system=RESEARCHER_SYSTEM_PROMPT)

            # 3) Cevabi + kaynaklari dondur
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
            logger.info(
                "researcher.done",
                query=query[:50],
                sources=len(sources),
                summary_len=len(summary),
            )

        except Exception as e:
            logger.exception("researcher.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<ResearcherAgent name={self.name!r}>"