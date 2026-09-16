"""Ozet cikarma agent'i."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


SUMMARIZER_PROMPT = """Sen bir ozet uzmanisin. Sana verilen uzun metni
kisa, net ve anlasilir sekilde ozetlersin.

Kurallar:
- En fazla 3 madde kullan
- Ana fikirleri koru
- Gereksiz detaylari at
- Turkce, akici bir dil kullan
"""


class SummarizerAgent(BaseAgent):
    """Uzun metinleri ozetleyen agent."""

    def __init__(
        self,
        name: str,
        bus: Any,
        model: str | None = None,
    ) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model=model)

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        try:
            result = self.llm.chat(
                prompt=f"Su metni ozetle:\n\n{message.content}",
                system=SUMMARIZER_PROMPT,
            )
            logger.info("summarizer.done", length=len(result))
            await self.send(
                message.sender,
                {
                    "research": result,
                    "sources": [],
                    "source_count": 0,
                },
                msg_type="result",
            )
        except Exception as e:
            logger.exception("summarizer.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<SummarizerAgent name={self.name!r}>"