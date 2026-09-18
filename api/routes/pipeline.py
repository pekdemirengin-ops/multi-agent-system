"""Pipeline endpoint'leri."""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.routes.agents import _agents, get_agent
from api.routes.auth import get_current_user
from core.pipeline import Pipeline, list_pipelines
from core.pipeline_history import add_result, clear_history, get_history, get_stats

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

    # Gecmise ekle
    await add_result(
        pipeline_name=result.pipeline_name,
        query=result.query,
        success=result.success,
        duration_ms=result.duration_ms,
        step_count=len(result.steps),
        final_answer=result.final_answer,
        error=result.error,
        user=_user,
    )

    return PipelineResponse(
        pipeline_name=result.pipeline_name,
        query=result.query,
        success=result.success,
        final_answer=result.final_answer,
        duration_ms=result.duration_ms,
        steps=result.steps,
        error=result.error,
    )

@router.get("/history")
async def get_pipeline_history(
    limit: int = 20,
    _user: str = Depends(get_current_user),
) -> dict:
    """Pipeline calistirma gecmisi."""
    items = await get_history(limit=limit)
    stats = await get_stats()
    return {
        "history": items,
        "stats": stats,
        "count": len(items),
    }


@router.delete("/history")
async def clear_pipeline_history(
    _user: str = Depends(get_current_user),
) -> dict:
    """Gecmisi temizler (sadece admin)."""
    count = await clear_history()
    return {"ok": True, "cleared": count}

# ============================================================
# STREAMING (SSE) - Adim adim canli gosterim
# ============================================================

from fastapi.responses import StreamingResponse
import json as json_lib
import asyncio


async def _stream_pipeline_events(pipeline_name: str, query: str, timeout: int):
    """Pipeline adimlarini SSE olarak stream eder."""
    from core.pipeline import PIPELINES

    steps = PIPELINES.get(pipeline_name, [])
    if not steps:
        yield f"data: {json_lib.dumps({'type': 'error', 'message': 'Pipeline bulunamadi'})}\n\n"
        return

    # Baslangic
    yield f"data: {json_lib.dumps({'type': 'start', 'pipeline': pipeline_name, 'total_steps': len(steps)})}\n\n"

    previous_output: Any = query
    overall_success = True
    start_time = __import__("time").perf_counter()

    for i, step in enumerate(steps, 1):
        agent_name = step.agent
        step_name = step.name or agent_name

        # Adim basladi
        yield f"data: {json_lib.dumps({'type': 'step_start', 'step': i, 'total': len(steps), 'agent': agent_name, 'name': step_name})}\n\n"

        if agent_name not in _agents:
            yield f"data: {json_lib.dumps({'type': 'step_error', 'step': i, 'agent': agent_name, 'error': 'Agent bulunamadi'})}\n\n"
            overall_success = False
            break

        step_start = __import__("time").perf_counter()
        step_input = step.get_input(previous_output, query)

        try:
            agent = _agents[agent_name]
            output = await asyncio.wait_for(
                _run_single_agent_internal(agent, step_input),
                timeout=timeout,
            )

            step_duration = int((__import__("time").perf_counter() - step_start) * 1000)
            previous_output = output

            # Cikti metni
            out_text = ""
            if isinstance(output, dict):
                for key in ["answer", "research", "translation", "result", "output", "content", "summary"]:
                    if key in output and output[key]:
                        out_text = str(output[key])
                        break
                if not out_text:
                    out_text = str(output)
            else:
                out_text = str(output)

            yield f"data: {json_lib.dumps({'type': 'step_done', 'step': i, 'agent': agent_name, 'duration_ms': step_duration, 'output': out_text[:1000]})}\n\n"

        except asyncio.TimeoutError:
            yield f"data: {json_lib.dumps({'type': 'step_error', 'step': i, 'agent': agent_name, 'error': 'Timeout'})}\n\n"
            overall_success = False
            break
        except Exception as e:
            yield f"data: {json_lib.dumps({'type': 'step_error', 'step': i, 'agent': agent_name, 'error': str(e)})}\n\n"
            overall_success = False
            break

    # Bitis
    total_duration = int((__import__("time").perf_counter() - start_time) * 1000)

    final_text = ""
    if isinstance(previous_output, dict):
        for key in ["answer", "research", "translation", "result", "output", "content", "summary"]:
            if key in previous_output and previous_output[key]:
                final_text = str(previous_output[key])
                break
        if not final_text:
            final_text = str(previous_output)
    else:
        final_text = str(previous_output)

    yield f"data: {json_lib.dumps({'type': 'done', 'success': overall_success, 'final_answer': final_text, 'duration_ms': total_duration, 'pipeline': pipeline_name})}\n\n"

    # Gecmise ekle
    try:
        await add_result(
            pipeline_name=pipeline_name,
            query=query,
            success=overall_success,
            duration_ms=total_duration,
            step_count=len(steps),
            final_answer=final_text,
            user="stream",
        )
    except Exception as e:
        logger.warning("pipeline.stream.history_error", error=str(e))


async def _run_single_agent_internal(agent: Any, input_text: str) -> dict:
    """Agent'i calistirir ve ciktisini doner."""
    import uuid as uuid_lib
    from core.base_agent import Message

    message = Message(
        sender="__stream__",
        receiver=agent.name,
        content=input_text,
        msg_type="task",
        id=str(uuid_lib.uuid4()),
    )

    collected: list[Any] = []
    original_send = agent.send

    async def capture_send(receiver: str, content: Any, msg_type: str = "result") -> None:
        if msg_type == "result":
            collected.append(content)

    agent.send = capture_send  # type: ignore
    try:
        await agent.handle(message)
    finally:
        agent.send = original_send  # type: ignore

    if not collected:
        return {"answer": ""}
    return collected[-1] if isinstance(collected[-1], dict) else {"answer": str(collected[-1])}


@router.post("/stream")
async def stream_pipeline(
    req: PipelineRequest,
    _user: str = Depends(get_current_user),
):
    """Pipeline'i SSE ile canli stream eder."""
    if req.pipeline not in [p["name"] for p in list_pipelines()]:
        raise HTTPException(status_code=400, detail=f"Pipeline bulunamadi: {req.pipeline}")

    return StreamingResponse(
        _stream_pipeline_events(req.pipeline, req.query, req.timeout),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# STREAMING (SSE) - Adim adim canli gosterim
# ============================================================

from fastapi.responses import StreamingResponse
import json as json_lib
import asyncio


async def _stream_pipeline_events(pipeline_name: str, query: str, timeout: int):
    """Pipeline adimlarini SSE olarak stream eder."""
    from core.pipeline import PIPELINES

    steps = PIPELINES.get(pipeline_name, [])
    if not steps:
        yield f"data: {json_lib.dumps({'type': 'error', 'message': 'Pipeline bulunamadi'})}\n\n"
        return

    # Baslangic
    yield f"data: {json_lib.dumps({'type': 'start', 'pipeline': pipeline_name, 'total_steps': len(steps)})}\n\n"

    previous_output: Any = query
    overall_success = True
    start_time = __import__("time").perf_counter()

    for i, step in enumerate(steps, 1):
        agent_name = step.agent
        step_name = step.name or agent_name

        # Adim basladi
        yield f"data: {json_lib.dumps({'type': 'step_start', 'step': i, 'total': len(steps), 'agent': agent_name, 'name': step_name})}\n\n"

        if agent_name not in _agents:
            yield f"data: {json_lib.dumps({'type': 'step_error', 'step': i, 'agent': agent_name, 'error': 'Agent bulunamadi'})}\n\n"
            overall_success = False
            break

        step_start = __import__("time").perf_counter()
        step_input = step.get_input(previous_output, query)

        try:
            agent = _agents[agent_name]
            output = await asyncio.wait_for(
                _run_single_agent_internal(agent, step_input),
                timeout=timeout,
            )

            step_duration = int((__import__("time").perf_counter() - step_start) * 1000)
            previous_output = output

            # Cikti metni
            out_text = ""
            if isinstance(output, dict):
                for key in ["answer", "research", "translation", "result", "output", "content", "summary"]:
                    if key in output and output[key]:
                        out_text = str(output[key])
                        break
                if not out_text:
                    out_text = str(output)
            else:
                out_text = str(output)

            yield f"data: {json_lib.dumps({'type': 'step_done', 'step': i, 'agent': agent_name, 'duration_ms': step_duration, 'output': out_text[:1000]})}\n\n"

        except asyncio.TimeoutError:
            yield f"data: {json_lib.dumps({'type': 'step_error', 'step': i, 'agent': agent_name, 'error': 'Timeout'})}\n\n"
            overall_success = False
            break
        except Exception as e:
            yield f"data: {json_lib.dumps({'type': 'step_error', 'step': i, 'agent': agent_name, 'error': str(e)})}\n\n"
            overall_success = False
            break

    # Bitis
    total_duration = int((__import__("time").perf_counter() - start_time) * 1000)

    final_text = ""
    if isinstance(previous_output, dict):
        for key in ["answer", "research", "translation", "result", "output", "content", "summary"]:
            if key in previous_output and previous_output[key]:
                final_text = str(previous_output[key])
                break
        if not final_text:
            final_text = str(previous_output)
    else:
        final_text = str(previous_output)

    yield f"data: {json_lib.dumps({'type': 'done', 'success': overall_success, 'final_answer': final_text, 'duration_ms': total_duration, 'pipeline': pipeline_name})}\n\n"

    # Gecmise ekle
    try:
        await add_result(
            pipeline_name=pipeline_name,
            query=query,
            success=overall_success,
            duration_ms=total_duration,
            step_count=len(steps),
            final_answer=final_text,
            user="stream",
        )
    except Exception as e:
        logger.warning("pipeline.stream.history_error", error=str(e))


async def _run_single_agent_internal(agent: Any, input_text: str) -> dict:
    """Agent'i calistirir ve ciktisini doner."""
    import uuid as uuid_lib
    from core.base_agent import Message

    message = Message(
        sender="__stream__",
        receiver=agent.name,
        content=input_text,
        msg_type="task",
        id=str(uuid_lib.uuid4()),
    )

    collected: list[Any] = []
    original_send = agent.send

    async def capture_send(receiver: str, content: Any, msg_type: str = "result") -> None:
        if msg_type == "result":
            collected.append(content)

    agent.send = capture_send  # type: ignore
    try:
        await agent.handle(message)
    finally:
        agent.send = original_send  # type: ignore

    if not collected:
        return {"answer": ""}
    return collected[-1] if isinstance(collected[-1], dict) else {"answer": str(collected[-1])}


@router.post("/stream")
async def stream_pipeline(
    req: PipelineRequest,
    _user: str = Depends(get_current_user),
):
    """Pipeline'i SSE ile canli stream eder."""
    if req.pipeline not in [p["name"] for p in list_pipelines()]:
        raise HTTPException(status_code=400, detail=f"Pipeline bulunamadi: {req.pipeline}")

    return StreamingResponse(
        _stream_pipeline_events(req.pipeline, req.query, req.timeout),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
