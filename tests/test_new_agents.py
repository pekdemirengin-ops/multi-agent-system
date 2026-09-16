"""Yeni agent testleri: SystemAgent, CoderAgent."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from core.message_bus import MessageBus


class TestSystemAgent:
    def test_get_system_status_keys(self) -> None:
        from tools.system_info import get_system_status

        status = get_system_status()
        expected_keys = {
            "cpu_percent",
            "memory_percent",
            "memory_used_gb",
            "memory_total_gb",
            "disk_percent",
            "disk_used_gb",
            "disk_total_gb",
            "boot_time_hours",
        }
        assert set(status.keys()) == expected_keys

    def test_format_status(self) -> None:
        from tools.system_info import format_status

        status = {
            "cpu_percent": 15.5,
            "memory_percent": 45.0,
            "memory_used_gb": 7.2,
            "memory_total_gb": 16.0,
            "disk_percent": 60.0,
            "disk_used_gb": 500.0,
            "disk_total_gb": 1000.0,
            "boot_time_hours": 12.5,
        }
        formatted = format_status(status)
        assert "CPU: 15.5%" in formatted
        assert "RAM: 45.0%" in formatted
        assert "Disk: 60.0%" in formatted

    def test_check_thresholds_no_alerts(self) -> None:
        from tools.system_info import check_thresholds

        status = {
            "cpu_percent": 10.0,
            "memory_percent": 20.0,
            "disk_percent": 30.0,
        }
        alerts = check_thresholds(status)
        assert alerts == []

    def test_check_thresholds_high_cpu(self) -> None:
        from tools.system_info import check_thresholds

        status = {
            "cpu_percent": 95.0,
            "memory_percent": 20.0,
            "disk_percent": 30.0,
        }
        alerts = check_thresholds(status)
        assert len(alerts) == 1
        assert "CPU" in alerts[0]


class TestCoderAgent:
    def test_extract_code_python_block(self) -> None:
        from agents.ai.coder_agent import _extract_code

        raw = "Aciklama\n```python\nprint('hi')\n```\nSonuc"
        code = _extract_code(raw)
        assert code == "print('hi')"

    def test_extract_code_no_block(self) -> None:
        from agents.ai.coder_agent import _extract_code

        code = _extract_code("print('hello')")
        assert code == "print('hello')"

    @pytest.mark.asyncio
    async def test_coder_agent_with_mock(self, bus: MessageBus) -> None:
        with patch("agents.ai.coder_agent.GroqLLMClient") as mock_client_cls:
            mock_llm = MagicMock()
            mock_llm.chat.return_value = "```python\nprint(2+2)\n```"
            mock_client_cls.return_value = mock_llm

            from agents.ai.coder_agent import CoderAgent
            from tests.conftest import EchoAgent

            coder = CoderAgent("coder", bus)
            caller = EchoAgent("caller", bus)

            await caller.send("coder", "test")
            import asyncio

            await asyncio.sleep(0.5)

            # Caller result almis olmali
            assert len(caller.received) >= 1
            result = caller.received[0].content
            assert isinstance(result, dict)
            assert "code" in result
            assert result["execution"]["safe"] is True


class TestCodeRunner:
    def test_safe_code_runs(self) -> None:
        from tools.code_runner import run_python

        r = run_python("print('hello')")
        assert r["safe"] is True
        assert r["returncode"] == 0
        assert "hello" in r["stdout"]

    def test_forbidden_import_blocked(self) -> None:
        from tools.code_runner import run_python

        r = run_python("import os\nprint('nope')")
        assert r["safe"] is False
        assert "os" in r["reason"].lower() or "Yasakli" in r["reason"]

    def test_syntax_error_handled(self) -> None:
        from tools.code_runner import run_python

        r = run_python("this is not python!!!")
        assert r["safe"] is False
        assert "Syntax" in r["reason"] or "syntax" in r["reason"].lower()

    def test_timeout(self) -> None:
        from tools.code_runner import run_python

        r = run_python("while True: pass", timeout=1)
        assert r["returncode"] == -1
        assert "Zaman" in r["stderr"] or "timeout" in r["reason"]