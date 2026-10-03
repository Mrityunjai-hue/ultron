"""
ULTRON V3 — Task Planner & Validation Engine
─────────────────────────────────────────────────────────────────────────────
Translates proposed tool actions and multi-step agent plans into validated
atomic task models with strict safety classification and capability verification.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import logging
import uuid
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from ultron.tasks.models import Task, TaskStep
from ultron.tasks.state import TaskState, StepStatus
from ultron.tasks.errors import TaskPlanningError, TaskSecurityViolationError
from ultron.tools.registry import get_tool_capability, TOOL_CAPABILITIES
from ultron.tools.safety import classify_file_operation, classify_app_operation, PolicyVerdict

logger = logging.getLogger("ultron.tasks.planner")

class TaskPlanner:
    """Constructs and validates structured task plans."""

    def __init__(self, workspace_root: Path | str):
        self.workspace_root = Path(workspace_root).resolve()

    def build_step(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        purpose: str = "",
        step_id: Optional[str] = None,
    ) -> TaskStep:
        """Constructs and safety-classifies a single task step."""
        clean_name = str(tool_name).strip()
        cap = get_tool_capability(clean_name)
        if not cap:
            raise TaskPlanningError(f"Tool '{clean_name}' is not a registered capability.")

        sid = step_id or f"step-{uuid.uuid4().hex[:6]}"
        safety_class = cap.safety_class
        requires_confirmation = cap.requires_confirmation

        # Check local safety policies
        if clean_name in ("open_app", "close_app"):
            app = str(arguments.get("app_name", "")).strip()
            verdict, reason = classify_app_operation(app, action="open" if clean_name == "open_app" else "close")
            if verdict == PolicyVerdict.BLOCKED:
                raise TaskSecurityViolationError(f"Step '{clean_name}' blocked by security policy: {reason}")
            elif verdict == PolicyVerdict.CONFIRM_REQUIRED:
                safety_class = "CONFIRM_REQUIRED"
                requires_confirmation = True

        elif clean_name in ("write_file", "delete_file", "copy_file", "move_file"):
            target_path = str(arguments.get("path") or arguments.get("destination") or arguments.get("source") or "")
            op_name = clean_name.replace("_file", "")
            verdict, reason = classify_file_operation(op_name, target_path, self.workspace_root)
            if verdict == PolicyVerdict.BLOCKED:
                raise TaskSecurityViolationError(f"Step '{clean_name}' blocked by security policy: {reason}")
            elif verdict == PolicyVerdict.CONFIRM_REQUIRED:
                safety_class = "CONFIRM_REQUIRED"
                requires_confirmation = True

        elif clean_name in ("chrome_navigate", "chrome_download_file"):
            raw_url = str(arguments.get("url", "")).strip()
            if raw_url and raw_url.lower() not in ("it", "that link", "that url", "that page", "the website", "the link", "this page"):
                from ultron.apps.chrome import validate_url
                from ultron.apps.errors import URLSecurityError, DownloadSecurityError
                try:
                    validate_url(raw_url)
                except URLSecurityError as url_err:
                    raise TaskSecurityViolationError(f"Step '{clean_name}' blocked: {url_err.reason}")

            if clean_name == "chrome_download_file":
                safety_class = "CONFIRM_REQUIRED"
                requires_confirmation = True
                dest = str(arguments.get("destination", "")).strip()
                if dest:
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

        elif clean_name in ("chrome_close", "windows_close_app"):
            safety_class = "CONFIRM_REQUIRED"
            requires_confirmation = True

        return TaskStep(
            step_id=sid,
            tool_name=clean_name,
            arguments=arguments,
            purpose=purpose or cap.description,
            safety_class=safety_class,
            requires_confirmation=requires_confirmation,
            status=StepStatus.PENDING,
            timeout_sec=cap.timeout_sec,
        )

    def plan_single_action(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_intent: str = "",
        session_id: str = "default",
    ) -> Task:
        """Constructs a 1-step task for immediate atomic tool execution."""
        step = self.build_step(tool_name, arguments, purpose=user_intent)
        task = Task.create(
            user_intent=user_intent or f"Execute {tool_name}",
            steps=[step],
            session_id=session_id,
        )
        task.state = TaskState.TASK_READY
        return task

    def plan_multi_step_task(
        self,
        user_intent: str,
        steps_spec: List[Dict[str, Any]],
        session_id: str = "default",
    ) -> Task:
        """Constructs and validates a multi-step task plan."""
        if not steps_spec:
            raise TaskPlanningError("Task must contain at least one step.")

        task_steps: List[TaskStep] = []
        for i, s in enumerate(steps_spec):
            tool = s.get("tool_name") or s.get("tool")
            args = s.get("arguments") or s.get("args") or {}
            purpose = s.get("purpose") or s.get("reason") or f"Step {i+1}"
            step = self.build_step(tool, args, purpose=purpose, step_id=f"step-{i+1}")
            task_steps.append(step)

        task = Task.create(
            user_intent=user_intent,
            steps=task_steps,
            session_id=session_id,
        )
        task.state = TaskState.TASK_READY
        logger.info(f"[Task Planner] Created plan '{task.task_id}' with {len(task_steps)} steps for intent: '{user_intent}'")
        return task
