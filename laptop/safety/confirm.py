"""
ULTRON Safety Confirmation System v2.0
─────────────────────────────────────────────────────────────────────────────
Manages interactive confirmation requests for dangerous operations
(overwriting files, deleting files, executing arbitrary shell commands).
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import time
import uuid
import logging
from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass, field

logger = logging.getLogger("ultron.safety.confirm")

@dataclass
class PendingConfirmation:
    id: str
    tool_name: str
    description: str
    arguments: Dict[str, Any]
    action_callback: Optional[Callable[[], Any]] = None
    created_at: float = field(default_factory=time.time)
    timeout_seconds: float = 30.0

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.timeout_seconds

class ConfirmationManager:
    """Tracks and resolves pending safety confirmations."""

    def __init__(self):
        self._pending: Dict[str, PendingConfirmation] = {}

    def request_confirmation(
        self,
        tool_name: str,
        description: str,
        arguments: Dict[str, Any],
        action_callback: Optional[Callable[[], Any]] = None,
        timeout_seconds: float = 30.0,
    ) -> PendingConfirmation:
        """Creates and stores a pending confirmation request."""
        # Purge expired requests
        self.cleanup_expired()

        confirm_id = str(uuid.uuid4())[:8]
        req = PendingConfirmation(
            id=confirm_id,
            tool_name=tool_name,
            description=description,
            arguments=arguments,
            action_callback=action_callback,
            timeout_seconds=timeout_seconds,
        )
        self._pending[confirm_id] = req
        logger.info(f"Confirmation requested [{confirm_id}]: {description}")
        return req

    def get_pending(self, confirm_id: str) -> Optional[PendingConfirmation]:
        """Retrieves a pending confirmation if valid and not expired."""
        req = self._pending.get(confirm_id)
        if req and req.is_expired:
            del self._pending[confirm_id]
            return None
        return req

    def get_latest_pending(self) -> Optional[PendingConfirmation]:
        """Gets the most recently requested pending confirmation."""
        self.cleanup_expired()
        if not self._pending:
            return None
        # Return newest by created_at
        return max(self._pending.values(), key=lambda r: r.created_at)

    async def resolve(self, confirm_id: str, approved: bool) -> Dict[str, Any]:
        """
        Resolves a pending confirmation.
        If approved and a callback is attached, executes it.
        """
        req = self._pending.pop(confirm_id, None)
        if not req:
            return {"success": False, "error": "Confirmation request not found or expired."}

        if req.is_expired:
            return {"success": False, "error": "Confirmation request timed out."}

        if not approved:
            logger.info(f"Confirmation [{confirm_id}] denied by user.")
            return {
                "success": False,
                "approved": False,
                "message": f"Action '{req.tool_name}' was declined by user.",
            }

        logger.info(f"Confirmation [{confirm_id}] approved by user. Executing action.")
        result = None
        if req.action_callback:
            try:
                import inspect
                if inspect.iscoroutinefunction(req.action_callback):
                    result = await req.action_callback()
                else:
                    result = req.action_callback()
            except Exception as e:
                logger.error(f"Error executing confirmed action: {e}")
                return {"success": False, "error": str(e)}

        return {
            "success": True,
            "approved": True,
            "tool_name": req.tool_name,
            "result": result,
            "message": f"Action '{req.tool_name}' confirmed and executed successfully.",
        }

    def cleanup_expired(self):
        """Removes all expired confirmations."""
        expired_ids = [cid for cid, r in self._pending.items() if r.is_expired]
        for cid in expired_ids:
            del self._pending[cid]
