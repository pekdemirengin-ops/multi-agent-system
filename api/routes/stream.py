"""Streaming endpoint - token token cevap akisi."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.config import get_settings
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
async def stream_chat(req: StreamRequest, request: Request):
    """Streaming sohbet - token token akitir.

    Server-Sent Events (SSE) formati kullanir.
    """
    # Rate limiting
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )
    rate_key = f"{req.user_id}:{client_ip}"
    allowed, remaining = rate_limiter.check(rate_key)
    if not allowed:
        raise HTTPException(status_code=429, detail="Cok fazla istek")

    # Validation
    valid, err = validate_message(req.message)
    if not valid:
        raise HTTPException(status_code=400, detail=err)

    # Hafiza: user mesajini kaydet
    memory = await get_memory()
    await memory.save_message(req.user_id, "user", req.message)
    history_text = await memory.format_for_llm(req.user_id, limit=10)

    # LLM client
    llm = GroqLLMClient()
    system = req.system_prompt or (
        "Sen yardimci bir AI asistansin. Turkce, net ve faydali cevap ver."
    )

    async def generate():
        """SSE stream."""
        full_answer = ""
        start = time.perf_counter()

        try:
            # Baslangic eventi
            yield f"data: {json.dumps({'type': 'start', 'message': req.message})}\n\n"

            # Prompt (hafiza ile)
            if history_text:
                prompt = f"{history_text}\n\n---\n\nKullanici: {req.message}"
            else:
                prompt = req.message

            # Streaming
            for token in llm.chat_stream(prompt=prompt, system=system):
                full_answer += token
                yield f"data: {json.dumps({'type': 'chunk', 'content': token})}\n\n"
                # Kucuk gecikme - UI render
                await asyncio.sleep(0.01)

            # Hafiza: cevabi kaydet
            await memory.save_message(req.user_id, "assistant", full_answer, agent="llm")

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