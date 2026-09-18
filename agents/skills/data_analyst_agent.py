"""Data Analyst Agent - veri analizi (CSV/Excel + LLM)."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from skills.data_analysis_skill import DataAnalysisSkill
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


ANALYST_PROMPT = """Sen bir veri analistisin. Kullanicinin veri sorusunu yanitla.

KURALLAR:
- Sayilarla konus
- Oranlari ve yuzdeleri hesapla
- Kisa ve net ol
- Gereksiz detaya girme
"""


class DataAnalystAgent(BaseAgent):
    """Veri analizi yapan agent (CSV/Excel + LLM)."""

    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)
        self.skill = DataAnalysisSkill()
        self.llm = GroqLLMClient(model="openai/gpt-oss-120b")

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        try:
            query = str(message.content)
            lower = query.lower()

            # CSV icerik var mi? (coklu satir + virgul/noktali virgul)
            if ("\n" in query and ("," in query or ";" in query)) or "csv" in lower:
                result = await self.skill(content=query, file_format="csv")

                if "error" in result:
                    answer = f"Analiz hatasi: {result['error']}"
                else:
                    answer = result.get("summary", "Analiz tamamlandi.")

                await self.send(message.sender, {"answer": answer}, msg_type="result")
                return

            # Normal LLM analizi
            answer = self.llm.chat(prompt=query, system=ANALYST_PROMPT)
            await self.send(message.sender, {"answer": answer.strip()}, msg_type="result")
            logger.info("data_analyst.done")

        except Exception as e:
            logger.exception("data_analyst.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<DataAnalystAgent name={self.name!r}>"
