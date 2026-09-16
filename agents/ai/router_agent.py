"""Router agent - soruyu analiz edip en uygun agent'i secer."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


ROUTER_PROMPT = """Sen bir yonlendiricisin. Kullanicinin sorusunu analiz edip
en uygun agent'i secersin.

KULLANILABILIR AGENT'LAR:

1. llm - GENEL BILGI ve SOHBET (ONCELIKLI)
   - Tanimlar: "Python nedir?", "JavaScript nedir?", "Yapay zeka nedir?"
   - Sohbet: "Merhaba", "Nasilsin?", "Sen kimsin?"
   - Genel sorular: "Nasil calisir?", "Neden onemli?"
   - Matematik, felsefe, bilim (temel bilgi)
   ANAHTAR: nedir, tanim, acikla, nasil, neden, merhaba, sen, sohbet

2. researcher - GUNCEL BILGI, HABER, TARIHLI OLAYLAR
   - "2026 Dunya Kupasi sampiyonu kim?" (guncel spor)
   - "2024 Nobel Odulu kime verildi?" (guncel haber)
   - "Bugun hava nasil?" (guncel durum)
   - "X olayi ne zaman oldu?" (tarihli olay)
   - "En son ne oldu?" (guncel)
   ANAHTAR: guncel, son, haber, tarih, kim kazandi, ne zaman, bugun, 2024, 2025, 2026

   ONEMLI: "X nedir?" sorusu LLM'e gider. "X ne zaman oldu?" sorusu RESEARCHER'a gider.

3. coder - KOD YAZMA/CALISTIRMA
   - "Fibonacci yazdir"
   - "Asal sayi fonksiyonu yaz"
   - "Faktoriyel hesapla"
   ANAHTAR: yaz, yazdir, hesapla, calistir, fonksiyon, kod, program, algoritma

4. system - SUNUCU/SISTEM DURUMU
   - "Sistem durumu nedir?"
   - "CPU ne kadar?"
   ANAHTAR: cpu, ram, bellek, disk, sunucu, sistem durumu, uptime

5. summarizer - OZET
   ANAHTAR: ozet, kisaca, ozetle

6. reviewer - KOD INCELEME
   ANAHTAR: incele, review, degerlendir

7. planner - PLANLAMA
   ANAHTAR: planla, adim, organize

ORNEKLER:
- "Python nedir?" -> llm
- "2026 Dunya Kupasi sampiyonu kim?" -> researcher
- "Fibonacci yazdir" -> coder
- "Sistem durumu" -> system
- "Merhaba" -> llm
- "2024 Nobel Odulu kime verildi?" -> researcher
- "JavaScript nedir?" -> llm

SADECE bir kelime dondur (agent adi). Baska hicbir sey yazma.
Ornek cevaplar: llm, researcher, coder, system, summarizer, reviewer, planner
"""


VALID_AGENTS = {"researcher", "coder", "system", "summarizer", "reviewer", "llm", "planner"}


class RouterAgent(BaseAgent):
    """Soruyu analiz edip en uygun agent'i secer."""

    def __init__(
        self,
        name: str,
        bus: Any,
        model: str | None = None,
        default_agent: str = "llm",
    ) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model=model)
        self.default_agent = default_agent

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        try:
            query = str(message.content)
            chosen = self._classify(query)
            logger.info("router.done", query=query[:60], agent=chosen)

            await self.send(
                message.sender,
                {
                    "agent": chosen,
                    "research": chosen,
                    "sources": [],
                    "source_count": 0,
                    "query": query,
                },
                msg_type="result",
            )
        except Exception as e:
            logger.exception("router.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def _classify(self, query: str) -> str:
        """LLM ile sorgu siniflandirir."""
        try:
            raw = self.llm.chat(prompt=f"Soru: {query}", system=ROUTER_PROMPT)
            agent = raw.strip().lower().split()[0].strip(".,!?:;\"'`*")
            if agent in VALID_AGENTS:
                return agent
            logger.warning("router.invalid_response", raw=raw[:50], agent=agent)
        except Exception as e:
            logger.exception("router.classify_error", error=str(e))

        return self.default_agent

    def __repr__(self) -> str:
        return f"<RouterAgent name={self.name!r}>"