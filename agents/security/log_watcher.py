"""Log tarama agent'i - tehdit tespit eder."""
from __future__ import annotations

from typing import Any

import structlog

from agents.security.threat_patterns import scan_line
from core.base_agent import BaseAgent, Message

logger = structlog.get_logger(__name__)


class LogWatcherAgent(BaseAgent):
    """Log satirlarini tarar, tehditleri tespit eder."""

    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)
        self.threat_count = 0

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        try:
            # Icerik: log satiri veya satirlar
            content = str(message.content)
            lines = content.split("\n")

            all_threats: list[dict[str, Any]] = []
            for i, line in enumerate(lines, 1):
                threats = scan_line(line)
                for t in threats:
                    t["line_number"] = i
                    all_threats.append(t)
                    self.threat_count += 1

                    # Kritik tehdit -> alert agent'a gonder
                    if t["severity"] in ("critical", "high"):
                        await self.send(
                            "alert",
                            {
                                "type": "threat",
                                "severity": t["severity"],
                                "category": t["category"],
                                "line": t["line"],
                                "line_number": t["line_number"],
                            },
                            msg_type="alert",
                        )

            logger.info(
                "log_watcher.scan_done",
                lines=len(lines),
                threats=len(all_threats),
            )

            await self.send(
                message.sender,
                {
                    "research": self._format_report(all_threats, len(lines)),
                    "sources": [],
                    "source_count": 0,
                    "threat_count": len(all_threats),
                    "total_threats": self.threat_count,
                },
                msg_type="result",
            )

        except Exception as e:
            logger.exception("log_watcher.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    @staticmethod
    def _format_report(threats: list[dict[str, Any]], lines_scanned: int) -> str:
        if not threats:
            return f"Tarama tamamlandi: {lines_scanned} satir, tehdit bulunamadi."

        lines = [
            f"Tarama tamamlandi: {lines_scanned} satir, {len(threats)} tehdit bulundu.",
            "",
        ]

        # Onem seviyesine gore grupla
        by_severity: dict[str, list[dict[str, Any]]] = {}
        for t in threats:
            by_severity.setdefault(t["severity"], []).append(t)

        for severity in ["critical", "high", "medium", "low"]:
            if severity not in by_severity:
                continue
            lines.append(f"### {severity.upper()} ({len(by_severity[severity])} adet)")
            for t in by_severity[severity][:5]:
                lines.append(f"- [{t['category']}] satir {t['line_number']}: {t['line'][:80]}")
            lines.append("")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"<LogWatcherAgent name={self.name!r} threats={self.threat_count}>"