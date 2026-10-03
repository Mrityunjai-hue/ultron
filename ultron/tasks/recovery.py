"""
ULTRON V3 — Failure Classification & Recovery Engine
─────────────────────────────────────────────────────────────────────────────
Classifies execution faults and verification failures into deterministic categories
and determines the authoritative recovery strategy (retry, replan, pause, or fail).
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
from enum import Enum
from typing import Optional, Tuple, Dict, Any

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ultron.tasks.plan import PlanStep
    from ultron.tasks.models import VerificationResult


class FailureClassification(str, Enum):
    """Categorization of an execution or verification fault."""
    TRANSIENT = "TRANSIENT"                       # Temporary glitch (network timeout, busy lock)
    RECOVERABLE = "RECOVERABLE"                   # Actionable mismatch (link 404, alternative route exists)
    USER_ACTION_REQUIRED = "USER_ACTION_REQUIRED" # User intervention needed (confirmation, clarification)
    UNSUPPORTED = "UNSUPPORTED"                   # Requested tool or capability unavailable
    SAFETY_BLOCKED = "SAFETY_BLOCKED"             # Security policy violation (hard block, no bypass)
    FATAL = "FATAL"                               # Unrecoverable substrate or runtime fault


class RecoveryStrategy(str, Enum):
    """Action to take based on the classified failure."""
    RETRY_STEP = "RETRY_STEP"
    DYNAMIC_REPLAN = "DYNAMIC_REPLAN"
    ASK_USER_CONFIRMATION = "ASK_USER_CONFIRMATION"
    ASK_USER_CLARIFICATION = "ASK_USER_CLARIFICATION"
    EXPLAIN_LIMITATION = "EXPLAIN_LIMITATION"
    FAIL_GOAL = "FAIL_GOAL"


class FailureClassifier:
    """Classifies execution results and determines recovery strategies."""

    @staticmethod
    def classify(
        error_msg: str,
        tool_name: str = "",
        status: Optional[str] = None,
        verification: Optional[VerificationResult] = None,
        retries_attempted: int = 0,
        max_retries: int = 2,
    ) -> Tuple[FailureClassification, RecoveryStrategy]:
        """
        Classifies an error message / status and maps it to a recovery strategy.
        """
        err_lower = str(error_msg or "").lower()
        status_upper = str(status or "").upper()

        # 1. User Confirmation Needed
        if status_upper == "CONFIRM_REQUIRED" or "requires explicit" in err_lower or "confirmation required" in err_lower:
            return FailureClassification.USER_ACTION_REQUIRED, RecoveryStrategy.ASK_USER_CONFIRMATION

        if status_upper == "CONFIRMATION_INVALID" or "token expired" in err_lower or "invalid confirmation" in err_lower:
            return FailureClassification.USER_ACTION_REQUIRED, RecoveryStrategy.ASK_USER_CONFIRMATION

        # 2. Safety Policy Block (Never bypassable or replannable)
        if (
            status_upper == "BLOCKED"
            or "security policy" in err_lower
            or "blocked" in err_lower
            or "prohibited" in err_lower
            or "escapes workspace" in err_lower
            or "executable extension" in err_lower
            or "system directory" in err_lower
        ):
            return FailureClassification.SAFETY_BLOCKED, RecoveryStrategy.FAIL_GOAL

        # 3. Unsupported Capability
        if (
            "not registered" in err_lower
            or "unsupported capability" in err_lower
            or "not supported" in err_lower
            or "unknown tool" in err_lower
        ):
            return FailureClassification.UNSUPPORTED, RecoveryStrategy.EXPLAIN_LIMITATION

        # 4. Transient Failures (Timeouts, network hiccups)
        if (
            "timeout" in err_lower
            or "timed out" in err_lower
            or "connection reset" in err_lower
            or "temporarily unavailable" in err_lower
            or "rate limit" in err_lower
        ):
            if retries_attempted < max_retries:
                return FailureClassification.TRANSIENT, RecoveryStrategy.RETRY_STEP
            else:
                # Retries exhausted -> attempt dynamic replan
                return FailureClassification.RECOVERABLE, RecoveryStrategy.DYNAMIC_REPLAN

        # 5. Recoverable Route / Page Mismatches
        if (
            "not found" in err_lower
            or "404" in err_lower
            or "missing" in err_lower
            or "no matching" in err_lower
            or "differed" in err_lower
            or "navigated to" in err_lower
            or "empty" in err_lower
        ):
            return FailureClassification.RECOVERABLE, RecoveryStrategy.DYNAMIC_REPLAN

        # 6. Verification Failures
        if verification and not verification.verified:
            verif_err = str(verification.error_message or "").lower()
            if "blocked" in verif_err:
                return FailureClassification.SAFETY_BLOCKED, RecoveryStrategy.FAIL_GOAL
            if retries_attempted < max_retries and "timeout" in verif_err:
                return FailureClassification.TRANSIENT, RecoveryStrategy.RETRY_STEP
            return FailureClassification.RECOVERABLE, RecoveryStrategy.DYNAMIC_REPLAN

        # Default fallback
        if retries_attempted < max_retries:
            return FailureClassification.TRANSIENT, RecoveryStrategy.RETRY_STEP
        return FailureClassification.RECOVERABLE, RecoveryStrategy.DYNAMIC_REPLAN
