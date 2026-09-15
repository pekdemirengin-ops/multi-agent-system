"""Arastirma agent'i — bir konu hakkinda bilgi toplar ve ozetler."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


RESEARCHER_SYSTEM_PROMPT = """Sen bir arastirmacisin. Verilen konu hakkinda
kapsamli ama ozlu bilgi toplarsin. Bilimsel, tarafsiz ve maddeler halinde yanit verirsin.
En fazla 5 madde kullan.
"""


class ResearcherAgent(BaseAgent):
    """Konu hakkinda bilgi toplayan ve ozetleyen agent."""

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
                prompt=f"Su konuyu arastir ve ozetle: {message.content}",
                system=RESEARCHER_SYSTEM_PROMPT,
            )
            logger.info("researcher.done", length=len(result))
            await self.send(
                message.sender,
                {"research": result},
                msg_type="result",
            )
        except Exception as e:
            logger.exception("researcher.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<ResearcherAgent name={self.name!r}>"