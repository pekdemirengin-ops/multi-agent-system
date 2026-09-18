"""File Operations Skill."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from skills.base_skill import BaseSkill, skill_registry


SAFE_DIR = Path(os.getenv("DATA_DIR", "data"))


class FileOperationsSkill(BaseSkill):
    name = "file_operations"
    description = "Dosya islemleri"

    def _safe_path(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            raise ValueError("Mutlak yol yasak")
        if ".." in p.parts:
            raise ValueError("Ust dizin yasak")
        return SAFE_DIR / p

    async def execute(self, action: str = "", path: str = "", content: str = "", **kwargs) -> dict[str, Any]:
        try:
            if action == "read":
                p = self._safe_path(path)
                if not p.exists():
                    return {"error": f"Yok: {path}"}
                text = p.read_text(encoding="utf-8")
                return {"path": path, "content": text, "size": len(text)}
            elif action == "write":
                p = self._safe_path(path)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                return {"path": path, "size": len(content), "written": True}
            elif action == "list":
                p = self._safe_path(path) if path else SAFE_DIR
                if not p.exists():
                    return {"error": f"Yok: {path}"}
                files = [{"name": f.name, "size": f.stat().st_size} for f in p.iterdir()]
                return {"path": str(p), "files": files, "count": len(files)}
            elif action == "delete":
                p = self._safe_path(path)
                if not p.exists():
                    return {"error": f"Yok: {path}"}
                p.unlink()
                return {"path": path, "deleted": True}
            return {"error": f"Bilinmeyen: {action}"}
        except Exception as e:
            return {"error": str(e)}


skill_registry.register(FileOperationsSkill())
