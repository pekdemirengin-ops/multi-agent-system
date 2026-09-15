import asyncio
from core.base_agent import BaseAgent, Message
from core.message_bus import MessageBus


class EchoAgent(BaseAgent):
    async def handle(self, message: Message) -> None:
        print(f"[{self.name}] aldim: {message.content}")
        if message.msg_type == "task":
            await self.send(message.sender, f"echo: {message.content}", msg_type="result")


class CallerAgent(BaseAgent):
    async def handle(self, message: Message) -> None:
        print(f"[{self.name}] cevap geldi: {message.content}")


async def main():
    bus = MessageBus()
    echo = EchoAgent("echo", bus)
    caller = CallerAgent("caller", bus)

    await caller.send("echo", "merhaba dunya")
    await asyncio.sleep(0.1)


asyncio.run(main())