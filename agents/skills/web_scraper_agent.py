"""Web Scraper Agent - URL'den icerik cekme + ozetleme."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from skills.web_scraping_skill import WebScrapingSkill
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


SUMMARY_PROMPT = """Sen bir icerik ozetleyicisisin. Verilen web sayfasi icerigini ozetle.

KURALLAR:
- Maksimum 5 cumle
- Ana fikirleri maddeler halinde
- Turkce
- Kaynak URL'yi belirt
"""


class WebScraperAgent(BaseAgent):
    """URL'den icerik ceker ve ozetler."""

    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)
        self.skill = WebScrapingSkill()
        self.llm = GroqLLMClient(model="openai/gpt-oss-120b")

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        try:
            text = str(message.content)

            # Skill ile icerik cek
            result = await self.skill(text=text)

            if "error" in result:
                await self.send(
                    message.sender,
                    {"answer": f"Hata: {result['error']}"},
                    msg_type="result",
                )
                return

            url = result.get("url", "")
            content = result.get("content", "")

            if not content:
                await self.send(
                    message.sender,
                    {"answer": "Icerik bulunamadi"},
                    msg_type="result",
                )
                return

            # LLM ile ozetle (max 5 cumle)
            try:
                prompt = f"URL: {url}\n\nIcerik:\n{content[:5000]}\n\nOzet:"
                summary = self.llm.chat(prompt=prompt, system=SUMMARY_PROMPT)
                answer = f"**{url}**\n\n{summary.strip()}"
            except Exception as e:
                logger.warning("web_scraper.summary_error", error=str(e))
                # LLM hata verirse ilk 500 karakteri don
                answer = f"**{url}**\n\n{content[:500]}..."

            await self.send(
                message.sender,
                {
                    "answer": answer,
                    "sources": [{"title": url[:60], "url": url}],
                },
                msg_type="result",
            )
            logger.info("web_scraper.done", url=url[:100], length=len(answer))

        except Exception as e:
            logger.exception("web_scraper.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<WebScraperAgent name={self.name!r}>"
