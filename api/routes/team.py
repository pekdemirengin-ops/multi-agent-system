"""Multi-agent isbirligi endpoint'i."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.routes import agents as agents_module
from core.base_agent import BaseAgent, Message

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["team"])


class TeamRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Gorev tanimi")
    timeout: int = Field(default=90, ge=10, le=180)


class TeamStepResult(BaseModel):
    agent: str
    task: str
    result: str
    duration_ms: int


class TeamResponse(BaseModel):
    plan: list[dict[str, Any]]
    results: list[TeamStepResult]
    final_summary: str
    total_duration_ms: int


class _Collector(BaseAgent):
    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)
        self.responses: dict[str, dict[str, Any]] = {}
        self._pending: set[str] = set()

    async def handle(self, message: Message) -> None:
        if message.msg_type == "result":
            self.responses[message.sender] = message.content
            self._pending.discard(message.sender)


async def _plan_task(task: str, timeout: int = 30) -> dict:
    bus = agents_module._bus
    if bus is None:
        return {"steps": []}

    collector = _Collector("__team_planner_collector__", bus)

    await bus.publish(
        Message(
            sender=collector.name,
            receiver="planner",
            content=task,
            msg_type="task",
        )
    )

    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        if "planner" in collector.responses:
            result = collector.responses.pop("planner")
            if isinstance(result, dict):
                return result.get("plan", {})
        await asyncio.sleep(0.2)

    return {"steps": []}


async def _call_agent(
    collector: _Collector,
    agent_name: str,
    task: str,
    timeout: int = 60,
) -> str:
    bus = agents_module._bus
    if bus is None:
        return "(bus yok)"

    collector._pending.add(agent_name)
    await bus.publish(
        Message(
            sender=collector.name,
            receiver=agent_name,
            content=task,
            msg_type="task",
        )
    )

    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        if agent_name not in collector._pending:
            response = collector.responses.pop(agent_name, {})
            if isinstance(response, dict):
                return (
                    response.get("research")
                    or response.get("answer")
                    or str(response)
                )
            return str(response)
        await asyncio.sleep(0.2)

    return "(zaman asimi)"


@router.post("/team", response_model=TeamResponse)
async def team_ask(req: TeamRequest) -> TeamResponse:
    await agents_module.init_agents()

    if "planner" not in agents_module._agents:
        raise HTTPException(
            status_code=503,
            detail=f"Planner yuklu degil. Mevcut: {list(agents_module._agents.keys())}",
        )

    start = time.perf_counter()

    logger.info("team.planning", task=req.message[:80])
    plan = await _plan_task(req.message, timeout=30)
    steps = plan.get("steps", [])

    if not steps:
        return TeamResponse(
            plan=[],
            results=[],
            final_summary="Plan olusturulamadi. Lutfen daha net bir gorev yazin.",
            total_duration_ms=int((time.perf_counter() - start) * 1000),
        )

    collector = _Collector("__team_worker__", agents_module._bus)
    results: list[TeamStepResult] = []
    per_step_timeout = max(req.timeout // max(len(steps), 1), 20)

    for step in steps:
        agent_name = step.get("agent", "")
        task = step.get("task", "")

        if agent_name not in agents_module._agents:
            if "researcher" in agents_module._agents:
                agent_name = "researcher"
            else:
                continue

        step_start = time.perf_counter()
        result_text = await _call_agent(
            collector,
            agent_name,
            f"{req.message}\n\nAlt gorev: {task}",
            timeout=per_step_timeout,
        )
        step_duration = int((time.perf_counter() - step_start) * 1000)

        results.append(
            TeamStepResult(
                agent=agent_name,
                task=task,
                result=result_text[:500],
                duration_ms=step_duration,
            )
        )
        logger.info(
            "team.step_done",
            agent=agent_name,
            duration_ms=step_duration,
        )

    summary_parts = [f"Gorev: {req.message}", "", f"Plan: {len(steps)} adim", ""]
    for i, r in enumerate(results, 1):
        summary_parts.append(f"{i}. [{r.agent}] {r.task[:80]}")
        summary_parts.append(f"   -> {r.result[:300]}")
        summary_parts.append("")

    return TeamResponse(
        plan=steps,
        results=results,
        final_summary="\n".join(summary_parts),
        total_duration_ms=int((time.perf_counter() - start) * 1000),
    )