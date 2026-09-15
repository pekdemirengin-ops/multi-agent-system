"""Agent endpoint'leri."""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException

from agents.ai import LLMAgent, ResearcherAgent
from api.schemas import AgentInfo, AgentsResponse, AskRequest, AskResponse, Source
from core.base_agent import BaseAgent, Message
from core.message_bus import MessageBus

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["agents"])


# --- Global state ---
_bus: MessageBus | None = None
_agents: dict[str, BaseAgent] = {}
_response_futures: dict[str, asyncio.Future] = {}


class ResponseCollector(BaseAgent):
    """API tarafindan gonderilen isteklerin cevaplarini toplar."""

    def __init__(self, name: str, bus: MessageBus) -> None:
        super().__init__(name, bus)

    async def handle(self, message: Message) -> None:
        # Gelen result mesajinin id'si ile eslesen future'i bul
        # Not: agent'lar send() yaparken YENI id uretiyor,
        # o yuzden once sender-tabanli, sonra sirayla kontrol et
        for fid, fut in list(_response_futures.items()):
            if not fut.done():
                fut.set_result(message.content)
                _response_futures.pop(fid, None)
                return


def init_agents() -> None:
    """Uygulama baslarken agent'lari olusturur."""
    global _bus, _agents
    if _bus is not None:
        return

    _bus = MessageBus()
    ResponseCollector("__api_collector__", _bus)

    _agents = {
        "researcher": ResearcherAgent("researcher", _bus),
        "llm": LLMAgent("llm", _bus, system_prompt="Kisa ve oz cevap ver."),
    }
    logger.info("api.agents_initialized", agents=list(_agents.keys()))


def get_agent(name: str) -> BaseAgent:
    if _bus is None:
        raise HTTPException(status_code=503, detail="Agentlar hazir degil")
    if name not in _agents:
        raise HTTPException(status_code=404, detail=f"Agent bulunamadi: {name}")
    return _agents[name]


@router.get("/agents", response_model=AgentsResponse)
async def list_agents() -> AgentsResponse:
    """Kayitli agent'lari listeler."""
    init_agents()
    return AgentsResponse(
        agents=[AgentInfo(name=n) for n in _agents],
        count=len(_agents),
    )


@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    """Bir agent'a soru sorar, cevabi bekler."""
    init_agents()
    get_agent(req.agent)  # validate

    start = time.perf_counter()

    # Future olustur
    fid = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()
    _response_futures[fid] = future

    # Mesaji gonder (sender = collector, boylece cevap oraya gelir)
    msg = Message(
        sender="__api_collector__",
        receiver=req.agent,
        content=req.message,
        msg_type="task",
        id=fid,
    )
    await _bus.publish(msg)  # type: ignore[union-attr]

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
                raw={"source_count": result.get("source_count", 0)},
            )

        if "answer" in result:
            return AskResponse(
                answer=result["answer"],
                agent=req.agent,
                sources=[],
                duration_ms=duration_ms,
            )

    return AskResponse(
        answer=str(result),
        agent=req.agent,
        duration_ms=duration_ms,
    )