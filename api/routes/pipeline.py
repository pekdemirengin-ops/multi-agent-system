"""Pipeline endpoint'leri."""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.routes.agents import _agents, get_agent
from api.routes.auth import get_current_user
from core.pipeline import Pipeline, list_pipelines

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


class PipelineRequest(BaseModel):
    """Pipeline calistirma istegi."""

    pipeline: str = Field(..., description="Pipeline adi (research, code, content, social, fact)")
    query: str = Field(..., description="Sorgu", min_length=1)
    timeout: int = Field(default=60, ge=5, le=180)


class PipelineStepResult(BaseModel):
    step: int
    agent: str
    name: str
    success: bool
    duration_ms: int
    output: str | None = None
    error: str | None = None


class PipelineResponse(BaseModel):
    pipeline_name: str
    query: str
    success: bool
    final_answer: str
    duration_ms: int
    steps: list[dict[str, Any]]
    error: str | None = None


@router.get("/list")
async def get_pipelines() -> dict[str, Any]:
    """Mevcut pipeline'lari listeler."""
    pipelines = list_pipelines()
    return {"pipelines": pipelines, "count": len(pipelines)}


@router.post("/run", response_model=PipelineResponse)
async def run_pipeline(
    req: PipelineRequest,
    _user: str = Depends(get_current_user),
) -> PipelineResponse:
    """Pipeline'i calistirir."""
    if req.pipeline not in [p["name"] for p in list_pipelines()]:
        raise HTTPException(status_code=400, detail=f"Pipeline bulunamadi: {req.pipeline}")

    pipeline = Pipeline(
        name=req.pipeline,
        bus=None,
        agents=_agents,
        timeout=req.timeout,
    )

    result = await pipeline.run(req.query)

    return PipelineResponse(
        pipeline_name=result.pipeline_name,
        query=result.query,
        success=result.success,
        final_answer=result.final_answer,
        duration_ms=result.duration_ms,
        steps=result.steps,
        error=result.error,
    )
