"""Hybrid Router agent - regex + LLM ile akilli yonlendirme."""
from __future__ import annotations

import re
import time
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


# ============================================================
# GUNCEL BILGI KURALLARI (researcher'a gider)
# ============================================================
FRESH_INFO_PATTERNS = [
    # Soru kelimeleri
    r"\bkim\b", r"\bkimdir\b", r"\bkimler\b",
    r"\bnerede\b", r"\bnerede\b", r"\bnerede\b",
    r"\bne\s*zaman\b", r"\bhangi\b", r"\bka[çc]\b",
    # Yerel yonetim
    r"\bbelediye\s*ba[şs]kan", r"\bvali\b", r"\bmilletvekili\b",
    r"\bbakan\b", r"\bcumhurba[şs]kan", r"\bba[şs]bakan\b",
    # Spor
    r"\bteknik\s*direkt[oö]r", r"\btransfer\b", r"\b[şs]ampiyon\b",
    # Guncel olaylar
    r"\bse[çc]im\b", r"\bse[çc]im\s*sonu[çc]", r"\bson\s*dakika\b",
    r"\bhaber\b", r"\bguncel\b", r"\bson\b", r"\byeni\b",
    r"\b[şs]u\s*an\b", r"\b[şs]imdi\b",
    # Yillar (2024+)
    r"\b202[4-9]\b", r"\b20[3-9]\d\b",
    # Belirli sorular
    r"\bka[çc]\s*ya[şs]", r"\bnereli\b", r"\bka[çc]\s*y[ıi]l",
]

# Bu pattern'ler "auto"da llm'e gitsin (genel bilgi)
GENERAL_INFO_PATTERNS = [
    r"\bnedir\b", r"\bne\s*demek\b", r"\btan[ıi]m\b",
    r"\bmerhaba\b", r"\bselam\b", r"\bnas[ıi]ls[ıi]n\b",
    r"\bsen\s*kimsin\b", r"\bte[şs]ekk[uü]r\b",
]

# Kod/hesaplama
CODER_PATTERNS = [
    r"\byazd[ıi]r\b", r"\bhesapla\b", r"\bcal[ıi][şs]t[ıi]r\b",
    r"\bkod\s*yaz\b", r"\bfonksiyon\s*yaz\b", r"\bprogram\s*yaz\b",
    r"\balgoritma\s*yaz\b", r"\bpython\s*kod\b",
    r"\bfaktoriyel\b", r"\bfibonacci\b",
]

# Sistem
SYSTEM_PATTERNS = [
    r"\bcpu\b", r"\bram\b", r"\bbellek\b", r"\bdisk\b",
    r"\bsunucu\b", r"\bsistem\s*durum\b", r"\buptime\b",
    r"\bkaynak\s*kullan",
]

# Ozet/review/plan
OTHER_PATTERNS = {
    "summarizer": [r"\bozetle\b", r"\bozet\s*[çc][ıi]kar\b", r"\bk[ıi]saca\s*anlat\b"],
    "reviewer": [r"\bincele\b", r"\breview\b", r"\bde[ğg]erlendir\b"],
    "planner": [r"\bplanla\b", r"\bad[ıi]mlara\s*b[oö]l\b", r"\borganize\s*et\b"],
}


def classify_by_regex(query: str) -> str | None:
    """Regex ile hizli siniflandirma. Sira onemli!"""
    lower = query.lower()

    # 1) Kod/hesaplama
    for pattern in CODER_PATTERNS:
        if re.search(pattern, lower):
            return "coder"

    # 2) Sistem
    for pattern in SYSTEM_PATTERNS:
        if re.search(pattern, lower):
            return "system"

    # 3) Ozet/review/plan
    for agent, patterns in OTHER_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, lower):
                return agent

    # 4) GUNCEL BILGI (researcher) - genel bilgiden ONCE
    for pattern in FRESH_INFO_PATTERNS:
        if re.search(pattern, lower):
            return "researcher"

    # 5) Genel bilgi (llm)
    for pattern in GENERAL_INFO_PATTERNS:
        if re.search(pattern, lower):
            return "llm"

    return None


ROUTER_PROMPT = """Sen bir yonlendiricisin. Soruyu analiz edip en uygun agent'i sec.

AGENT'LAR:
- researcher: Guncel bilgi, haber, kisi/yer isimleri, tarihli olaylar, kim/ne zaman/nerede sorulari
- coder: Kod yazma, hesaplama, matematik
- system: Sistem durumu (CPU, RAM, disk)
- summarizer: Ozet
- reviewer: Kod inceleme
- planner: Planlama
- llm: SADECE genel tanim (nedir, ne demek), selamlama

ONEMLI: Kisi ismi, yer ismi, tarih, guncel olay iceren sorular HER ZAMAN researcher'a gider.

SADECE bir kelime dondur.

Ornek:
Soru: Python nedir? -> llm
Soru: Kozan belediye baskani kim? -> researcher
Soru: Istanbul valisi kim? -> researcher
Soru: 2026 Dunya Kupasi sampiyonu kim? -> researcher
Soru: Fibonacci yazdir -> coder
Soru: Merhaba -> llm
"""


VALID_AGENTS = {"researcher", "coder", "system", "summarizer", "reviewer", "llm", "planner"}


class RouterAgent(BaseAgent):
    """Hybrid router: once regex, sonra LLM."""

    def __init__(
        self,
        name: str,
        bus: Any,
        model: str | None = None,
        default_agent: str = "researcher",
        use_fast_model: bool = True,
    ) -> None:
        super().__init__(name, bus)
        self.model = model or ("llama-3.1-8b-instant" if use_fast_model else None)
        self.llm = GroqLLMClient(model=self.model)
        self.default_agent = default_agent

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        try:
            query = str(message.content)
            start = time.perf_counter()

            chosen = classify_by_regex(query)
            method = "regex"

            if chosen is None:
                chosen = self._classify_llm(query)
                method = "llm"

            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.info("router.done", query=query[:50], agent=chosen, method=method, duration_ms=duration_ms)

            await self.send(
                message.sender,
                {
                    "agent": chosen,
                    "research": chosen,
                    "sources": [],
                    "source_count": 0,
                    "query": query,
                    "router_method": method,
                    "router_duration_ms": duration_ms,
                },
                msg_type="result",
            )
        except Exception as e:
            logger.exception("router.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def _classify_llm(self, query: str) -> str:
        try:
            raw = self.llm.chat(prompt=f"Soru: {query}\n\nCevap:", system=ROUTER_PROMPT)
            agent = raw.strip().lower().split()[0].strip(".,!?:;\"'`*")
            if agent in VALID_AGENTS:
                return agent
            logger.warning("router.invalid_llm_response", raw=raw[:50], agent=agent)
        except Exception as e:
            logger.exception("router.llm_error", error=str(e))
        return self.default_agent