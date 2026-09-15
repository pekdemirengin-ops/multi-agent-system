import asyncio
from core.base_agent import BaseAgent, Message
from core.message_bus import MessageBus
from agents.ai import LLMAgent


class TestCaller(BaseAgent):
    async def handle(self, message: Message) -> None:
        print()
        print("=" * 50)
        print(f"[{self.name}] yanit tipi: {message.msg_type}")
        print(f"[{self.name}] yanit: {message.content}")
        print("=" * 50)


async def main():
    bus = MessageBus()
    llm = LLMAgent(
        "assistant",
        bus,
        system_prompt="Kisa ve oz cevap ver. En fazla 2 cumle.",
    )
    caller = TestCaller("tester", bus)

    print("Groq'a soru gonderiliyor...")
    await caller.send("assistant", "Turkiye'nin baskenti neresi ve nufusu yaklasik kac?")
    await asyncio.sleep(8)


asyncio.run(main())