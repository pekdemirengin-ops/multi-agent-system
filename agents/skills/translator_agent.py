"""Translator Agent - ceviri agent'i."""
from __future__ import annotations

import re
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
            lower = text.lower()

            # Hedef dil
            target = "en"
            if "türkçe" in lower or "turkce" in lower:
                target = "tr"
            elif "almanca" in lower:
                target = "de"
            elif "fransızca" in lower or "fransizca" in lower:
                target = "fr"
            elif "ispanyolca" in lower:
                target = "es"
            elif "rusça" in lower or "rusca" in lower:
                target = "ru"

            # Metni temizle: "cevir", "çevir", "ingilizceye", "türkçeye" vs.
            clean = text
            patterns = [
                r"\bingilizceye\s+[çc]evir\b",
                r"\bt[üu]rk[çc]eye\s+[çc]evir\b",
                r"\balmancaya\s+[çc]evir\b",
                r"\bfrans[ıi]zcaya\s+[çc]evir\b",
                r"\bispanyolcaya\s+[çc]evir\b",
                r"\brus[çc]aya\s+[çc]evir\b",
                r"\b[çc]evir\b",
                r"\btranslate\s+to\s+\w+\b",
                r"\btranslate\b",
            ]
            for p in patterns:
                clean = re.sub(p, "", clean, flags=re.IGNORECASE)
            clean = clean.strip(" :.,!?")

            if not clean:
                clean = text

            result = await self.skill(text=clean, target_lang=target)
            answer = result.get("translation", result.get("error", "Ceviri yapilamadi"))

            await self.send(message.sender, {"answer": answer}, msg_type="result")
            logger.info("translator.done", target=target, length=len(answer))
        except Exception as e:
            logger.exception("translator.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<TranslatorAgent name={self.name!r}>"
