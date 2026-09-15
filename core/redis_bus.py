"""Redis Pub/Sub tabanli mesajlasma veriyolu."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

import structlog
from redis.asyncio import Redis

from core.base_agent import Message

if TYPE_CHECKING:
    from core.base_agent import BaseAgent

logger = structlog.get_logger(__name__)


class RedisMessageBus:
    """Redis Pub/Sub tabanli dagitik mesaj veriyolu."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        channel_prefix: str = "mas",
        max_history: int = 1000,
    ) -> None:
        self.redis_url = redis_url
        self.channel_prefix = channel_prefix
        self._redis: Redis | None = None
        self._pubsub: Any = None
        self._agents: dict[str, "BaseAgent"] = {}
        self._listener_task: asyncio.Task | None = None
        self._history: list[Message] = []
        self.max_history = max_history

    async def connect(self) -> None:
        """Redis'e baglan ve listener'i baslat."""
        if self._redis is not None:
            return
        try:
            self._redis = Redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.ping()
            self._pubsub = self._redis.pubsub()
            await self._pubsub.psubscribe(f"{self.channel_prefix}:*")
            self._listener_task = asyncio.create_task(self._listen_loop())
            logger.info("redis_bus.connected", url=self.redis_url)
        except Exception as e:
            logger.exception("redis_bus.connect_error", error=str(e))
            self._redis = None

    async def close(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            try:
                await self._pubsub.punsubscribe()
                await self._pubsub.close()
            except Exception:
                pass
        if self._redis:
            await self._redis.close()
        logger.info("redis_bus.closed")

    def register(self, agent: "BaseAgent") -> None:
        if agent.name in self._agents:
            raise ValueError(f"Agent zaten kayitli: {agent.name}")
        self._agents[agent.name] = agent
        logger.info("redis_bus.agent_registered", agent=agent.name, total=len(self._agents))

    def unregister(self, name: str) -> None:
        self._agents.pop(name, None)

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    async def publish(self, message: Message) -> None:
        self._history.append(message)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history :]

        await self._deliver_local(message)

        if self._redis is not None:
            try:
                channel = f"{self.channel_prefix}:{message.receiver}"
                payload = self._serialize(message)
                await self._redis.publish(channel, payload)
            except Exception as e:
                logger.exception("redis_bus.publish_error", error=str(e))

    async def _deliver_local(self, message: Message) -> None:
        if message.receiver == "*":
            for agent in self._agents.values():
                if agent.name == message.sender:
                    continue
                await self._safe_handle(agent, message)
            return
        agent = self._agents.get(message.receiver)
        if agent is not None:
            await self._safe_handle(agent, message)

    async def _safe_handle(self, agent: "BaseAgent", message: Message) -> None:
        try:
            await agent.handle(message)
        except Exception as e:
            logger.exception("redis_bus.handle_error", agent=agent.name, error=str(e))

    async def _listen_loop(self) -> None:
        if self._pubsub is None:
            return
        try:
            async for raw in self._pubsub.listen():
                if raw.get("type") != "pmessage":
                    continue
                try:
                    data = json.loads(raw["data"])
                    msg = self._deserialize(data)
                    if msg.sender in self._agents:
                        continue
                    await self._deliver_local(msg)
                except Exception as e:
                    logger.exception("redis_bus.listen_parse_error", error=str(e))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("redis_bus.listen_error", error=str(e))

    @staticmethod
    def _serialize(message: Message) -> str:
        return json.dumps(
            {
                "id": message.id,
                "sender": message.sender,
                "receiver": message.receiver,
                "content": message.content,
                "msg_type": message.msg_type,
                "created_at": message.created_at.isoformat(),
            },
            default=str,
        )

    @staticmethod
    def _deserialize(data: dict[str, Any]) -> Message:
        return Message(
            id=data["id"],
            sender=data["sender"],
            receiver=data["receiver"],
            content=data["content"],
            msg_type=data.get("msg_type", "task"),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    def history(self) -> list[Message]:
        return list(self._history)

    def __repr__(self) -> str:
        return f"<RedisMessageBus agents={len(self._agents)} url={self.redis_url}>"