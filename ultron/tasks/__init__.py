"""
ULTRON V3 — Advanced Desktop Agent Task Execution Subsystem
─────────────────────────────────────────────────────────────────────────────
Exposes task planning, models, verification, lifecycle execution, and cancellation.
─────────────────────────────────────────────────────────────────────────────
"""
from ultron.tasks.models import Task, TaskStep, VerificationResult
from ultron.tasks.state import TaskState, StepStatus
from ultron.tasks.goal import Goal, GoalState, GoalOutcome, GoalConstraint
from ultron.tasks.plan import Plan, PlanStep, PlanStatus, SideEffectType, validate_dependency_graph
from ultron.tasks.context import TaskContext, Checkpoint
from ultron.tasks.recovery import FailureClassification, RecoveryStrategy, FailureClassifier
from ultron.tasks.replanner import DynamicReplanner
from ultron.tasks.goal_planner import GoalPlanner
from ultron.tasks.errors import (
    TaskError,
    TaskPlanningError,
    TaskSecurityViolationError,
    TaskVerificationError,
    TaskTimeoutError,
    TaskCancelledError,
    TaskConcurrencyError,
)
from ultron.tasks.planner import TaskPlanner
from ultron.tasks.verifier import ActionVerifier
from ultron.tasks.cancellation import TaskCancellationManager
from ultron.tasks.executor import TaskExecutionEngine

__all__ = [
    "Task",
    "TaskStep",
    "VerificationResult",
    "TaskState",
    "StepStatus",
    "Goal",
    "GoalState",
    "GoalOutcome",
    "GoalConstraint",
    "Plan",
    "PlanStep",
    "PlanStatus",
    "SideEffectType",
    "validate_dependency_graph",
    "TaskContext",
    "Checkpoint",
    "FailureClassification",
    "RecoveryStrategy",
    "FailureClassifier",
    "DynamicReplanner",
    "GoalPlanner",
    "TaskError",
    "TaskPlanningError",
    "TaskSecurityViolationError",
    "TaskVerificationError",
    "TaskTimeoutError",
    "TaskCancelledError",
    "TaskConcurrencyError",
    "TaskPlanner",
    "ActionVerifier",
    "TaskCancellationManager",
    "TaskExecutionEngine",
]

