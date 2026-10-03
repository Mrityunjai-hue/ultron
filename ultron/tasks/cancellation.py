"""
ULTRON V3 — Global Task Cancellation Manager
─────────────────────────────────────────────────────────────────────────────
Handles instant cancellation of active multi-step desktop tasks upon explicit
user commands ("Stop", "Cancel that", "Cancel the task").
Distinct from audio playback barge-in: aborts pending task steps while
preserving voice engine readiness.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import logging
from typing import Optional, Set

from ultron.tasks.errors import TaskCancelledError

logger = logging.getLogger("ultron.tasks.cancellation")

class TaskCancellationManager:
    """Manages cancellation tokens and abort signals for active tasks."""

    def __init__(self):
        self._cancelled_tasks: Set[str] = set()
        self._active_task_id: Optional[str] = None

    def register_active_task(self, task_id: str):
        """Sets current active task."""
        self._active_task_id = task_id

    def cancel_task(self, task_id: Optional[str] = None, reason: str = "User requested cancellation") -> bool:
        """
        Cancels the specified task or the currently active task.
        Returns True if a task was marked cancelled.
        """
        target_id = task_id or self._active_task_id
        if not target_id:
            logger.info("[Cancellation] No active task to cancel.")
            return False

        logger.info(f"[Cancellation] Aborting task '{target_id}' (Reason: {reason})")
        self._cancelled_tasks.add(target_id)
        return True

    def is_task_cancelled(self, task_id: str) -> bool:
        """Checks if a task has received a cancellation signal."""
        return task_id in self._cancelled_tasks

    def assert_not_cancelled(self, task_id: str):
        """Raises TaskCancelledError if task was cancelled."""
        if self.is_task_cancelled(task_id):
            raise TaskCancelledError(f"Task '{task_id}' was cancelled by user.", task_id=task_id)

    def clear_task(self, task_id: str):
        """Cleans up completed/failed/cancelled task tracking."""
        self._cancelled_tasks.discard(task_id)
        if self._active_task_id == task_id:
            self._active_task_id = None
