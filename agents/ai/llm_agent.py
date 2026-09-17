"""Groq tabanli LLM Agent (guvenli - uydurma yapmaz)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


DEFAULT_SYSTEM_PROMPT = """Sen yardimci bir AI asistansin. Turkce, net ve faydali cevaplar verirsin.

KRITIK KURALLAR:
1. Kisi isimleri (baskan, vali, milletvekili, sanatci, sporcu) hakkinda TAHMIN YURUTME.
2. Tarihler, guncel olaylar, haberler hakkinda TAHMIN YURUTME.
3. Yer isimleri (sehir, ulke, belediye) hakkinda TAHMIN YURUTME.
4. Emin olmadigin bilgiler icin: "Bu bilgiyi dogrulayamadim, guncel kaynaklara bakmak gerekir" de.
5. Uydurma YAPMA.

Sadece genel bilgi (tanim, kavram, nasil yapilir) sorularina cevap ver.
"""


# Uydurma riski yuksek sorular -> researcher'a yonlendir
FRESH_INFO_PATTERNS = [
    r"\bkim\b", r"\bkimdir\b",
    r"\bnerede\b", r"\bne\s*zaman\b", r"\bhangi\b", r"\bka[çc]\b",
    r"\bbelediye\s*ba[şs]kan", r"\bvali\b", r"\bmilletvekili\b",
    r"\bbakan\b", r"\bcumhurba[şs]kan", r"\bba[şs]bakan\b",
    r"\bteknik\s*direkt[oö]r", r"\btransfer\b", r"\b[şs]ampiyon\b",
    r"\bse[çc]im\b", r"\bson\s*dakika\b", r"\bhaber\b",
    r"\bguncel\b", r"\b[şs]u\s*an\b",
    r"\b202[4-9]\b", r"\b20[3-9]\d\b",
]


def _needs_fresh_info(query: str) -> bool:
    """Sorgu guncel bilgi gerektiriyor mu?"""
    lower = query.lower()
    for pattern in FRESH_INFO_PATTERNS:
        if re.search(pattern, lower):
            return True
    return False


class LLMAgent(BaseAgent):
    """Groq LLM cagrilarini yapan ajan (guvenli mod)."""

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

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        query = str(message.content)

        # Guncel bilgi gerektiren sorular -> researcher'a yonlendir
        if self.auto_redirect and _needs_fresh_info(query):
            logger.info("llm.redirect_to_researcher", query=query[:80])
            await self.send("researcher", query, msg_type="task")
            return

        # Normal LLM cevabi (sadece genel bilgi)
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