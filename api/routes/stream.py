"""Streaming endpoint - token token cevap akisi."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.routes.auth import get_optional_user
from core.memory import get_memory
from core.security import rate_limiter, validate_message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["stream"])


class StreamRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="default")
    system_prompt: str | None = None


@router.post("/stream")
async def stream_chat(
    req: StreamRequest,
    request: Request,
    authenticated_user: str | None = Depends(get_optional_user),
):
    """Streaming sohbet - token token akitir (SSE)."""
    # Auth zorunlu (streaming icin)
    if not authenticated_user:
        raise HTTPException(
            status_code=401,
            detail="Token gerekli",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Rate limiting
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )
    effective_user = authenticated_user or req.user_id
    rate_key = f"{effective_user}:{client_ip}"
    allowed, remaining = rate_limiter.check(rate_key)
    if not allowed:
        raise HTTPException(status_code=429, detail="Cok fazla istek")

    # Validation
    valid, err = validate_message(req.message)
    if not valid:
        raise HTTPException(status_code=400, detail=err)

    # Hafiza
    memory = await get_memory()
    await memory.save_message(effective_user, "user", req.message)
    history_text = await memory.format_for_llm(effective_user, limit=10)

    llm = GroqLLMClient()
    system = req.system_prompt or (
        "Sen yardimci bir AI asistansin. Turkce, net ve faydali cevap ver."
    )

    async def generate():
        full_answer = ""
        start = time.perf_counter()

        try:
            yield f"data: {json.dumps({'type': 'start'})}\n\n"

            if history_text:
                prompt = f"{history_text}\n\n---\n\nKullanici: {req.message}"
            else:
                prompt = req.message

            for token in llm.chat_stream(prompt=prompt, system=system):
                full_answer += token
                yield f"data: {json.dumps({'type': 'chunk', 'content': token})}\n\n"
                await asyncio.sleep(0.005)

            await memory.save_message(effective_user, "assistant", full_answer, agent="llm")

            duration_ms = int((time.perf_counter() - start) * 1000)
            yield f"data: {json.dumps({'type': 'done', 'duration_ms': duration_ms, 'length': len(full_answer)})}\n\n"

        except Exception as e:
            logger.exception("stream.error", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )