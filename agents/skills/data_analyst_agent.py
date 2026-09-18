"""Data Analyst Agent - veri analizi."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


ANALYST_PROMPT = """Sen bir veri analistisin. Kullanicinin veri sorusunu yanitla.

KURALLAR:
- Sayilarla konus
- Oranlari ve yuzdeleri hesapla
- Kisa ve net ol
- Gereksiz detaya girme
"""


class DataAnalystAgent(BaseAgent):
    """Veri analizi yapan agent."""

    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model="openai/gpt-oss-120b")

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return
        try:
            query = str(message.content)
            answer = self.llm.chat(prompt=query, system=ANALYST_PROMPT)
            await self.send(message.sender, {"answer": answer.strip()}, msg_type="result")
            logger.info("data_analyst.done")
        except Exception as e:
            logger.exception("data_analyst.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<DataAnalystAgent name={self.name!r}>"
