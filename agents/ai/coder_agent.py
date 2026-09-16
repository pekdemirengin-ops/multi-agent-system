"""Kod yazan ve calistiran agent."""
from __future__ import annotations

import re
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.code_runner import run_python
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


CODER_PROMPT = """Sen bir Python programcisisin. Kullanicinin istegine gore
Python kodu yazarsin. Sadece kod blogu dondur, aciklama yazma.

Kurallar:
- Kodu ```python ... ``` blogu icine al
- Sadece standart kutuphane kullan (import math, import random gibi)
- os, sys, subprocess, requests gibi modulleri KULLANMA
- Kodu tek basina calistirilabilir yaz
- Cikti print() ile ver
"""


def _extract_code(text: str) -> str:
    """LLM ciktisindan kod blogunu cikarir."""
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


class CoderAgent(BaseAgent):
    """LLM ile kod yazar, guvenli sandbox'ta calistirir."""

    def __init__(
        self,
        name: str,
        bus: Any,
        model: str | None = None,
    ) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model=model)

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        try:
            raw = self.llm.chat(prompt=str(message.content), system=CODER_PROMPT)
            code = _extract_code(raw)
            logger.info("coder.code_written", length=len(code))

            result = run_python(code, timeout=10)
            answer = self._format_answer(code, result)

            await self.send(
                message.sender,
                {
                    "research": answer,
                    "code": code,
                    "execution": result,
                    "sources": [],
                    "source_count": 0,
                },
                msg_type="result",
            )
            logger.info(
                "coder.done",
                returncode=result["returncode"],
                safe=result["safe"],
            )

        except Exception as e:
            logger.exception("coder.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    @staticmethod
    def _format_answer(code: str, result: dict[str, Any]) -> str:
        lines = ["```python", code, "```", ""]
        if not result["safe"]:
            lines.append(f"GUVENLIK REDDI: {result['reason']}")
        elif result["returncode"] == 0:
            lines.append("Cikti:")
            lines.append("```")
            lines.append(result["stdout"].strip() or "(cikti yok)")
            lines.append("```")
        else:
            lines.append(f"HATA (returncode {result['returncode']}):")
            lines.append("```")
            lines.append(result["stderr"].strip() or "(hata mesaji yok)")
            lines.append("```")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"<CoderAgent name={self.name!r}>"