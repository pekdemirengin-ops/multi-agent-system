"""Intent Analyzer Agent - LLM ile soru niyetini analiz eder."""
from __future__ import annotations

import json
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


INTENT_PROMPT = """Sen bir soru analiz uzmanisin. Kullanicinin sorusunu analiz et ve NE ISTEDIGINI JSON olarak don.

Soru tiplerini tani:
- "tanit", "anlat", "bilgi ver", "hakkinda", "ozgecmis" -> BYOGRAF (ad, dogum, egitim, kariyer, kisisel)
- "kimdir", "kim" -> KIMLIK (sadece ad, unvan)
- "nerede", "hangi ulke" -> YER
- "ne zaman", "hangi yil" -> ZAMAN
- "kac", "yuz olcumu", "nufus" -> SAYISAL
- "listele", "say" -> LISTE
- "karsilastir", "fark" -> KARSILASTIRMA

SADECE su JSON formatinda cevap ver:
{
  "intent": "tanit|kimdir|nerede|ne_zaman|sayisal|liste|karsilastir|genel",
  "subject": "sorunun ana konusu (ornek: Adana valisi)",
  "fields": ["istenen bilgi alanlari"],
  "turkish_queries": ["sorgu1", "sorgu2", "sorgu3"]
}

ORNEK 1:
Soru: "Adana valisini tanit"
Cevap: {
  "intent": "tanit",
  "subject": "Adana valisi",
  "fields": ["ad", "dogum", "egitim", "kariyer"],
  "turkish_queries": ["Adana valisi kimdir", "Adana valisi Mustafa Yavuz biyografi", "Adana valisi ozgecmis"]
}

ORNEK 2:
Soru: "Kozan yuz olcumu kac km2"
Cevap: {
  "intent": "sayisal",
  "subject": "Kozan yuz olcumu",
  "fields": ["yuz olcumu km2"],
  "turkish_queries": ["Kozan yuz olcumu km2", "Kozan alan"]
}

ORNEK 3:
Soru: "Ronaldo kimdir, hangi takimda oynuyor"
Cevap: {
  "intent": "kimdir",
  "subject": "Cristiano Ronaldo",
  "fields": ["kimlik", "takim"],
  "turkish_queries": ["Cristiano Ronaldo kimdir", "Cristiano Ronaldo hangi takimda oynuyor"]
}

Simdi sen analiz et:
"""


class IntentAnalyzer(BaseAgent):
    """LLM ile soru niyetini analiz eder."""

    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model="openai/gpt-oss-120b")

    def analyze(self, query: str) -> dict:
        """Soruyu analiz eder, JSON doner."""
        try:
            raw = self.llm.chat(
                prompt=f"Soru: {query}",
                system=INTENT_PROMPT,
            )
            # JSON cikar
            raw = raw.strip()
            # Code fence temizle
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            # JSON parse
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
                logger.info("intent.analyzed",
                            intent=data.get("intent"),
                            subject=data.get("subject"),
                            queries=len(data.get("turkish_queries", [])))
                return data

        except Exception as e:
            logger.exception("intent.error", error=str(e))

        # Fallback
        return {
            "intent": "genel",
            "subject": query,
            "fields": [],
            "turkish_queries": [query, f"{query} kimdir"],
        }

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        query = str(message.content)
        result = self.analyze(query)

        await self.send(
            message.sender,
            result,
            msg_type="result",
        )

    def __repr__(self) -> str:
        return f"<IntentAnalyzer name={self.name!r}>"
