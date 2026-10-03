"""
ULTRON V3 — Task State Enumerations & Definitions
─────────────────────────────────────────────────────────────────────────────
Defines authoritative lifecycle states for multi-step agent tasks.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
from enum import Enum

class TaskState(str, Enum):
    TASK_RECEIVED = "TASK_RECEIVED"
    TASK_PLANNING = "TASK_PLANNING"
    TASK_READY = "TASK_READY"
    TASK_EXECUTING = "TASK_EXECUTING"
    TASK_VERIFYING = "TASK_VERIFYING"
    TASK_WAITING_CONFIRMATION = "TASK_WAITING_CONFIRMATION"
    TASK_PAUSED = "TASK_PAUSED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_CANCELLED = "TASK_CANCELLED"

class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"

