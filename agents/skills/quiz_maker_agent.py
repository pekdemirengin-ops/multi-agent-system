"""Quiz Maker Agent - test/quiz uretimi."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


QUIZ_PROMPT = """Sen bir quiz hazirlayicisisin. Verilen konu hakkinda 5 soruluk test hazirla.

FORMAT:
1. Soru?
   A) ...
   B) ...
   C) ...
   D) ...
   Dogru: X

2. Soru?
   ...

KURALLAR:
- Her soru 4 secenekli
- Dogru cevap belirt
- Kisa ve net
"""


class QuizMakerAgent(BaseAgent):
    """Quiz ureten agent."""

    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model="openai/gpt-oss-120b")

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return
        try:
            topic = str(message.content)
            answer = self.llm.chat(prompt=f"Konu: {topic}", system=QUIZ_PROMPT)
            await self.send(message.sender, {"answer": answer.strip()}, msg_type="result")
            logger.info("quiz_maker.done", topic=topic[:50])
        except Exception as e:
            logger.exception("quiz_maker.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<QuizMakerAgent name={self.name!r}>"
