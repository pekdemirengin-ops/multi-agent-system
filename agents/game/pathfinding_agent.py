"""Pathfinding Agent - A* algoritmasi."""
from __future__ import annotations

import heapq
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message

logger = structlog.get_logger(__name__)


class PathfindingAgent(BaseAgent):
    """Grid uzerinde A* ile yol bulur."""

    def __init__(self, name: str, bus: Any) -> None:
        super().__init__(name, bus)
        self.last_path: list[tuple[int, int]] = []

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        try:
            content = message.content

            # JSON dict beklenir
            if isinstance(content, dict):
                params = content
            else:
                # Metinden parse etmeye calis
                params = self._parse_text(str(content))

            # Eger params bos ise, content icinde JSON olabilir (cift string)
            if not params and isinstance(content, str):
                # Escape'li JSON'u temizle
                cleaned = content.strip()
                if cleaned.startswith("'") and cleaned.endswith("'"):
                    cleaned = cleaned[1:-1]
                cleaned = cleaned.replace('\\"', '"').replace("\\n", "\n")
                params = self._parse_text(cleaned)

            if not params:
                await self.send(
                    message.sender,
                    {
                        "research": (
                            "Pathfinding icin parametreler eksik.\n\n"
                            "Beklenen format:\n"
                            "{\n"
                            '  "grid": [[0,0,0],[0,1,0],[0,0,0]],\n'
                            '  "start": [0,0],\n'
                            '  "goal": [2,2]\n'
                            "}\n\n"
                            "0 = bos, 1 = engel"
                        ),
                        "sources": [],
                        "source_count": 0,
                    },
                    msg_type="result",
                )
                return

            grid = params.get("grid", [])
            start = tuple(params.get("start", []))
            goal = tuple(params.get("goal", []))

            if not grid or not start or not goal:
                await self.send(
                    message.sender,
                    {"error": "grid, start, goal gerekli"},
                    msg_type="error",
                )
                return

            path = self._a_star(grid, start, goal)
            self.last_path = path

            if not path:
                answer = f"Yol bulunamadi: {start} -> {goal}"
            else:
                lines = [
                    f"Yol bulundu: {len(path)} adim",
                    f"Baslangic: {start}",
                    f"Hedef: {goal}",
                    "",
                    "Yol:",
                ]
                for i, (x, y) in enumerate(path):
                    lines.append(f"  {i + 1}. ({x}, {y})")
                lines.append("")
                lines.append("Grid gorseli:")
                lines.append(self._visualize(grid, path, start, goal))
                answer = "\n".join(lines)

            logger.info("pathfinding.done", start=start, goal=goal, path_len=len(path))

            await self.send(
                message.sender,
                {
                    "research": answer,
                    "sources": [],
                    "source_count": 0,
                    "path": path,
                    "path_length": len(path),
                },
                msg_type="result",
            )

        except Exception as e:
            logger.exception("pathfinding.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    def _a_star(
        self,
        grid: list[list[int]],
        start: tuple[int, int],
        goal: tuple[int, int],
    ) -> list[tuple[int, int]]:
        """A* algoritmasi."""
        if not grid or not grid[0]:
            return []

        rows, cols = len(grid), len(grid[0])

        # Sinir kontrolu
        if not (0 <= start[0] < rows and 0 <= start[1] < cols):
            return []
        if not (0 <= goal[0] < rows and 0 <= goal[1] < cols):
            return []
        if grid[start[0]][start[1]] == 1 or grid[goal[0]][goal[1]] == 1:
            return []

        # Heuristic: Manhattan distance
        def h(p: tuple[int, int]) -> int:
            return abs(p[0] - goal[0]) + abs(p[1] - goal[1])

        open_set: list[tuple[int, tuple[int, int]]] = [(h(start), start)]
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        g_score: dict[tuple[int, int], int] = {start: 0}

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal:
                # Yolu geriye dogru olustur
                path = []
                while current is not None:
                    path.append(current)
                    current = came_from[current]
                return list(reversed(path))

            cx, cy = current
            # 4 yon: yukari, asagi, sol, sag
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy

                if not (0 <= nx < rows and 0 <= ny < cols):
                    continue
                if grid[nx][ny] == 1:  # engel
                    continue

                tentative_g = g_score[current] + 1
                neighbor = (nx, ny)

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + h(neighbor)
                    heapq.heappush(open_set, (f, neighbor))

        return []

    @staticmethod
    def _visualize(
        grid: list[list[int]],
        path: list[tuple[int, int]],
        start: tuple[int, int],
        goal: tuple[int, int],
    ) -> str:
        """Grid'i gorsellestirir (sabit genislik)."""
        path_set = set(path)
        lines = []
        for x, row in enumerate(grid):
            cells = []
            for y, cell in enumerate(row):
                if (x, y) == start:
                    cells.append("S")
                elif (x, y) == goal:
                    cells.append("G")
                elif cell == 1:
                    cells.append("#")
                elif (x, y) in path_set:
                    cells.append(".")
                else:
                    cells.append(" ")
            lines.append(" ".join(cells))
        return "\n".join(lines)

    @staticmethod
    def _parse_text(text: str) -> dict[str, Any]:
        """Metinden parametreleri parse etmeye calisir (JSON veya regex)."""
        import json
        import re

        # 1) JSON parse dene
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "grid" in data and "start" in data and "goal" in data:
                return data
        except (json.JSONDecodeError, ValueError):
            pass

        # 2) Regex ile parse et
        params: dict[str, Any] = {}

        # Grid boyutu (5x5 gibi)
        size_match = re.search(r"(\d+)\s*[xX]\s*(\d+)", text)
        if size_match:
            rows, cols = int(size_match.group(1)), int(size_match.group(2))
            params["grid"] = [[0] * cols for _ in range(rows)]

        # Baslangic ve hedef
        coords = re.findall(r"\((\d+),\s*(\d+)\)", text)
        if len(coords) >= 2:
            params["start"] = [int(coords[0][0]), int(coords[0][1])]
            params["goal"] = [int(coords[-1][0]), int(coords[-1][1])]

        # Engeller (obstacle/engel)
        if "engel" in text.lower() or "obstacle" in text.lower():
            # Simdilik default grid olustur
            if "grid" not in params:
                params["grid"] = [[0] * 5 for _ in range(5)]

        return params if "grid" in params and "start" in params and "goal" in params else {}

    def __repr__(self) -> str:
        return f"<PathfindingAgent name={self.name!r} last_path_len={len(self.last_path)}>"