"""Intent Analyzer - Cogul + coklu varlik destekli."""
from __future__ import annotations

import json
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


INTENT_PROMPT = """Sen bir soru analiz uzmanisin. Kullanicinin sorusunu analiz et ve NE ISTEDIGINI JSON olarak don.

Soru tiplerini tani:
- "tanit", "anlat", "bilgi ver", "hakkinda", "ozgecmis" -> BYOGRAF
- "kimdir", "kim" -> KIMLIK (TEK kisi)
- "kimler" -> KIMLER (COKLU kisi/kurum - HEPSINI listele)
- "nerede", "hangi ulke" -> YER
- "ne zaman", "hangi yil" -> ZAMAN
- "kac", "yuz olcumu", "nufus" -> SAYISAL
- "listele", "say", "hepsi" -> LISTE (COKLU)
- "karsilastir", "fark" -> KARSILASTIRMA
- "neden", "nicin" -> NEDEN

ONEMLI: "kimler", "hangileri", "hepsi", "kac tane" gibi COGUL sorulari tespit et.
Cogul sorularda: birden fazla varlik varsa HEPSINI getir.

SADECE su JSON formatinda cevap ver:
{
  "intent": "tanit|kimdir|kimler|nerede|ne_zaman|sayisal|liste|karsilastir|neden|genel",
  "is_plural": true|false,
  "subject": "sorunun ana konusu",
  "expected_count": sayi veya null,
  "fields": ["istenen bilgi alanlari"],
  "turkish_queries": ["sorgu1", "sorgu2", "sorgu3"]
}

ORNEK 1 (cogul):
Soru: "Istanbul bogaz koprusunu kimler, kac yilinda yapti?"
Cevap: {
  "intent": "kimler",
  "is_plural": true,
  "subject": "Istanbul Bogazi kopruleri",
  "expected_count": 3,
  "fields": ["kopru adi", "yapimci", "yil"],
  "turkish_queries": [
    "Istanbul Bogazi kopruleri listesi",
    "15 Temmuz Sehitler Koprusu yapimci yil",
    "Fatih Sultan Mehmet Koprusu yapimci yil",
    "Yavuz Sultan Selim Koprusu yapimci yil"
  ]
}

ORNEK 2 (tekil):
Soru: "Adana valisini tanit"
Cevap: {
  "intent": "tanit",
  "is_plural": false,
  "subject": "Adana valisi",
  "expected_count": 1,
  "fields": ["ad", "dogum", "egitim", "kariyer"],
  "turkish_queries": ["Adana valisi kimdir", "Adana valisi biyografi", "Adana valisi ozgecmis"]
}

ORNEK 3 (sayisal):
Soru: "Kozan yuz olcumu kac km2"
Cevap: {
  "intent": "sayisal",
  "is_plural": false,
  "subject": "Kozan yuz olcumu",
  "expected_count": 1,
  "fields": ["yuz olcumu"],
  "turkish_queries": ["Kozan yuz olcumu km2", "Kozan alan"]
}

Simdi sen analiz et:
"""


class IntentAnalyzer(BaseAgent):
    """LLM ile soru niyetini + cogul/tekil analiz eder."""

    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model="openai/gpt-oss-120b")

    def analyze(self, query: str) -> dict:
        """Soruyu analiz eder."""
        try:
            raw = self.llm.chat(
                prompt=f"Soru: {query}",
                system=INTENT_PROMPT,
            )
            raw = raw.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
                logger.info("intent.analyzed",
                            intent=data.get("intent"),
                            plural=data.get("is_plural"),
                            queries=len(data.get("turkish_queries", [])))
                return data

        except Exception as e:
            logger.exception("intent.error", error=str(e))

        # Fallback
        return {
            "intent": "genel",
            "is_plural": False,
            "subject": query,
            "expected_count": 1,
            "fields": [],
            "turkish_queries": [query, f"{query} kimdir"],
        }

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return
        query = str(message.content)
        result = self.analyze(query)
        await self.send(message.sender, result, msg_type="result")

    def __repr__(self) -> str:
        return f"<IntentAnalyzer name={self.name!r}>"
