"""Translator Agent - ceviri agent'i."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from skills.translation_skill import TranslationSkill

logger = structlog.get_logger(__name__)


class TranslatorAgent(BaseAgent):
    """Ceviri yapan agent."""

    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)
        self.skill = TranslationSkill()

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return
        try:
            text = str(message.content)
            # Basit dil algilama: "ingilizceye cevir" -> en
            target = "en"
            lower = text.lower()
            if "turkce" in lower or "türkçe" in lower:
                target = "tr"
            elif "almanca" in lower:
                target = "de"
            elif "fransizca" in lower or "fransızca" in lower:
                target = "fr"

            # Metni temizle
            for w in ["ingilizceye cevir", "turkceye cevir", "türkçeye çevir",
                      "almancaya cevir", "fransizcaya cevir", "cevir", "çevir"]:
                text = text.replace(w, "").replace(w.title(), "")
            text = text.strip(" :.,!")

            result = await self.skill(text=text, target_lang=target)
            answer = result.get("translation", result.get("error", "Ceviri yapilamadi"))
            await self.send(message.sender, {"answer": answer}, msg_type="result")
            logger.info("translator.done", target=target, length=len(answer))
        except Exception as e:
            logger.exception("translator.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<TranslatorAgent name={self.name!r}>"
