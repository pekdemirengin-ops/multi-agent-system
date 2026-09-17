"""Groq tabanli LLM Agent (akilli yonlendirme)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


DEFAULT_SYSTEM_PROMPT = """Sen yardimci bir AI asistansin. Turkce, net ve faydali cevaplar verirsin.

Kurallar:
- Soruya dogrudan cevap ver
- Maddeler halinde, oz ve net ol
- Ornek ver (gerekiyorsa)
- En fazla 5 madde kullan
- Gereksiz uzatma
"""

# Guncel bilgi gerektiren sorular
FRESH_INFO_KEYWORDS = [
    "kim", "ne zaman", "guncel", "son", "yeni", "su an", "simdi",
    "baskan", "devlet baskani", "cumhurbaskani", "seçim", "secim",
]

# Yillar (2024+)
FRESH_YEAR_PATTERN = re.compile(r"\b(202[4-9]|203[0-9])\b")


class LLMAgent(BaseAgent):
    """Groq LLM cagrilarini yapan ajan (akilli yonlendirme)."""

    def __init__(
        self,
        name: str,
        bus: Any,
        model: str | None = None,
        system_prompt: str | None = None,
        auto_redirect: bool = True,
    ) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model=model)
        base_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        today = datetime.now().strftime("%Y-%m-%d")
        self.system_prompt = f"{base_prompt}\n\nBugunun tarihi: {today}"
        self.auto_redirect = auto_redirect

    def _needs_fresh_info(self, query: str) -> bool:
        """Sorgunun guncel bilgi gerektirip gerektirmedigini belirler."""
        lower = query.lower()

        # Yil var mi? (2024+)
        if FRESH_YEAR_PATTERN.search(lower):
            return True

        # Guncel kelimeler var mi?
        for kw in FRESH_INFO_KEYWORDS:
            if kw in lower:
                return True

        return False

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        query = str(message.content)

        # Guncel bilgi gerekiyorsa researcher'a yonlendir
        if self.auto_redirect and self._needs_fresh_info(query):
            logger.info("llm.redirect_to_researcher", query=query[:80])
            await self.send(
                "researcher",
                query,
                msg_type="task",
            )
            return

        # Normal LLM cevabi
        try:
            answer = self.llm.chat(
                prompt=query,
                system=self.system_prompt,
            )
            logger.info("llm.response", agent=self.name, length=len(answer))
            await self.send(
                message.sender,
                {"answer": answer},
                msg_type="result",
            )
        except Exception as e:
            logger.exception("llm.error", agent=self.name, error=str(e))
            await self.send(
                message.sender,
                {"error": str(e)},
                msg_type="error",
            )

    def __repr__(self) -> str:
        return f"<LLMAgent name={self.name!r} model={self.llm.model}>"