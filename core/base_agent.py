"""Tüm agent'ların atası olan soyut sınıf."""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.message_bus import MessageBus


@dataclass
class Message:
    """Agent'lar arası taşınan mesaj."""

    sender: str
    receiver: str
    content: Any
    msg_type: str = "task"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"Message({self.sender}->{self.receiver}, type={self.msg_type})"


class BaseAgent(ABC):
    """Tüm agent'ların türediği soyut sınıf.

    Her agent'in şunları yapması beklenir:
    - `handle()` metodunu implement etmek
    - `send()` ile başka agent'lara mesaj göndermek
    - `name` benzersiz olmalı
    """

    def __init__(self, name: str, bus: "MessageBus") -> None:
        if not name:
            raise ValueError("Agent adı boş olamaz")
        self.name = name
        self.bus = bus
        self.bus.register(self)

    @abstractmethod
    async def handle(self, message: Message) -> None:
        """Gelen mesajı işler. Alt sınıflar bunu implement etmeli."""
        ...

    async def send(
        self,
        receiver: str,
        content: Any,
        msg_type: str = "task",
    ) -> None:
        """Başka bir agent'a (veya '*' ile herkese) mesaj gönderir."""
        msg = Message(
            sender=self.name,
            receiver=receiver,
            content=content,
            msg_type=msg_type,
        )
        await self.bus.publish(msg)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"