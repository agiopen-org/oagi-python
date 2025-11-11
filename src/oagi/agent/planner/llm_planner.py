"""LLM-based planner for task decomposition and reflection."""

import json
from typing import Any

from ...client import AsyncClient
from .memory import PlannerMemory
from .models import Action, PlannerOutput, ReflectionOutput


class LLMPlanner:
    """LLM-based planner for task decomposition and reflection.

    This class provides planning and reflection capabilities using OAGI workers.
    """

    def __init__(self, client: AsyncClient | None = None):
        """Initialize the LLM planner.

        Args:
            client: AsyncClient for OAGI API calls. If None, one will be created when needed.
        """
        self.client = client
        self._owns_client = False  # Track if we created the client

    def _ensure_client(self) -> AsyncClient:
        """Ensure we have a client, creating one if needed."""
        if not self.client:
            self.client = AsyncClient()
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
        screenshot_url = None
        if screenshot:
            upload_response = await client.put_s3_presigned_url(screenshot)
            screenshot_url = upload_response.download_url

        # Format contexts using memory if provided
        if memory and todo_index is not None:
            internal_context = memory.format_internal_context(todo_index)
            external_context = memory.format_external_context()
        else:
            # Fallback to basic formatting
            internal_context = f"## Current Todo\n{todo}"
            external_context = self._format_external_context_from_dict(context)

        # Call OAGI worker
        response = await client.call_worker(
            worker_id="oagi_first",
            overall_todo=todo,
            internal_context=internal_context,
            external_context=external_context,
            current_screenshot=screenshot_url,
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
        result_screenshot_url = None
        if screenshot:
            upload_response = await client.put_s3_presigned_url(screenshot)
            result_screenshot_url = upload_response.download_url

        # Format contexts using memory if provided
        if memory and todo_index is not None:
            internal_context = memory.format_internal_context(todo_index)
            external_context = memory.format_external_context()
            overall_todo = memory.todos[todo_index].description if memory.todos else ""
        else:
            # Fallback to basic formatting
            internal_context = self._format_internal_context_from_dict(context)
            external_context = self._format_external_context_from_dict(context)
            overall_todo = context.get("current_todo", "")

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

        # Format prior notes from context
        prior_notes = self._format_execution_notes(context)

        # Call OAGI worker
        response = await client.call_worker(
            worker_id="oagi_follow",
            overall_todo=overall_todo,
            internal_context=internal_context,
            external_context=external_context,
            current_subtask_instruction=current_instruction or "",
            window_steps=window_steps,
            window_screenshots=[],  # Could be populated if we track screenshot history
            result_screenshot=result_screenshot_url,
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

        # Format contexts using memory if provided
        if memory and todo_index is not None:
            internal_context = memory.format_internal_context(todo_index)
            external_context = memory.format_external_context()
            overall_todo = memory.todos[todo_index].description if memory.todos else ""
            latest_todo_summary = memory.todo_execution_summaries.get(todo_index, "")
        else:
            # Fallback to basic formatting
            internal_context = self._format_internal_context_from_dict(context)
            external_context = self._format_external_context_from_dict(context)
            overall_todo = context.get("current_todo", "")
            latest_todo_summary = ""

        # Call OAGI worker
        response = await client.call_worker(
            worker_id="oagi_task_summary",
            overall_todo=overall_todo,
            internal_context=internal_context,
            external_context=external_context,
            latest_todo_summary=latest_todo_summary,
        )

        # Parse response and extract summary
        try:
            result = json.loads(response.response)
            return result.get("task_summary", response.response)
        except json.JSONDecodeError:
            return response.response

    def _format_internal_context_from_dict(self, context: dict[str, Any]) -> str:
        """Format internal context from dictionary (fallback).

        Args:
            context: Context dictionary

        Returns:
            Markdown-formatted internal context
        """
        parts = ["## Current TODO"]

        # Add current todo
        if "current_todo" in context:
            parts.append(f"Working on: {context['current_todo']}")

        # Add todos with status
        if "todos" in context:
            parts.append("\n## All Todos")
            for todo_item in context["todos"]:
                parts.append(
                    f"{todo_item['index']}. {todo_item['description']} ({todo_item['status']})"
                )

        return "\n".join(parts)

    def _format_external_context_from_dict(self, context: dict[str, Any]) -> str | None:
        """Format external context from dictionary (fallback).

        Args:
            context: Context dictionary

        Returns:
            Markdown-formatted external context or None
        """
        if not context.get("task_description"):
            return None

        parts = ["## Overall Context"]
        parts.append(context["task_description"])

        # Add deliverables
        if "deliverables" in context:
            parts.append("\n## Deliverables")
            for deliverable in context["deliverables"]:
                status = "✅" if deliverable["achieved"] else "❌"
                parts.append(f"{status} {deliverable['description']}")

        return "\n".join(parts)

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

    def _build_initial_plan_prompt(
        self,
        todo: str,
        context: dict[str, Any],
    ) -> str:
        """Build prompt for initial planning.

        Args:
            todo: The todo to plan for
            context: Full execution context

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "You are a task planning assistant. Your goal is to convert a high-level todo into a clear, actionable instruction.",
            "",
            f"Overall Task: {context.get('task_description', 'Not specified')}",
            "",
            "All Todos:",
        ]

        # Add todos with status
        for todo_item in context.get("todos", []):
            status_emoji = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅",
                "skipped": "⏭️",
            }.get(todo_item["status"], "❓")
            prompt_parts.append(
                f"{status_emoji} [{todo_item['index']}] {todo_item['description']} ({todo_item['status']})"
            )

        prompt_parts.extend(
            [
                "",
                f"Current Todo to Execute: {todo}",
                "",
                "Deliverables to achieve:",
            ]
        )

        # Add deliverables
        for deliverable in context.get("deliverables", []):
            achieved_emoji = "✅" if deliverable["achieved"] else "❌"
            prompt_parts.append(f"{achieved_emoji} {deliverable['description']}")

        # Add execution history if exists
        if context.get("history"):
            prompt_parts.extend(["", "Previous Execution History:"])
            for hist in context["history"]:
                prompt_parts.append(
                    f"- Todo {hist['todo_index']}: {hist['todo']} "
                    f"({hist['action_count']} actions, completed: {hist['completed']})"
                )
                if hist.get("summary"):
                    prompt_parts.append(f"  Summary: {hist['summary']}")

        prompt_parts.extend(
            [
                "",
                "Please provide:",
                "1. A clear, specific instruction for executing this todo",
                "2. Your reasoning for this approach",
                "3. Any subtasks if the todo needs to be broken down (optional)",
                "",
                "Respond in JSON format:",
                '{"instruction": "...", "reasoning": "...", "subtodos": [...]}',
            ]
        )

        return "\n".join(prompt_parts)

    def _build_reflection_prompt(
        self,
        actions: list[Action],
        context: dict[str, Any],
    ) -> str:
        """Build prompt for reflection.

        Args:
            actions: Recent actions to reflect on
            context: Full execution context

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "You are reflecting on the progress of a task execution.",
            "",
            f"Overall Task: {context.get('task_description', 'Not specified')}",
            f"Current Todo: {context.get('current_todo', 'Not specified')}",
            "",
            f"Recent {len(actions)} actions:",
        ]

        # Add recent actions
        for action in actions[-10:]:  # Show last 10 actions
            prompt_parts.append(f"- {action.action_type}: {action.target or 'N/A'}")
            if action.reasoning:
                prompt_parts.append(f"  Reasoning: {action.reasoning}")

        prompt_parts.extend(
            [
                "",
                "Please assess:",
                "1. Is the current approach working?",
                "2. Should we continue with the current instruction or pivot?",
                "3. If pivoting, what should the new instruction be?",
                "4. Overall assessment of progress",
                "",
                "Respond in JSON format:",
                '{"continue_current": true/false, "new_instruction": "..." or null, '
                '"reasoning": "...", "success_assessment": true/false}',
            ]
        )

        return "\n".join(prompt_parts)

    def _build_summary_prompt(
        self,
        execution_history: list[Action],
        context: dict[str, Any],
    ) -> str:
        """Build prompt for execution summary.

        Args:
            execution_history: Complete execution history
            context: Full execution context

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "Please provide a concise summary of the task execution.",
            "",
            f"Task: {context.get('task_description', 'Not specified')}",
            f"Todo: {context.get('current_todo', 'Not specified')}",
            f"Total Actions: {len(execution_history)}",
            "",
            "Action Types Summary:",
        ]

        # Count action types
        action_counts: dict[str, int] = {}
        for action in execution_history:
            action_counts[action.action_type] = (
                action_counts.get(action.action_type, 0) + 1
            )

        for action_type, count in action_counts.items():
            prompt_parts.append(f"- {action_type}: {count}")

        prompt_parts.extend(
            [
                "",
                "Please provide a 2-3 sentence summary describing:",
                "1. What was accomplished",
                "2. Key actions taken",
                "3. Overall outcome",
            ]
        )

        return "\n".join(prompt_parts)

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
