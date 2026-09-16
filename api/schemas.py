"""API request/response modelleri."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Agent'a soru sorma istegi."""

    message: str = Field(..., description="Sorulacak soru/gorev", min_length=1)
    agent: str = Field(
        default="researcher",
        description="Hangi agent'a gonderilecek (veya 'auto')",
    )
    timeout: int = Field(default=30, ge=1, le=120, description="Saniye cinsinden timeout")
    user_id: str = Field(default="default", description="Kullanici ID (hafiza icin)")


class Source(BaseModel):
    title: str
    url: str


class AskResponse(BaseModel):
    """Agent'tan gelen cevap."""

    answer: str
    agent: str
    sources: list[Source] = Field(default_factory=list)
    duration_ms: int
    raw: dict[str, Any] | None = None


class AgentInfo(BaseModel):
    name: str
    status: str = "ready"


class AgentsResponse(BaseModel):
    agents: list[AgentInfo]
    count: int


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.3.0"


class MemoryStats(BaseModel):
    total_messages: int
    unique_users: int