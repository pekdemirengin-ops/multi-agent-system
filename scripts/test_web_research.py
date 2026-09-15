import asyncio
from core.base_agent import BaseAgent, Message
from core.message_bus import MessageBus
from agents.ai import ResearcherAgent


class TestCaller(BaseAgent):
    async def handle(self, message: Message) -> None:
        if message.msg_type == "error":
            print(f"\n[TESTER] HATA: {message.content}")
            return
        data = message.content
        print("\n" + "=" * 60)
        print("OZET:")
        print("=" * 60)
        print(data.get("research", ""))
        print()
        print("=" * 60)
        print(f"KAYNAKLAR ({data.get('source_count', 0)} adet):")
        print("=" * 60)
        for i, s in enumerate(data.get("sources", []), 1):
            print(f"{i}. {s['title']}")
            print(f"   {s['url']}")


async def main():
    bus = MessageBus()
    researcher = ResearcherAgent("researcher", bus)
    tester = TestCaller("tester", bus)

    query = "2024 yilinda Nobel Edebiyat Odulu kime verildi?"
    print(f"Soru: {query}")
    print("Web arastirmasi yapiliyor...")
    await tester.send("researcher", query)
    await asyncio.sleep(15)


asyncio.run(main())