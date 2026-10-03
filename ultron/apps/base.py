"""
ULTRON V3 — Application Adapter Base Contract
─────────────────────────────────────────────────────────────────────────────
Defines the strict abstract base interface that all application adapters must
implement. Guarantees that applications expose only structured, safe, and
empirically verifiable capabilities without arbitrary OS or coordinate access.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ultron.tasks.models import VerificationResult

class ApplicationAdapter(ABC):
    """Abstract Base Class for controlled desktop and browser application adapters."""

    @property
    @abstractmethod
    def app_id(self) -> str:
        """Unique application identifier (e.g. 'chrome', 'windows')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable application name."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the application executable or subsystem is installed locally."""
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """Returns True if the application currently has an active process running."""
        pass

    @abstractmethod
    def get_active_window(self) -> Dict[str, Any]:
        """Returns details about the current active window for this application."""
        pass

    @abstractmethod
    def capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Returns dictionary mapping supported capability names to metadata."""
        pass

    @abstractmethod
    async def execute_capability(
        self,
        capability: str,
        arguments: Dict[str, Any],
        session_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Executes a controlled, structured application action.
        Must NOT perform arbitrary coordinate clicking or unrestricted script execution.
        """
        pass

    @abstractmethod
    def verify(
        self,
        capability: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
    ) -> VerificationResult:
        """
        Empirically verifies that the capability execution actually succeeded
        on the underlying application state before reporting success.
        """
        pass

    @abstractmethod
    async def shutdown(self):
        """Releases active sessions, closes open handles, and cleans up state."""
        pass
