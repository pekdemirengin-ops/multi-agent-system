"""NPC Agent - basit oyun karakteri AI."""
from __future__ import annotations

import random
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


NPC_SYSTEM_PROMPT = """Sen bir oyun NPC'sisin (Non-Player Character).
Kullanicinin mesajina gore karakterin tepkisini olustur.

Kurallar:
- Karakterin kisiselligine uygun tepki ver
- Kisa ve atmosferik cevap ver (1-2 cumle)
- Turkce cevap ver
- RPG/fantastik oyun dili kullan
"""


class NPCAgent(BaseAgent):
    """Basit NPC - durum + kisisellik + LLM tepki."""

    PERSONALITIES = {
        "friendly": "Merhaba gezgin! Yardimci olabilir miyim?",
        "hostile": "Hedefime yaklastin. Savasa hazir ol!",
        "merchant": "Mallarima bakmak ister misin?",
        "guard": "Bu bolgeye girmek icin iznin var mi?",
        "quest_giver": "Bir gorevim var. Yardim eder misin?",
    }

    def __init__(
        self,
        name: str,
        bus: Any,
        personality: str = "friendly",
        model: str | None = None,
    ) -> None:
        super().__init__(name, bus)
        self.personality = personality
        self.llm = GroqLLMClient(model=model)
        self.state = {
            "hp": 100,
            "mood": "neutral",
            "location": "village",
            "inventory": ["bread", "sword"],
        }

    async def handle(self, message: Message) -> None:
        if message.msg_type not in ("task", "event"):
            return

        try:
            content = str(message.content)

            # Durum guncellemesi (event)
            if message.msg_type == "event":
                await self._handle_event(message)
                return

            # Kullanicidan soru/etkilesim (task)
            # Kisisellige uygun LLM tepkisi
            prompt = (
                f"NPC kisiselligi: {self.personality}\n"
                f"NPC durumu: HP={self.state['hp']}, mood={self.state['mood']}, "
                f"konum={self.state['location']}\n"
                f"Kullanici: {content}\n\n"
                f"NPC olarak tepki ver:"
            )

            reaction = self.llm.chat(prompt=prompt, system=NPC_SYSTEM_PROMPT)

            answer = (
                f"[{self.name} - {self.personality}]\n"
                f"Durum: HP={self.state['hp']}, mood={self.state['mood']}\n\n"
                f"Tepki: {reaction}"
            )

            logger.info("npc.reaction", name=self.name, personality=self.personality)

            await self.send(
                message.sender,
                {
                    "research": answer,
                    "sources": [],
                    "source_count": 0,
                    "npc_state": self.state,
                },
                msg_type="result",
            )

        except Exception as e:
            logger.exception("npc.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    async def _handle_event(self, message: Message) -> None:
        """Oyun olayini isle (oyuncu yaklasti, saldirdi, vs)."""
        event = message.content.get("event", "") if isinstance(message.content, dict) else str(message.content)

        if event == "player_near":
            self.state["mood"] = "alert"
            reaction = self.PERSONALITIES.get(self.personality, "Sen kimsin?")
        elif event == "player_attacked":
            self.state["hp"] -= 20
            self.state["mood"] = "angry"
            reaction = "Ahh! Bana saldirdin! Savas!"
        elif event == "player_helped":
            self.state["mood"] = "happy"
            reaction = "Tesekkurler! Sana minnettarim."
        else:
            reaction = f"Ne oldu? ({event})"

        logger.info("npc.event", name=self.name, event=event, hp=self.state["hp"])

        await self.send(
            message.sender,
            {
                "research": f"[{self.name}] {reaction}\nDurum: HP={self.state['hp']}, mood={self.state['mood']}",
                "sources": [],
                "source_count": 0,
                "npc_state": self.state,
            },
            msg_type="result",
        )

    def __repr__(self) -> str:
        return f"<NPCAgent name={self.name!r} personality={self.personality}>"