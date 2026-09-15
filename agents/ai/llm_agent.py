"""Groq tabanlı LLM Agent."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


class LLMAgent(BaseAgent):
    """Groq LLM çağrılarını yapan ajan.

    Mesaj alır → LLM'e gönderir → sonucu gönderene döner.
    """

    def __init__(
        self,
        name: str,
        bus: Any,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model=model)
        self.system_prompt = system_prompt or "Sen yardımcı bir asistansın."

    async def handle(self, message: Message) -> None:
        """Mesajı LLM'e gönderir, yanıtı gönderene döner."""
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