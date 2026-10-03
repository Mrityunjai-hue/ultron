"""
ULTRON Task Execution Supervisor v2.0
─────────────────────────────────────────────────────────────────────────────
Execution Supervisor & Bookkeeper (NOT an independent planner brain).
Architectural Rule: Native LLM tool calling is the sole decision maker.
TaskPlanner enforces:
- Max execution step limits (default: 6 steps to prevent runaway loops)
- Task cancellation
- Progress bookkeeping (0.0 to 1.0)
- Execution history tracking
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import time
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger("ultron.brain.supervisor")

@dataclass
class ExecutionStep:
    step_number: int
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    success: bool = False
    duration_ms: float = 0.0
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

class TaskSupervisor:
    """
    Supervises tool-calling execution sequences initiated by the LLM.
    Guards against runaway loops, tracks progress, and manages cancellation.
    """

    def __init__(self, max_steps: int = 6):
        self.max_steps = max_steps
        self.steps: List[ExecutionStep] = []
        self._is_cancelled: bool = False
        self.started_at: float = 0.0

    def start_task(self):
        """Initializes a new supervised task."""
        self.steps.clear()
        self._is_cancelled = False
        self.started_at = time.time()

    def cancel(self):
        """Flags the current task execution as cancelled."""
        self._is_cancelled = True
        logger.info("Task execution supervisor received cancellation signal.")

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled

    @property
    def current_step(self) -> int:
        return len(self.steps)

    @property
    def progress(self) -> float:
        """Returns normalized progress between 0.0 and 1.0."""
        if not self.steps:
            return 0.0
        return min(len(self.steps) / self.max_steps, 1.0)

    def can_proceed(self) -> bool:
        """Checks if another tool step is permitted under safety limits."""
        if self._is_cancelled:
            logger.warning("Task execution aborted: Cancellation requested.")
            return False
        if len(self.steps) >= self.max_steps:
            logger.warning(f"Task execution halted: Exceeded maximum step limit ({self.max_steps}).")
            return False
        return True

    def record_step(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Optional[Any] = None,
        success: bool = True,
        duration_ms: float = 0.0,
        error: Optional[str] = None,
    ) -> ExecutionStep:
        """Logs a completed tool execution step."""
        step = ExecutionStep(
            step_number=len(self.steps) + 1,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            success=success,
            duration_ms=duration_ms,
            error=error,
        )
        self.steps.append(step)
        return step

    def get_summary(self) -> Dict[str, Any]:
        """Provides execution audit summary."""
        total_time = (time.time() - self.started_at) if self.started_at else 0.0
        return {
            "total_steps": len(self.steps),
            "max_steps": self.max_steps,
            "is_cancelled": self._is_cancelled,
            "duration_seconds": round(total_time, 2),
            "steps": [
                {
                    "step": s.step_number,
                    "tool": s.tool_name,
                    "success": s.success,
                    "duration_ms": round(s.duration_ms, 1),
                    "error": s.error,
                }
                for s in self.steps
            ],
        }
