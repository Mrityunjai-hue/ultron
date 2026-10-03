"""
ULTRON V3 — Bounded Task Execution Journal
─────────────────────────────────────────────────────────────────────────────
Maintains an immutable, bounded lifecycle audit log for all goal planning,
step executions, verifications, retries, dynamic replans, and confirmations.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional

from ultron.tasks.persistence import scrub_secrets

logger = logging.getLogger("ultron.tasks.journal")

MAX_JOURNAL_ENTRIES = 500


class JournalEventType(str, Enum):
    """Authoritative lifecycle journal event types."""
    TASK_CREATED = "TASK_CREATED"
    PLAN_CREATED = "PLAN_CREATED"
    STEP_STARTED = "STEP_STARTED"
    STEP_COMPLETED = "STEP_COMPLETED"
    STEP_VERIFIED = "STEP_VERIFIED"
    STEP_FAILED = "STEP_FAILED"
    RETRY_STARTED = "RETRY_STARTED"
    REPLAN_STARTED = "REPLAN_STARTED"
    REPLAN_COMPLETED = "REPLAN_COMPLETED"
    CONFIRMATION_REQUESTED = "CONFIRMATION_REQUESTED"
    CONFIRMATION_APPROVED = "CONFIRMATION_APPROVED"
    CONFIRMATION_REJECTED = "CONFIRMATION_REJECTED"
    TASK_PAUSED = "TASK_PAUSED"
    TASK_RESUMED = "TASK_RESUMED"
    TASK_CANCELLED = "TASK_CANCELLED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"


@dataclass
class JournalEntry:
    """Individual structured journal log record."""
    entry_id: str
    timestamp: float
    event_type: str
    goal_id: str
    task_id: Optional[str] = None
    plan_id: Optional[str] = None
    plan_version: int = 1
    step_id: Optional[str] = None
    capability: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TaskJournal:
    """Manages bounded in-memory and persistent journal auditing."""

    def __init__(self, workspace_root: Optional[Path | str] = None, max_entries: int = MAX_JOURNAL_ENTRIES):
        self.max_entries = max_entries
        self._entries: List[JournalEntry] = []
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None
        self.log_file = (self.workspace_root / ".ultron_tasks" / "journal.jsonl") if self.workspace_root else None

        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        event_type: JournalEventType | str,
        goal_id: Optional[str] = None,
        task_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        plan_version: int = 1,
        step_id: Optional[str] = None,
        capability: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> JournalEntry:
        """Appends a new secret-scrubbed lifecycle event to the journal."""
        eid = f"jrn-{uuid.uuid4().hex[:6]}"
        evt_str = event_type.value if isinstance(event_type, JournalEventType) else str(event_type)
        safe_meta = scrub_secrets(metadata or {})
        effective_goal = goal_id or task_id or "unknown"
        effective_task = task_id or goal_id or "unknown"

        entry = JournalEntry(
            entry_id=eid,
            timestamp=time.time(),
            event_type=evt_str,
            goal_id=effective_goal,
            task_id=effective_task,
            plan_id=plan_id,
            plan_version=plan_version,
            step_id=step_id,
            capability=capability,
            metadata=safe_meta,
        )

        if len(self._entries) >= self.max_entries:
            self._entries.pop(0)

        self._entries.append(entry)

        # Append to persistent JSONL log
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry.to_dict()) + "\n")
            except Exception as err:
                logger.warning(f"[Journal] Failed to append to log file: {err}")

        logger.debug(f"[Journal] {evt_str} | Goal: {goal_id} | Step: {step_id or '-'}")
        return entry

    def get_events_for_goal(self, goal_id: str) -> List[Dict[str, Any]]:
        """Returns all recorded journal entries matching a goal ID."""
        return [e.to_dict() for e in self._entries if e.goal_id == goal_id or e.task_id == goal_id]

    def get_entries_for_goal(self, goal_id: str) -> List[Dict[str, Any]]:
        """Alias for get_events_for_goal."""
        return self.get_events_for_goal(goal_id)

    def list_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent N journal events."""
        return [e.to_dict() for e in self._entries[-limit:]]

    def list_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Alias for list_recent_events."""
        return self.list_recent_events(limit)

    def count(self) -> int:
        return len(self._entries)

    def clear(self):
        self._entries.clear()

