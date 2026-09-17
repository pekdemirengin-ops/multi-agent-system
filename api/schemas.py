"""API request/response modelleri."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Agent'a soru sorma istegi."""

    message: str = Field(..., description="Sorulacak soru/gorev", min_length=1)
    agent: str = Field(default="researcher", description="Hangi agent (veya 'auto')")
    timeout: int = Field(default=30, ge=1, le=120)
    user_id: str = Field(default="default", description="Kullanici ID (hafiza icin)")


class Source(BaseModel):
    title: str
    url: str


class AskResponse(BaseModel):
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


# ============================================================
# Auth modelleri
# ============================================================

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 604800  # 7 gun
    username: str


class UserInfo(BaseModel):
    username: str
    is_admin: bool = False
    role: str = "user"
    created_at: str = ""


class UserListResponse(BaseModel):
    users: list[UserInfo]
    total: int


class RoleUpdateRequest(BaseModel):
    role: str = Field(..., description="admin veya user")


class AuthStatus(BaseModel):
    authenticated: bool
    username: str | None = None