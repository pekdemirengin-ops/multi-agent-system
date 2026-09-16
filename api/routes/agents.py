"""Agent endpoint'leri (hafiza destekli)."""
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
from core.memory import get_memory
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
        logger.info("api.bus_initialized", bus="redis")
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

    # Hafiza baslat
    await get_memory()

    logger.info("api.agents_initialized", agents=list(_agents.keys()), bus=_bus_type)


def get_agent(name: str) -> BaseAgent:
    if _bus is None:
        raise HTTPException(status_code=503, detail="Agentlar hazir degil")
    if name not in _agents:
        raise HTTPException(status_code=404, detail=f"Agent bulunamadi: {name}")
    return _agents[name]


async def _run_single_agent(agent_name: str, message_text: str, timeout: int) -> dict[str, Any]:
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

    memory = await get_memory()
    user_id = req.user_id or "default"

    # 1) Kullanici mesajini kaydet
    await memory.save_message(user_id, "user", req.message)

    # 2) Gecmisi al
    history_text = await memory.format_for_llm(user_id, limit=10)

    # 3) Auto-routing
    chosen_agent = req.agent
    router_used = False

    if req.agent == "auto":
        router_used = True
        router_result = await _run_single_agent("router", req.message, timeout=15)
        if isinstance(router_result, dict):
            chosen_agent = router_result.get("agent", "researcher")
        else:
            chosen_agent = "researcher"
        logger.info("api.auto_routed", chosen=chosen_agent)

    get_agent(chosen_agent)

    # 4) Mesaji gecmisle birlikte agent'a gonder
    if history_text:
        full_message = (
            f"{history_text}\n\n"
            f"---\n\n"
            f"Kullanici simdi soruyor: {req.message}"
        )
    else:
        full_message = req.message

    result = await _run_single_agent(chosen_agent, full_message, timeout=req.timeout)

    duration_ms = int((time.perf_counter() - start) * 1000)

    # 5) Cevabi kaydet
    if isinstance(result, dict):
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        if "research" in result:
            sources = [
                Source(title=s["title"], url=s["url"])
                for s in result.get("sources", [])
            ]
            await memory.save_message(
                user_id,
                "assistant",
                result["research"],
                agent=chosen_agent,
                sources=[{"title": s.title, "url": s.url} for s in sources],
            )
            return AskResponse(
                answer=result["research"],
                agent=chosen_agent,
                sources=sources,
                duration_ms=duration_ms,
                raw={
                    "source_count": result.get("source_count", 0),
                    "bus": _bus_type,
                    "router_used": router_used,
                    "has_history": bool(history_text),
                },
            )

        if "answer" in result:
            await memory.save_message(
                user_id, "assistant", result["answer"], agent=chosen_agent
            )
            return AskResponse(
                answer=result["answer"],
                agent=chosen_agent,
                sources=[],
                duration_ms=duration_ms,
                raw={"bus": _bus_type, "router_used": router_used, "has_history": bool(history_text)},
            )

    answer_text = str(result)
    await memory.save_message(user_id, "assistant", answer_text, agent=chosen_agent)
    return AskResponse(
        answer=answer_text,
        agent=chosen_agent,
        duration_ms=duration_ms,
        raw={"bus": _bus_type, "router_used": router_used, "has_history": bool(history_text)},
    )