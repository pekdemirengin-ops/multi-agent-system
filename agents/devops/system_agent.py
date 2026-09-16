"""Sistem izleme agent'i - CPU, RAM, disk raporlar."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient
from tools.system_info import check_thresholds, format_status, get_system_status

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """Sen bir sistem izleme uzmanisin. Sana verilen sistem metriklerini
yorumlar, olasi sorunlari belirtir, gerekiyorsa onerilerde bulunursun.

Kisa ve net cevap ver. En fazla 3 madde kullan.
"""


class SystemAgent(BaseAgent):
    """Sistem metriklerini raporlayan ve yorumlayan agent."""

    def __init__(
        self,
        name: str,
        bus: Any,
        model: str | None = None,
        cpu_limit: float = 85.0,
        mem_limit: float = 90.0,
        disk_limit: float = 90.0,
    ) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model=model)
        self.cpu_limit = cpu_limit
        self.mem_limit = mem_limit
        self.disk_limit = disk_limit

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        try:
            status = get_system_status()
            alerts = check_thresholds(
                status,
                cpu_limit=self.cpu_limit,
                mem_limit=self.mem_limit,
                disk_limit=self.disk_limit,
            )

            formatted = format_status(status)
            prompt = (
                f"Sistem metrikleri:\n{formatted}\n\n"
                f"Uyarilar: {alerts if alerts else 'Yok'}\n\n"
                f"Kullanicinin sorusu: {message.content}"
            )
            comment = self.llm.chat(prompt=prompt, system=SYSTEM_PROMPT)

            logger.info(
                "system_agent.done",
                cpu=status["cpu_percent"],
                mem=status["memory_percent"],
                alerts=len(alerts),
            )

            await self.send(
                message.sender,
                {
                    "research": comment,
                    "status": status,
                    "alerts": alerts,
                    "sources": [],
                    "source_count": 0,
                },
                msg_type="result",
            )

        except Exception as e:
            logger.exception("system_agent.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<SystemAgent name={self.name!r}>"