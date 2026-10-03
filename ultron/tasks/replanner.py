"""
ULTRON V3 — Dynamic Replanner
─────────────────────────────────────────────────────────────────────────────
Generates alternative execution plans when runtime reality differs from
expectations. Preserves completed idempotent work and enforces maximum replan limits.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import copy
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

from ultron.tasks.goal import Goal, GoalState
from ultron.tasks.plan import Plan, PlanStep, PlanStatus, validate_dependency_graph, SideEffectType
from ultron.tasks.state import StepStatus
from ultron.tasks.context import TaskContext
from ultron.tasks.recovery import FailureClassification
from ultron.tasks.errors import TaskPlanningError, TaskSecurityViolationError
from ultron.tools.registry import get_tool_capability

logger = logging.getLogger("ultron.tasks.replanner")


class DynamicReplanner:
    """Constructs alternative execution plans from runtime failure observations."""

    def __init__(self, workspace_root: Path | str):
        self.workspace_root = Path(workspace_root).resolve()

    def can_replan(self, goal: Goal) -> bool:
        """Determines if the goal has remaining replanning attempts."""
        return goal.replan_count < goal.constraints.max_replans

    def replan_after_failure(
        self,
        goal: Goal,
        current_plan: Plan,
        failed_step: PlanStep,
        failure_class: FailureClassification,
        context: TaskContext,
    ) -> Plan:
        """
        Synthesizes a new Plan version that adapts to the failure.
        Preserves previously completed steps (idempotent recovery).
        """
        if not self.can_replan(goal):
            raise TaskPlanningError(
                f"Goal '{goal.goal_id}' reached maximum replan limit ({goal.constraints.max_replans})."
            )

        goal.replan_count += 1
        new_version = current_plan.version + 1
        replan_reason = f"Replan v{new_version}: Recovering from '{failed_step.error or failed_step.capability}' on {failed_step.step_id}"

        # 1. Identify completed steps from latest checkpoint
        completed_step_ids = current_plan.get_completed_step_ids()
        new_steps: List[PlanStep] = []

        # Retain completed steps in new plan marked COMPLETED
        for s in current_plan.steps:
            if s.step_id in completed_step_ids:
                retained_step = copy.deepcopy(s)
                retained_step.status = StepStatus.COMPLETED
                new_steps.append(retained_step)

        # 2. Synthesize alternative steps for remaining work
        remaining_uncompleted = [s for s in current_plan.steps if s.step_id not in completed_step_ids]

        # Alternative route strategy depending on failed tool
        if failed_step.capability == "chrome_click_link":
            # Link click failed; try finding alternative link or search again
            alt_query = context.get_variable("alt_query") or "admissions overview"
            step_find_alt = PlanStep(
                step_id=f"step-{len(new_steps) + 1}",
                capability="chrome_find_link",
                arguments={"query": alt_query},
                purpose=f"Search for alternative link matching '{alt_query}'",
                prerequisites=[new_steps[-1].step_id] if new_steps else [],
                produces_intermediate_key="alt_link",
                side_effect=SideEffectType.READ,
            )
            step_click_alt = PlanStep(
                step_id=f"step-{len(new_steps) + 2}",
                capability="chrome_click_link",
                arguments={"target": "$alt_link"},
                purpose="Follow alternative link target",
                prerequisites=[step_find_alt.step_id],
                side_effect=SideEffectType.READ,
            )
            new_steps.extend([step_find_alt, step_click_alt])

            # Append any subsequent steps after the clicked link
            for s in remaining_uncompleted:
                if s.step_id != failed_step.step_id:
                    nxt = copy.deepcopy(s)
                    nxt.step_id = f"step-{len(new_steps) + 1}"
                    nxt.prerequisites = [new_steps[-1].step_id]
                    nxt.status = StepStatus.PENDING
                    new_steps.append(nxt)

        elif failed_step.capability == "chrome_search":
            # Search was too specific or empty -> generalize query
            orig_query = str(failed_step.arguments.get("query", ""))
            simplified_query = orig_query.replace("2026", "").replace("notification", "").strip() or "HBTU Kanpur"
            step_search_retry = PlanStep(
                step_id=f"step-{len(new_steps) + 1}",
                capability="chrome_search",
                arguments={"query": simplified_query},
                purpose=f"Broaden search query to '{simplified_query}'",
                prerequisites=[new_steps[-1].step_id] if new_steps else [],
                side_effect=SideEffectType.READ,
            )
            new_steps.append(step_search_retry)

            for s in remaining_uncompleted:
                if s.step_id != failed_step.step_id:
                    nxt = copy.deepcopy(s)
                    nxt.step_id = f"step-{len(new_steps) + 1}"
                    nxt.prerequisites = [new_steps[-1].step_id]
                    nxt.status = StepStatus.PENDING
                    new_steps.append(nxt)

        elif failed_step.capability == "write_file":
            # File write failed (e.g. content formatting mismatch); re-attempt write with sanitized content
            dest = failed_step.arguments.get("destination") or failed_step.arguments.get("path")
            content = failed_step.arguments.get("content", "")
            step_write = PlanStep(
                step_id=f"step-{len(new_steps) + 1}",
                capability="write_file",
                arguments={"path": dest, "content": str(content)},
                purpose=f"Write content to '{dest}'",
                prerequisites=[new_steps[-1].step_id] if new_steps else [],
                safety_class="CONFIRM_REQUIRED",
                requires_confirmation=True,
                side_effect=SideEffectType.WRITE,
            )
            new_steps.append(step_write)

        else:
            # General fallback: re-include remaining steps with reset pending status
            for s in remaining_uncompleted:
                nxt = copy.deepcopy(s)
                nxt.status = StepStatus.PENDING
                nxt.retries_attempted = 0
                nxt.error = None
                new_steps.append(nxt)

        # 3. Construct and validate new plan
        new_plan = Plan.create(
            goal_id=goal.goal_id,
            steps=new_steps,
            version=new_version,
            reason=replan_reason,
            expected_outcomes=current_plan.expected_outcomes,
            fallback_options=current_plan.fallback_options,
        )

        current_plan.status = PlanStatus.SUPERSEDED
        context.record_replan(current_plan.version, new_version, replan_reason)
        logger.info(f"[Dynamic Replanner] Generated {replan_reason} with {len(new_steps)} steps.")
        return new_plan
