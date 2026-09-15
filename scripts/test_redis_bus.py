import asyncio
from core.base_agent import BaseAgent, Message
from core.redis_bus import RedisMessageBus


class EchoAgent(BaseAgent):
    async def handle(self, message: Message) -> None:
        print(f"[{self.name}] aldim: {message.content}")
        if message.msg_type == "task":
            await self.send(message.sender, f"echo: {message.content}", msg_type="result")


class CallerAgent(BaseAgent):
    async def handle(self, message: Message) -> None:
        print(f"[{self.name}] cevap geldi: {message.content}")


async def main():
    # Docker'da calisan Redis'e baglan
    bus = RedisMessageBus(redis_url="redis://localhost:6379/0")
    await bus.connect()
    print(f"Redis baglantisi: {bus._redis is not None}")
    print(f"Bus: {bus}")

    echo = EchoAgent("echo", bus)
    caller = CallerAgent("caller", bus)

    await caller.send("echo", "merhaba redis")
    await asyncio.sleep(1)

    await bus.close()


asyncio.run(main())