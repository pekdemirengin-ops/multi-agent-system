"""Pytest ortak fixture'lari."""
from __future__ import annotations

from typing import AsyncGenerator

import pytest
import pytest_asyncio

from core.base_agent import BaseAgent, Message
from core.message_bus import MessageBus


class EchoAgent(BaseAgent):
    """Test icin basit echo agent."""

    def __init__(self, name: str, bus: MessageBus) -> None:
        super().__init__(name, bus)
        self.received: list[Message] = []

    async def handle(self, message: Message) -> None:
        self.received.append(message)
        if message.msg_type == "task":
            await self.send(message.sender, f"echo: {message.content}", msg_type="result")


@pytest_asyncio.fixture
async def bus() -> AsyncGenerator[MessageBus, None]:
    """Temiz bir in-memory bus dondurur."""
    yield MessageBus()


@pytest_asyncio.fixture
async def echo_agent(bus: MessageBus) -> EchoAgent:
    """Echo agent dondurur."""
    return EchoAgent("echo", bus)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"