"""Router agent - soruyu analiz edip en uygun agent'i secer."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


ROUTER_PROMPT = """Sen bir yonlendiricisin. Kullanicinin sorusunu analiz eder
ve en uygun agent'i secersin.

Kullanilabilir agent'lar:

- researcher: SADECE guncel bilgi, haber, tarih gerektiren sorular
  Ornek: "2024 Nobel Odulu kime verildi?", "Bugun hava nasil?", "X olayi ne zaman oldu?"
  DIKKAT: Genel tanimlar ("X nedir?") researcher'a GITMEZ, llm'e gider.
  Anahtar: guncel, haber, tarih, son dakika, kim kazandi

- coder: Kod YAZDIRMA veya CALISTIRMA istekleri
  Ornek: "Fibonacci yazdir", "Asal sayi fonksiyonu yaz", "Faktoriyel hesapla"
  Anahtar: yaz, yazdir, hesapla, calistir, fonksiyon, kod, algoritma

- system: Bu sunucunun/sistemin durumu
  Ornek: "Sistem durumu nedir?", "CPU ne kadar?", "RAM kullanim?"
  Anahtar: cpu, ram, bellek, disk, sunucu, kaynak, uptime, sistem durumu

- summarizer: Uzun metni ozetle
  Ornek: "Bu metni ozetle: ...", "Kisaca anlat"
  Anahtar: ozet, kisaca, ozetle

- reviewer: Kod incele
  Ornek: "Su kodu incele: ..."
  Anahtar: incele, review, geri bildirim, degerlendir

- llm: Genel bilgi sorulari, tanimlar, sohbet
  Ornek: "Python nedir?", "Fibonacci nedir?", "JavaScript nedir?", "Sen kimsin?", "Merhaba"
  Anahtar: nedir, tanim, acikla, ne, nasil, neden, merhaba, sen

- planner: Karmasik gorevleri planla
  Ornek: "X ve Y yap, planla"
  Anahtar: planla, adim, organize

ONEMLI KURALLAR:
1. "X nedir?" -> genellikle LLM (researcher DEGIL)
2. "X yazdir/hesapla" -> coder
3. "Guncel/haber" -> researcher
4. "Sistem/cpu/ram" -> system
5. Emin degilsen -> llm

SADECE bir kelime dondur (agent adi), baska hicbir sey yazma.
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
            agent = raw.strip().lower().split()[0].strip(".,!?:;\"'")
            if agent in VALID_AGENTS:
                return agent
            logger.warning("router.invalid_response", raw=raw[:50], agent=agent)
        except Exception as e:
            logger.exception("router.classify_error", error=str(e))

        return self.default_agent

    def __repr__(self) -> str:
        return f"<RouterAgent name={self.name!r}>"