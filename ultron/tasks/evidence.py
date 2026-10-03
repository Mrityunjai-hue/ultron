"""
ULTRON V3 — Evidence Chain & Goal Completion Verification
─────────────────────────────────────────────────────────────────────────────
Tracks verifiable empirical evidence for all completed steps and validates
that final goal outcomes are backed by tangible evidence on disk or in state.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import hashlib
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from ultron.tasks.persistence import scrub_secrets


@dataclass
class EvidenceRecord:
    """Empirical evidence artifact for an individual executed step."""
    record_id: str
    timestamp: float
    action: str
    arguments: Dict[str, Any]
    observation: Dict[str, Any]
    verification_method: str
    verified: bool
    evidence_data: Dict[str, Any]
    goal_id: Optional[str] = None
    plan_version: int = 1
    step_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceChain:
    """Maintains an ordered, auditable chain of evidence for goal completion."""

    def __init__(self, workspace_root: Path | str):
        self.workspace_root = Path(workspace_root).resolve()
        self._records: List[EvidenceRecord] = []

    def record_step_evidence(
        self,
        action: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        verification_method: str = "empirical_check",
        verified: bool = True,
        goal_id: Optional[str] = None,
        plan_version: int = 1,
        step_id: Optional[str] = None,
        capability: Optional[str] = None,
        execution_result: Optional[Dict[str, Any]] = None,
        verification: Optional[Any] = None,
    ) -> EvidenceRecord:
        """Constructs and stores an evidence record from a verified step execution."""
        rec_id = f"evd-{len(self._records) + 1:03d}"
        now = time.time()

        eff_action = capability or action or "unknown_action"
        eff_args = arguments or {}
        eff_res = execution_result if execution_result is not None else (result or {})

        v_method = verification_method
        v_verified = verified
        if verification is not None:
            if hasattr(verification, "method"):
                v_method = verification.method
            if hasattr(verification, "verified"):
                v_verified = verification.verified

        evidence_data: Dict[str, Any] = {}

        # 1. File artifacts evidence
        path_candidate = eff_res.get("saved_to") or eff_res.get("path") or eff_args.get("path") or eff_args.get("destination")
        if path_candidate:
            try:
                p = Path(path_candidate)
                if not p.is_absolute():
                    p = (self.workspace_root / p).resolve()
                if p.exists() and p.is_file():
                    evidence_data["file_path"] = str(p.relative_to(self.workspace_root)) if p.is_relative_to(self.workspace_root) else str(p)
                    evidence_data["file_size_bytes"] = p.stat().st_size
                    evidence_data["mtime"] = p.stat().st_mtime
                    # Compute fast content hash for small files
                    if p.stat().st_size < 1_000_000:
                        evidence_data["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
                elif p.exists() and p.is_dir():
                    evidence_data["directory_path"] = str(p.relative_to(self.workspace_root)) if p.is_relative_to(self.workspace_root) else str(p)
                    evidence_data["is_dir"] = True
            except Exception:
                pass

        # 2. Browser artifacts evidence
        if "url" in eff_res or "current_url" in eff_res or "destination_url" in eff_res:
            evidence_data["url"] = eff_res.get("destination_url") or eff_res.get("current_url") or eff_res.get("url")
            evidence_data["title"] = eff_res.get("new_title") or eff_res.get("title")

        if "query" in eff_res:
            evidence_data["search_query"] = eff_res.get("query")

        # 3. System / App artifacts evidence
        if "active_app" in eff_res:
            evidence_data["active_app"] = eff_res.get("active_app")

        record = EvidenceRecord(
            record_id=rec_id,
            timestamp=now,
            action=eff_action,
            arguments=scrub_secrets(eff_args),
            observation=scrub_secrets(eff_res),
            verification_method=v_method,
            verified=v_verified,
            evidence_data=evidence_data,
            goal_id=goal_id,
            plan_version=plan_version,
            step_id=step_id,
        )
        self._records.append(record)
        return record

    def list_records(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._records]

    def get_goal_evidence(self, goal_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns evidence records belonging to a goal (or all if goal_id is None)."""
        if not goal_id:
            return self.list_records()
        return [r.to_dict() for r in self._records if r.goal_id == goal_id or r.goal_id is None]

    def verify_goal_outcome(
        self,
        goal_or_target: Any = None,
        context_or_min_size: Any = None,
        min_size: int = 1,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validates that the final goal is backed by concrete empirical evidence.
        Supports both (goal, context) and (target_file, min_size) invocations.
        """
        target_file = None
        min_file_size = min_size

        # If goal object was passed
        if goal_or_target is not None and hasattr(goal_or_target, "desired_outcome"):
            outcome = goal_or_target.desired_outcome
            if outcome and hasattr(outcome, "target_file") and outcome.target_file:
                target_file = outcome.target_file
                min_file_size = getattr(outcome, "min_file_size_bytes", 1)
        elif isinstance(goal_or_target, (str, Path)):
            target_file = str(goal_or_target)
            if isinstance(context_or_min_size, int):
                min_file_size = context_or_min_size

        if not target_file:
            return True, {"verified": True, "message": "No specific file outcome specified.", "records_count": len(self._records)}

        target_p = Path(target_file)
        if not target_p.is_absolute():
            target_p = (self.workspace_root / target_p).resolve()

        if not target_p.exists():
            return False, {"verified": False, "error": f"Target file '{target_p}' does not exist on disk."}

        file_size = target_p.stat().st_size
        if file_size < min_file_size:
            return False, {
                "verified": False,
                "error": f"Target file '{target_p}' size ({file_size} bytes) is below required minimum ({min_file_size} bytes).",
            }

        evidence_summary = {
            "path": str(target_p),
            "size_bytes": file_size,
            "mtime": target_p.stat().st_mtime,
            "verified": True,
            "records_count": len(self._records),
        }
        return True, evidence_summary

