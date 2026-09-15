"""Agent kayıt ve oluşturma sistemi."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Type

import structlog

from core.base_agent import BaseAgent

if TYPE_CHECKING:
    from core.message_bus import MessageBus

logger = structlog.get_logger(__name__)


class AgentRegistry:
    """Agent sınıflarını isimle kaydeder ve toplu oluşturur.

    Kullanım:
        registry = AgentRegistry()
        registry.add("planner", PlannerAgent)
        registry.add("coder", LLMAgent, model="gpt-4o-mini")
        agents = registry.create_all(bus)
    """

    def __init__(self) -> None:
        self._entries: dict[str, tuple[Type[BaseAgent], dict[str, Any]]] = {}

    def add(
        self,
        name: str,
        agent_cls: Type[BaseAgent],
        **kwargs: Any,
    ) -> None:
        """Bir agent sınıfını isimle kaydeder.

        Args:
            name: Agent'ın benzersiz adı (bus'ta bu isimle görünür)
            agent_cls: BaseAgent'tan türeyen sınıf
            **kwargs: Agent __init__'ine geçilecek ek parametreler
        """
        if not issubclass(agent_cls, BaseAgent):
            raise TypeError(f"{agent_cls.__name__} BaseAgent'tan türemeli")
        if name in self._entries:
            raise ValueError(f"Agent adı zaten kayıtlı: {name}")
        self._entries[name] = (agent_cls, kwargs)
        logger.info("registry.added", name=name, cls=agent_cls.__name__)

    def remove(self, name: str) -> None:
        self._entries.pop(name, None)

    def get(self, name: str) -> Type[BaseAgent] | None:
        entry = self._entries.get(name)
        return entry[0] if entry else None

    def list_entries(self) -> dict[str, str]:
        """Kayıtlı agent'ları {isim: sınıf_adı} olarak döner."""
        return {name: cls.__name__ for name, (cls, _) in self._entries.items()}

    def create(self, name: str, bus: "MessageBus") -> BaseAgent:
        """Tek bir agent'ı oluşturur."""
        if name not in self._entries:
            raise KeyError(f"Agent kayıtlı değil: {name}")
        cls, kwargs = self._entries[name]
        return cls(name=name, bus=bus, **kwargs)

    def create_all(self, bus: "MessageBus") -> list[BaseAgent]:
        """Kayıtlı tüm agent'ları oluşturur ve döner."""
        agents: list[BaseAgent] = []
        for name, (cls, kwargs) in self._entries.items():
            try:
                agent = cls(name=name, bus=bus, **kwargs)
                agents.append(agent)
            except Exception as e:
                logger.exception("registry.create.error", name=name, error=str(e))
        logger.info("registry.created_all", count=len(agents))
        return agents

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"<AgentRegistry entries={len(self._entries)}>"