"""Base Skill - tum skill'lerin temeli."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class BaseSkill(ABC):
    """Tum skill'lerin base class'i."""

    name: str = "base_skill"
    description: str = "Base skill"

    def __init__(self) -> None:
        self.logger = logger.bind(skill=self.name)

    @abstractmethod
    async def execute(self, **kwargs) -> dict[str, Any]:
        pass

    async def __call__(self, **kwargs) -> dict[str, Any]:
        self.logger.info("skill.execute", kwargs=list(kwargs.keys()))
        try:
            result = await self.execute(**kwargs)
            self.logger.info("skill.done", success=True)
            return {"success": True, **result}
        except Exception as e:
            self.logger.exception("skill.error", error=str(e))
            return {"success": False, "error": str(e)}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.name] = skill
        logger.info("skill.registered", name=skill.name)

    def get(self, name: str) -> BaseSkill | None:
        return self._skills.get(name)

    def list_skills(self) -> list[str]:
        return list(self._skills.keys())


skill_registry = SkillRegistry()
