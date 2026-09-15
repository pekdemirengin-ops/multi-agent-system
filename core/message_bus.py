"""Agent'lar arası asenkron mesajlaşma veriyolu."""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from typing import TYPE_CHECKING, Callable

import structlog

from core.base_agent import Message

if TYPE_CHECKING:
    from core.base_agent import BaseAgent

logger = structlog.get_logger(__name__)


class MessageBus:
    """In-memory asenkron mesaj veriyolu.

    Özellikler:
    - Agent kayıt/çıkar
    - Mesaj yönlendirme (tek alıcı, broadcast '*', topic)
    - Geçmiş kaydı (debug için)
    - Subscribe/unsubscribe (callback tabanlı)
    """

    def __init__(self, max_history: int = 1000) -> None:
        self._agents: dict[str, BaseAgent] = {}
        self._subscribers: dict[str, list[Callable[[Message], None]]] = defaultdict(list)
        self._history: deque[Message] = deque(maxlen=max_history)
        self._lock = asyncio.Lock()

    # ---------- Kayıt ----------

    def register(self, agent: "BaseAgent") -> None:
        """Agent'ı veriyoluna kaydeder."""
        if agent.name in self._agents:
            raise ValueError(f"Agent zaten kayıtlı: {agent.name}")
        self._agents[agent.name] = agent
        logger.info("agent.registered", agent=agent.name, total=len(self._agents))

    def unregister(self, name: str) -> None:
        """Agent'ı veriyolundan çıkarır."""
        self._agents.pop(name, None)
        logger.info("agent.unregistered", agent=name)

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    # ---------- Abonelik ----------

    def subscribe(self, topic: str, callback: Callable[[Message], None]) -> None:
        """Bir topic'e callback abone eder."""
        self._subscribers[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable[[Message], None]) -> None:
        if callback in self._subscribers.get(topic, []):
            self._subscribers[topic].remove(callback)

    # ---------- Yayın ----------

    async def publish(self, message: Message) -> None:
        """Mesajı uygun alıcıya/abonelere iletir."""
        self._history.append(message)

        # 1) Topic abonelerine ilet (receiver topic olabilir)
        if message.receiver in self._subscribers:
            for cb in self._subscribers[message.receiver]:
                try:
                    result = cb(message)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.exception("subscriber.error", topic=message.receiver, error=str(e))

        # 2) Broadcast
        if message.receiver == "*":
            for agent in self._agents.values():
                if agent.name == message.sender:
                    continue
                await self._deliver(agent, message)
            return

        # 3) Tek agent
        agent = self._agents.get(message.receiver)
        if agent is not None:
            await self._deliver(agent, message)
        elif message.receiver not in self._subscribers:
            logger.warning("bus.no_receiver", receiver=message.receiver, msg_id=message.id)

    async def _deliver(self, agent: "BaseAgent", message: Message) -> None:
        """Tek bir agent'a mesajı iletir; hataları yakalar."""
        try:
            await agent.handle(message)
        except Exception as e:
            logger.exception(
                "agent.handle.error",
                agent=agent.name,
                msg_id=message.id,
                error=str(e),
            )

    # ---------- Geçmiş ----------

    def history(self) -> list[Message]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()

    def __repr__(self) -> str:
        return f"<MessageBus agents={len(self._agents)} history={len(self._history)}>"