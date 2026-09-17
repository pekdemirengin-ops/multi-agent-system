"""Arastirma agent'i - web arama + akilli sorgu."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.web_search import format_results, search

logger = structlog.get_logger(__name__)


class ResearcherAgent(BaseAgent):
    """Web'de arastirir, sonuclari formatlar, LLM KULLANMAZ."""

    def __init__(
        self,
        name: str,
        bus: Any,
        max_search_results: int = 5,
    ) -> None:
        super().__init__(name, bus)
        self.max_search_results = max_search_results

    def _enrich_query(self, query: str) -> str:
        """Sorguyu zenginlestirir (yil ekler)."""
        current_year = datetime.now().year
        # Sorguda zaten yil var mi?
        if any(str(y) in query for y in range(current_year - 2, current_year + 2)):
            return query
        # "kim", "ne zaman", "guncel" varsa yil ekle
        keywords = ["kim", "ne zaman", "guncel", "son", "yeni", "su an", "simdi"]
        if any(k in query.lower() for k in keywords):
            return f"{query} {current_year}"
        return query

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        query = str(message.content)
        enriched = self._enrich_query(query)
        logger.info("researcher.start", query=query[:80], enriched=enriched[:80])

        try:
            sources = search(enriched, max_results=self.max_search_results)

            if not sources:
                answer = "Bu konuda web'de sonuc bulunamadi."
            else:
                today = datetime.now().strftime("%Y-%m-%d")
                lines = [
                    f"**{today} itibariyle web arama sonuclari:**",
                    f"**Sorgu:** {enriched}",
                    "",
                ]
                for i, s in enumerate(sources, 1):
                    lines.append(f"**{i}. {s['title']}**")
                    lines.append(f"   URL: {s['url']}")
                    lines.append(f"   {s['snippet']}")
                    lines.append("")

                answer = "\n".join(lines)

            await self.send(
                message.sender,
                {
                    "research": answer,
                    "sources": [{"title": s["title"], "url": s["url"]} for s in sources],
                    "query": query,
                    "enriched_query": enriched,
                    "source_count": len(sources),
                },
                msg_type="result",
            )
            logger.info("researcher.done", sources=len(sources))

        except Exception as e:
            logger.exception("researcher.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<ResearcherAgent name={self.name!r} (no-llm, smart-query)>"