"""
ULTRON V3 — Task Execution Exceptions & Structured Errors
─────────────────────────────────────────────────────────────────────────────
Structured exceptions for task planning, execution, verification, and safety.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
from typing import Optional, Dict, Any

class TaskError(Exception):
    """Base exception for task execution failures."""
    def __init__(self, message: str, task_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.task_id = task_id
        self.details = details or {}

class TaskPlanningError(TaskError):
    """Raised when an invalid task plan is proposed."""
    pass

class TaskSecurityViolationError(TaskError):
    """Raised when a task step violates local safety policies."""
    pass

class TaskVerificationError(TaskError):
    """Raised when an action execution fails post-execution verification."""
    pass

class TaskTimeoutError(TaskError):
    """Raised when a task step exceeds its maximum allowed execution duration."""
    pass

class TaskCancelledError(TaskError):
    """Raised when an active task is aborted by user command or cancellation."""
    pass

class TaskConcurrencyError(TaskError):
    """Raised when attempting to start a task while another is already active."""
    pass
