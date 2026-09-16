"""Hybrid Router agent - regex + LLM ile akilli yonlendirme."""
from __future__ import annotations

import re
import time
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


REGEX_RULES: list[tuple[str, str]] = [
    (r"\b(cpu|ram|bellek|disk|sunucu|sistem\s*durum|uptime|kaynak\s*kullan)", "system"),
    (r"\b(yazd[ıi]r|hesapla|calist[ıi]r|kod\s*yaz|fonksiyon\s*yaz|program\s*yaz|algoritma\s*yaz|python\s*kod|faktoriyel|fibonacci)", "coder"),
    (r"\b(ozetle|ozet\s*c[ıi]kar|k[ıi]saca\s*anlat|k[ıi]sa\s*ozet)", "summarizer"),
    (r"\b(incele|review|degerlendir|geri\s*bildirim)", "reviewer"),
    (r"\b(planla|ad[ıi]mlara\s*bol|organize\s*et)", "planner"),
    (r"\b(guncel|son\s*dakika|haber|ne\s*zaman|kim\s*kazand[ıi]|202[4-9]|2030)", "researcher"),
    (r"\b(nedir|ne\s*demek|tan[ıi]m|a[çc][ıi]kla|merhaba|selam|nas[ıi]ls[ıi]n|sen\s*kimsin)", "llm"),
]


def classify_by_regex(query: str) -> str | None:
    """Regex ile hizli siniflandirma."""
    lower = query.lower()
    for pattern, agent in REGEX_RULES:
        if re.search(pattern, lower):
            return agent
    return None


ROUTER_PROMPT = """Sen bir yonlendiricisin. Soruyu analiz edip en uygun agent'i sec.

AGENT'LAR:
- llm: Genel bilgi, tanim, sohbet
- researcher: Guncel bilgi, haber, tarihli olay
- coder: Kod yazma, hesaplama
- system: Sistem durumu
- summarizer: Ozet
- reviewer: Kod inceleme
- planner: Planlama

SADECE bir kelime dondur.

Ornek:
Soru: Python nedir? -> llm
Soru: 2026 Dunya Kupasi sampiyonu kim? -> researcher
Soru: Fibonacci yazdir -> coder

Cevap:"""


VALID_AGENTS = {"researcher", "coder", "system", "summarizer", "reviewer", "llm", "planner"}


class RouterAgent(BaseAgent):
    """Hybrid router: once regex, sonra LLM."""

    def __init__(
        self,
        name: str,
        bus: Any,
        model: str | None = None,
        default_agent: str = "llm",
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

    def __repr__(self) -> str:
        return f"<RouterAgent name={self.name!r} model={self.model}>"