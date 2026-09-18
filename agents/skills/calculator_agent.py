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
            import re
            raw = str(message.content)

            # Sadece matematiksel ifadeyi bul (rakam, operator)
            # "2 + 3 * 4 hesapla" -> "2 + 3 * 4"
            math_pattern = r"[0-9]+(?:\s*[+\-*/^()]+\s*[0-9]+)+"
            matches = re.findall(math_pattern, raw)

            if matches:
                expr = max(matches, key=len).strip()
            else:
                # Alternatif: rakam ve operatorleri topla
                cleaned = re.sub(r"[^0-9+\-*/().^\s]", " ", raw)
                cleaned = re.sub(r"\s+", " ", cleaned).strip()
                expr = cleaned

            if not expr:
                await self.send(message.sender, {"answer": "Matematiksel ifade bulunamadi."}, msg_type="result")
                return

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
