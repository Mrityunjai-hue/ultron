"""
ULTRON Safety Audit Logger v2.0
─────────────────────────────────────────────────────────────────────────────
Immutable append-only JSONL log of all tool executions, safety verdicts,
and policy overrides.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger("ultron.safety.audit")

DEFAULT_LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "audit.log"

class AuditLogger:
    """Appends structured audit entries for every tool call and safety assessment."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or DEFAULT_LOG_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        verdict: str,
        user: Optional[str] = None,
        success: bool = True,
        duration_ms: float = 0.0,
        result_summary: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Appends an immutable audit event entry."""
        entry = {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "user": user or "ANONYMOUS",
            "tool_name": tool_name,
            "arguments": arguments,
            "verdict": verdict,
            "success": success,
            "duration_ms": round(duration_ms, 2),
            "result_summary": result_summary,
            "error": error,
        }

        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed writing safety audit entry: {e}")

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves recent audit log entries in reverse chronological order."""
        if not self.log_path.exists():
            return []

        entries = []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"Failed reading safety audit entries: {e}")

        return entries[-limit:][::-1]
