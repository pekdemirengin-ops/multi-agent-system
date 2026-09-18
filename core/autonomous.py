"""Autonomous Engine - hedefi planlar ve adim adim calistirir."""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, AsyncIterator

import structlog

from core.base_agent import BaseAgent, Message
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


# ============================================================
# Planner Prompt
# ============================================================
PLANNER_PROMPT = """Sen bir gorev planlayicisisin. Kullanicinin hedefini analiz et ve
bu hedefe ulasmak icin 2-5 ARA ADIM olustur.

KURALLAR:
- Her adim tek bir bilgi istemeli
- Adimlar birbirine bagimli OLMAMALI (paralel calisabilir)
- Her adim icin en uygun agent'i sec
- Turkce
- SADECE JSON don

MEVCUT AGENT'LAR:
- researcher: web arastirma, guncel bilgi, kisi/yer sorulari
- coder: kod yazma
- summarizer: ozetleme
- translator: ceviri
- calculator: matematik
- data_analyst: veri analizi
- fact_checker: bilgi dogrulama
- quiz_maker: quiz/test uretimi
- email_composer: email yazma
- social_media: tweet/sosyal medya
- web_scraper: URL'den icerik cekme

CIKTI FORMATI (JSON):
{
  "goal_summary": "Hedefin kisa ozeti",
  "steps": [
    {"step": 1, "query": "Kozan belediye baskani kim?", "agent": "researcher"},
    {"step": 2, "query": "Kozan nufusu kac?", "agent": "researcher"},
    {"step": 3, "query": "Kozan yuz olcumu kac km2?", "agent": "researcher"}
  ],
  "report_title": "Kozan Hakkinda Rapor"
}
"""


FINAL_REPORT_PROMPT = """Sen bir rapor yazarisin. Asagidaki arastirma sonuclarindan
KAPSAMLI ve DUZENLI bir rapor yaz.

FORMAT:
# [Baslik]

## [Alt Baslik 1]
[Icerik]

## [Alt Baslik 2]
[Icerik]

KURALLAR:
- Maddeler halinde, net ve oz
- SADECE verilen bilgileri kullan
- Bilgi eksikse "bulunamadi" yaz
- Turkce
- Maksimum 500 kelime
"""


# ============================================================
# Veri Siniflari
# ============================================================
@dataclass
class AutonomousStep:
    """Tek bir adim."""
    step: int
    query: str
    agent: str
    status: str = "pending"  # pending | running | done | error
    output: str = ""
    duration_ms: int = 0
    error: str | None = None


@dataclass
class AutonomousResult:
    """Autonomous calistirma sonucu."""
    goal: str
    goal_summary: str = ""
    report_title: str = ""
    steps: list[AutonomousStep] = field(default_factory=list)
    final_report: str = ""
    success: bool = False
    duration_ms: int = 0
    error: str | None = None


# ============================================================
# Autonomous Engine
# ============================================================
class AutonomousEngine:
    """Hedef verilir, planlar ve calistirir."""

    def __init__(self, agents: dict[str, BaseAgent], timeout: int = 60) -> None:
        self.agents = agents
        self.timeout = timeout
        self.llm = GroqLLMClient(model="openai/gpt-oss-120b")

    def _extract_json(self, raw: str) -> dict | None:
        """Metinden JSON cikarir."""
        try:
            # Code fence temizle
            text = raw.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            # JSON bul
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception as e:
            logger.warning("autonomous.json_parse_error", error=str(e))
        return None

    async def plan(self, goal: str) -> tuple[list[AutonomousStep], str, str]:
        """Hedefi alt adimlara boler.

        Returns:
            (steps, goal_summary, report_title)
        """
        logger.info("autonomous.planning", goal=goal[:100])

        try:
            raw = self.llm.chat(
                prompt=f"Hedef: {goal}",
                system=PLANNER_PROMPT,
            )
            data = self._extract_json(raw)

            if not data or "steps" not in data:
                # Fallback: tek adim
                return (
                    [AutonomousStep(step=1, query=goal, agent="researcher")],
                    goal,
                    "Rapor",
                )

            steps = []
            for s in data.get("steps", [])[:5]:  # Max 5 adim
                steps.append(AutonomousStep(
                    step=int(s.get("step", len(steps) + 1)),
                    query=str(s.get("query", "")),
                    agent=str(s.get("agent", "researcher")),
                ))

            goal_summary = str(data.get("goal_summary", goal))
            report_title = str(data.get("report_title", "Rapor"))

            logger.info("autonomous.plan_done", step_count=len(steps))
            return steps, goal_summary, report_title

        except Exception as e:
            logger.exception("autonomous.plan_error", error=str(e))
            return (
                [AutonomousStep(step=1, query=goal, agent="researcher")],
                goal,
                "Rapor",
            )

    async def _run_step(self, step: AutonomousStep) -> AutonomousStep:
        """Tek bir adimi calistirir."""
        import time
        start = time.perf_counter()

        step.status = "running"

        agent_name = step.agent
        if agent_name not in self.agents:
            # Fallback: researcher
            agent_name = "researcher" if "researcher" in self.agents else list(self.agents.keys())[0]

        try:
            agent = self.agents[agent_name]
            output = await asyncio.wait_for(
                self._run_agent_internal(agent, step.query),
                timeout=self.timeout,
            )
            step.duration_ms = int((time.perf_counter() - start) * 1000)
            step.status = "done"

            # Cikti metnini cikar
            if isinstance(output, dict):
                for key in ["answer", "research", "translation", "result", "summary"]:
                    if key in output and output[key]:
                        step.output = str(output[key])
                        break
                if not step.output:
                    step.output = str(output)
            else:
                step.output = str(output)

            # Bos cevap kontrolu
            if not step.output or len(step.output) < 5:
                step.status = "error"
                step.error = "Bos cevap"

            logger.info("autonomous.step_done", step=step.step, agent=agent_name, duration_ms=step.duration_ms)
            return step

        except asyncio.TimeoutError:
            step.duration_ms = int((time.perf_counter() - start) * 1000)
            step.status = "error"
            step.error = "Timeout"
            logger.warning("autonomous.step_timeout", step=step.step)
            return step
        except Exception as e:
            step.duration_ms = int((time.perf_counter() - start) * 1000)
            step.status = "error"
            step.error = str(e)
            logger.exception("autonomous.step_error", step=step.step, error=str(e))
            return step

    async def _run_agent_internal(self, agent: BaseAgent, input_text: str) -> dict:
        """Agent'i calistirir ve ciktisini toplar."""
        message = Message(
            sender="__autonomous__",
            receiver=agent.name,
            content=input_text,
            msg_type="task",
            id=str(uuid.uuid4()),
        )

        collected: list[Any] = []
        original_send = agent.send

        async def capture_send(receiver: str, content: Any, msg_type: str = "result") -> None:
            if msg_type == "result":
                collected.append(content)

        agent.send = capture_send  # type: ignore
        try:
            await agent.handle(message)
        finally:
            agent.send = original_send  # type: ignore

        if not collected:
            return {"answer": ""}
        return collected[-1] if isinstance(collected[-1], dict) else {"answer": str(collected[-1])}

    async def execute(self, goal: str) -> AutonomousResult:
        """Hedefi tam olarak calistirir (non-streaming)."""
        import time
        start = time.perf_counter()

        result = AutonomousResult(goal=goal)

        try:
            # 1) Planla
            steps, goal_summary, report_title = await self.plan(goal)
            result.steps = steps
            result.goal_summary = goal_summary
            result.report_title = report_title

            # 2) Adimlari paralel calistir
            logger.info("autonomous.executing", step_count=len(steps))
            tasks = [self._run_step(s) for s in steps]
            result.steps = await asyncio.gather(*tasks)

            # 3) Final rapor
            result.final_report = await self._generate_report(result)
            result.success = True
            result.duration_ms = int((time.perf_counter() - start) * 1000)

            logger.info("autonomous.done", duration_ms=result.duration_ms)
            return result

        except Exception as e:
            logger.exception("autonomous.error", error=str(e))
            result.success = False
            result.error = str(e)
            result.duration_ms = int((time.perf_counter() - start) * 1000)
            return result

    async def execute_stream(self, goal: str) -> AsyncIterator[dict]:
        """Hedefi SSE ile canli stream eder."""
        import time
        start = time.perf_counter()

        # 1) Plan
        yield {"type": "planning", "message": "Plan olusturuluyor..."}

        steps, goal_summary, report_title = await self.plan(goal)

        yield {
            "type": "plan_ready",
            "goal_summary": goal_summary,
            "report_title": report_title,
            "steps": [
                {"step": s.step, "query": s.query, "agent": s.agent}
                for s in steps
            ],
            "total_steps": len(steps),
        }

        # 2) Adimlari sirali calistir (canli gosterim icin)
        for step in steps:
            yield {
                "type": "step_start",
                "step": step.step,
                "query": step.query,
                "agent": step.agent,
                "total": len(steps),
            }

            result = await self._run_step(step)

            if result.status == "done":
                yield {
                    "type": "step_done",
                    "step": result.step,
                    "agent": result.agent,
                    "output": result.output[:500],
                    "duration_ms": result.duration_ms,
                }
            else:
                yield {
                    "type": "step_error",
                    "step": result.step,
                    "agent": result.agent,
                    "error": result.error,
                    "duration_ms": result.duration_ms,
                }

        # 3) Final rapor
        yield {"type": "report_generating", "message": "Final rapor hazirlaniyor..."}

        result = AutonomousResult(
            goal=goal,
            goal_summary=goal_summary,
            report_title=report_title,
            steps=steps,
        )
        result.final_report = await self._generate_report(result)
        result.duration_ms = int((time.perf_counter() - start) * 1000)
        result.success = True

        yield {
            "type": "done",
            "success": True,
            "final_report": result.final_report,
            "duration_ms": result.duration_ms,
            "steps_completed": sum(1 for s in steps if s.status == "done"),
            "total_steps": len(steps),
        }

    async def _generate_report(self, result: AutonomousResult) -> str:
        """Adim sonuclarindan final rapor uretir."""
        # Sonuclari topla
        lines = [f"Hedef: {result.goal}", ""]
        for step in result.steps:
            if step.status == "done":
                lines.append(f"Soru: {step.query}")
                lines.append(f"Cevap: {step.output[:800]}")
                lines.append("")
            else:
                lines.append(f"Soru: {step.query}")
                lines.append(f"Sonuc: {step.error or 'Bulunamadi'}")
                lines.append("")

        context = "\n".join(lines)

        try:
            raw = self.llm.chat(
                prompt=f"Arastirma Sonuclari:\n{context}\n\nRapor:",
                system=FINAL_REPORT_PROMPT,
            )
            return raw.strip()
        except Exception as e:
            logger.exception("autonomous.report_error", error=str(e))
            # Fallback: sonuclari birlestir
            fallback = f"# {result.report_title}\n\n"
            for step in result.steps:
                if step.status == "done":
                    fallback += f"## {step.query}\n{step.output[:300]}\n\n"
            return fallback
