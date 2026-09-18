"""Fact Checker Agent - bilgi dogrulama."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient
from tools.web_search import search

logger = structlog.get_logger(__name__)


FACT_CHECK_PROMPT = """Sen bir fact-checker'sin. Verilen iddiayi kaynaklara gore dogrula.

KURALLAR:
- Kaynaklarda iddia DOGRU ise: "DOGRU: <aciklama>"
- Kaynaklarda iddia YANLIS ise: "YANLIS: <dogrusu>"
- Kaynaklarda bilgi yoksa: "DOGRULANAMADI"
- Kisa ve net cevap ver
"""


class FactCheckerAgent(BaseAgent):
    """Bilgi dogrulama yapan agent."""

    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model="openai/gpt-oss-120b")

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return
        try:
            claim = str(message.content)
            # Arama yap
            results = search(claim, max_results=5)
            context = "\n".join(f"- {r['title']}: {r['snippet'][:200]}" for r in results[:5])

            prompt = f"Iddia: {claim}\n\nKaynaklar:\n{context}\n\nDogrulama:"
            answer = self.llm.chat(prompt=prompt, system=FACT_CHECK_PROMPT)

            await self.send(
                message.sender,
                {"answer": answer.strip(), "sources": [{"title": r["title"], "url": r["url"]} for r in results[:5]]},
                msg_type="result",
            )
            logger.info("fact_checker.done")
        except Exception as e:
            logger.exception("fact_checker.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<FactCheckerAgent name={self.name!r}>"
