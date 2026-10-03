"""
ULTRON — Production Application Lifecycle State Machine
─────────────────────────────────────────────────────────────────────────────
Formal state management governing system transitions from boot to shutdown:
STARTING → INITIALIZING → READY ↔ RUNNING ↔ RECOVERING → STOPPING → STOPPED
Guarantees clean state transitions and rejects invalid state hops.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import logging
import time
from enum import Enum
from typing import Dict, Set, Optional, Callable, List

logger = logging.getLogger("ultron.core.lifecycle")


class LifecycleState(str, Enum):
    STARTING = "STARTING"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    RECOVERING = "RECOVERING"
    FAILED = "FAILED"


VALID_TRANSITIONS: Dict[LifecycleState, Set[LifecycleState]] = {
    LifecycleState.STARTING: {LifecycleState.INITIALIZING, LifecycleState.FAILED, LifecycleState.STOPPING},
    LifecycleState.INITIALIZING: {LifecycleState.READY, LifecycleState.FAILED, LifecycleState.RECOVERING, LifecycleState.STOPPING},
    LifecycleState.READY: {LifecycleState.RUNNING, LifecycleState.STOPPING, LifecycleState.RECOVERING, LifecycleState.FAILED},
    LifecycleState.RUNNING: {LifecycleState.READY, LifecycleState.STOPPING, LifecycleState.RECOVERING, LifecycleState.FAILED},
    LifecycleState.RECOVERING: {LifecycleState.READY, LifecycleState.FAILED, LifecycleState.STOPPING},
    LifecycleState.STOPPING: {LifecycleState.STOPPED, LifecycleState.FAILED},
    LifecycleState.STOPPED: {LifecycleState.STARTING},
    LifecycleState.FAILED: {LifecycleState.RECOVERING, LifecycleState.STOPPING, LifecycleState.STOPPED, LifecycleState.STARTING},
}


class InvalidLifecycleTransitionError(Exception):
    """Raised when an illegal lifecycle state jump is attempted."""
    pass


class LifecycleManager:
    """Manages verified state transitions and lifecycle listeners."""

    def __init__(self, initial_state: LifecycleState = LifecycleState.STARTING):
        self._current_state = initial_state
        self._state_history: List[Dict[str, Any]] = [
            {"state": initial_state.value, "timestamp": time.time(), "reason": "Initial boot"}
        ]
        self._listeners: List[Callable[[LifecycleState, LifecycleState, Optional[str]], None]] = []

    @property
    def current_state(self) -> LifecycleState:
        return self._current_state

    def add_listener(self, callback: Callable[[LifecycleState, LifecycleState, Optional[str]], None]) -> None:
        self._listeners.append(callback)

    def can_transition_to(self, target: LifecycleState) -> bool:
        allowed = VALID_TRANSITIONS.get(self._current_state, set())
        return target in allowed

    def transition_to(self, target: LifecycleState, reason: Optional[str] = None) -> None:
        if target == self._current_state:
            return

        if not self.can_transition_to(target):
            err_msg = f"Illegal lifecycle transition: {self._current_state.value} -> {target.value} (Reason: {reason})"
            logger.error(f"[Lifecycle] {err_msg}")
            raise InvalidLifecycleTransitionError(err_msg)

        prev_state = self._current_state
        self._current_state = target
        self._state_history.append({"state": target.value, "timestamp": time.time(), "reason": reason or ""})

        logger.info(f"[Lifecycle] State transition: {prev_state.value} -> {target.value} ({reason or 'no reason specified'})")

        for listener in self._listeners:
            try:
                listener(prev_state, target, reason)
            except Exception as ex:
                logger.error(f"[Lifecycle] Error in state transition listener: {ex}")

    def is_active(self) -> bool:
        return self._current_state in (LifecycleState.READY, LifecycleState.RUNNING, LifecycleState.RECOVERING)

    def is_terminal(self) -> bool:
        return self._current_state in (LifecycleState.STOPPED, LifecycleState.FAILED)

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._state_history)
