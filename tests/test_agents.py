"""Agent testleri (LLM cagrilari mock'lanmis)."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from core.message_bus import MessageBus


class TestPlannerAgent:
    @pytest.mark.asyncio
    async def test_planner_parses_json(self, bus: MessageBus) -> None:
        with patch("agents.ai.planner_agent.GroqLLMClient") as mock_client_cls:
            mock_llm = MagicMock()
            mock_llm.chat.return_value = '{"steps": [{"agent": "researcher", "task": "test"}]}'
            mock_client_cls.return_value = mock_llm

            from agents.ai.planner_agent import PlannerAgent

            planner = PlannerAgent("planner", bus)
            result = planner._parse_plan(mock_llm.chat.return_value)
            assert "steps" in result
            assert len(result["steps"]) == 1
            assert result["steps"][0]["agent"] == "researcher"

    def test_planner_parses_with_code_fence(self, bus: MessageBus) -> None:
        with patch("agents.ai.planner_agent.GroqLLMClient"):
            from agents.ai.planner_agent import PlannerAgent

            planner = PlannerAgent("planner", bus)
            raw = '```json\n{"steps": [{"agent": "x", "task": "y"}]}\n```'
            result = planner._parse_plan(raw)
            assert len(result["steps"]) == 1


class TestLLMAgent:
    @pytest.mark.asyncio
    async def test_llm_agent_handle_calls_llm(self, bus: MessageBus) -> None:
        with patch("agents.ai.llm_agent.GroqLLMClient") as mock_client_cls:
            mock_llm = MagicMock()
            mock_llm.chat.return_value = "Mocked LLM response"
            mock_llm.model = "mock-model"
            mock_client_cls.return_value = mock_llm

            from agents.ai.llm_agent import LLMAgent
            from tests.conftest import EchoAgent

            llm_agent = LLMAgent("llm", bus)
            caller = EchoAgent("caller", bus)

            await caller.send("llm", "test soru")
            await asyncio.sleep(0.1)

            assert mock_llm.chat.called