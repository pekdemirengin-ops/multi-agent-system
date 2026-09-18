"""Multi-Agent Pipeline - sirali agent calistirma."""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import structlog

from core.base_agent import BaseAgent, Message

logger = structlog.get_logger(__name__)


@dataclass
class PipelineStep:
    """Pipeline'daki tek adim."""

    agent: str
    """Agent adi."""

    name: str = ""
    """Adim adi (opsiyonel)."""

    transform: Callable[[Any], str] | None = None
    """Onceki adimin ciktisini bir sonraki adima nasil cevirecegiz."""

    def get_input(self, previous_output: Any, original_query: str) -> str:
        """Adim icin girdi uretir."""
        if self.transform:
            return self.transform(previous_output)
        if isinstance(previous_output, dict):
            # answer field varsa onu kullan
            return str(previous_output.get("answer", previous_output))
        return str(previous_output)


@dataclass
class PipelineResult:
    """Pipeline sonucu."""

    pipeline_name: str
    query: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    final_answer: str = ""
    success: bool = False
    duration_ms: int = 0
    error: str | None = None


# Hazir pipeline'lar
PIPELINES: dict[str, list[PipelineStep]] = {
    "research": [
        PipelineStep(agent="researcher", name="Arastirma"),
        PipelineStep(
            agent="fact_checker",
            name="Dogrulama",
            transform=lambda prev: f"Iddia: {prev.get('answer', prev)[:500]}\n\nDogrula.",
        ),
        PipelineStep(
            agent="summarizer",
            name="Ozetleme",
            transform=lambda prev: f"Su metni ozetle: {prev.get('answer', prev)[:1000]}",
        ),
    ],
    "code": [
        PipelineStep(agent="planner", name="Planlama"),
        PipelineStep(
            agent="coder",
            name="Kodlama",
            transform=lambda prev: prev.get("answer", str(prev)),
        ),
        PipelineStep(
            agent="reviewer",
            name="Inceleme",
            transform=lambda prev: f"Su kodu incele: {prev.get('answer', prev)[:1000]}",
        ),
    ],
    "content": [
        PipelineStep(agent="researcher", name="Arastirma"),
        PipelineStep(
            agent="email_composer",
            name="Email Yazma",
            transform=lambda prev: f"Su bilgiye gore email yaz: {prev.get('answer', prev)[:500]}",
        ),
    ],
    "social": [
        PipelineStep(agent="researcher", name="Arastirma"),
        PipelineStep(
            agent="social_media",
            name="Sosyal Medya",
            transform=lambda prev: f"Su bilgiye gore tweet yaz: {prev.get('answer', prev)[:500]}",
        ),
    ],
    "fact": [
        PipelineStep(agent="researcher", name="Arastirma"),
        PipelineStep(
            agent="fact_checker",
            name="Dogrulama",
            transform=lambda prev: prev.get("answer", str(prev)),
        ),
    ],
}


class Pipeline:
    """Multi-Agent Pipeline calistiricisi."""

    def __init__(
        self,
        name: str,
        bus: Any,
        agents: dict[str, BaseAgent],
        timeout: int = 60,
    ) -> None:
        self.name = name
        self.bus = bus
        self.agents = agents
        self.timeout = timeout

    async def run(self, query: str) -> PipelineResult:
        """Pipeline'i calistirir."""
        import time
        start = time.perf_counter()

        steps = PIPELINES.get(self.name, [])
        if not steps:
            return PipelineResult(
                pipeline_name=self.name,
                query=query,
                success=False,
                error=f"Pipeline bulunamadi: {self.name}",
            )

        result = PipelineResult(pipeline_name=self.name, query=query)
        previous_output: Any = query

        for i, step in enumerate(steps, 1):
            step_start = time.perf_counter()
            agent_name = step.agent
            step_name = step.name or agent_name

            logger.info(
                "pipeline.step_start",
                pipeline=self.name,
                step=i,
                total=len(steps),
                agent=agent_name,
            )

            if agent_name not in self.agents:
                result.error = f"Agent bulunamadi: {agent_name}"
                result.success = False
                break

            # Girdi uret
            step_input = step.get_input(previous_output, query)

            # Agent'i calistir
            try:
                agent = self.agents[agent_name]
                output = await self._run_agent(agent, step_input)

                step_duration = int((time.perf_counter() - step_start) * 1000)
                result.steps.append({
                    "step": i,
                    "agent": agent_name,
                    "name": step_name,
                    "input": step_input[:200],
                    "output": str(output)[:500],
                    "duration_ms": step_duration,
                    "success": True,
                })

                previous_output = output
                logger.info(
                    "pipeline.step_done",
                    pipeline=self.name,
                    step=i,
                    agent=agent_name,
                    duration_ms=step_duration,
                )

            except Exception as e:
                step_duration = int((time.perf_counter() - step_start) * 1000)
                result.steps.append({
                    "step": i,
                    "agent": agent_name,
                    "name": step_name,
                    "input": step_input[:200],
                    "error": str(e),
                    "duration_ms": step_duration,
                    "success": False,
                })
                logger.exception("pipeline.step_error", step=i, agent=agent_name, error=str(e))
                result.error = f"Adim {i} ({agent_name}): {str(e)}"
                result.success = False
                break

        # Final cevap
        if isinstance(previous_output, dict):
            result.final_answer = str(previous_output.get("answer", previous_output))
        else:
            result.final_answer = str(previous_output)

        result.success = result.error is None
        result.duration_ms = int((time.perf_counter() - start) * 1000)

        logger.info(
            "pipeline.done",
            pipeline=self.name,
            success=result.success,
            duration_ms=result.duration_ms,
            steps=len(result.steps),
        )

        return result

    async def _run_agent(self, agent: BaseAgent, input_text: str) -> dict[str, Any]:
        """Tek bir agent'i calistirir."""
        from api.routes.agents import _run_single_agent
        # Direkt agent'in handle'ini cagir
        message = Message(
            sender="__pipeline__",
            receiver=agent.name,
            content=input_text,
            msg_type="task",
            id=str(uuid.uuid4()),
        )

        # Agent ciktisini topla
        collected: list[Any] = []

        original_send = agent.send

        async def capture_send(receiver: str, content: Any, msg_type: str = "result") -> None:
            if msg_type == "result":
                collected.append(content)

        agent.send = capture_send  # type: ignore

        try:
            await asyncio.wait_for(agent.handle(message), timeout=self.timeout)
        finally:
            agent.send = original_send  # type: ignore

        if not collected:
            return {"answer": ""}

        last = collected[-1]
        if isinstance(last, dict):
            # Standart field'lari sirayla dene
            for key in ["answer", "research", "translation", "result", "output", "content", "summary"]:
                if key in last and last[key]:
                    val = last[key]
                    return {"answer": str(val)}
            # Hicbiri yoksa ilk string field'i al
            for key, val in last.items():
                if isinstance(val, str) and val:
                    return {"answer": val}
            return {"answer": str(last)}

        return {"answer": str(last)}


def list_pipelines() -> list[dict[str, Any]]:
    """Kayitli pipeline'lari doner."""
    return [
        {
            "name": name,
            "steps": [s.agent for s in steps],
            "step_count": len(steps),
        }
        for name, steps in PIPELINES.items()
    ]
