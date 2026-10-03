"""
ULTRON V3 — Task & Step Data Models
─────────────────────────────────────────────────────────────────────────────
Defines structured internal models for multi-step tasks, verification results,
and execution status tracking.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from ultron.tasks.state import TaskState, StepStatus

@dataclass
class VerificationResult:
    """Outcome of mandatory post-action verification."""
    verified: bool
    method: str
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class TaskStep:
    """Individual atomic execution step within a task."""
    step_id: str
    tool_name: str
    arguments: Dict[str, Any]
    purpose: str = ""
    safety_class: str = "SAFE"
    requires_confirmation: bool = False
    status: StepStatus = StepStatus.PENDING
    retries_attempted: int = 0
    max_retries: int = 2
    timeout_sec: float = 15.0
    execution_result: Optional[Dict[str, Any]] = None
    verification_result: Optional[VerificationResult] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None

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

    def mark_cancelled(self, reason: str = "Task cancelled"):
        self.status = StepStatus.CANCELLED
        self.error = reason
        self.completed_at = time.time()

    @property
    def verification(self) -> Optional[VerificationResult]:
        return self.verification_result

@dataclass
class Task:
    """Authoritative representation of a multi-step user goal/task."""
    task_id: str
    user_intent: str
    steps: List[TaskStep] = field(default_factory=list)
    current_step_index: int = 0
    state: TaskState = TaskState.TASK_RECEIVED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    cancellation_reason: Optional[str] = None
    failure_reason: Optional[str] = None
    session_id: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, user_intent: str, steps: Optional[List[TaskStep]] = None, session_id: str = "default") -> Task:
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        return cls(
            task_id=task_id,
            user_intent=user_intent,
            steps=steps or [],
            current_step_index=0,
            state=TaskState.TASK_RECEIVED,
            created_at=time.time(),
            updated_at=time.time(),
            session_id=session_id,
        )

    @property
    def current_step(self) -> Optional[TaskStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def is_finished(self) -> bool:
        return self.state in (TaskState.TASK_COMPLETED, TaskState.TASK_FAILED, TaskState.TASK_CANCELLED)

    def transition_to(self, new_state: TaskState, reason: Optional[str] = None):
        self.state = new_state
        self.updated_at = time.time()
        if new_state == TaskState.TASK_COMPLETED:
            self.completed_at = time.time()
        elif new_state == TaskState.TASK_FAILED:
            self.failure_reason = reason
            self.completed_at = time.time()
        elif new_state == TaskState.TASK_CANCELLED:
            self.cancellation_reason = reason
            self.completed_at = time.time()
