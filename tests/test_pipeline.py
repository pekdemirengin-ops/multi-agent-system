"""Pipeline testleri."""
from __future__ import annotations

import pytest

from core.pipeline import PIPELINES, PipelineStep, list_pipelines


class TestPipelineDefinitions:
    def test_research_pipeline_exists(self) -> None:
        assert "research" in PIPELINES

    def test_code_pipeline_exists(self) -> None:
        assert "code" in PIPELINES

    def test_content_pipeline_exists(self) -> None:
        assert "content" in PIPELINES

    def test_social_pipeline_exists(self) -> None:
        assert "social" in PIPELINES

    def test_fact_pipeline_exists(self) -> None:
        assert "fact" in PIPELINES

    def test_research_pipeline_steps(self) -> None:
        steps = PIPELINES["research"]
        agents = [s.agent for s in steps]
        assert agents == ["researcher", "fact_checker", "summarizer"]

    def test_code_pipeline_steps(self) -> None:
        steps = PIPELINES["code"]
        agents = [s.agent for s in steps]
        assert agents == ["planner", "coder", "reviewer"]

    def test_content_pipeline_steps(self) -> None:
        steps = PIPELINES["content"]
        agents = [s.agent for s in steps]
        assert agents == ["researcher", "email_composer"]

    def test_fact_pipeline_steps(self) -> None:
        steps = PIPELINES["fact"]
        agents = [s.agent for s in steps]
        assert agents == ["researcher", "fact_checker"]


class TestPipelineStep:
    def test_step_creation(self) -> None:
        step = PipelineStep(agent="researcher", name="Arastirma")
        assert step.agent == "researcher"
        assert step.name == "Arastirma"

    def test_step_get_input_default(self) -> None:
        step = PipelineStep(agent="researcher")
        result = step.get_input("onceki cikti", "orijinal soru")
        assert "onceki cikti" in result

    def test_step_get_input_dict(self) -> None:
        step = PipelineStep(agent="researcher")
        result = step.get_input({"answer": "test cevap"}, "soru")
        assert result == "test cevap"

    def test_step_get_input_with_transform(self) -> None:
        step = PipelineStep(
            agent="coder",
            transform=lambda prev: f"KOD: {prev}",
        )
        result = step.get_input("test", "soru")
        assert result == "KOD: test"


class TestListPipelines:
    def test_list_returns_list(self) -> None:
        pipelines = list_pipelines()
        assert isinstance(pipelines, list)
        assert len(pipelines) >= 5

    def test_each_pipeline_has_name(self) -> None:
        for p in list_pipelines():
            assert "name" in p
            assert "steps" in p
            assert "step_count" in p

    def test_research_in_list(self) -> None:
        names = [p["name"] for p in list_pipelines()]
        assert "research" in names
        assert "code" in names
