import asyncio
from core.base_agent import BaseAgent, Message
from core.message_bus import MessageBus
from agents.ai import LLMAgent, PlannerAgent, ResearcherAgent


class Coordinator(BaseAgent):
    """Planner'a planlatir, sonra adimlari ilgili agentlara dagitir."""

    def __init__(self, name, bus, max_steps=3):
        super().__init__(name, bus)
        self.max_steps = max_steps
        self.results = []

    async def handle(self, message: Message) -> None:
        if message.msg_type == "result" and "plan" in message.content:
            # Planner'dan plan geldi -> adimlari dagit
            plan = message.content["plan"]
            steps = plan.get("steps", [])[: self.max_steps]
            print(f"\n[koordinator] Plan alindi: {len(steps)} adim")
            for i, step in enumerate(steps, 1):
                agent = step.get("agent", "researcher")
                task = step.get("task", "")
                print(f"  {i}. {agent} -> {task[:60]}...")
                # Basitlestirme: sadece 'researcher' agentlari destekle
                if agent == "researcher":
                    await self.send("researcher", task)
                else:
                    await self.send("researcher", task)  # fallback

        elif message.msg_type == "result" and "research" in message.content:
            # Researcher'dan arastirma geldi
            self.results.append(message.content["research"])
            print(f"\n[koordinator] Arastirma #{len(self.results)} geldi ({len(message.content['research'])} karakter)")

        elif message.msg_type == "error":
            print(f"\n[koordinator] HATA: {message.content}")


async def main():
    bus = MessageBus()
    planner = PlannerAgent("planner", bus)
    researcher = ResearcherAgent("researcher", bus)
    coordinator = Coordinator("koordinator", bus)

    print("=" * 60)
    print("TEST: Planner -> Researcher pipeline")
    print("=" * 60)

    # Koordinator planner'a gorev verir
    await coordinator.send("planner", "Python'da asyncio nedir ve neden kullanilir?")
    await asyncio.sleep(15)

    print("\n" + "=" * 60)
    print(f"TOPLAM {len(coordinator.results)} arastirma tamamlandi")
    print("=" * 60)
    for i, r in enumerate(coordinator.results, 1):
        print(f"\n--- Arastirma {i} ---")
        print(r[:400])


asyncio.run(main())