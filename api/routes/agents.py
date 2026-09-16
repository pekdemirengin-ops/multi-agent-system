"""Agent endpoint'leri."""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException

from agents.ai import CoderAgent, LLMAgent, PlannerAgent, ResearcherAgent
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
        }
    )
    logger.info("api.agents_initialized", agents=list(_agents.keys()), bus=_bus_type)


def get_agent(name: str) -> BaseAgent:
    if _bus is None:
        raise HTTPException(status_code=503, detail="Agentlar hazir degil")
    if name not in _agents:
        raise HTTPException(status_code=404, detail=f"Agent bulunamadi: {name}")
    return _agents[name]


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
    get_agent(req.agent)

    start = time.perf_counter()

    fid = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()
    _response_futures[fid] = future

    msg = Message(
        sender="__api_collector__",
        receiver=req.agent,
        content=req.message,
        msg_type="task",
        id=fid,
    )
    await _bus.publish(msg)

    try:
        result = await asyncio.wait_for(future, timeout=req.timeout)
    except asyncio.TimeoutError:
        _response_futures.pop(fid, None)
        raise HTTPException(status_code=504, detail="Agent zaman asimina ugradi") from None

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
                agent=req.agent,
                sources=sources,
                duration_ms=duration_ms,
                raw={
                    "source_count": result.get("source_count", 0),
                    "bus": _bus_type,
                    "status": result.get("status"),
                    "alerts": result.get("alerts"),
                    "code": result.get("code"),
                    "execution": result.get("execution"),
                },
            )

        if "answer" in result:
            return AskResponse(
                answer=result["answer"],
                agent=req.agent,
                sources=[],
                duration_ms=duration_ms,
            )

        if "plan" in result:
            plan = result["plan"]
            steps_text = "\n".join(
                f"{i}. [{s.get('agent', '?')}] {s.get('task', '')}"
                for i, s in enumerate(plan.get("steps", []), 1)
            )
            return AskResponse(
                answer=f"Plan ({len(plan.get('steps', []))} adim):\n{steps_text}",
                agent=req.agent,
                duration_ms=duration_ms,
                raw={"plan": plan, "bus": _bus_type},
            )

    return AskResponse(
        answer=str(result),
        agent=req.agent,
        duration_ms=duration_ms,
    )