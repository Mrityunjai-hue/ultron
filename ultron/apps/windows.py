"""
ULTRON V3 — Conservative Windows Desktop Application Adapter
─────────────────────────────────────────────────────────────────────────────
Provides safe, structured awareness of running desktop applications and active
windows without exposing arbitrary coordinate clicking or global keyboard injection.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from ultron.apps.base import ApplicationAdapter
from ultron.apps.errors import CapabilityNotSupportedError
from ultron.desktop.system import (
    get_active_app,
    get_running_apps,
    enumerate_windows,
    open_application,
    close_application,
)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ultron.tasks.models import VerificationResult

logger = logging.getLogger("ultron.apps.windows")

class WindowsAppAdapter(ApplicationAdapter):
    """Conservative desktop adapter for safe window and process management on Windows."""

    def __init__(self, workspace_root: Path | str):
        self.workspace_root = Path(workspace_root).resolve()

    @property
    def app_id(self) -> str:
        return "windows"

    @property
    def display_name(self) -> str:
        return "Windows Desktop"

    def is_available(self) -> bool:
        return True

    def is_running(self) -> bool:
        return True

    def get_active_window(self) -> Dict[str, Any]:
        return get_active_app()

    def capabilities(self) -> Dict[str, Dict[str, Any]]:
        return {
            "windows_get_active_window": {
                "description": "Returns details about the current foreground window on Windows desktop.",
                "safety_class": "SAFE",
                "requires_confirmation": False,
                "timeout_sec": 5.0,
            },
            "windows_enumerate_windows": {
                "description": "Lists visible open application windows on the desktop.",
                "safety_class": "SAFE",
                "requires_confirmation": False,
                "timeout_sec": 8.0,
            },
            "windows_get_running_apps": {
                "description": "Lists active desktop processes.",
                "safety_class": "SAFE",
                "requires_confirmation": False,
                "timeout_sec": 8.0,
            },
            "windows_open_app": {
                "description": "Launches a supported desktop application.",
                "safety_class": "SAFE",
                "requires_confirmation": False,
                "timeout_sec": 15.0,
            },
            "windows_close_app": {
                "description": "Closes a running desktop application with confirmation.",
                "safety_class": "CONFIRM_REQUIRED",
                "requires_confirmation": True,
                "timeout_sec": 10.0,
            },
        }

    async def execute_capability(
        self,
        capability: str,
        arguments: Dict[str, Any],
        session_id: str = "default",
    ) -> Dict[str, Any]:
        caps = self.capabilities()
        if capability not in caps:
            raise CapabilityNotSupportedError(capability, self.app_id)

        if capability == "windows_get_active_window":
            return get_active_app()

        elif capability == "windows_enumerate_windows":
            return enumerate_windows()

        elif capability == "windows_get_running_apps":
            return get_running_apps()

        elif capability == "windows_open_app":
            app = str(arguments.get("app_name", "")).strip()
            return open_application(app)

        elif capability == "windows_close_app":
            app = str(arguments.get("app_name", "")).strip()
            return close_application(app)

        return {"success": False, "error": f"Unhandled capability '{capability}'."}

    def verify(
        self,
        capability: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
    ) -> VerificationResult:
        from ultron.tasks.models import VerificationResult
        t0 = time.time()
        if not result or not result.get("success", False):
            err_msg = result.get("error") or result.get("message") or "Windows desktop action failed."
            return VerificationResult(
                verified=False,
                method="windows_result_check",
                details={"result": result},
                error_message=err_msg,
                timestamp=t0,
            )

        return VerificationResult(
            verified=True,
            method="windows_action_verification",
            details={"capability": capability, "result": result},
            timestamp=t0,
        )

    async def shutdown(self):
        pass
