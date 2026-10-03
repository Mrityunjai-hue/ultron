"""
ULTRON V3 — Plan Model & Dependency Graph Validator
─────────────────────────────────────────────────────────────────────────────
Defines structured multi-step execution plans with explicit prerequisite
dependencies, intermediate key passing, side-effect classifications, and
cycle-free dependency graph validation.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Set, Tuple

from ultron.tasks.state import StepStatus
from ultron.tasks.errors import TaskPlanningError
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ultron.tasks.models import VerificationResult


class PlanStatus(str, Enum):
    """Lifecycle status of an execution plan."""
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"
    CANCELLED = "CANCELLED"


class SideEffectType(str, Enum):
    """Classification of tool action side-effects."""
    READ = "READ"           # Passive observation (no disk/app/system mutation)
    WRITE = "WRITE"         # Mutation of filesystem, state, or memory
    DELETE = "DELETE"       # Destructive file or resource removal
    EXTERNAL = "EXTERNAL"   # Remote network mutation, download, or web submit


class RetrySafety(str, Enum):
    """Safety classification for automated step retries."""
    IDEMPOTENT = "IDEMPOTENT"                 # Completely safe to repeat any number of times
    SAFE_TO_RETRY = "SAFE_TO_RETRY"           # Safe to retry with same parameters
    NOT_SAFE_TO_RETRY = "NOT_SAFE_TO_RETRY"   # Side-effecting; requires state verification before retry


def get_capability_retry_safety(capability: str) -> RetrySafety:
    """Determines retry safety classification for a capability."""
    cap = capability.lower().strip()
    if cap in (
        "read_file", "get_file_info", "list_directory", "get_page_title",
        "get_page_text", "get_current_time", "get_system_status", "get_active_app",
        "get_running_apps", "get_active_window", "enumerate_windows", "list_memories",
        "chrome_get_active_tab", "read_clipboard",
    ):
        return RetrySafety.IDEMPOTENT

    elif cap in (
        "chrome_search", "chrome_navigate", "chrome_find_link", "chrome_launch",
        "remember_fact", "forget_fact", "write_clipboard", "open_app", "windows_open_app",
    ):
        return RetrySafety.SAFE_TO_RETRY

    return RetrySafety.NOT_SAFE_TO_RETRY


@dataclass
class PlanStep:
    """Individual atomic execution node within an execution plan."""
    step_id: str
    capability: str
    arguments: Dict[str, Any]
    purpose: str = ""
    prerequisites: List[str] = field(default_factory=list)
    expected_result: Optional[Dict[str, Any]] = None
    verification_condition: Optional[str] = None
    produces_intermediate_key: Optional[str] = None
    consumes_intermediate_keys: List[str] = field(default_factory=list)
    safety_class: str = "SAFE"
    requires_confirmation: bool = False
    side_effect: SideEffectType = SideEffectType.READ
    retry_safety: RetrySafety = RetrySafety.SAFE_TO_RETRY
    fallback_strategy: Optional[str] = None
    retries_attempted: int = 0
    max_retries: int = 2
    timeout_sec: float = 15.0
    status: StepStatus = StepStatus.PENDING

    execution_result: Optional[Dict[str, Any]] = None
    verification_result: Optional[VerificationResult] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def mark_running(self):
        self.status = StepStatus.RUNNING
        self.started_at = time.time()

    def mark_completed(self, result: Dict[str, Any], verification: Optional[VerificationResult] = None):
        self.status = StepStatus.COMPLETED
        self.execution_result = result
        self.verification_result = verification
        self.completed_at = time.time()

    def mark_failed(self, error: str, result: Optional[Dict[str, Any]] = None, verification: Optional[VerificationResult] = None):
        self.status = StepStatus.FAILED
        self.error = error
        self.execution_result = result
        self.verification_result = verification
        self.completed_at = time.time()

    def mark_cancelled(self, reason: str = "Plan cancelled"):
        self.status = StepStatus.CANCELLED
        self.error = reason
        self.completed_at = time.time()


@dataclass
class Plan:
    """Authoritative executable plan generated to satisfy a Goal."""
    plan_id: str
    goal_id: str
    version: int = 1
    steps: List[PlanStep] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    expected_outcomes: Dict[str, Any] = field(default_factory=dict)
    fallback_options: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    reason_for_creation: str = "Initial plan"
    status: PlanStatus = PlanStatus.PENDING

    @classmethod
    def create(
        cls,
        goal_id: str,
        steps: List[PlanStep],
        version: int = 1,
        reason: str = "Initial plan",
        expected_outcomes: Optional[Dict[str, Any]] = None,
        fallback_options: Optional[List[Dict[str, Any]]] = None,
    ) -> Plan:
        pid = f"plan-{uuid.uuid4().hex[:8]}"
        deps: Dict[str, List[str]] = {}
        for s in steps:
            deps[s.step_id] = list(s.prerequisites)

        plan = cls(
            plan_id=pid,
            goal_id=goal_id,
            version=version,
            steps=steps,
            dependencies=deps,
            expected_outcomes=expected_outcomes or {},
            fallback_options=fallback_options or [],
            created_at=time.time(),
            reason_for_creation=reason,
            status=PlanStatus.PENDING,
        )
        validate_dependency_graph(plan.steps)
        return plan

    def get_step(self, step_id: str) -> Optional[PlanStep]:
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return None

    def get_completed_step_ids(self) -> Set[str]:
        return {s.step_id for s in self.steps if s.status == StepStatus.COMPLETED}

    def are_prerequisites_satisfied(self, step: PlanStep) -> bool:
        completed = self.get_completed_step_ids()
        return all(prereq in completed for prereq in step.prerequisites)

    def is_finished(self) -> bool:
        return self.status in (PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.SUPERSEDED, PlanStatus.CANCELLED)


def validate_dependency_graph(
    steps: List[PlanStep],
    max_steps: int = 20,
    max_depth: int = 10,
) -> List[str]:
    """
    Validates that a plan's dependency graph is acyclic, well-bounded,
    and returns a topologically sorted list of step IDs.
    """
    if not steps:
        raise TaskPlanningError("Plan must contain at least one step.")

    if len(steps) > max_steps:
        raise TaskPlanningError(f"Plan step count ({len(steps)}) exceeds maximum limit of {max_steps}.")

    step_map: Dict[str, PlanStep] = {}
    for s in steps:
        if s.step_id in step_map:
            raise TaskPlanningError(f"Duplicate step ID '{s.step_id}' found in plan.")
        step_map[s.step_id] = s

    # Validate that all prerequisite step IDs exist
    for s in steps:
        for prereq in s.prerequisites:
            if prereq not in step_map:
                raise TaskPlanningError(f"Step '{s.step_id}' references unknown prerequisite '{prereq}'.")
            if prereq == s.step_id:
                raise TaskPlanningError(f"Step '{s.step_id}' cannot depend on itself (circular dependency).")

    # Topological Sort & Cycle Detection using Kahn's Algorithm
    in_degree: Dict[str, int] = {s.step_id: len(s.prerequisites) for s in steps}
    dependents: Dict[str, List[str]] = {s.step_id: [] for s in steps}
    for s in steps:
        for prereq in s.prerequisites:
            dependents[prereq].append(s.step_id)

    queue = [sid for sid, deg in in_degree.items() if deg == 0]
    sorted_order: List[str] = []
    depth_map: Dict[str, int] = {sid: 1 for sid in queue}

    while queue:
        curr = queue.pop(0)
        sorted_order.append(curr)
        curr_depth = depth_map[curr]

        if curr_depth > max_depth:
            raise TaskPlanningError(
                f"Plan dependency depth ({curr_depth}) at step '{curr}' exceeds maximum limit of {max_depth}."
            )

        for nxt in dependents[curr]:
            in_degree[nxt] -= 1
            depth_map[nxt] = max(depth_map.get(nxt, 1), curr_depth + 1)
            if in_degree[nxt] == 0:
                queue.append(nxt)

    if len(sorted_order) != len(steps):
        unresolved = [sid for sid, deg in in_degree.items() if deg > 0]
        raise TaskPlanningError(f"Circular dependency detected involving steps: {unresolved}")

    return sorted_order
