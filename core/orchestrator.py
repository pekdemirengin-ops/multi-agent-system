"""Görev dağıtımı ve akış yönetimi."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

from core.base_agent import Message

if TYPE_CHECKING:
    from core.message_bus import MessageBus

logger = structlog.get_logger(__name__)


@dataclass
class PlanStep:
    """Tek bir plan adımı."""

    agent: str
    content: Any
    msg_type: str = "task"
    depends_on: list[str] = field(default_factory=list)
    step_id: str = ""


@dataclass
class Plan:
    """Sıralı/bağımlı adımlardan oluşan plan."""

    steps: list[PlanStep] = field(default_factory=list)
    name: str = "default"

    def add(self, agent: str, content: Any, **kwargs: Any) -> None:
        self.steps.append(PlanStep(agent=agent, content=content, **kwargs))


class Orchestrator:
    """Planları agent'lara dağıtır, sonuçları toplar."""

    def __init__(self, bus: "MessageBus") -> None:
        self.bus = bus
        self._results: dict[str, Any] = {}

    async def dispatch(self, plan: Plan) -> None:
        """Planı sırayla çalıştırır (bağımlılık sırasına uyarak)."""
        completed: set[str] = set()

        for step in plan.steps:
            if step.depends_on and not all(d in completed for d in step.depends_on):
                logger.warning(
                    "orchestrator.dependency_skip",
                    step_id=step.step_id,
                    missing=[d for d in step.depends_on if d not in completed],
                )
                continue

            msg = Message(
                sender="orchestrator",
                receiver=step.agent,
                content=step.content,
                msg_type=step.msg_type,
            )
            logger.info(
                "orchestrator.dispatch",
                step=step.step_id or step.agent,
                target=step.agent,
            )
            await self.bus.publish(msg)
            completed.add(step.step_id or step.agent)

        logger.info("orchestrator.plan_completed", name=plan.name, steps=len(plan.steps))

    async def dispatch_one(self, agent: str, content: Any, msg_type: str = "task") -> None:
        """Tek bir agent'a mesaj gönderir (kısayol)."""
        await self.bus.publish(
            Message(
                sender="orchestrator",
                receiver=agent,
                content=content,
                msg_type=msg_type,
            )
        )

    def __repr__(self) -> str:
        return "<Orchestrator>"