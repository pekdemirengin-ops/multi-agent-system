"""Görev planlayıcı agent — karmaşık görevleri alt adımlara böler."""
from __future__ import annotations

import json
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


PLANNER_SYSTEM_PROMPT = """Sen bir gorev planlayicisisin. Kullanicinin verdigi gorevi
alt adimlara bolersin. Her adim icin hangi agent'in gorev alacagini belirtirsin.

Kullanilabilir agent'lar:
- researcher: bilgi toplar, arastirir
- coder: kod yazar
- reviewer: kodu/cevabi inceler
- summarizer: ozet cikarir

Sadece su JSON formatinda cevap ver, baska hicbir sey yazma:
{
  "steps": [
    {"agent": "researcher", "task": "..."},
    {"agent": "summarizer", "task": "..."}
  ]
}
"""


class PlannerAgent(BaseAgent):
    """Gorevi alt adimlara bolen agent."""

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
            raw = self.llm.chat(
                prompt=f"Su gorevi planla: {message.content}",
                system=PLANNER_SYSTEM_PROMPT,
            )
            plan = self._parse_plan(raw)
            logger.info("planner.plan_created", steps=len(plan.get("steps", [])))
            await self.send(
                message.sender,
                {"plan": plan, "raw": raw},
                msg_type="result",
            )
        except Exception as e:
            logger.exception("planner.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def _parse_plan(self, raw: str) -> dict:
        """LLM ciktisindan JSON plan cikarir; code fence varsa temizler."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("planner.json_parse_failed", raw=raw[:200])
            return {"steps": [], "raw": raw}

    def __repr__(self) -> str:
        return f"<PlannerAgent name={self.name!r}>"