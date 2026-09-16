"""Agent endpoint'leri."""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException

from agents.ai import (
    CoderAgent,
    LLMAgent,
    PlannerAgent,
    ResearcherAgent,
    ReviewerAgent,
    RouterAgent,
    SummarizerAgent,
)
from agents.devops import SystemAgent
from api.schemas import AgentInfo, AgentsResponse, AskRequest, AskResponse, Source
from core.base_agent import BaseAgent, Message
from core.config import get_settings
from core.message_bus import MessageBus
from core.redis_bus import RedisMessageBus

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["agents"])


_bus: Any = None
_agents: dict[str, BaseAgent] = {}
_response_futures: dict[str, asyncio.Future] = {}
_bus_type: str = "in-memory"


class ResponseCollector(BaseAgent):
    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)

    async def handle(self, message: Message) -> None:
        for fid, fut in list(_response_futures.items()):
            if not fut.done():
                fut.set_result(message.content)
                _response_futures.pop(fid, None)
                return


async def init_agents() -> None:
    global _bus, _bus_type
    if _bus is not None:
        return

    settings = get_settings()

    if settings.use_redis_bus:
        _bus = RedisMessageBus(redis_url=settings.redis_url)
        await _bus.connect()
        _bus_type = "redis"
        logger.info("api.bus_initialized", bus="redis", url=settings.redis_url)
    else:
        _bus = MessageBus()
        _bus_type = "in-memory"
        logger.info("api.bus_initialized", bus="in-memory")

    ResponseCollector("__api_collector__", _bus)

    _agents.clear()
    _agents.update(
        {
            "researcher": ResearcherAgent("researcher", _bus),
            "llm": LLMAgent("llm", _bus, system_prompt="Kisa ve oz cevap ver."),
            "system": SystemAgent("system", _bus),
            "coder": CoderAgent("coder", _bus),
            "planner": PlannerAgent("planner", _bus),
            "reviewer": ReviewerAgent("reviewer", _bus),
            "summarizer": SummarizerAgent("summarizer", _bus),
            "router": RouterAgent("router", _bus),
        }
    )
    logger.info("api.agents_initialized", agents=list(_agents.keys()), bus=_bus_type)


def get_agent(name: str) -> BaseAgent:
    if _bus is None:
        raise HTTPException(status_code=503, detail="Agentlar hazir degil")
    if name not in _agents:
        raise HTTPException(status_code=404, detail=f"Agent bulunamadi: {name}")
    return _agents[name]


async def _run_single_agent(agent_name: str, message_text: str, timeout: int) -> dict[str, Any]:
    """Tek bir agent'a gorev gonderir ve sonucu dondurur."""
    fid = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()
    _response_futures[fid] = future

    msg = Message(
        sender="__api_collector__",
        receiver=agent_name,
        content=message_text,
        msg_type="task",
        id=fid,
    )
    await _bus.publish(msg)

    try:
        result = await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        _response_futures.pop(fid, None)
        raise HTTPException(status_code=504, detail="Agent zaman asimina ugradi") from None

    return result


@router.get("/agents", response_model=AgentsResponse)
async def list_agents() -> AgentsResponse:
    await init_agents()
    return AgentsResponse(
        agents=[AgentInfo(name=n) for n in _agents],
        count=len(_agents),
    )


@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    await init_agents()
    start = time.perf_counter()

    # Auto-routing
    chosen_agent = req.agent
    router_used = False

    if req.agent == "auto":
        router_used = True
        # Router agent'a sor
        router_result = await _run_single_agent("router", req.message, timeout=15)
        if isinstance(router_result, dict):
            chosen_agent = router_result.get("agent", "researcher")
        else:
            chosen_agent = "researcher"
        logger.info("api.auto_routed", chosen=chosen_agent, query=req.message[:60])

    # Secilen agent'i kontrol et
    get_agent(chosen_agent)

    # Asil agent'i calistir
    result = await _run_single_agent(chosen_agent, req.message, timeout=req.timeout)

    duration_ms = int((time.perf_counter() - start) * 1000)

    if isinstance(result, dict):
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        if "research" in result:
            sources = [
                Source(title=s["title"], url=s["url"])
                for s in result.get("sources", [])
            ]
            return AskResponse(
                answer=result["research"],
                agent=chosen_agent,
                sources=sources,
                duration_ms=duration_ms,
                raw={
                    "source_count": result.get("source_count", 0),
                    "bus": _bus_type,
                    "status": result.get("status"),
                    "alerts": result.get("alerts"),
                    "code": result.get("code"),
                    "execution": result.get("execution"),
                    "router_used": router_used,
                    "original_request": req.agent,
                },
            )

        if "answer" in result:
            return AskResponse(
                answer=result["answer"],
                agent=chosen_agent,
                sources=[],
                duration_ms=duration_ms,
                raw={
                    "bus": _bus_type,
                    "router_used": router_used,
                    "original_request": req.agent,
                },
            )

        if "plan" in result:
            plan = result["plan"]
            steps_text = "\n".join(
                f"{i}. [{s.get('agent', '?')}] {s.get('task', '')}"
                for i, s in enumerate(plan.get("steps", []), 1)
            )
            return AskResponse(
                answer=f"Plan ({len(plan.get('steps', []))} adim):\n{steps_text}",
                agent=chosen_agent,
                duration_ms=duration_ms,
                raw={"plan": plan, "bus": _bus_type, "router_used": router_used},
            )

    return AskResponse(
        answer=str(result),
        agent=chosen_agent,
        duration_ms=duration_ms,
        raw={"bus": _bus_type, "router_used": router_used},
    )