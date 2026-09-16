"""Core katmani testleri."""
from __future__ import annotations

import asyncio

import pytest
from core.base_agent import Message
from core.message_bus import MessageBus
from core.registry import AgentRegistry
from tests.conftest import EchoAgent


class TestMessage:
    def test_message_creation(self) -> None:
        msg = Message(sender="a", receiver="b", content="hello")
        assert msg.sender == "a"
        assert msg.receiver == "b"
        assert msg.content == "hello"
        assert msg.msg_type == "task"
        assert msg.id
        assert msg.created_at

    def test_message_repr(self) -> None:
        msg = Message(sender="a", receiver="b", content="hello")
        assert "a->b" in repr(msg)


class TestBaseAgent:
    def test_agent_requires_name(self, bus: MessageBus) -> None:
        with pytest.raises(ValueError):
            EchoAgent("", bus)

    def test_agent_registers_on_bus(self, bus: MessageBus) -> None:
        EchoAgent("test_agent", bus)
        assert "test_agent" in bus.list_agents()

    def test_duplicate_name_raises(self, bus: MessageBus) -> None:
        EchoAgent("dup", bus)
        with pytest.raises(ValueError):
            EchoAgent("dup", bus)


class TestMessageBus:
    @pytest.mark.asyncio
    async def test_publish_delivers_message(self, bus: MessageBus) -> None:
        echo = EchoAgent("echo", bus)
        caller = EchoAgent("caller", bus)

        await caller.send("echo", "hello")
        await asyncio.sleep(0.05)

        assert len(echo.received) == 1
        assert echo.received[0].content == "hello"
        assert echo.received[0].sender == "caller"

    @pytest.mark.asyncio
    async def test_broadcast(self, bus: MessageBus) -> None:
        a = EchoAgent("a", bus)
        b = EchoAgent("b", bus)
        c = EchoAgent("c", bus)

        # a kendine "task" gonderir, broadcast ile
        await a.send("*", "broadcast")
        await asyncio.sleep(0.05)

        # a, kendi task'ini almamali (sender=receiver ise skip)
        # Ama b ve c echo cevabi gonderir, a onlari alir
        a_task_msgs = [m for m in a.received if m.msg_type == "task"]
        assert len(a_task_msgs) == 0, "a kendi task'ini almamali"

        # b ve c task'i almali
        b_tasks = [m for m in b.received if m.msg_type == "task"]
        c_tasks = [m for m in c.received if m.msg_type == "task"]
        assert len(b_tasks) == 1
        assert len(c_tasks) == 1

        # b ve c'nin echo cevaplari a'ya gelmis olmali
        a_result_msgs = [m for m in a.received if m.msg_type == "result"]
        assert len(a_result_msgs) == 2


class TestAgentRegistry:
    def test_add_agent_class(self) -> None:
        registry = AgentRegistry()
        registry.add("echo", EchoAgent)
        assert "echo" in registry.list_entries()

    def test_add_invalid_class(self) -> None:
        registry = AgentRegistry()

        class NotAnAgent:
            pass

        with pytest.raises(TypeError):
            registry.add("invalid", NotAnAgent)  # type: ignore[arg-type]

    def test_duplicate_add_raises(self) -> None:
        registry = AgentRegistry()
        registry.add("echo", EchoAgent)
        with pytest.raises(ValueError):
            registry.add("echo", EchoAgent)

    def test_create_all(self, bus: MessageBus) -> None:
        registry = AgentRegistry()
        registry.add("echo1", EchoAgent)
        registry.add("echo2", EchoAgent)
        agents = registry.create_all(bus)
        assert len(agents) == 2
        assert len(bus.list_agents()) == 2