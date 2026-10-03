"""
ULTRON V3 — Goal Planner
─────────────────────────────────────────────────────────────────────────────
Transforms high-level user requests and natural language goals into validated,
dependency-ordered execution plans. Strictly isolates prompt injection and
enforces authoritative local safety boundaries.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from ultron.tasks.goal import Goal, GoalState, GoalOutcome, GoalConstraint
from ultron.tasks.plan import (
    Plan,
    PlanStep,
    PlanStatus,
    SideEffectType,
    RetrySafety,
    get_capability_retry_safety,
    validate_dependency_graph,
)
from ultron.tasks.errors import TaskPlanningError, TaskSecurityViolationError
from ultron.tools.registry import get_tool_capability, TOOL_CAPABILITIES
from ultron.tools.safety import classify_file_operation, classify_app_operation, PolicyVerdict
from ultron.apps.chrome import validate_url
from ultron.apps.errors import URLSecurityError, DownloadSecurityError

logger = logging.getLogger("ultron.tasks.goal_planner")


class GoalPlanner:
    """Decomposes goals and builds validated dependency-ordered execution plans."""

    def __init__(self, workspace_root: Path | str):
        self.workspace_root = Path(workspace_root).resolve()

    def build_plan_step(
        self,
        capability: str,
        arguments: Dict[str, Any],
        purpose: str = "",
        step_id: Optional[str] = None,
        prerequisites: Optional[List[str]] = None,
        produces_key: Optional[str] = None,
        consumes_keys: Optional[List[str]] = None,
    ) -> PlanStep:
        """Constructs and validates an individual plan step."""
        clean_cap = str(capability).strip()
        cap_info = get_tool_capability(clean_cap)
        if not cap_info:
            raise TaskPlanningError(f"Capability '{clean_cap}' is not registered in ULTRON tool catalog.")

        safety_class = cap_info.safety_class
        requires_confirmation = cap_info.requires_confirmation
        side_effect = SideEffectType.READ

        # Side-effect assignment & safety policy enforcement
        if clean_cap in ("write_file", "create_directory", "copy_file", "move_file"):
            side_effect = SideEffectType.WRITE
            target_path = str(arguments.get("path") or arguments.get("destination") or arguments.get("source") or "")
            op_name = clean_cap.replace("_file", "")
            verdict, reason = classify_file_operation(op_name, target_path, self.workspace_root)
            if verdict == PolicyVerdict.BLOCKED:
                raise TaskSecurityViolationError(f"Step '{clean_cap}' blocked by security policy: {reason}")
            elif verdict == PolicyVerdict.CONFIRM_REQUIRED:
                safety_class = "CONFIRM_REQUIRED"
                requires_confirmation = True

        elif clean_cap == "delete_file":
            side_effect = SideEffectType.DELETE
            target_path = str(arguments.get("path", ""))
            verdict, reason = classify_file_operation("delete", target_path, self.workspace_root)
            if verdict == PolicyVerdict.BLOCKED:
                raise TaskSecurityViolationError(f"Step '{clean_cap}' blocked by security policy: {reason}")
            safety_class = "CONFIRM_REQUIRED"
            requires_confirmation = True

        elif clean_cap in ("open_app", "close_app", "windows_open_app", "windows_close_app"):
            app_name = str(arguments.get("app_name", ""))
            is_open = "open" in clean_cap
            verdict, reason = classify_app_operation(app_name, action="open" if is_open else "close")
            if verdict == PolicyVerdict.BLOCKED:
                raise TaskSecurityViolationError(f"Step '{clean_cap}' blocked by security policy: {reason}")
            elif verdict == PolicyVerdict.CONFIRM_REQUIRED or not is_open:
                safety_class = "CONFIRM_REQUIRED"
                requires_confirmation = True

        elif clean_cap in ("chrome_navigate", "chrome_download_file"):
            raw_url = str(arguments.get("url", "")).strip()
            # If URL is a dynamic variable ($selected_url), skip static syntax check
            if raw_url and not raw_url.startswith("$") and raw_url.lower() not in (
                "it", "that link", "that url", "that page", "the website", "the link", "this page"
            ):
                try:
                    validate_url(raw_url)
                except URLSecurityError as e:
                    raise TaskSecurityViolationError(f"Step '{clean_cap}' blocked: {e.reason}")

            if clean_cap == "chrome_download_file":
                side_effect = SideEffectType.EXTERNAL
                safety_class = "CONFIRM_REQUIRED"
                requires_confirmation = True
                dest = str(arguments.get("destination", "")).strip()
                if dest and not dest.startswith("$"):
                    dest_p = Path(dest)
                    if not dest_p.is_absolute():
                        dest_p = (self.workspace_root / dest_p).resolve()
                    else:
                        dest_p = dest_p.resolve()
                    try:
                        dest_p.relative_to(self.workspace_root)
                    except ValueError:
                        raise TaskSecurityViolationError("Download destination escapes workspace sandbox.")
                    if dest_p.suffix.lower() in {".exe", ".bat", ".cmd", ".ps1", ".vbs", ".msi", ".dll", ".scr"}:
                        raise TaskSecurityViolationError(f"Direct download of executable extension '{dest_p.suffix}' is blocked.")

        elif clean_cap in ("chrome_close", "windows_close_app"):
            safety_class = "CONFIRM_REQUIRED"
            requires_confirmation = True

        retry_safety = get_capability_retry_safety(clean_cap)

        return PlanStep(
            step_id=step_id or "step-1",
            capability=clean_cap,
            arguments=arguments,
            purpose=purpose or cap_info.description,
            prerequisites=list(prerequisites or []),
            produces_intermediate_key=produces_key,
            consumes_intermediate_keys=list(consumes_keys or []),
            safety_class=safety_class,
            requires_confirmation=requires_confirmation,
            side_effect=side_effect,
            retry_safety=retry_safety,
            timeout_sec=cap_info.timeout_sec,
        )


    def plan_from_goal_spec(
        self,
        goal: Goal,
        steps_spec: List[Dict[str, Any]],
    ) -> Plan:
        """Constructs and validates a Plan for a given Goal."""
        if not steps_spec:
            raise TaskPlanningError("Goal plan specification must contain at least one step.")

        plan_steps: List[PlanStep] = []
        for i, s in enumerate(steps_spec):
            cap = s.get("capability") or s.get("tool_name") or s.get("tool")
            args = s.get("arguments") or s.get("args") or {}
            purpose = s.get("purpose") or s.get("reason") or f"Step {i+1}"
            prereqs = s.get("prerequisites") or s.get("depends_on") or ([] if i == 0 else [plan_steps[-1].step_id])
            produces = s.get("produces_key") or s.get("produces_intermediate_key")
            consumes = s.get("consumes_keys") or s.get("consumes_intermediate_keys") or []

            step = self.build_plan_step(
                capability=cap,
                arguments=args,
                purpose=purpose,
                step_id=f"step-{i+1}",
                prerequisites=prereqs,
                produces_key=produces,
                consumes_keys=consumes,
            )
            plan_steps.append(step)

        # Enforce dependency validation
        validate_dependency_graph(
            plan_steps,
            max_steps=goal.constraints.max_steps_per_plan,
            max_depth=goal.constraints.max_dependency_depth,
        )

        plan = Plan.create(
            goal_id=goal.goal_id,
            steps=plan_steps,
            version=1,
            reason=f"Initial plan for goal: {goal.normalized_objective}",
            expected_outcomes=goal.desired_outcome.__dict__ if goal.desired_outcome else {},
        )
        goal.active_plan_id = plan.plan_id
        goal.current_status = GoalState.GOAL_PLANNING
        logger.info(f"[Goal Planner] Generated Plan '{plan.plan_id}' with {len(plan_steps)} steps for Goal '{goal.goal_id}'.")
        return plan
