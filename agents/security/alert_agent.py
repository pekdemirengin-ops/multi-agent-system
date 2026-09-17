"""Uyari toplama agent'i."""
from __future__ import annotations

import time
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message

logger = structlog.get_logger(__name__)


class AlertAgent(BaseAgent):
    """Uyarilari toplar ve raporlar."""

    def __init__(self, name: str, bus: Any, max_alerts: int = 100) -> None:
        super().__init__(name, bus)
        self.alerts: list[dict[str, Any]] = []
        self.max_alerts = max_alerts
        self.critical_count = 0
        self.high_count = 0
        self.medium_count = 0
        self.low_count = 0

    async def handle(self, message: Message) -> None:
        if message.msg_type not in ("alert", "task"):
            return

        if message.msg_type == "alert":
            content = message.content if isinstance(message.content, dict) else {"message": str(message.content)}
            content["received_at"] = time.time()
            self.alerts.append(content)
            if len(self.alerts) > self.max_alerts:
                self.alerts = self.alerts[-self.max_alerts:]

            severity = content.get("severity", "low")
            if severity == "critical":
                self.critical_count += 1
            elif severity == "high":
                self.high_count += 1
            elif severity == "medium":
                self.medium_count += 1
            else:
                self.low_count += 1

            logger.warning(
                "alert.received",
                severity=severity,
                category=content.get("category", "unknown"),
            )
            return

        # task: mevcut uyarilari raporla
        await self.send(
            message.sender,
            {
                "research": self._format_alerts(),
                "sources": [],
                "source_count": 0,
                "alert_count": len(self.alerts),
            },
            msg_type="result",
        )

    def _format_alerts(self) -> str:
        if not self.alerts:
            return "Aktif uyari yok."

        lines = [
            f"Toplam {len(self.alerts)} uyari:",
            f"- CRITICAL: {self.critical_count}",
            f"- HIGH: {self.high_count}",
            f"- MEDIUM: {self.medium_count}",
            f"- LOW: {self.low_count}",
            "",
            "Son 5 uyari:",
        ]
        for a in self.alerts[-5:]:
            lines.append(
                f"- [{a.get('severity', '?').upper()}] "
                f"{a.get('category', 'unknown')}: "
                f"{str(a.get('line', ''))[:60]}"
            )
        return "\n".join(lines)

    def clear(self) -> None:
        self.alerts.clear()
        self.critical_count = 0
        self.high_count = 0
        self.medium_count = 0
        self.low_count = 0

    def __repr__(self) -> str:
        return f"<AlertAgent alerts={len(self.alerts)} critical={self.critical_count}>"