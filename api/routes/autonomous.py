"""Autonomous endpoint'leri - hedef ver, kendi planlasin."""
from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.routes.agents import _agents
from api.routes.auth import get_current_user
from core.autonomous import AutonomousEngine, AutonomousResult

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/autonomous", tags=["autonomous"])


class AutonomousRequest(BaseModel):
    """Autonomous calistirma istegi."""

    goal: str = Field(..., description="Hedef", min_length=5)
    timeout: int = Field(default=60, ge=10, le=180)


class AutonomousResponse(BaseModel):
    success: bool
    goal: str
    goal_summary: str = ""
    report_title: str = ""
    final_report: str = ""
    steps: list[dict[str, Any]] = []
    duration_ms: int = 0
    error: str | None = None


@router.post("/run", response_model=AutonomousResponse)
async def run_autonomous(
    req: AutonomousRequest,
    _user: str = Depends(get_current_user),
) -> AutonomousResponse:
    """Hedefi planlar ve calistirir (non-streaming)."""
    if not _agents:
        raise HTTPException(status_code=503, detail="Agent hazir degil")

    engine = AutonomousEngine(agents=_agents, timeout=req.timeout)
    result: AutonomousResult = await engine.execute(req.goal)

    return AutonomousResponse(
        success=result.success,
        goal=result.goal,
        goal_summary=result.goal_summary,
        report_title=result.report_title,
        final_report=result.final_report,
        steps=[
            {
                "step": s.step,
                "query": s.query,
                "agent": s.agent,
                "status": s.status,
                "duration_ms": s.duration_ms,
                "output": s.output[:300] if s.output else "",
                "error": s.error,
            }
            for s in result.steps
        ],
        duration_ms=result.duration_ms,
        error=result.error,
    )


async def _stream_events(goal: str, timeout: int):
    """SSE stream generator."""
    if not _agents:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Agent hazir degil'})}\n\n"
        return

    try:
        engine = AutonomousEngine(agents=_agents, timeout=timeout)
        async for event in engine.execute_stream(goal):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.exception("autonomous.stream_error", error=str(e))
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


@router.post("/stream")
async def stream_autonomous(
    req: AutonomousRequest,
    _user: str = Depends(get_current_user),
):
    """Hedefi SSE ile canli stream eder."""
    return StreamingResponse(
        _stream_events(req.goal, req.timeout),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/examples")
async def get_examples() -> dict:
    """Ornek hedefler."""
    return {
        "examples": [
            {"goal": "Kozan hakkinda kapsamli bir rapor yaz"},
            {"goal": "Python ogrenmek icin yol haritasi olustur"},
            {"goal": "Turkiye'nin en kalabalik 3 sehrini arastir"},
            {"goal": "Yapay zeka hakkinda 5 soruluk quiz hazirla"},
            {"goal": "Cristiano Ronaldo hakkinda biyografi yaz"},
        ]
    }
