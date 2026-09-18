"""Calculator Agent - matematik agent'i."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from skills.calculator_skill import CalculatorSkill

logger = structlog.get_logger(__name__)


class CalculatorAgent(BaseAgent):
    """Matematik hesaplayan agent."""

    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)
        self.skill = CalculatorSkill()

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return
        try:
            expr = str(message.content)
            # Matematiksel ifadeyi cikar
            for w in ["hesapla", "kac eder", "kaç eder", "sonuc", "sonuç"]:
                expr = expr.replace(w, "")
            expr = expr.strip(" :.,!?")

            result = await self.skill(expression=expr)
            if "error" in result:
                answer = f"Hesaplama hatasi: {result['error']}"
            else:
                answer = f"{result['expression']} = {result['result']}"

            await self.send(message.sender, {"answer": answer}, msg_type="result")
            logger.info("calculator.done", expression=expr[:50])
        except Exception as e:
            logger.exception("calculator.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<CalculatorAgent name={self.name!r}>"
