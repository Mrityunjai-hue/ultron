"""
ULTRON V3 — Core Events & Telemetry
─────────────────────────────────────────────────────────────────────────────
Defines engine states, event models, and an asynchronous event bus.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Any, Optional

class ActivityState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    RESPONDING = "RESPONDING"
    INTERRUPTED = "INTERRUPTED"
    OFFLINE = "OFFLINE"

@dataclass
class EngineEvent:
    state: ActivityState
    operation: str = "none"
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)

class EventBus:
    """Lightweight in-memory event distributor."""
    
    def __init__(self):
        self._subscribers: List[Callable[[EngineEvent], None]] = []

    def subscribe(self, callback: Callable[[EngineEvent], None]):
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[EngineEvent], None]):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def publish(self, event: EngineEvent):
        for cb in self._subscribers:
            try:
                cb(event)
            except Exception:
                pass
