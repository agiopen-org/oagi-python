# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import json
from typing import Any

from ...client import AsyncClient
from .memory import PlannerMemory
from .models import Action, PlannerOutput, ReflectionOutput


class Planner:
    """Planner for task decomposition and reflection.

    This class provides planning and reflection capabilities using OAGI workers.
    """

    def __init__(
        self,
        client: AsyncClient | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """Initialize the planner.

        Args:
            client: AsyncClient for OAGI API calls. If None, one will be created when needed.
            api_key: API key for creating internal client
            base_url: Base URL for creating internal client
        """
        self.client = client
        self.api_key = api_key
        self.base_url = base_url
        self._owns_client = False  # Track if we created the client

    def _ensure_client(self) -> AsyncClient:
        """Ensure we have a client, creating one if needed."""
        if not self.client:
            self.client = AsyncClient(api_key=self.api_key, base_url=self.base_url)
            self._owns_client = True
        return self.client

    async def close(self):
        """Close the client if we own it."""
        if self._owns_client and self.client:
            await self.client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _extract_memory_data(
        self,
        memory: PlannerMemory | None,
        context: dict[str, Any],
        todo_index: int | None = None,
    ) -> tuple[str, list, list, list, str | None, str]:
        """Extract memory data for API calls.

        Args:
            memory: Optional PlannerMemory instance
            context: Fallback context dictionary
            todo_index: Optional todo index for extracting overall_todo

        Returns:
            Tuple of (task_description, todos, deliverables, history,
                     task_execution_summary, overall_todo)
        """
        if memory and todo_index is not None:
            # Use memory data
            task_description = memory.task_description
            todos = [
                {
                    "index": i,
                    "description": t.description,
                    "status": t.status.value,
                    "execution_summary": memory.todo_execution_summaries.get(i),
                }
                for i, t in enumerate(memory.todos)
            ]
            deliverables = [d.model_dump() for d in memory.deliverables]
            history = [
                {
                    "todo_index": h.todo_index,
                    "todo_description": h.todo,
                    "action_count": len(h.actions),
                    "summary": h.summary,
                    "completed": h.completed,
                }
                for h in memory.history
            ]
            task_execution_summary = memory.task_execution_summary or None
            overall_todo = memory.todos[todo_index].description if memory.todos else ""
        else:
            # Fallback to basic context
            task_description = context.get("task_description", "")
            todos = context.get("todos", [])
            deliverables = context.get("deliverables", [])
            history = context.get("history", [])
            task_execution_summary = None
            overall_todo = context.get("current_todo", "")

        return (
            task_description,
            todos,
            deliverables,
            history,
            task_execution_summary,
            overall_todo,
        )

    async def initial_plan(
        self,
        todo: str,
        context: dict[str, Any],
        screenshot: bytes | None = None,
        memory: PlannerMemory | None = None,
        todo_index: int | None = None,
    ) -> PlannerOutput:
        """Generate initial plan for a todo.

        Args:
            todo: The todo description to plan for
            context: Full context including task, todos, deliverables, and history
            screenshot: Optional screenshot for visual context
            memory: Optional PlannerMemory for formatting contexts
            todo_index: Optional todo index for formatting internal context

        Returns:
            PlannerOutput with instruction, reasoning, and optional subtodos
        """
        # Ensure we have a client
        client = self._ensure_client()

        # Upload screenshot if provided
        screenshot_uuid = None
        if screenshot:
            upload_response = await client.put_s3_presigned_url(screenshot)
            screenshot_uuid = upload_response.uuid

        # Extract memory data if provided
        (
            task_description,
            todos,
            deliverables,
            history,
            task_execution_summary,
            _,  # overall_todo not needed here, we use the `todo` parameter
        ) = self._extract_memory_data(memory, context, todo_index)

        # Call OAGI worker
        response = await client.call_worker(
            worker_id="oagi_first",
            overall_todo=todo,
            task_description=task_description,
            todos=todos,
            deliverables=deliverables,
            history=history,
            current_todo_index=todo_index,
            task_execution_summary=task_execution_summary,
            current_screenshot=screenshot_uuid,
        )

        # Parse response
        return self._parse_planner_output(response.response)

    async def reflect(
        self,
        actions: list[Action],
        context: dict[str, Any],
        screenshot: bytes | None = None,
        memory: PlannerMemory | None = None,
        todo_index: int | None = None,
        current_instruction: str | None = None,
    ) -> ReflectionOutput:
        """Reflect on recent actions and progress.

        Args:
            actions: Recent actions to reflect on
            context: Full context including task, todos, deliverables, and history
            screenshot: Optional current screenshot
            memory: Optional PlannerMemory for formatting contexts
            todo_index: Optional todo index for formatting internal context
            current_instruction: Current subtask instruction being executed

        Returns:
            ReflectionOutput with continuation decision and reasoning
        """
        # Ensure we have a client
        client = self._ensure_client()

        # Upload screenshot if provided
        result_screenshot_uuid = None
        if screenshot:
            upload_response = await client.put_s3_presigned_url(screenshot)
            result_screenshot_uuid = upload_response.uuid

        # Extract memory data if provided
        (
            task_description,
            todos,
            deliverables,
            history,
            task_execution_summary,
            overall_todo,
        ) = self._extract_memory_data(memory, context, todo_index)

        # Convert actions to window_steps format
        window_steps = [
            {
                "step_number": i + 1,
                "action_type": action.action_type,
                "target": action.target or "",
                "reasoning": action.reasoning or "",
            }
            for i, action in enumerate(actions[-10:])  # Last 10 actions
        ]

        # Format prior notes from context (still needed as a simple string summary)
        prior_notes = self._format_execution_notes(context)

        # Call OAGI worker
        response = await client.call_worker(
            worker_id="oagi_follow",
            overall_todo=overall_todo,
            task_description=task_description,
            todos=todos,
            deliverables=deliverables,
            history=history,
            current_todo_index=todo_index,
            task_execution_summary=task_execution_summary,
            current_subtask_instruction=current_instruction or "",
            window_steps=window_steps,
            window_screenshots=[],  # Could be populated if we track screenshot history
            result_screenshot=result_screenshot_uuid,
            prior_notes=prior_notes,
        )

        # Parse response
        return self._parse_reflection_output(response.response)

    async def summarize(
        self,
        execution_history: list[Action],
        context: dict[str, Any],
        memory: PlannerMemory | None = None,
        todo_index: int | None = None,
    ) -> str:
        """Generate execution summary.

        Args:
            execution_history: Complete execution history
            context: Full context including task, todos, deliverables
            memory: Optional PlannerMemory for formatting contexts
            todo_index: Optional todo index for formatting internal context

        Returns:
            String summary of the execution
        """
        # Ensure we have a client
        client = self._ensure_client()

        # Extract memory data if provided
        (
            task_description,
            todos,
            deliverables,
            history,
            task_execution_summary,
            overall_todo,
        ) = self._extract_memory_data(memory, context, todo_index)

        # Extract latest_todo_summary (specific to summarize method)
        if memory and todo_index is not None:
            latest_todo_summary = memory.todo_execution_summaries.get(todo_index, "")
        else:
            latest_todo_summary = ""

        # Call OAGI worker
        response = await client.call_worker(
            worker_id="oagi_task_summary",
            overall_todo=overall_todo,
            task_description=task_description,
            todos=todos,
            deliverables=deliverables,
            history=history,
            current_todo_index=todo_index,
            task_execution_summary=task_execution_summary,
            latest_todo_summary=latest_todo_summary,
        )

        # Parse response and extract summary
        try:
            result = json.loads(response.response)
            return result.get("task_summary", response.response)
        except json.JSONDecodeError:
            return response.response

    def _format_execution_notes(self, context: dict[str, Any]) -> str:
        """Format execution history notes.

        Args:
            context: Context dictionary

        Returns:
            Formatted execution notes
        """
        if not context.get("history"):
            return ""

        parts = []
        for hist in context["history"]:
            parts.append(
                f"Todo {hist['todo_index']}: {hist['action_count']} actions, "
                f"completed: {hist['completed']}"
            )
            if hist.get("summary"):
                parts.append(f"Summary: {hist['summary']}")

        return "\n".join(parts)

    def _parse_planner_output(self, response: str) -> PlannerOutput:
        """Parse OAGI worker response into structured planner output.

        Args:
            response: Raw string response from OAGI worker (oagi_first)

        Returns:
            Structured PlannerOutput
        """
        try:
            # Try to parse as JSON (oagi_first format)
            data = json.loads(response)
            # oagi_first returns: {"reasoning": "...", "subtask": "..."}
            return PlannerOutput(
                instruction=data.get("subtask", data.get("instruction", "")),
                reasoning=data.get("reasoning", ""),
                subtodos=data.get(
                    "subtodos", []
                ),  # Not typically returned by oagi_first
            )
        except (json.JSONDecodeError, KeyError):
            # Fallback: use the entire response as instruction
            return PlannerOutput(
                instruction=response,
                reasoning="Failed to parse structured response",
                subtodos=[],
            )

    def _parse_reflection_output(self, response: str) -> ReflectionOutput:
        """Parse reflection response into structured output.

        Args:
            response: Raw string response from OAGI worker (oagi_follow)

        Returns:
            Structured ReflectionOutput
        """
        try:
            # Try to parse as JSON (oagi_follow format)
            data = json.loads(response)
            # oagi_follow returns:
            # {"assessment": "...", "summary": "...", "reflection": "...",
            #  "success": "yes" | "no", "subtask_instruction": "..."}

            # Determine if we should continue or pivot
            success = data.get("success", "no") == "yes"
            new_subtask = data.get("subtask_instruction", "").strip()

            # Continue current if success is not achieved and no new subtask provided
            # Pivot if a new subtask instruction is provided
            continue_current = not success and not new_subtask

            return ReflectionOutput(
                continue_current=continue_current,
                new_instruction=new_subtask if new_subtask else None,
                reasoning=data.get("reflection", data.get("reasoning", "")),
                success_assessment=success,
            )
        except (json.JSONDecodeError, KeyError):
            # Fallback: continue with current approach
            return ReflectionOutput(
                continue_current=True,
                new_instruction=None,
                reasoning="Failed to parse reflection response, continuing current approach",
                success_assessment=False,
            )
