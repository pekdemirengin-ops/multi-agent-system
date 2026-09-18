"""Skill testleri."""
from __future__ import annotations

import pytest

from skills import (
    CalculatorSkill,
    FileOperationsSkill,
    TranslationSkill,
    skill_registry,
)


class TestCalculatorSkill:
    @pytest.mark.asyncio
    async def test_basic_addition(self) -> None:
        skill = CalculatorSkill()
        r = await skill(expression="2 + 3")
        assert r["success"] is True
        assert r["result"] == 5

    @pytest.mark.asyncio
    async def test_multiplication(self) -> None:
        skill = CalculatorSkill()
        r = await skill(expression="4 * 5")
        assert r["success"] is True
        assert r["result"] == 20

    @pytest.mark.asyncio
    async def test_complex_expression(self) -> None:
        skill = CalculatorSkill()
        r = await skill(expression="2 + 3 * 4")
        assert r["success"] is True
        assert r["result"] == 14

    @pytest.mark.asyncio
    async def test_sqrt(self) -> None:
        skill = CalculatorSkill()
        r = await skill(expression="sqrt(16)")
        assert r["success"] is True
        assert r["result"] == 4.0

    @pytest.mark.asyncio
    async def test_power(self) -> None:
        skill = CalculatorSkill()
        r = await skill(expression="2^10")
        assert r["success"] is True
        assert r["result"] == 1024

    @pytest.mark.asyncio
    async def test_empty_expression(self) -> None:
        skill = CalculatorSkill()
        r = await skill(expression="")
        assert "error" in r

    @pytest.mark.asyncio
    async def test_invalid_expression(self) -> None:
        skill = CalculatorSkill()
        r = await skill(expression="abc + def")
        assert "error" in r or r.get("success") is False


class TestTranslationSkill:
    @pytest.mark.asyncio
    async def test_empty_text(self) -> None:
        skill = TranslationSkill()
        r = await skill(text="", target_lang="en")
        assert "error" in r

    @pytest.mark.asyncio
    async def test_registered(self) -> None:
        assert "translation" in skill_registry.list_skills()


class TestFileOperationsSkill:
    @pytest.mark.asyncio
    async def test_write_read(self, tmp_path) -> None:
        import os
        os.environ["DATA_DIR"] = str(tmp_path)
        skill = FileOperationsSkill()
        r = await skill(action="write", path="test.txt", content="hello")
        assert r["success"] is True
        assert r["written"] is True

        r = await skill(action="read", path="test.txt")
        assert r["success"] is True
        assert r["content"] == "hello"

    @pytest.mark.asyncio
    async def test_absolute_path_blocked(self) -> None:
        skill = FileOperationsSkill()
        r = await skill(action="read", path="/etc/passwd")
        assert "error" in r or r.get("success") is False

    @pytest.mark.asyncio
    async def test_parent_dir_blocked(self) -> None:
        skill = FileOperationsSkill()
        r = await skill(action="read", path="../../etc/passwd")
        assert "error" in r or r.get("success") is False


class TestSkillRegistry:
    def test_calculator_registered(self) -> None:
        assert "calculator" in skill_registry.list_skills()

    def test_file_operations_registered(self) -> None:
        assert "file_operations" in skill_registry.list_skills()

    def test_get_skill(self) -> None:
        skill = skill_registry.get("calculator")
        assert skill is not None
        assert skill.name == "calculator"
