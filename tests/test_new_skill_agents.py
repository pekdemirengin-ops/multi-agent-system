"""8 yeni skill-based agent testleri."""
from __future__ import annotations

import pytest

from agents.skills import (
    CalculatorAgent,
    DataAnalystAgent,
    EmailComposerAgent,
    FactCheckerAgent,
    FileManagerAgent,
    QuizMakerAgent,
    SocialMediaAgent,
    TranslatorAgent,
)
from core.message_bus import MessageBus


def _bus():
    return MessageBus()


class TestAgentImports:
    def test_translator(self) -> None:
        a = TranslatorAgent("translator", _bus())
        assert a.name == "translator"

    def test_calculator(self) -> None:
        a = CalculatorAgent("calculator", _bus())
        assert a.name == "calculator"

    def test_quiz_maker(self) -> None:
        a = QuizMakerAgent("quiz_maker", _bus())
        assert a.name == "quiz_maker"

    def test_email_composer(self) -> None:
        a = EmailComposerAgent("email_composer", _bus())
        assert a.name == "email_composer"

    def test_social_media(self) -> None:
        a = SocialMediaAgent("social_media", _bus())
        assert a.name == "social_media"

    def test_fact_checker(self) -> None:
        a = FactCheckerAgent("fact_checker", _bus())
        assert a.name == "fact_checker"

    def test_data_analyst(self) -> None:
        a = DataAnalystAgent("data_analyst", _bus())
        assert a.name == "data_analyst"

    def test_file_manager(self) -> None:
        a = FileManagerAgent("file_manager", _bus())
        assert a.name == "file_manager"


class TestAgentSkills:
    def test_translator_has_skill(self) -> None:
        a = TranslatorAgent("translator", _bus())
        assert a.skill.name == "translation"

    def test_calculator_has_skill(self) -> None:
        a = CalculatorAgent("calculator", _bus())
        assert a.skill.name == "calculator"

    def test_file_manager_has_skill(self) -> None:
        a = FileManagerAgent("file_manager", _bus())
        assert a.skill.name == "file_operations"


class TestNO_HISTORY:
    def test_new_agents_in_no_history(self) -> None:
        """Yeni 8 agent NO_HISTORY_AGENTS'te olmali."""
        import re
        from pathlib import Path
        content = Path("api/routes/agents.py").read_text(encoding="utf-8")
        match = re.search(r"NO_HISTORY_AGENTS = \{([^}]+)\}", content)
        assert match is not None
        no_history_str = match.group(1)
        for agent in ["translator", "calculator", "file_manager", "fact_checker",
                      "data_analyst", "quiz_maker", "email_composer", "social_media"]:
            assert f'"{agent}"' in no_history_str, f"{agent} NO_HISTORY'de yok!"
