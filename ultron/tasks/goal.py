"""
ULTRON V3 — Goal Model & Lifecycle State Machine
─────────────────────────────────────────────────────────────────────────────
Defines structured representations for high-level user goals, completion criteria,
constraints, and authoritative goal lifecycle states.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional


class GoalState(str, Enum):
    """Authoritative lifecycle states of a user goal."""
    GOAL_RECEIVED = "GOAL_RECEIVED"
    GOAL_UNDERSTANDING = "GOAL_UNDERSTANDING"
    GOAL_PLANNING = "GOAL_PLANNING"
    GOAL_EXECUTING = "GOAL_EXECUTING"
    GOAL_REPLANNING = "GOAL_REPLANNING"
    GOAL_WAITING_USER = "GOAL_WAITING_USER"
    GOAL_PAUSED = "GOAL_PAUSED"
    GOAL_COMPLETED = "GOAL_COMPLETED"
    GOAL_FAILED = "GOAL_FAILED"
    GOAL_CANCELLED = "GOAL_CANCELLED"



@dataclass
class GoalOutcome:
    """Explicit desired outcome and empirical completion conditions for a goal."""
    description: str
    target_file: Optional[str] = None
    expected_data_keys: List[str] = field(default_factory=list)
    verification_rule: Optional[str] = None
    min_file_size_bytes: int = 1


@dataclass
class GoalConstraint:
    """Constraints imposed on goal planning and execution."""
    max_replans: int = 5
    max_steps_per_plan: int = 20
    max_dependency_depth: int = 10
    timeout_sec: float = 120.0
    allowed_apps: List[str] = field(default_factory=list)
    workspace_only: bool = True


@dataclass
class Goal:
    """Authoritative representation of a high-level user goal."""
    goal_id: str
    original_user_request: str
    normalized_objective: str
    constraints: GoalConstraint = field(default_factory=GoalConstraint)
    desired_outcome: Optional[GoalOutcome] = None
    current_status: GoalState = GoalState.GOAL_RECEIVED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    deadline: Optional[float] = None
    active_plan_id: Optional[str] = None
    completed_conditions: List[str] = field(default_factory=list)
    failure_reason: Optional[str] = None
    cancellation_reason: Optional[str] = None
    replan_count: int = 0
    session_id: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        user_request: str,
        normalized_objective: Optional[str] = None,
        desired_outcome: Optional[GoalOutcome] = None,
        constraints: Optional[GoalConstraint] = None,
        session_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Goal:
        gid = f"goal-{uuid.uuid4().hex[:8]}"
        norm = normalized_objective or user_request.strip()
        return cls(
            goal_id=gid,
            original_user_request=user_request.strip(),
            normalized_objective=norm,
            constraints=constraints or GoalConstraint(),
            desired_outcome=desired_outcome,
            current_status=GoalState.GOAL_RECEIVED,
            created_at=time.time(),
            updated_at=time.time(),
            session_id=session_id,
            metadata=metadata or {},
        )

    @property
    def is_active(self) -> bool:
        return self.current_status in (
            GoalState.GOAL_RECEIVED,
            GoalState.GOAL_UNDERSTANDING,
            GoalState.GOAL_PLANNING,
            GoalState.GOAL_EXECUTING,
            GoalState.GOAL_REPLANNING,
            GoalState.GOAL_WAITING_USER,
        )

    @property
    def is_finished(self) -> bool:
        return self.current_status in (
            GoalState.GOAL_COMPLETED,
            GoalState.GOAL_FAILED,
            GoalState.GOAL_CANCELLED,
        )

    @property
    def state(self) -> GoalState:
        return self.current_status

    @property
    def user_request(self) -> str:
        return self.original_user_request

    def mark_cancelled(self, reason: str = "Goal cancelled"):
        self.transition_to(GoalState.GOAL_CANCELLED, reason)

    def transition_to(self, new_state: GoalState, reason: Optional[str] = None):
        self.current_status = new_state
        self.updated_at = time.time()
        if new_state == GoalState.GOAL_COMPLETED:
            self.completed_at = time.time()
        elif new_state == GoalState.GOAL_FAILED:
            self.failure_reason = reason
            self.completed_at = time.time()
        elif new_state == GoalState.GOAL_CANCELLED:
            self.cancellation_reason = reason
            self.completed_at = time.time()

    def record_condition_completed(self, condition: str):
        if condition not in self.completed_conditions:
            self.completed_conditions.append(condition)
            self.updated_at = time.time()


GoalConstraints = GoalConstraint

