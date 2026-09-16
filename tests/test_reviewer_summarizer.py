"""Reviewer ve Summarizer agent testleri."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from core.message_bus import MessageBus


class TestReviewerAgent:
    @pytest.mark.asyncio
    async def test_reviewer_with_mock(self, bus: MessageBus) -> None:
        with patch("agents.ai.reviewer_agent.GroqLLMClient") as mock_client_cls:
            mock_llm = MagicMock()
            mock_llm.chat.return_value = "- Kod iyi gorunuyor\n- Type hint eksik"
            mock_client_cls.return_value = mock_llm

            from agents.ai.reviewer_agent import ReviewerAgent
            from tests.conftest import EchoAgent

            reviewer = ReviewerAgent("reviewer", bus)
            caller = EchoAgent("caller", bus)

            await caller.send("reviewer", "def foo(): pass")
            import asyncio

            await asyncio.sleep(0.1)

            assert len(caller.received) >= 1
            assert mock_llm.chat.called


class TestSummarizerAgent:
    @pytest.mark.asyncio
    async def test_summarizer_with_mock(self, bus: MessageBus) -> None:
        with patch("agents.ai.summarizer_agent.GroqLLMClient") as mock_client_cls:
            mock_llm = MagicMock()
            mock_llm.chat.return_value = "- Ozet 1\n- Ozet 2"
            mock_client_cls.return_value = mock_llm

            from agents.ai.summarizer_agent import SummarizerAgent
            from tests.conftest import EchoAgent

            summarizer = SummarizerAgent("summarizer", bus)
            caller = EchoAgent("caller", bus)

            await caller.send("summarizer", "Uzun metin...")
            import asyncio

            await asyncio.sleep(0.1)

            assert len(caller.received) >= 1
            assert mock_llm.chat.called