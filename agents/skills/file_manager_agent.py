"""File Manager Agent - dosya islemleri."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from skills.file_operations_skill import FileOperationsSkill

logger = structlog.get_logger(__name__)


class FileManagerAgent(BaseAgent):
    """Dosya islemleri yapan agent."""

    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)
        self.skill = FileOperationsSkill()

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return
        try:
            text = str(message.content)
            lower = text.lower()

            if "listele" in lower or "list" in lower:
                result = await self.skill(action="list", path="")
                answer = f"Toplam {result.get('count', 0)} dosya"
            elif "oku" in lower or "read" in lower:
                result = await self.skill(action="read", path="")
                answer = result.get("content", result.get("error", ""))
            else:
                answer = "Kullanim: 'listele' veya 'oku <dosya>'"

            await self.send(message.sender, {"answer": answer}, msg_type="result")
            logger.info("file_manager.done")
        except Exception as e:
            logger.exception("file_manager.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<FileManagerAgent name={self.name!r}>"
