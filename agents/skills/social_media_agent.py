"""Social Media Agent - sosyal medya postu."""
from __future__ import annotations

from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


SOCIAL_PROMPT = """Sen bir sosyal medya uzmanisin. Kullanicinin konusu hakkinda
Twitter/X veya LinkedIn postu yaz.

KURALLAR:
- Etkileyici hook (ilk cumle)
- Kisa ve oz (max 280 karakter Twitter icin)
- 3-5 hashtag
- Emoji kullan (az)
- Turkce

FORMAT:
<post metni>

<hashtagler>
"""


class SocialMediaAgent(BaseAgent):
    """Sosyal medya postu yazan agent."""

    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model="openai/gpt-oss-120b")

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return
        try:
            topic = str(message.content)
            answer = self.llm.chat(prompt=f"Konu: {topic}", system=SOCIAL_PROMPT)
            await self.send(message.sender, {"answer": answer.strip()}, msg_type="result")
            logger.info("social_media.done")
        except Exception as e:
            logger.exception("social_media.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def __repr__(self) -> str:
        return f"<SocialMediaAgent name={self.name!r}>"
