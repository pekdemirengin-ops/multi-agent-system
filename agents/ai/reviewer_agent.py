"""Kod inceleme agent'i."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


REVIEWER_PROMPT = """Sen deneyimli bir kod inceleyicisisin. Sana verilen kodu
incelersin, hatalari, performans sorunlarini ve iyilestirme firsatlarini belirtirsin.

Kurallar:
- Kisa ve net geri bildirim ver
- En fazla 5 madde kullan
- Kritik hatalari oncelikli belirt
- Iyilestirme onerileri sun
"""


class ReviewerAgent(BaseAgent):
    """Kod veya cevap inceleyen agent."""

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
                prompt=f"Su kodu/cevabi incele:\n\n{message.content}",
                system=REVIEWER_PROMPT,
            )
            logger.info("reviewer.done", length=len(result))
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
            logger.exception("reviewer.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<ReviewerAgent name={self.name!r}>"