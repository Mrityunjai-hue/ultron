"""
ULTRON V3 — Task Context, Intermediate Key Passing & Checkpoint Store
─────────────────────────────────────────────────────────────────────────────
Maintains bounded intermediate variables, environmental observations,
secret-scrubbed context state, and lightweight recovery checkpoints.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import copy
import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set

MAX_VARIABLES = 50
MAX_CHECKPOINTS = 10
MAX_HISTORY_ITEMS = 25
MAX_STRING_VAL_LEN = 10000

# Secret scrubbing patterns
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|password|secret|token|auth[_-]?header|bearer\s+[a-zA-Z0-9_\-\.]{15,})"),
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),  # Google API keys
    re.compile(r"ghp_[0-9a-zA-Z]{36}"),     # GitHub tokens
]


@dataclass
class Checkpoint:
    """Snapshot of execution progress at a verified milestone."""
    checkpoint_id: str
    timestamp: float
    completed_step_ids: List[str]
    variables: Dict[str, Any]
    plan_version: int
    observed_state: Dict[str, Any]
    integrity_hash: str = ""

    def __post_init__(self):
        if not self.integrity_hash:
            self.integrity_hash = self.compute_integrity_hash()

    def compute_integrity_hash(self) -> str:
        payload = f"{self.checkpoint_id}:{self.timestamp}:{sorted(self.completed_step_ids)}:{self.plan_version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def is_valid(self) -> bool:
        if not self.checkpoint_id or self.plan_version < 1:
            return False
        return self.integrity_hash == self.compute_integrity_hash()



class TaskContext:
    """Authoritative, bounded runtime context for goal planning and execution."""

    def __init__(self, goal_id: str):
        self.goal_id = goal_id
        self._variables: Dict[str, Any] = {}
        self._observations: Dict[str, Any] = {}
        self._checkpoints: List[Checkpoint] = []
        self._failure_history: List[Dict[str, Any]] = []
        self._replan_history: List[Dict[str, Any]] = []
        self.created_at: float = time.time()

    def set_variable(self, key: str, value: Any) -> None:
        """Stores a named intermediate result with security sanitization."""
        clean_key = str(key).strip().lstrip("$")
        if not clean_key:
            return

        sanitized_val = self._sanitize_value(value)
        if len(self._variables) >= MAX_VARIABLES and clean_key not in self._variables:
            # Evict oldest entry
            oldest_key = next(iter(self._variables))
            del self._variables[oldest_key]

        self._variables[clean_key] = sanitized_val

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Retrieves a stored intermediate variable."""
        clean_key = str(key).strip().lstrip("$")
        return self._variables.get(clean_key, default)

    def list_variables(self) -> Dict[str, Any]:
        """Returns a shallow copy of stored variables."""
        return copy.deepcopy(self._variables)

    def resolve_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Substitutes `$variable_name` or `{variable_name}` references in arguments
        with values previously populated in the TaskContext.
        """
        resolved: Dict[str, Any] = {}
        for k, v in arguments.items():
            resolved[k] = self._resolve_single_val(v)
        return resolved

    def _resolve_single_val(self, val: Any) -> Any:
        if isinstance(val, str):
            clean_s = val.strip()
            # Exact reference match e.g. "$pdf_url" or "$destination"
            if clean_s.startswith("$"):
                var_name = clean_s[1:]
                if var_name in self._variables:
                    return self._variables[var_name]

            # Formatted string match e.g. "Download to {filename}"
            matches = re.findall(r"\{([a-zA-Z0-9_]+)\}", clean_s)
            if matches:
                out_str = clean_s
                for var_name in matches:
                    if var_name in self._variables:
                        out_str = out_str.replace(f"{{{var_name}}}", str(self._variables[var_name]))
                return out_str
            return val

        elif isinstance(val, dict):
            return {k: self._resolve_single_val(item) for k, item in val.items()}

        elif isinstance(val, list):
            return [self._resolve_single_val(item) for item in val]

        return val

    def record_observation(self, key: str, value: Any) -> None:
        """Records an external environment state observation."""
        self._observations[key] = self._sanitize_value(value)

    def get_observation(self, key: str, default: Any = None) -> Any:
        return self._observations.get(key, default)

    def list_observations(self) -> Dict[str, Any]:
        return copy.deepcopy(self._observations)

    def create_checkpoint(
        self,
        completed_step_ids: List[str],
        plan_version: int,
        observed_state: Optional[Dict[str, Any]] = None,
    ) -> Checkpoint:
        """Creates and stores a recovery checkpoint."""
        cid = f"chk-{uuid.uuid4().hex[:6]}"
        state = copy.deepcopy(observed_state or self._observations)
        vars_snapshot = copy.deepcopy(self._variables)

        chk = Checkpoint(
            checkpoint_id=cid,
            timestamp=time.time(),
            completed_step_ids=list(completed_step_ids),
            variables=vars_snapshot,
            plan_version=plan_version,
            observed_state=state,
        )

        if len(self._checkpoints) >= MAX_CHECKPOINTS:
            self._checkpoints.pop(0)

        self._checkpoints.append(chk)
        return chk

    def get_latest_checkpoint(self) -> Optional[Checkpoint]:
        """Returns the most recent checkpoint if one exists."""
        if self._checkpoints:
            return self._checkpoints[-1]
        return None

    def restore_from_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Restores context variables and state from a checkpoint."""
        self._variables = copy.deepcopy(checkpoint.variables)
        self._observations.update(checkpoint.observed_state)

    def record_failure(self, step_id: str, error: str, failure_class: str) -> None:
        """Appends a failure event to bounded history."""
        if len(self._failure_history) >= MAX_HISTORY_ITEMS:
            self._failure_history.pop(0)
        self._failure_history.append({
            "step_id": step_id,
            "error": str(error),
            "failure_class": failure_class,
            "timestamp": time.time(),
        })

    def record_replan(self, from_version: int, to_version: int, reason: str) -> None:
        """Appends a replan iteration event to bounded history."""
        if len(self._replan_history) >= MAX_HISTORY_ITEMS:
            self._replan_history.pop(0)
        self._replan_history.append({
            "from_version": from_version,
            "to_version": to_version,
            "reason": reason,
            "timestamp": time.time(),
        })

    @property
    def replan_history(self) -> List[Dict[str, Any]]:
        return list(self._replan_history)

    @property
    def failure_history(self) -> List[Dict[str, Any]]:
        return list(self._failure_history)

    def _sanitize_value(self, val: Any) -> Any:
        if isinstance(val, str):
            # Limit length
            truncated = val[:MAX_STRING_VAL_LEN]
            # Scrub secrets
            for pat in SECRET_PATTERNS:
                if pat.search(truncated):
                    return "[REDACTED_SECRET]"
            return truncated
        elif isinstance(val, dict):
            return {k: self._sanitize_value(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [self._sanitize_value(v) for v in val]
        return val
