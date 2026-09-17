"""Groq tabanli LLM Agent."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


DEFAULT_SYSTEM_PROMPT = """Sen yardimci bir AI asistansin. Turkce, net ve faydali cevaplar verirsin.

Kurallar:
- Soruya dogrudan cevap ver
- Maddeler halinde, oz ve net ol
- Ornek ver (gerekiyorsa)
- En fazla 5 madde kullan
- Gereksiz uzatma
"""


class LLMAgent(BaseAgent):
    """Groq LLM cagrilarini yapan ajan."""

    def __init__(
        self,
        name: str,
        bus: Any,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model=model)
        base_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        today = datetime.now().strftime("%Y-%m-%d")
        self.system_prompt = f"{base_prompt}\n\nBugunun tarihi: {today}"

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        try:
            answer = self.llm.chat(
                prompt=str(message.content),
                system=self.system_prompt,
            )
            logger.info("llm.response", agent=self.name, length=len(answer))
            await self.send(
                message.sender,
                {"answer": answer},
                msg_type="result",
            )
        except Exception as e:
            logger.exception("llm.error", agent=self.name, error=str(e))
            await self.send(
                message.sender,
                {"error": str(e)},
                msg_type="error",
            )

    def __repr__(self) -> str:
        return f"<LLMAgent name={self.name!r} model={self.llm.model}>"