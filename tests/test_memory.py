"""Hafiza modulu testleri."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.memory import ConversationMemory


@pytest.fixture
def temp_memory() -> ConversationMemory:
    """Gecici SQLite dosyasi ile memory olusturur."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test_memory.db"
        mem = ConversationMemory(db_path=db_path)
        yield mem


class TestConversationMemory:
    @pytest.mark.asyncio
    async def test_init_creates_table(self, temp_memory: ConversationMemory) -> None:
        await temp_memory.init()
        assert temp_memory.db_path.exists()

    @pytest.mark.asyncio
    async def test_save_and_get_message(self, temp_memory: ConversationMemory) -> None:
        await temp_memory.init()
        await temp_memory.save_message("user1", "user", "Merhaba")
        await temp_memory.save_message("user1", "assistant", "Selam!")

        history = await temp_memory.get_history("user1")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Merhaba"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Selam!"

    @pytest.mark.asyncio
    async def test_user_isolation(self, temp_memory: ConversationMemory) -> None:
        await temp_memory.init()
        await temp_memory.save_message("alice", "user", "Alice mesaji")
        await temp_memory.save_message("bob", "user", "Bob mesaji")

        alice_history = await temp_memory.get_history("alice")
        bob_history = await temp_memory.get_history("bob")

        assert len(alice_history) == 1
        assert alice_history[0]["content"] == "Alice mesaji"
        assert len(bob_history) == 1
        assert bob_history[0]["content"] == "Bob mesaji"

    @pytest.mark.asyncio
    async def test_limit(self, temp_memory: ConversationMemory) -> None:
        await temp_memory.init()
        for i in range(20):
            await temp_memory.save_message("user1", "user", f"Mesaj {i}")

        history = await temp_memory.get_history("user1", limit=5)
        assert len(history) == 5
        # En son 5 mesaj: 15, 16, 17, 18, 19
        assert history[0]["content"] == "Mesaj 15"
        assert history[-1]["content"] == "Mesaj 19"

    @pytest.mark.asyncio
    async def test_format_for_llm(self, temp_memory: ConversationMemory) -> None:
        await temp_memory.init()
        await temp_memory.save_message("user1", "user", "Python nedir?")
        await temp_memory.save_message("user1", "assistant", "Bir programlama dili.")

        formatted = await temp_memory.format_for_llm("user1")
        assert "Onceki konusmalar" in formatted
        assert "Kullanici: Python nedir?" in formatted
        assert "Asistan: Bir programlama dili." in formatted

    @pytest.mark.asyncio
    async def test_format_empty_history(self, temp_memory: ConversationMemory) -> None:
        await temp_memory.init()
        formatted = await temp_memory.format_for_llm("nobody")
        assert formatted == ""

    @pytest.mark.asyncio
    async def test_clear_user(self, temp_memory: ConversationMemory) -> None:
        await temp_memory.init()
        await temp_memory.save_message("user1", "user", "Test 1")
        await temp_memory.save_message("user1", "user", "Test 2")

        deleted = await temp_memory.clear_user("user1")
        assert deleted == 2

        history = await temp_memory.get_history("user1")
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_stats(self, temp_memory: ConversationMemory) -> None:
        await temp_memory.init()
        await temp_memory.save_message("alice", "user", "A1")
        await temp_memory.save_message("alice", "assistant", "A2")
        await temp_memory.save_message("bob", "user", "B1")

        stats = await temp_memory.stats()
        assert stats["total_messages"] == 3
        assert stats["unique_users"] == 2