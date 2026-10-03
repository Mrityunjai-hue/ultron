"""
ULTRON V3 — Task Execution Engine & Lifecycle Coordinator
─────────────────────────────────────────────────────────────────────────────
Orchestrates authoritative multi-step agent execution with:
- Strict singleton active task concurrency control
- Pre-execution safety validation
- Confirmation pausing and resumption via ConfirmationManager
- Mandatory post-execution empirical verification
- Bounded retries (max 2 per recoverable step)
- Instant global task cancellation
- SessionMemory context tracking
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import asyncio
import logging
import time
from pathlib import Path
from ultron.tasks.models import Task, TaskStep, VerificationResult
from ultron.tasks.state import TaskState, StepStatus
from ultron.tasks.goal import Goal, GoalState, GoalOutcome, GoalConstraint
from ultron.tasks.plan import Plan, PlanStep, PlanStatus, validate_dependency_graph, SideEffectType, RetrySafety
from ultron.tasks.context import TaskContext, Checkpoint
from ultron.tasks.recovery import FailureClassification, RecoveryStrategy, FailureClassifier
from ultron.tasks.replanner import DynamicReplanner
from ultron.tasks.goal_planner import GoalPlanner
from ultron.tasks.persistence import TaskPersistenceManager, CorruptedStateError, scrub_secrets
from ultron.tasks.journal import TaskJournal, JournalEventType
from ultron.tasks.evidence import EvidenceChain
from ultron.tasks.errors import (
    TaskError,
    TaskCancelledError,
    TaskTimeoutError,
    TaskVerificationError,
    TaskConcurrencyError,
    TaskSecurityViolationError,
    TaskPlanningError,
)
from ultron.tasks.verifier import ActionVerifier
from ultron.tasks.cancellation import TaskCancellationManager
from ultron.tools.executor import ToolExecutor
from ultron.tools.confirmation import ConfirmationManager
from ultron.memory.manager import MemoryManager
from ultron.core.events import EventBus, EngineEvent, ActivityState

logger = logging.getLogger("ultron.tasks.executor")

class TaskExecutionEngine:
    """Authoritative coordinator for executing multi-step desktop tasks and intelligent goals."""

    def __init__(
        self,
        tool_executor: ToolExecutor,
        confirmation_manager: ConfirmationManager,
        memory_manager: MemoryManager,
        event_bus: Optional[EventBus] = None,
        workspace_root: Optional[Path | str] = None,
    ):
        self.tools = tool_executor
        self.confirmation = confirmation_manager
        self.memory = memory_manager
        self.event_bus = event_bus or EventBus()
        self.workspace_root = Path(workspace_root or tool_executor.workspace_root).resolve()

        self.verifier = ActionVerifier(self.workspace_root, memory_manager=self.memory)
        self.cancellation = TaskCancellationManager()
        self.goal_planner = GoalPlanner(self.workspace_root)
        self.replanner = DynamicReplanner(self.workspace_root)
        self.persistence = TaskPersistenceManager(self.workspace_root)
        self.journal = TaskJournal(workspace_root=self.workspace_root)
        self.evidence = EvidenceChain(self.workspace_root)

        self.active_task: Optional[Task] = None
        self.active_goal: Optional[Goal] = None
        self.active_plan: Optional[Plan] = None
        self._contexts: Dict[str, TaskContext] = {}
        self._lock = asyncio.Lock()


    def get_or_create_context(self, goal_id: str) -> TaskContext:
        """Retrieves or creates a bounded runtime context for a goal."""
        if goal_id not in self._contexts:
            self._contexts[goal_id] = TaskContext(goal_id)
        return self._contexts[goal_id]


    def _publish_event(self, state: ActivityState, operation: str = "task", message: str = "", data: Optional[dict] = None):
        """Dispatches telemetry event to bus for UI and runtime observers."""
        self.event_bus.publish(EngineEvent(
            state=state,
            operation=operation,
            message=message,
            data=data or {},
        ))

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """Executes a validated task through the full verification lifecycle."""
        async with self._lock:
            if self.active_task and not self.active_task.is_finished:
                if self.active_task.task_id != task.task_id:
                    raise TaskConcurrencyError(
                        f"Task '{self.active_task.task_id}' is currently running. Cancel it first to execute new task.",
                        task_id=task.task_id,
                    )

            self.active_task = task
            self.cancellation.register_active_task(task.task_id)

            if self.cancellation.is_task_cancelled(task.task_id):
                task.transition_to(TaskState.TASK_CANCELLED, reason="Task cancelled prior to execution")
                self._publish_event(ActivityState.IDLE, operation="task_cancelled", message=f"Task {task.task_id} cancelled")
                return {
                    "success": False,
                    "status": "TASK_CANCELLED",
                    "task_id": task.task_id,
                    "message": "Task was cancelled prior to execution.",
                    "completed_steps": [],
                }

            task.transition_to(TaskState.TASK_EXECUTING)
            self._publish_event(ActivityState.THINKING, operation="task_start", message=task.user_intent)

            logger.info(f"[Task Engine] Starting task '{task.task_id}' with {len(task.steps)} steps (Intent: {task.user_intent})")

            results_summary: List[Dict[str, Any]] = []

            while task.current_step_index < len(task.steps):
                # 1. Check for global cancellation
                if self.cancellation.is_task_cancelled(task.task_id):
                    task.transition_to(TaskState.TASK_CANCELLED, reason="User cancelled task")
                    self._publish_event(ActivityState.IDLE, operation="task_cancelled", message=f"Task {task.task_id} cancelled")
                    return {
                        "success": False,
                        "status": "TASK_CANCELLED",
                        "task_id": task.task_id,
                        "message": "Task was cancelled by user.",
                        "completed_steps": results_summary,
                    }

                step = task.steps[task.current_step_index]
                self._resolve_step_pronouns(step)
                logger.info(f"[Task Engine] Step {task.current_step_index + 1}/{len(task.steps)}: {step.tool_name} (Purpose: {step.purpose})")

                # 2. Safety & Confirmation Gateway Check
                if step.requires_confirmation and not step.arguments.get("confirmation_token"):
                    # Check if token exists in pending confirmations
                    task.transition_to(TaskState.TASK_WAITING_CONFIRMATION)
                    step.status = StepStatus.WAITING_CONFIRMATION

                    pending = self.confirmation.create_pending_confirmation(
                        tool_name=step.tool_name,
                        arguments=step.arguments,
                        session_id=task.session_id,
                    )
                    step.arguments["confirmation_token"] = pending.token

                    target_name = str(step.arguments.get("path") or step.arguments.get("app_name") or step.arguments.get("destination") or "")
                    self._publish_event(
                        ActivityState.THINKING,
                        operation="confirmation_required",
                        message=f"Confirmation required for {step.tool_name} on {target_name}",
                        data={"token": pending.token, "task_id": task.task_id, "step_id": step.step_id},
                    )

                    return {
                        "success": False,
                        "status": "CONFIRM_REQUIRED",
                        "task_id": task.task_id,
                        "step_id": step.step_id,
                        "action": step.tool_name,
                        "target": target_name,
                        "confirmation_token": pending.token,
                        "message": f"Action '{step.tool_name}' on '{target_name}' requires explicit user confirmation.",
                        "prompt_user": f"Confirm {step.tool_name} on {target_name}?",
                    }

                # 3. Step Execution with Bounded Retries & Timeout
                step_success = False
                exec_res = {}
                verification: Optional[VerificationResult] = None

                while step.retries_attempted <= step.max_retries:
                    self.cancellation.assert_not_cancelled(task.task_id)
                    step.mark_running()
                    self._publish_event(ActivityState.THINKING, operation=step.tool_name, message=step.purpose)

                    try:
                        # Execute tool with bounded timeout
                        exec_res = await asyncio.wait_for(
                            self.tools.execute(
                                tool_name=step.tool_name,
                                arguments=step.arguments,
                                session_id=task.session_id,
                            ),
                            timeout=step.timeout_sec,
                        )

                        # Handle CONFIRM_REQUIRED returned from executor
                        if isinstance(exec_res, dict) and exec_res.get("status") == "CONFIRM_REQUIRED":
                            task.transition_to(TaskState.TASK_WAITING_CONFIRMATION)
                            step.status = StepStatus.WAITING_CONFIRMATION
                            return {
                                "success": False,
                                "status": "CONFIRM_REQUIRED",
                                "task_id": task.task_id,
                                "step_id": step.step_id,
                                "action": exec_res.get("action", step.tool_name),
                                "target": exec_res.get("target", ""),
                                "confirmation_token": exec_res.get("confirmation_token", ""),
                                "message": exec_res.get("message", ""),
                                "prompt_user": exec_res.get("prompt_user", "Please confirm action."),
                            }

                        # 4. Mandatory Post-Action Verification
                        task.transition_to(TaskState.TASK_VERIFYING)
                        step.status = StepStatus.VERIFYING
                        verification = self.verifier.verify_step(step, exec_res)

                        if verification.verified:
                            step_success = True
                            step.mark_completed(exec_res, verification)
                            logger.info(f"[Task Engine] Step '{step.step_id}' ({step.tool_name}) verified via {verification.method}")
                            break
                        else:
                            step.retries_attempted += 1
                            logger.warning(f"[Task Engine] Step '{step.step_id}' verification failed: {verification.error_message}. Retry {step.retries_attempted}/{step.max_retries}")
                            if step.retries_attempted <= step.max_retries:
                                await asyncio.sleep(0.1)

                    except asyncio.TimeoutError:
                        step.retries_attempted += 1
                        logger.error(f"[Task Engine] Step '{step.step_id}' timed out after {step.timeout_sec}s.")
                        if step.retries_attempted > step.max_retries:
                            exec_res = {"success": False, "error": f"Step timed out after {step.timeout_sec}s"}
                            break
                    except TaskCancelledError:
                        task.transition_to(TaskState.TASK_CANCELLED, reason="Cancelled during step execution")
                        step.mark_cancelled()
                        return {
                            "success": False,
                            "status": "TASK_CANCELLED",
                            "task_id": task.task_id,
                            "message": "Task was cancelled by user.",
                        }
                    except Exception as err:
                        step.retries_attempted += 1
                        logger.error(f"[Task Engine] Execution fault on step '{step.step_id}': {err}", exc_info=True)
                        exec_res = {"success": False, "error": str(err)}
                        if step.retries_attempted > step.max_retries:
                            break

                # 5. Evaluate Step Outcome
                if not step_success:
                    err_reason = (verification.error_message if verification else None) or exec_res.get("error") or "Step execution and verification failed"
                    step.mark_failed(err_reason, exec_res, verification)
                    task.transition_to(TaskState.TASK_FAILED, reason=err_reason)
                    self._publish_event(ActivityState.IDLE, operation="task_failed", message=err_reason)

                    return {
                        "success": False,
                        "status": "TASK_FAILED",
                        "task_id": task.task_id,
                        "failed_step_id": step.step_id,
                        "failed_tool": step.tool_name,
                        "error": err_reason,
                        "completed_steps": results_summary,
                    }

                # Record step result to context and session memory
                results_summary.append({
                    "step_id": step.step_id,
                    "tool": step.tool_name,
                    "result": exec_res,
                    "verified": True,
                })
                self.memory.record_turn(
                    role="tool",
                    content=str(exec_res),
                    tool_name=step.tool_name,
                    tool_args=step.arguments,
                    tool_result=exec_res,
                )

                task.current_step_index += 1

            # 6. Task Successfully Completed
            task.transition_to(TaskState.TASK_COMPLETED)
            self._publish_event(ActivityState.IDLE, operation="task_completed", message=f"Task {task.task_id} completed successfully")
            logger.info(f"[Task Engine] Task '{task.task_id}' successfully executed and verified {len(task.steps)} steps.")

            return {
                "success": True,
                "status": "COMPLETED",
                "task_id": task.task_id,
                "user_intent": task.user_intent,
                "steps_count": len(task.steps),
                "results": results_summary,
            }

    async def resume_task_with_confirmation(self, task_id: str, confirmation_token: str) -> Dict[str, Any]:
        """Resumes a task paused in TASK_WAITING_CONFIRMATION."""
        if not self.active_task or self.active_task.task_id != task_id:
            return {"success": False, "error": f"No active task with ID '{task_id}' found."}

        task = self.active_task
        if task.state != TaskState.TASK_WAITING_CONFIRMATION:
            return {"success": False, "error": f"Task '{task_id}' is in state {task.state}, not awaiting confirmation."}

        curr_step = task.current_step
        if curr_step:
            curr_step.arguments["confirmation_token"] = confirmation_token

        task.transition_to(TaskState.TASK_EXECUTING)
        return await self.execute_task(task)

    def cancel_active_task(self, reason: str = "User voice cancellation") -> bool:
        """Immediately signals cancellation for the active task."""
        if self.active_task and not self.active_task.is_finished:
            logger.info(f"[Task Engine] Cancelling active task '{self.active_task.task_id}': {reason}")
            self.cancellation.cancel_task(self.active_task.task_id, reason=reason)
            self.active_task.transition_to(TaskState.TASK_CANCELLED, reason=reason)
            self._publish_event(ActivityState.IDLE, operation="task_cancelled", message=reason)
            return True
        return False

    def _resolve_step_pronouns(self, step: TaskStep) -> None:
        """Resolves pronoun references in step arguments using SessionMemory."""
        if not self.memory or not hasattr(self.memory, "session") or not self.memory.session:
            return

        tool_name = step.tool_name
        args = step.arguments

        if tool_name in ("open_app", "close_app", "windows_open_app", "windows_close_app"):
            raw_app = str(args.get("app_name", "")).strip()
            if raw_app.lower() in ("it", "the app", "that app", "this app", "the application"):
                resolved = self.memory.session.resolve_target("app")
                if resolved:
                    args["app_name"] = resolved

        elif tool_name in (
            "read_file",
            "write_file",
            "delete_file",
            "get_file_info",
            "list_directory",
            "create_directory",
            "chrome_download_file",
        ):
            raw_path = str(args.get("path") or args.get("destination") or "").strip()
            if raw_path.lower() in (
                "it",
                "the file",
                "that file",
                "this file",
                "the document",
                "the folder",
                "the directory",
                "that download",
            ):
                resolved = self.memory.session.resolve_target("file")
                if resolved:
                    if "path" in args:
                        args["path"] = resolved
                    elif "destination" in args:
                        args["destination"] = resolved

        if tool_name in ("chrome_navigate", "chrome_download_file"):
            raw_url = str(args.get("url", "")).strip()
            if raw_url.lower() in (
                "it",
                "that link",
                "that url",
                "that page",
                "the website",
                "the link",
                "this page",
            ):
                resolved = self.memory.session.resolve_target("url")
                if resolved:
                    args["url"] = resolved

        if tool_name == "chrome_search":
            raw_query = str(args.get("query", "")).strip()
            if raw_query.lower() in ("it", "that", "the search", "the query"):
                resolved = self.memory.session.resolve_target("query")
                if resolved:
                    args["query"] = resolved

    def _persist_state(self, goal: Goal, plan: Optional[Plan] = None, context: Optional[TaskContext] = None):
        """Atomically saves goal execution state to disk."""
        try:
            goal_dict = {
                "goal_id": goal.goal_id,
                "original_user_request": goal.original_user_request,
                "normalized_objective": goal.normalized_objective,
                "current_status": goal.current_status.value if hasattr(goal.current_status, "value") else str(goal.current_status),
                "replan_count": goal.replan_count,
                "created_at": goal.created_at,
                "updated_at": goal.updated_at,
                "completed_at": goal.completed_at,
                "deadline": goal.deadline,
                "session_id": goal.session_id,
                "active_plan_id": plan.plan_id if plan else goal.active_plan_id,
                "completed_conditions": goal.completed_conditions,
                "failure_reason": goal.failure_reason,
                "cancellation_reason": goal.cancellation_reason,
                "metadata": goal.metadata,
            }
            plan_dict = None
            if plan:
                plan_dict = {
                    "plan_id": plan.plan_id,
                    "goal_id": plan.goal_id,
                    "version": plan.version,
                    "status": plan.status.value if hasattr(plan.status, "value") else str(plan.status),
                    "created_at": plan.created_at,
                    "steps": [
                        {
                            "step_id": s.step_id,
                            "capability": s.capability,
                            "arguments": s.arguments,
                            "purpose": s.purpose,
                            "prerequisites": s.prerequisites,
                            "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                            "safety_class": s.safety_class,
                            "requires_confirmation": s.requires_confirmation,
                            "side_effect": s.side_effect.value if hasattr(s.side_effect, "value") else str(s.side_effect),
                            "retry_safety": s.retry_safety.value if hasattr(s.retry_safety, "value") else str(s.retry_safety),
                            "retries_attempted": s.retries_attempted,
                            "max_retries": s.max_retries,
                            "produces_intermediate_key": s.produces_intermediate_key,
                            "consumes_intermediate_keys": s.consumes_intermediate_keys,
                            "execution_result": s.execution_result,
                            "error": s.error,
                        }
                        for s in plan.steps
                    ],
                }
            ctx_dict = None
            if context:
                ctx_dict = {
                    "goal_id": context.goal_id,
                    "variables": context.list_variables(),
                    "observations": context.list_observations(),
                    "checkpoints": [
                        {
                            "checkpoint_id": c.checkpoint_id,
                            "timestamp": c.timestamp,
                            "completed_step_ids": c.completed_step_ids,
                            "variables": c.variables,
                            "plan_version": c.plan_version,
                            "observed_state": c.observed_state,
                            "integrity_hash": c.integrity_hash,
                        }
                        for c in context._checkpoints
                    ],
                }
            evidence_list = self.evidence.get_goal_evidence(goal.goal_id)
            self.persistence.persist_goal_state(
                goal_id=goal.goal_id,
                goal_data=goal_dict,
                plan_data=plan_dict,
                context_data=ctx_dict,
                evidence_data=evidence_list,
            )
        except Exception as e:
            logger.warning(f"[Task Engine] Failed to persist state for goal {goal.goal_id}: {e}")

    def _probe_environment_for_step(self, step: PlanStep) -> Tuple[bool, Dict[str, Any]]:
        """
        Empirically inspects environment before retrying or resuming a side-effecting step.
        Returns (already_completed, result_details).
        """
        cap = step.capability.lower()
        args = step.arguments

        # 1. File write probe
        if cap == "write_file":
            raw_path = args.get("path") or args.get("destination")
            if raw_path:
                p = Path(raw_path)
                if not p.is_absolute():
                    p = (self.workspace_root / p).resolve()
                if p.exists() and p.is_file():
                    expected_content = args.get("content")
                    if expected_content is not None:
                        try:
                            actual_content = p.read_text(encoding="utf-8")
                            if actual_content == expected_content:
                                return True, {"path": str(p), "size_bytes": p.stat().st_size, "probed": True, "success": True}
                        except Exception:
                            pass
                    elif p.stat().st_size > 0:
                        return True, {"path": str(p), "size_bytes": p.stat().st_size, "probed": True, "success": True}

        # 2. Directory create probe
        elif cap == "create_directory":
            raw_path = args.get("path") or args.get("destination")
            if raw_path:
                p = Path(raw_path)
                if not p.is_absolute():
                    p = (self.workspace_root / p).resolve()
                if p.exists() and p.is_dir():
                    return True, {"path": str(p), "probed": True, "success": True}

        # 3. File delete probe
        elif cap == "delete_file":
            raw_path = args.get("path")
            if raw_path:
                p = Path(raw_path)
                if not p.is_absolute():
                    p = (self.workspace_root / p).resolve()
                if not p.exists():
                    return True, {"path": str(p), "deleted": True, "probed": True, "success": True}

        # 4. Chrome download file probe
        elif cap == "chrome_download_file":
            raw_dest = args.get("destination") or args.get("path")
            if raw_dest:
                p = Path(raw_dest)
                if not p.is_absolute():
                    p = (self.workspace_root / p).resolve()
                if p.exists() and p.is_file() and p.stat().st_size > 0:
                    return True, {"saved_to": str(p), "size_bytes": p.stat().st_size, "probed": True, "success": True}

        return False, {}

    async def execute_goal(
        self,
        goal: Goal,
        initial_plan: Optional[Plan] = None,
    ) -> Dict[str, Any]:
        """
        Executes a high-level goal through dependency-ordered plans, intermediate key
        resolution, automatic checkpointing, evidence tracking, atomic persistence,
        and dynamic replanning on recoverable failure.
        """
        async with self._lock:
            if self.active_goal and self.active_goal.is_active:
                if self.active_goal.goal_id != goal.goal_id:
                    raise TaskConcurrencyError(
                        f"Goal '{self.active_goal.goal_id}' is currently active. Cancel it before starting a new goal.",
                        task_id=goal.goal_id,
                    )

            self.active_goal = goal
            self.cancellation.register_active_task(goal.goal_id)

            if self.cancellation.is_task_cancelled(goal.goal_id):
                goal.transition_to(GoalState.GOAL_CANCELLED, reason="Goal cancelled prior to execution")
                self.journal.record(
                    JournalEventType.TASK_CANCELLED,
                    task_id=goal.goal_id,
                    goal_id=goal.goal_id,
                    metadata={"reason": "Goal cancelled prior to execution"},
                )
                self._persist_state(goal, initial_plan, self._contexts.get(goal.goal_id))
                self._publish_event(ActivityState.IDLE, operation="goal_cancelled", message=f"Goal {goal.goal_id} cancelled")
                return {
                    "success": False,
                    "status": "GOAL_CANCELLED",
                    "goal_id": goal.goal_id,
                    "message": "Goal was cancelled prior to execution.",
                    "completed_steps": [],
                }

            context = self.get_or_create_context(goal.goal_id)
            current_plan = initial_plan

            if not current_plan:
                # If no plan supplied, generate plan from goal's metadata spec if present
                steps_spec = goal.metadata.get("steps_spec", [])
                if steps_spec:
                    current_plan = self.goal_planner.plan_from_goal_spec(goal, steps_spec)
                else:
                    raise TaskPlanningError(f"No executable plan or steps_spec provided for goal '{goal.goal_id}'.")

            self.active_plan = current_plan
            goal.transition_to(GoalState.GOAL_EXECUTING)

            # Record Lifecycle Creation Events
            self.journal.record(
                JournalEventType.TASK_CREATED,
                task_id=goal.goal_id,
                goal_id=goal.goal_id,
                plan_version=current_plan.version,
                metadata={"objective": goal.normalized_objective},
            )
            self.journal.record(
                JournalEventType.PLAN_CREATED,
                task_id=goal.goal_id,
                goal_id=goal.goal_id,
                plan_version=current_plan.version,
                metadata={"steps_count": len(current_plan.steps), "plan_id": current_plan.plan_id},
            )
            self._persist_state(goal, current_plan, context)

            self._publish_event(ActivityState.THINKING, operation="goal_start", message=goal.normalized_objective)
            logger.info(f"[Goal Engine] Starting Goal '{goal.goal_id}' with Plan '{current_plan.plan_id}' (v{current_plan.version})")

            # Execution Budgets
            start_time = goal.created_at if (goal.created_at and goal.created_at > 0) else time.time()
            max_duration = goal.constraints.timeout_sec if goal.constraints and goal.constraints.timeout_sec else 300.0
            max_steps_allowed = (goal.constraints.max_steps_per_plan * 3) if goal.constraints else 60
            steps_executed_count = 0
            results_summary: List[Dict[str, Any]] = []

            while not current_plan.is_finished():
                # 0. Execution Budget Check
                if time.time() - start_time > max_duration:
                    timeout_msg = f"Goal execution exceeded duration budget of {max_duration}s."
                    logger.error(f"[Goal Engine] {timeout_msg}")
                    goal.transition_to(GoalState.GOAL_FAILED, reason=timeout_msg)
                    current_plan.status = PlanStatus.FAILED
                    self.journal.record(
                        JournalEventType.TASK_FAILED,
                        task_id=goal.goal_id,
                        goal_id=goal.goal_id,
                        plan_version=current_plan.version,
                        metadata={"error": timeout_msg, "duration": time.time() - start_time},
                    )
                    self._persist_state(goal, current_plan, context)
                    return {
                        "success": False,
                        "status": "GOAL_FAILED",
                        "goal_id": goal.goal_id,
                        "error": timeout_msg,
                        "completed_steps": results_summary,
                    }

                if steps_executed_count >= max_steps_allowed:
                    step_budget_msg = f"Goal execution exceeded maximum step budget of {max_steps_allowed} steps."
                    logger.error(f"[Goal Engine] {step_budget_msg}")
                    goal.transition_to(GoalState.GOAL_FAILED, reason=step_budget_msg)
                    current_plan.status = PlanStatus.FAILED
                    self.journal.record(
                        JournalEventType.TASK_FAILED,
                        task_id=goal.goal_id,
                        goal_id=goal.goal_id,
                        plan_version=current_plan.version,
                        metadata={"error": step_budget_msg},
                    )
                    self._persist_state(goal, current_plan, context)
                    return {
                        "success": False,
                        "status": "GOAL_FAILED",
                        "goal_id": goal.goal_id,
                        "error": step_budget_msg,
                        "completed_steps": results_summary,
                    }

                # 1. Global cancellation check
                if self.cancellation.is_task_cancelled(goal.goal_id):
                    goal.transition_to(GoalState.GOAL_CANCELLED, reason="User cancelled goal")
                    current_plan.status = PlanStatus.CANCELLED
                    self.journal.record(
                        JournalEventType.TASK_CANCELLED,
                        task_id=goal.goal_id,
                        goal_id=goal.goal_id,
                        plan_version=current_plan.version,
                        metadata={"reason": "User cancelled goal"},
                    )
                    self._persist_state(goal, current_plan, context)
                    self._publish_event(ActivityState.IDLE, operation="goal_cancelled", message=f"Goal {goal.goal_id} cancelled")
                    return {
                        "success": False,
                        "status": "GOAL_CANCELLED",
                        "goal_id": goal.goal_id,
                        "message": "Goal was cancelled by user.",
                        "completed_steps": results_summary,
                    }

                # 2. Check for paused goal
                if goal.current_status == GoalState.GOAL_PAUSED:
                    self._persist_state(goal, current_plan, context)
                    return {
                        "success": False,
                        "status": "GOAL_PAUSED",
                        "goal_id": goal.goal_id,
                        "message": "Goal is paused.",
                        "completed_steps": results_summary,
                    }

                # 3. Identify next executable step whose prerequisites are completed
                next_step: Optional[PlanStep] = None
                for s in current_plan.steps:
                    if s.status in (StepStatus.PENDING, StepStatus.UNKNOWN_OUTCOME) and current_plan.are_prerequisites_satisfied(s):
                        next_step = s
                        break

                if not next_step:
                    all_done = all(s.status == StepStatus.COMPLETED for s in current_plan.steps)
                    if all_done:
                        current_plan.status = PlanStatus.COMPLETED
                        break
                    else:
                        unresolved = [s.step_id for s in current_plan.steps if s.status in (StepStatus.PENDING, StepStatus.UNKNOWN_OUTCOME)]
                        err_text = f"Plan blocked on unresolved prerequisites for steps: {unresolved}"
                        goal.transition_to(GoalState.GOAL_FAILED, reason=err_text)
                        current_plan.status = PlanStatus.FAILED
                        self.journal.record(
                            JournalEventType.TASK_FAILED,
                            task_id=goal.goal_id,
                            goal_id=goal.goal_id,
                            plan_version=current_plan.version,
                            metadata={"error": err_text},
                        )
                        self._persist_state(goal, current_plan, context)
                        return {
                            "success": False,
                            "status": "GOAL_FAILED",
                            "goal_id": goal.goal_id,
                            "error": err_text,
                            "completed_steps": results_summary,
                        }

                step = next_step
                resolved_args = context.resolve_arguments(step.arguments)
                step.arguments = resolved_args
                self._resolve_plan_step_pronouns(step)

                # 4. Idempotent Environment Pre-Probe (Unknown outcome or non-idempotent safety guard)
                if step.retry_safety == RetrySafety.NOT_SAFE_TO_RETRY or step.status == StepStatus.UNKNOWN_OUTCOME:
                    probed, probe_res = self._probe_environment_for_step(step)
                    if probed:
                        logger.info(f"[Goal Engine] Step '{step.step_id}' ({step.capability}) verified via environment pre-probe.")
                        step_model = TaskStep(step_id=step.step_id, tool_name=step.capability, arguments=step.arguments)
                        v_res = self.verifier.verify_step(step_model, probe_res)
                        step.mark_completed(probe_res, v_res)

                        if step.produces_intermediate_key:
                            val = probe_res.get("saved_to") or probe_res.get("path") or probe_res
                            context.set_variable(step.produces_intermediate_key, val)

                        context.create_checkpoint(
                            completed_step_ids=list(current_plan.get_completed_step_ids()),
                            plan_version=current_plan.version,
                        )
                        self.evidence.record_step_evidence(
                            goal_id=goal.goal_id,
                            plan_version=current_plan.version,
                            step_id=step.step_id,
                            capability=step.capability,
                            arguments=step.arguments,
                            execution_result=probe_res,
                            verification=v_res,
                        )
                        self.journal.record(
                            JournalEventType.STEP_VERIFIED,
                            task_id=goal.goal_id,
                            goal_id=goal.goal_id,
                            plan_version=current_plan.version,
                            step_id=step.step_id,
                            metadata={"method": "environment_pre_probe"},
                        )
                        self._persist_state(goal, current_plan, context)
                        results_summary.append({
                            "step_id": step.step_id,
                            "capability": step.capability,
                            "result": probe_res,
                            "verified": True,
                            "probed": True,
                        })
                        continue

                # 5. Confirmation Gateway Check
                if step.requires_confirmation and not step.arguments.get("confirmation_token"):
                    goal.transition_to(GoalState.GOAL_WAITING_USER)
                    step.status = StepStatus.WAITING_CONFIRMATION

                    pending = self.confirmation.create_pending_confirmation(
                        tool_name=step.capability,
                        arguments=step.arguments,
                        session_id=goal.session_id,
                    )
                    step.arguments["confirmation_token"] = pending.token
                    target_name = str(step.arguments.get("path") or step.arguments.get("app_name") or step.arguments.get("destination") or step.arguments.get("url") or "")

                    self.journal.record(
                        JournalEventType.CONFIRMATION_REQUESTED,
                        task_id=goal.goal_id,
                        goal_id=goal.goal_id,
                        plan_version=current_plan.version,
                        step_id=step.step_id,
                        metadata={"action": step.capability, "target": target_name},
                    )
                    self._persist_state(goal, current_plan, context)

                    self._publish_event(
                        ActivityState.THINKING,
                        operation="confirmation_required",
                        message=f"Confirmation required for {step.capability} on {target_name}",
                        data={"token": pending.token, "goal_id": goal.goal_id, "step_id": step.step_id},
                    )

                    return {
                        "success": False,
                        "status": "CONFIRM_REQUIRED",
                        "goal_id": goal.goal_id,
                        "step_id": step.step_id,
                        "action": step.capability,
                        "target": target_name,
                        "confirmation_token": pending.token,
                        "message": f"Action '{step.capability}' on '{target_name}' requires explicit user confirmation.",
                        "prompt_user": f"Confirm {step.capability} on {target_name}?",
                    }

                # 6. Step Execution & Verification with Bounded Retries & Dynamic Replanning
                step_success = False
                exec_res: Dict[str, Any] = {}
                verif: Optional[VerificationResult] = None
                steps_executed_count += 1

                while step.retries_attempted <= step.max_retries:
                    self.cancellation.assert_not_cancelled(goal.goal_id)
                    step.mark_running()
                    self.journal.record(
                        JournalEventType.STEP_STARTED,
                        task_id=goal.goal_id,
                        goal_id=goal.goal_id,
                        plan_version=current_plan.version,
                        step_id=step.step_id,
                        metadata={"capability": step.capability, "attempt": step.retries_attempted + 1},
                    )
                    self._publish_event(ActivityState.THINKING, operation=step.capability, message=step.purpose)

                    try:
                        exec_res = await asyncio.wait_for(
                            self.tools.execute(
                                tool_name=step.capability,
                                arguments=step.arguments,
                                session_id=goal.session_id,
                            ),
                            timeout=step.timeout_sec,
                        )

                        if isinstance(exec_res, dict) and exec_res.get("status") == "CONFIRM_REQUIRED":
                            goal.transition_to(GoalState.GOAL_WAITING_USER)
                            step.status = StepStatus.WAITING_CONFIRMATION
                            self.journal.record(
                                JournalEventType.CONFIRMATION_REQUESTED,
                                task_id=goal.goal_id,
                                goal_id=goal.goal_id,
                                plan_version=current_plan.version,
                                step_id=step.step_id,
                                metadata={"action": step.capability},
                            )
                            self._persist_state(goal, current_plan, context)
                            return {
                                "success": False,
                                "status": "CONFIRM_REQUIRED",
                                "goal_id": goal.goal_id,
                                "step_id": step.step_id,
                                "action": step.capability,
                                "confirmation_token": exec_res.get("confirmation_token"),
                                "message": exec_res.get("message"),
                            }

                        # Verification
                        step_model = TaskStep(
                            step_id=step.step_id,
                            tool_name=step.capability,
                            arguments=step.arguments,
                            purpose=step.purpose,
                        )
                        verif = self.verifier.verify_step(step_model, exec_res)

                        if exec_res.get("success", False) and verif.verified:
                            step_success = True
                            step.mark_completed(exec_res, verif)
                            break
                        else:
                            step.retries_attempted += 1
                            err_reason = verif.error_message or exec_res.get("error") or "Verification failed."
                            logger.warning(f"[Goal Engine] Step '{step.step_id}' failed (Attempt {step.retries_attempted}/{step.max_retries + 1}): {err_reason}")
                            if step.retries_attempted <= step.max_retries:
                                self.journal.record(
                                    JournalEventType.RETRY_STARTED,
                                    task_id=goal.goal_id,
                                    goal_id=goal.goal_id,
                                    plan_version=current_plan.version,
                                    step_id=step.step_id,
                                    metadata={"attempt": step.retries_attempted, "error": err_reason},
                                )
                                await asyncio.sleep(0.2 * step.retries_attempted)

                    except asyncio.TimeoutError:
                        step.retries_attempted += 1
                        step.status = StepStatus.UNKNOWN_OUTCOME
                        err_reason = f"Step execution timed out after {step.timeout_sec}s."
                        logger.warning(f"[Goal Engine] Step '{step.step_id}' timed out; marked UNKNOWN_OUTCOME.")
                    except TaskCancelledError:
                        goal.transition_to(GoalState.GOAL_CANCELLED, reason="Cancelled during step execution")
                        step.mark_cancelled()
                        self.journal.record(
                            JournalEventType.TASK_CANCELLED,
                            task_id=goal.goal_id,
                            goal_id=goal.goal_id,
                            plan_version=current_plan.version,
                            step_id=step.step_id,
                        )
                        self._persist_state(goal, current_plan, context)
                        return {
                            "success": False,
                            "status": "GOAL_CANCELLED",
                            "goal_id": goal.goal_id,
                            "message": "Goal was cancelled by user.",
                        }
                    except Exception as err:
                        step.retries_attempted += 1
                        err_reason = str(err)
                        logger.error(f"[Goal Engine] Error on step '{step.step_id}': {err}")

                # 7. Handle Step Outcome
                if step_success:
                    # Save intermediate variable if produced
                    if step.produces_intermediate_key:
                        val = (
                            exec_res.get("saved_to")
                            or exec_res.get("links")
                            or exec_res.get("destination_url")
                            or exec_res.get("current_url")
                            or exec_res.get("url")
                            or exec_res.get("result")
                            or exec_res
                        )
                        context.set_variable(step.produces_intermediate_key, val)

                    # Update Checkpoint & Evidence
                    context.create_checkpoint(
                        completed_step_ids=list(current_plan.get_completed_step_ids()),
                        plan_version=current_plan.version,
                    )
                    self.evidence.record_step_evidence(
                        goal_id=goal.goal_id,
                        plan_version=current_plan.version,
                        step_id=step.step_id,
                        capability=step.capability,
                        arguments=step.arguments,
                        execution_result=exec_res,
                        verification=verif,
                    )
                    self.journal.record(
                        JournalEventType.STEP_VERIFIED,
                        task_id=goal.goal_id,
                        goal_id=goal.goal_id,
                        plan_version=current_plan.version,
                        step_id=step.step_id,
                        metadata={"capability": step.capability},
                    )
                    self.journal.record(
                        JournalEventType.STEP_COMPLETED,
                        task_id=goal.goal_id,
                        goal_id=goal.goal_id,
                        plan_version=current_plan.version,
                        step_id=step.step_id,
                    )
                    self._persist_state(goal, current_plan, context)

                    results_summary.append({
                        "step_id": step.step_id,
                        "capability": step.capability,
                        "result": exec_res,
                        "verified": True,
                    })

                    self.memory.record_turn(
                        role="tool",
                        content=str(exec_res),
                        tool_name=step.capability,
                        tool_args=step.arguments,
                        tool_result=exec_res,
                    )
                else:
                    # Step failed all retries -> Classify and attempt dynamic replan
                    step.mark_failed(err_reason, exec_res, verif)
                    self.journal.record(
                        JournalEventType.STEP_FAILED,
                        task_id=goal.goal_id,
                        goal_id=goal.goal_id,
                        plan_version=current_plan.version,
                        step_id=step.step_id,
                        metadata={"error": err_reason},
                    )

                    fail_class, strat = FailureClassifier.classify(
                        error_msg=err_reason,
                        tool_name=step.capability,
                        status=exec_res.get("status") if isinstance(exec_res, dict) else None,
                        verification=verif,
                        retries_attempted=step.retries_attempted,
                        max_retries=step.max_retries,
                    )
                    context.record_failure(step.step_id, err_reason, fail_class.value)

                    if strat == RecoveryStrategy.DYNAMIC_REPLAN and self.replanner.can_replan(goal):
                        self.journal.record(
                            JournalEventType.REPLAN_STARTED,
                            task_id=goal.goal_id,
                            goal_id=goal.goal_id,
                            plan_version=current_plan.version,
                            metadata={"failed_step": step.step_id, "reason": err_reason},
                        )
                        goal.transition_to(GoalState.GOAL_REPLANNING)
                        self._publish_event(
                            ActivityState.THINKING,
                            operation="replan",
                            message=f"Replanning goal after step '{step.step_id}' failed: {err_reason}",
                        )
                        new_plan = self.replanner.replan_after_failure(
                            goal=goal,
                            current_plan=current_plan,
                            failed_step=step,
                            failure_class=fail_class,
                            context=context,
                        )
                        current_plan = new_plan
                        self.active_plan = current_plan
                        self.journal.record(
                            JournalEventType.REPLAN_COMPLETED,
                            task_id=goal.goal_id,
                            goal_id=goal.goal_id,
                            plan_version=current_plan.version,
                            metadata={"new_version": current_plan.version, "steps_count": len(current_plan.steps)},
                        )
                        self._persist_state(goal, current_plan, context)
                        goal.transition_to(GoalState.GOAL_EXECUTING)
                        continue

                    # Unrecoverable or safety blocked failure
                    goal.transition_to(GoalState.GOAL_FAILED, reason=err_reason)
                    current_plan.status = PlanStatus.FAILED
                    self.journal.record(
                        JournalEventType.TASK_FAILED,
                        task_id=goal.goal_id,
                        goal_id=goal.goal_id,
                        plan_version=current_plan.version,
                        metadata={"error": err_reason, "failed_step": step.step_id},
                    )
                    self._persist_state(goal, current_plan, context)
                    self._publish_event(ActivityState.IDLE, operation="goal_failed", message=err_reason)

                    return {
                        "success": False,
                        "status": "GOAL_FAILED",
                        "goal_id": goal.goal_id,
                        "failed_step": step.step_id,
                        "failed_capability": step.capability,
                        "failure_class": fail_class.value,
                        "error": err_reason,
                        "completed_steps": results_summary,
                    }

            # 8. Empirical Goal Outcome Verification & Completion
            if goal.desired_outcome:
                if goal.desired_outcome.target_file:
                    target_p = Path(goal.desired_outcome.target_file)
                    if not target_p.is_absolute():
                        target_p = (self.workspace_root / target_p).resolve()
                    if not target_p.exists() or target_p.stat().st_size < goal.desired_outcome.min_file_size_bytes:
                        err_out = f"Desired file '{target_p}' was not produced or is empty."
                        goal.transition_to(GoalState.GOAL_FAILED, reason=err_out)
                        self.journal.record(
                            JournalEventType.TASK_FAILED,
                            task_id=goal.goal_id,
                            goal_id=goal.goal_id,
                            plan_version=current_plan.version,
                            metadata={"error": err_out},
                        )
                        self._persist_state(goal, current_plan, context)
                        return {
                            "success": False,
                            "status": "GOAL_FAILED",
                            "goal_id": goal.goal_id,
                            "error": err_out,
                            "completed_steps": results_summary,
                        }

            # Verify evidence completeness
            evidence_valid, evidence_summary = self.evidence.verify_goal_outcome(goal, context)

            goal.transition_to(GoalState.GOAL_COMPLETED)
            current_plan.status = PlanStatus.COMPLETED
            self.journal.record(
                JournalEventType.TASK_COMPLETED,
                task_id=goal.goal_id,
                goal_id=goal.goal_id,
                plan_version=current_plan.version,
                metadata={"steps_completed": len(results_summary), "evidence_valid": evidence_valid},
            )
            self._persist_state(goal, current_plan, context)

            self._publish_event(ActivityState.IDLE, operation="goal_completed", message=f"Goal {goal.goal_id} completed successfully")
            logger.info(f"[Goal Engine] Goal '{goal.goal_id}' completed successfully across {len(results_summary)} steps.")

            return {
                "success": True,
                "status": "COMPLETED",
                "goal_id": goal.goal_id,
                "objective": goal.normalized_objective,
                "plan_version": current_plan.version,
                "steps_completed": len(results_summary),
                "results": results_summary,
                "context_variables": context.list_variables(),
                "evidence_summary": evidence_summary,
            }

    async def resume_goal_with_confirmation(self, goal_id: str, confirmation_token: str) -> Dict[str, Any]:
        """Resumes a goal paused in GOAL_WAITING_USER."""
        if not self.active_goal or self.active_goal.goal_id != goal_id:
            return {"success": False, "error": f"No active goal with ID '{goal_id}' found."}

        goal = self.active_goal
        if goal.current_status != GoalState.GOAL_WAITING_USER:
            return {"success": False, "error": f"Goal '{goal_id}' is in state {goal.current_status}, not awaiting confirmation."}

        self.journal.record(
            JournalEventType.CONFIRMATION_APPROVED,
            task_id=goal_id,
            goal_id=goal_id,
            plan_version=self.active_plan.version if self.active_plan else 1,
        )

        if self.active_plan:
            for s in self.active_plan.steps:
                if s.status == StepStatus.WAITING_CONFIRMATION:
                    s.arguments["confirmation_token"] = confirmation_token
                    s.status = StepStatus.PENDING

        goal.transition_to(GoalState.GOAL_EXECUTING)
        return await self.execute_goal(goal, initial_plan=self.active_plan)

    def pause_active_goal(self, reason: str = "User pause request") -> bool:
        """Pauses the currently active goal execution without cancelling it."""
        if self.active_goal and self.active_goal.is_active:
            logger.info(f"[Goal Engine] Pausing active goal '{self.active_goal.goal_id}': {reason}")
            self.active_goal.transition_to(GoalState.GOAL_PAUSED, reason=reason)
            self.journal.record(
                JournalEventType.TASK_PAUSED,
                task_id=self.active_goal.goal_id,
                goal_id=self.active_goal.goal_id,
                plan_version=self.active_plan.version if self.active_plan else 1,
                metadata={"reason": reason},
            )
            ctx = self._contexts.get(self.active_goal.goal_id)
            self._persist_state(self.active_goal, self.active_plan, ctx)
            self._publish_event(ActivityState.IDLE, operation="goal_paused", message=reason)
            return True
        return False

    async def resume_active_goal(self, goal_id: str) -> Dict[str, Any]:
        """Resumes a paused active goal."""
        if not self.active_goal or self.active_goal.goal_id != goal_id:
            return await self.resume_persisted_goal(goal_id)

        if self.cancellation.is_task_cancelled(goal_id):
            raise TaskCancelledError(f"Goal '{goal_id}' was cancelled and cannot be resumed.")

        if self.active_goal.current_status != GoalState.GOAL_PAUSED:
            return {"success": False, "error": f"Goal '{goal_id}' is not paused (status: {self.active_goal.current_status})."}

        self.journal.record(
            JournalEventType.TASK_RESUMED,
            task_id=goal_id,
            goal_id=goal_id,
            plan_version=self.active_plan.version if self.active_plan else 1,
            metadata={"resumed_from": "pause"},
        )
        self.active_goal.transition_to(GoalState.GOAL_EXECUTING)
        return await self.execute_goal(self.active_goal, initial_plan=self.active_plan)

    async def resume_persisted_goal(self, goal_id: str) -> Dict[str, Any]:
        """
        Recovers a goal from disk after crash or restart.
        Validates integrity, restores checkpoint, probes environment for in-flight actions,
        and safely resumes execution without duplicate side effects.
        """
        async with self._lock:
            # 1. Load state from persistence
            saved = self.persistence.load_goal_state(goal_id)
            if not saved:
                return {
                    "success": False,
                    "status": "RECOVERY_FAILED",
                    "goal_id": goal_id,
                    "error": f"Persisted state for goal '{goal_id}' not found or was corrupted/quarantined.",
                }

            goal_info = saved.get("goal", {})
            plan_info = saved.get("plan", {})
            ctx_info = saved.get("context", {})

            # 2. Check sticky cancellation
            if goal_info.get("current_status") == GoalState.GOAL_CANCELLED.value or self.cancellation.is_task_cancelled(goal_id):
                return {
                    "success": False,
                    "status": "GOAL_CANCELLED",
                    "goal_id": goal_id,
                    "error": "Goal was cancelled and cannot be resumed.",
                }

            # 3. Check already completed
            if goal_info.get("current_status") == GoalState.GOAL_COMPLETED.value:
                return {
                    "success": True,
                    "status": "COMPLETED",
                    "goal_id": goal_id,
                    "message": "Goal was already completed prior to recovery.",
                }

            # 4. Reconstruct Goal
            goal = Goal(
                goal_id=goal_info.get("goal_id", goal_id),
                original_user_request=goal_info.get("original_user_request", ""),
                normalized_objective=goal_info.get("normalized_objective", ""),
                current_status=GoalState.GOAL_EXECUTING,
                replan_count=goal_info.get("replan_count", 0),
                created_at=goal_info.get("created_at", time.time()),
                updated_at=time.time(),
                session_id=goal_info.get("session_id", "default"),
                metadata=goal_info.get("metadata", {}),
            )

            # 5. Reconstruct Plan
            steps: List[PlanStep] = []
            for s_data in plan_info.get("steps", []):
                st_val = s_data.get("status", "PENDING")
                st_enum = StepStatus(st_val) if st_val in StepStatus.__members__ else StepStatus.PENDING
                step = PlanStep(
                    step_id=s_data.get("step_id", ""),
                    capability=s_data.get("capability", ""),
                    arguments=s_data.get("arguments", {}),
                    purpose=s_data.get("purpose", ""),
                    prerequisites=s_data.get("prerequisites", []),
                    status=st_enum,
                    safety_class=s_data.get("safety_class", "SAFE"),
                    requires_confirmation=s_data.get("requires_confirmation", False),
                    side_effect=SideEffectType(s_data.get("side_effect", "READ")),
                    retry_safety=RetrySafety(s_data.get("retry_safety", "SAFE_TO_RETRY")),
                    retries_attempted=s_data.get("retries_attempted", 0),
                    max_retries=s_data.get("max_retries", 2),
                    produces_intermediate_key=s_data.get("produces_intermediate_key"),
                    consumes_intermediate_keys=s_data.get("consumes_intermediate_keys", []),
                    execution_result=s_data.get("execution_result"),
                    error=s_data.get("error"),
                )
                steps.append(step)

            plan = Plan(
                plan_id=plan_info.get("plan_id", f"plan-{goal_id}"),
                goal_id=goal_id,
                version=plan_info.get("version", 1),
                steps=steps,
                status=PlanStatus.EXECUTING,
            )

            # 6. Reconstruct TaskContext & Checkpoint
            context = TaskContext(goal_id)
            for k, v in ctx_info.get("variables", {}).items():
                context.set_variable(k, v)
            for k, v in ctx_info.get("observations", {}).items():
                context.record_observation(k, v)

            for chk_data in ctx_info.get("checkpoints", []):
                chk = Checkpoint(
                    checkpoint_id=chk_data["checkpoint_id"],
                    timestamp=chk_data["timestamp"],
                    completed_step_ids=chk_data["completed_step_ids"],
                    variables=chk_data["variables"],
                    plan_version=chk_data["plan_version"],
                    observed_state=chk_data["observed_state"],
                    integrity_hash=chk_data.get("integrity_hash", ""),
                )
                if chk.is_valid():
                    context._checkpoints.append(chk)
                else:
                    logger.warning(f"[Crash Recovery] Checkpoint {chk.checkpoint_id} failed integrity verification; skipping.")

            # 7. Pre-probe in-flight / running step for idempotent recovery
            for s in plan.steps:
                if s.status in (StepStatus.RUNNING, StepStatus.VERIFYING, StepStatus.UNKNOWN_OUTCOME):
                    if plan.are_prerequisites_satisfied(s):
                        probed, probe_res = self._probe_environment_for_step(s)
                        if probed:
                            logger.info(f"[Crash Recovery] Step '{s.step_id}' ({s.capability}) verified via environment pre-probe.")
                            step_model = TaskStep(step_id=s.step_id, tool_name=s.capability, arguments=s.arguments)
                            v_res = self.verifier.verify_step(step_model, probe_res)
                            s.mark_completed(probe_res, v_res)
                            if s.produces_intermediate_key:
                                context.set_variable(s.produces_intermediate_key, probe_res.get("saved_to") or probe_res.get("path") or probe_res)
                        else:
                            # In-flight step was not completed prior to crash; reset to PENDING for safe execution
                            s.status = StepStatus.PENDING


            self._contexts[goal_id] = context
            self.active_goal = goal
            self.active_plan = plan

            self.journal.record(
                JournalEventType.TASK_RESUMED,
                task_id=goal_id,
                goal_id=goal_id,
                plan_version=plan.version,
                metadata={"action": "crash_recovery_resumed"},
            )

        # 8. Resume execution
        return await self.execute_goal(goal, initial_plan=plan)

    def cancel_active_goal(self, reason: str = "User voice cancellation") -> bool:
        """Immediately signals cancellation for the active goal and plan."""
        if self.active_goal and self.active_goal.is_active:
            logger.info(f"[Goal Engine] Cancelling active goal '{self.active_goal.goal_id}': {reason}")
            self.cancellation.cancel_task(self.active_goal.goal_id, reason=reason)
            self.active_goal.transition_to(GoalState.GOAL_CANCELLED, reason=reason)
            if self.active_plan:
                self.active_plan.status = PlanStatus.CANCELLED
            self.journal.record(
                JournalEventType.TASK_CANCELLED,
                task_id=self.active_goal.goal_id,
                goal_id=self.active_goal.goal_id,
                plan_version=self.active_plan.version if self.active_plan else 1,
                metadata={"reason": reason},
            )
            ctx = self._contexts.get(self.active_goal.goal_id)
            self._persist_state(self.active_goal, self.active_plan, ctx)
            self._publish_event(ActivityState.IDLE, operation="goal_cancelled", message=reason)
            return True
        return False

    def _resolve_plan_step_pronouns(self, step: PlanStep) -> None:
        """Resolves pronoun references in plan step arguments."""
        if not self.memory or not hasattr(self.memory, "session") or not self.memory.session:
            return

        cap = step.capability
        args = step.arguments

        if cap in ("open_app", "close_app", "windows_open_app", "windows_close_app"):
            raw_app = str(args.get("app_name", "")).strip()
            if raw_app.lower() in ("it", "the app", "that app", "this app", "the application"):
                resolved = self.memory.session.resolve_target("app")
                if resolved:
                    args["app_name"] = resolved

        elif cap in (
            "read_file",
            "write_file",
            "delete_file",
            "get_file_info",
            "list_directory",
            "create_directory",
            "chrome_download_file",
        ):
            raw_path = str(args.get("path") or args.get("destination") or "").strip()
            if raw_path.lower() in (
                "it",
                "the file",
                "that file",
                "this file",
                "the document",
                "the folder",
                "the directory",
                "that download",
            ):
                resolved = self.memory.session.resolve_target("file")
                if resolved:
                    if "path" in args:
                        args["path"] = resolved
                    elif "destination" in args:
                        args["destination"] = resolved

        if cap in ("chrome_navigate", "chrome_download_file"):
            raw_url = str(args.get("url", "")).strip()
            if raw_url.lower() in (
                "it",
                "that link",
                "that url",
                "that page",
                "the website",
                "the link",
                "this page",
            ):
                resolved = self.memory.session.resolve_target("url")
                if resolved:
                    args["url"] = resolved

        if cap == "chrome_search":
            raw_query = str(args.get("query", "")).strip()
            if raw_query.lower() in ("it", "that", "the search", "the query"):
                resolved = self.memory.session.resolve_target("query")
                if resolved:
                    args["query"] = resolved



