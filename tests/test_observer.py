"""Tests for observer package."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from oagi.agent.observer import (
    ActionEvent,
    AsyncAgentObserver,
    ExportFormat,
    LogEvent,
    PlanEvent,
    SplitEvent,
    StepEvent,
)
from oagi.types import Action, ActionType, Step


@pytest.fixture
def sample_step():
    return Step(
        reason="Clicking the button",
        actions=[
            Action(type=ActionType.CLICK, argument="500,300"),
            Action(type=ActionType.TYPE, argument="hello"),
        ],
        stop=False,
    )


@pytest.fixture
def sample_step_complete():
    return Step(
        reason="Task completed",
        actions=[],
        stop=True,
    )


class TestAsyncAgentObserver:
    @pytest.mark.asyncio
    async def test_on_event_records_step_event(self, sample_step):
        observer = AsyncAgentObserver()

        event = StepEvent(
            step_num=1,
            image=b"test_image_bytes",
            step=sample_step,
        )
        await observer.on_event(event)

        assert len(observer.events) == 1
        assert observer.events[0] == event

    @pytest.mark.asyncio
    async def test_on_event_records_action_event(self):
        observer = AsyncAgentObserver()

        actions = [Action(type=ActionType.CLICK, argument="100,200")]
        event = ActionEvent(
            step_num=1,
            actions=actions,
            error=None,
        )
        await observer.on_event(event)

        assert len(observer.events) == 1
        assert observer.events[0] == event

    @pytest.mark.asyncio
    async def test_on_event_records_action_event_with_error(self):
        observer = AsyncAgentObserver()

        actions = [Action(type=ActionType.CLICK, argument="100,200")]
        event = ActionEvent(
            step_num=1,
            actions=actions,
            error="Click failed",
        )
        await observer.on_event(event)

        assert len(observer.events) == 1
        assert observer.events[0].error == "Click failed"

    def test_add_log(self):
        observer = AsyncAgentObserver()
        observer.add_log("Test message")

        assert len(observer.events) == 1
        assert isinstance(observer.events[0], LogEvent)
        assert observer.events[0].message == "Test message"

    def test_add_split(self):
        observer = AsyncAgentObserver()
        observer.add_split("Section 1")

        assert len(observer.events) == 1
        assert isinstance(observer.events[0], SplitEvent)
        assert observer.events[0].label == "Section 1"

    def test_add_split_empty_label(self):
        observer = AsyncAgentObserver()
        observer.add_split()

        assert len(observer.events) == 1
        assert isinstance(observer.events[0], SplitEvent)
        assert observer.events[0].label == ""

    def test_clear(self):
        observer = AsyncAgentObserver()
        observer.add_log("Test 1")
        observer.add_log("Test 2")

        assert len(observer.events) == 2
        observer.clear()
        assert len(observer.events) == 0

    @pytest.mark.asyncio
    async def test_get_events_by_step(self, sample_step):
        observer = AsyncAgentObserver()

        # Add events for step 1
        await observer.on_event(StepEvent(step_num=1, image=b"img1", step=sample_step))
        await observer.on_event(
            ActionEvent(
                step_num=1,
                actions=[Action(type=ActionType.CLICK, argument="100,200")],
            )
        )

        # Add events for step 2
        await observer.on_event(StepEvent(step_num=2, image=b"img2", step=sample_step))

        # Add log (no step_num)
        observer.add_log("Test log")

        step1_events = observer.get_events_by_step(1)
        assert len(step1_events) == 2

        step2_events = observer.get_events_by_step(2)
        assert len(step2_events) == 1

    @pytest.mark.asyncio
    async def test_export_markdown(self, sample_step):
        observer = AsyncAgentObserver()

        await observer.on_event(
            StepEvent(step_num=1, image="http://example.com/img.png", step=sample_step)
        )
        observer.add_log("Test log message")
        observer.add_split("Section Break")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.md"
            observer.export(ExportFormat.MARKDOWN, str(output_path))

            assert output_path.exists()
            content = output_path.read_text()
            assert "Step 1" in content
            assert "Clicking the button" in content
            assert "Test log message" in content
            assert "Section Break" in content

    @pytest.mark.asyncio
    async def test_export_html(self, sample_step):
        observer = AsyncAgentObserver()

        await observer.on_event(
            StepEvent(step_num=1, image=b"test_image_bytes", step=sample_step)
        )
        await observer.on_event(
            ActionEvent(
                step_num=1,
                actions=sample_step.actions,
            )
        )
        observer.add_log("Test log")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            observer.export("html", str(output_path))

            assert output_path.exists()
            content = output_path.read_text()
            assert "<html" in content
            assert "Step 1" in content
            assert "Clicking the button" in content
            assert "Test log" in content
            # Check base64 image is embedded
            assert "data:image/png;base64," in content

    @pytest.mark.asyncio
    async def test_export_json(self, sample_step):
        observer = AsyncAgentObserver()

        await observer.on_event(
            StepEvent(step_num=1, image=b"test_image_bytes", step=sample_step)
        )
        await observer.on_event(
            ActionEvent(
                step_num=1,
                actions=sample_step.actions,
            )
        )
        observer.add_log("Test log")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.json"
            observer.export(ExportFormat.JSON, str(output_path))

            assert output_path.exists()
            content = output_path.read_text()
            data = json.loads(content)
            assert len(data) == 3
            assert data[0]["type"] == "step"
            assert data[0]["step_num"] == 1
            assert data[0]["image_encoding"] == "base64"
            assert data[1]["type"] == "action"
            assert data[2]["type"] == "log"


class TestEventModels:
    def test_step_event_with_bytes_image(self):
        step = Step(reason="test", actions=[], stop=False)
        event = StepEvent(step_num=1, image=b"bytes", step=step)
        assert isinstance(event.image, bytes)

    def test_step_event_with_url_image(self):
        step = Step(reason="test", actions=[], stop=False)
        event = StepEvent(step_num=1, image="http://example.com/img.png", step=step)
        assert isinstance(event.image, str)

    def test_event_timestamp_auto_generated(self):
        event = LogEvent(message="test")
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)

    def test_action_event_default_no_error(self):
        actions = [Action(type=ActionType.CLICK, argument="100,200")]
        event = ActionEvent(step_num=1, actions=actions)
        assert event.error is None

    def test_split_event_default_empty_label(self):
        event = SplitEvent()
        assert event.label == ""

    def test_plan_event_with_bytes_image(self):
        event = PlanEvent(
            phase="initial",
            image=b"test_image",
            reasoning="Planning reasoning",
            result="Generated instruction",
        )
        assert event.type == "plan"
        assert event.phase == "initial"
        assert isinstance(event.image, bytes)
        assert event.reasoning == "Planning reasoning"
        assert event.result == "Generated instruction"

    def test_plan_event_with_url_image(self):
        event = PlanEvent(
            phase="reflection",
            image="http://example.com/img.png",
            reasoning="Reflection reasoning",
            result="continue",
        )
        assert event.type == "plan"
        assert event.phase == "reflection"
        assert isinstance(event.image, str)

    def test_plan_event_without_image(self):
        event = PlanEvent(
            phase="summary",
            reasoning="Summary text",
        )
        assert event.type == "plan"
        assert event.phase == "summary"
        assert event.image is None
        assert event.result is None


class TestPlanEventExports:
    @pytest.mark.asyncio
    async def test_export_markdown_with_plan_event(self):
        observer = AsyncAgentObserver()

        await observer.on_event(
            PlanEvent(
                phase="initial",
                image="http://example.com/img.png",
                reasoning="Initial planning reasoning",
                result="Generated instruction",
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.md"
            observer.export(ExportFormat.MARKDOWN, str(output_path))

            assert output_path.exists()
            content = output_path.read_text()
            assert "Initial Planning" in content
            assert "Initial planning reasoning" in content
            assert "Generated instruction" in content

    @pytest.mark.asyncio
    async def test_export_html_with_plan_event(self):
        observer = AsyncAgentObserver()

        await observer.on_event(
            PlanEvent(
                phase="reflection",
                image=b"test_image_bytes",
                reasoning="Reflection reasoning",
                result="pivot",
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            observer.export("html", str(output_path))

            assert output_path.exists()
            content = output_path.read_text()
            assert "<html" in content
            assert "Reflection" in content
            assert "Reflection reasoning" in content
            assert "pivot" in content
            assert "data:image/png;base64," in content

    @pytest.mark.asyncio
    async def test_export_json_with_plan_event(self):
        observer = AsyncAgentObserver()

        await observer.on_event(
            PlanEvent(
                phase="summary",
                image=None,
                reasoning="Task summary",
                result=None,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.json"
            observer.export(ExportFormat.JSON, str(output_path))

            assert output_path.exists()
            content = output_path.read_text()
            data = json.loads(content)
            assert len(data) == 1
            assert data[0]["type"] == "plan"
            assert data[0]["phase"] == "summary"
            assert data[0]["reasoning"] == "Task summary"

    @pytest.mark.asyncio
    async def test_export_json_with_plan_event_bytes_image(self):
        observer = AsyncAgentObserver()

        await observer.on_event(
            PlanEvent(
                phase="initial",
                image=b"test_image",
                reasoning="Planning",
                result="instruction",
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.json"
            observer.export(ExportFormat.JSON, str(output_path))

            content = output_path.read_text()
            data = json.loads(content)
            assert data[0]["image_encoding"] == "base64"
