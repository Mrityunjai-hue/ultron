"""
ULTRON V3 — Task Durability & Atomic Persistence Layer
─────────────────────────────────────────────────────────────────────────────
Provides atomic, checksum-verified, crash-resilient disk persistence for
long-running goals, execution plans, checkpoints, and evidence chains.
Strictly quarantines corrupted states and strips sensitive secrets.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import copy
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("ultron.tasks.persistence")

# Secret scrubbing patterns
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|password|secret|token|auth[_-]?header|bearer\s+[a-zA-Z0-9_\-\.]{15,})"),
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),  # Google API keys
    re.compile(r"ghp_[0-9a-zA-Z]{36}"),     # GitHub tokens
]


SECRET_KEY_PATTERN = re.compile(r"(?i)(api[_-]?key|password|secret|token|auth[_-]?header|bearer|private[_-]?key|access[_-]?key)")


class CorruptedStateError(Exception):
    """Raised when persisted task state fails integrity or checksum validation."""
    pass


def scrub_secrets(val: Any) -> Any:
    """Recursively redacts API keys, tokens, and authorization headers."""
    if isinstance(val, str):
        for pat in SECRET_PATTERNS:
            if pat.search(val):
                return "[REDACTED_SECRET]"
        return val
    elif isinstance(val, dict):
        sanitized = {}
        for k, v in val.items():
            if SECRET_KEY_PATTERN.search(str(k)):
                sanitized[k] = "[REDACTED_SECRET]"
            else:
                sanitized[k] = scrub_secrets(v)
        return sanitized
    elif isinstance(val, list):
        return [scrub_secrets(item) for item in val]
    elif is_dataclass(val):
        return scrub_secrets(asdict(val))
    return val



def compute_checksum(data: Dict[str, Any]) -> str:
    """Computes deterministic SHA256 checksum for a data dictionary."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class TaskPersistenceManager:
    """Manages atomic disk persistence and recovery of active goals and plans."""

    def __init__(self, workspace_root: Path | str):
        self.workspace_root = Path(workspace_root).resolve()
        self.storage_dir = self.workspace_root / ".ultron_tasks"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_goal_file(self, goal_id: str) -> Path:
        clean_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", goal_id)
        return self.storage_dir / f"goal_{clean_id}.json"

    def persist_goal_state(
        self,
        goal_id: str,
        goal_data: Dict[str, Any],
        plan_data: Optional[Dict[str, Any]] = None,
        context_data: Optional[Dict[str, Any]] = None,
        evidence_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Path:
        """
        Atomically saves goal execution state to disk with checksum verification.
        Uses a temporary file and atomic replace to prevent corrupted half-writes.
        """
        target_file = self._get_goal_file(goal_id)
        tmp_file = self.storage_dir / f"tmp_{target_file.name}.{int(time.time() * 1000)}"

        # Strip any secrets before saving
        safe_goal = scrub_secrets(goal_data)
        safe_plan = scrub_secrets(plan_data) if plan_data else None
        safe_context = scrub_secrets(context_data) if context_data else None
        safe_evidence = scrub_secrets(evidence_data) if evidence_data else []

        payload = {
            "goal_id": goal_id,
            "timestamp": time.time(),
            "goal": safe_goal,
            "plan": safe_plan,
            "context": safe_context,
            "evidence": safe_evidence,
        }

        checksum = compute_checksum(payload)
        envelope = {
            "version": 1,
            "checksum": checksum,
            "payload": payload,
        }

        # Write to temp file and atomically replace
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(envelope, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_file, target_file)
            logger.debug(f"[Persistence] Atomically persisted goal '{goal_id}' to {target_file.name}")
            return target_file
        except Exception as err:
            logger.error(f"[Persistence] Failed to persist goal '{goal_id}': {err}")
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except Exception:
                    pass
            raise

    def load_goal_state(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads and validates a persisted goal state. Quarantines corrupted files.
        """
        target_file = self._get_goal_file(goal_id)
        if not target_file.exists():
            return None

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                envelope = json.load(f)

            if not isinstance(envelope, dict) or "checksum" not in envelope or "payload" not in envelope:
                raise CorruptedStateError("Malformed persistence envelope missing checksum or payload.")

            expected_checksum = envelope["checksum"]
            payload = envelope["payload"]
            actual_checksum = compute_checksum(payload)

            if expected_checksum != actual_checksum:
                raise CorruptedStateError(f"Checksum mismatch: expected {expected_checksum}, calculated {actual_checksum}.")

            return payload

        except (json.JSONDecodeError, CorruptedStateError, KeyError, Exception) as err:
            logger.error(f"[Persistence] Corrupted state detected for goal '{goal_id}': {err}. Quarantining file.")
            self._quarantine_file(target_file, reason=str(err))
            return None

    def _quarantine_file(self, target_file: Path, reason: str = ""):
        """Renames a corrupted state file to prevent unhandled crash loops."""
        try:
            quarantine_path = target_file.with_name(f"{target_file.name}.corrupted_{int(time.time())}")
            os.replace(target_file, quarantine_path)
            logger.warning(f"[Persistence] Quarantined corrupted state file to {quarantine_path.name} (Reason: {reason})")
        except Exception as e:
            logger.error(f"[Persistence] Failed to quarantine file {target_file}: {e}")


    def list_persisted_goals(self) -> List[str]:
        """Returns all valid persisted goal IDs present on disk."""
        goal_ids = []
        for p in self.storage_dir.glob("goal_*.json"):
            gid = p.stem.replace("goal_", "")
            goal_ids.append(gid)
        return goal_ids

    def delete_persisted_goal(self, goal_id: str) -> bool:
        """Removes persisted file when goal is completed or purged."""
        target_file = self._get_goal_file(goal_id)
        if target_file.exists():
            try:
                target_file.unlink()
                return True
            except Exception as err:
                logger.warning(f"[Persistence] Could not delete state file {target_file}: {err}")
        return False
