"""
ULTRON V3 — Cryptographic Confirmation Security Gateway
─────────────────────────────────────────────────────────────────────────────
Maintains local authoritative pending confirmation state for destructive actions.
Prevents cloud LLM from manufacturing or spoofing confirmation states.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple

@dataclass
class PendingConfirmation:
    token: str
    tool_name: str
    target: str
    arguments: Dict[str, Any]
    session_id: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    consumed: bool = False

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

class ConfirmationManager:
    """Authoritative local gatekeeper for high-risk and state-changing actions."""

    def __init__(self, default_ttl_sec: float = 60.0):
        self.default_ttl_sec = default_ttl_sec
        self._pending: Dict[str, PendingConfirmation] = {}

    def _extract_target(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Extracts and normalizes the target entity of an operation."""
        clean = {k: v for k, v in arguments.items() if k not in ("token", "confirmation_token", "confirmed", "confirm")}
        if tool_name in ("write_file", "delete_file", "read_file"):
            return str(clean.get("path", "")).strip().lower().replace("/", "\\")
        elif tool_name in ("close_app", "open_app", "windows_close_app", "windows_open_app"):
            return str(clean.get("app_name", "")).strip().lower().replace(".exe", "")
        elif tool_name == "chrome_download_file":
            url_val = str(clean.get("url", "")).strip()
            dest_val = str(clean.get("destination", "")).strip()
            return f"{url_val}->{dest_val}".lower()
        elif tool_name == "chrome_close":
            return "chrome"
        return str(clean)

    def create_pending_confirmation(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        session_id: str = "default",
        ttl_sec: Optional[float] = None,
    ) -> PendingConfirmation:
        """
        Registers an explicit local confirmation requirement.
        Generates a short-lived, single-use cryptographic token.
        """
        self.clear_expired()
        token = f"conf-{uuid.uuid4().hex[:12]}"
        ttl = ttl_sec or self.default_ttl_sec
        target = self._extract_target(tool_name, arguments)

        # Store safe copy of arguments without token
        clean_args = {k: v for k, v in arguments.items() if k not in ("token", "confirmation_token", "confirmed", "confirm")}

        pending = PendingConfirmation(
            token=token,
            tool_name=tool_name,
            target=target,
            arguments=clean_args,
            session_id=session_id,
            created_at=time.time(),
            expires_at=time.time() + ttl,
            consumed=False,
        )
        self._pending[token] = pending
        return pending

    def validate_and_consume(
        self,
        token: Optional[str],
        tool_name: str,
        arguments: Dict[str, Any],
        session_id: str = "default",
    ) -> Tuple[bool, str]:
        """
        Authoritatively verifies whether the exact action was confirmed locally.
        Immediately invalidates and consumes the token upon verification.
        """
        if not token or not isinstance(token, str):
            return False, "Action requires a valid confirmation token."

        token = token.strip()
        pending = self._pending.get(token)

        if not pending:
            return False, "Invalid or unauthorized confirmation token."

        if pending.consumed:
            return False, "Confirmation token has already been consumed."

        if pending.is_expired():
            del self._pending[token]
            return False, "Confirmation token has expired."

        if pending.session_id != session_id:
            return False, "Confirmation token session mismatch."

        if pending.tool_name != tool_name:
            return False, f"Token was issued for tool '{pending.tool_name}', not '{tool_name}'."

        current_target = self._extract_target(tool_name, arguments)
        if pending.target != current_target:
            return False, f"Token was issued for target '{pending.target}', not '{current_target}'."

        # Mark consumed and purge immediately (single-use guarantee)
        pending.consumed = True
        del self._pending[token]
        self.clear_expired()
        return True, "Confirmation token verified and consumed successfully."

    def dismiss(self, token: str) -> bool:
        """Explicitly dismisses/rejects a pending confirmation."""
        return self._pending.pop(token.strip(), None) is not None

    def get_pending(self, token: str) -> Optional[PendingConfirmation]:
        """Retrieves a pending confirmation object if still active."""
        self.clear_expired()
        return self._pending.get(token.strip())

    def clear_expired(self):
        """Purges stale pending confirmations."""
        now = time.time()
        expired_keys = [k for k, v in self._pending.items() if now > v.expires_at or v.consumed]
        for k in expired_keys:
            self._pending.pop(k, None)

    def get_pending_count(self) -> int:
        self.clear_expired()
        return len(self._pending)
