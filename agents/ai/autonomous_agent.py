"""Autonomous Agent - hedef verilir, kendi planlar ve calistirir."""
from __future__ import annotations

from typing import Any

import structlog

from core.autonomous import AutonomousEngine, AutonomousResult
from core.base_agent import BaseAgent, Message

logger = structlog.get_logger(__name__)


class AutonomousAgent(BaseAgent):
    """Hedefi planlar ve adim adim calistirir."""

    def __init__(self, name: str, bus: Any, agents: dict | None = None) -> None:
        super().__init__(name, bus)
        self._agents_ref = agents

    def _get_agents(self) -> dict:
        """Agent referansini alir (lazy - circular import onlemek icin)."""
        if self._agents_ref:
            return self._agents_ref
        # api.routes.agents'dan al
        try:
            from api.routes.agents import _agents
            return _agents
        except Exception:
            return {}

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        goal = str(message.content)
        logger.info("autonomous_agent.start", goal=goal[:100])

        try:
            agents = self._get_agents()
            if not agents:
                await self.send(
                    message.sender,
                    {"error": "Agent'lar hazir degil"},
                    msg_type="error",
                )
                return

            engine = AutonomousEngine(agents=agents, timeout=60)
            result: AutonomousResult = await engine.execute(goal)

            if result.success:
                await self.send(
                    message.sender,
                    {
                        "answer": result.final_report,
                        "goal_summary": result.goal_summary,
                        "report_title": result.report_title,
                        "steps": [
                            {
                                "step": s.step,
                                "query": s.query,
                                "agent": s.agent,
                                "status": s.status,
                                "duration_ms": s.duration_ms,
                            }
                            for s in result.steps
                        ],
                        "duration_ms": result.duration_ms,
                    },
                    msg_type="result",
                )
                logger.info("autonomous_agent.done",
                            steps=len(result.steps),
                            duration_ms=result.duration_ms)
            else:
                await self.send(
                    message.sender,
                    {"error": result.error or "Autonomous calistirma basarisiz"},
                    msg_type="error",
                )

        except Exception as e:
            logger.exception("autonomous_agent.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<AutonomousAgent name={self.name!r}>"
