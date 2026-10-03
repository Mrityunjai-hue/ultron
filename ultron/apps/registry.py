"""
ULTRON V3 — Application Adapter Registry
─────────────────────────────────────────────────────────────────────────────
Authoritative registry of supported application adapters (Chrome, Windows, etc.).
Routes capability dispatch, verifies application state, and ensures clean resource
cleanup across sessions and runtime shutdowns.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from ultron.apps.base import ApplicationAdapter
from ultron.apps.chrome import ChromeAdapter
from ultron.apps.windows import WindowsAppAdapter
from ultron.apps.errors import AdapterUnavailableError, CapabilityNotSupportedError
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ultron.tasks.models import VerificationResult

logger = logging.getLogger("ultron.apps.registry")

class ApplicationRegistry:
    """Central manager and dispatcher for controlled application adapters."""

    def __init__(self, workspace_root: Path | str):
        self.workspace_root = Path(workspace_root).resolve()
        self._adapters: Dict[str, ApplicationAdapter] = {}
        self._capability_to_app: Dict[str, str] = {}

        # Register default adapters
        self.register_adapter(ChromeAdapter(self.workspace_root))
        self.register_adapter(WindowsAppAdapter(self.workspace_root))

    def register_adapter(self, adapter: ApplicationAdapter):
        """Registers an application adapter and maps its capabilities."""
        self._adapters[adapter.app_id] = adapter
        for cap_name in adapter.capabilities():
            self._capability_to_app[cap_name] = adapter.app_id
        logger.info(f"[App Registry] Registered adapter '{adapter.app_id}' with {len(adapter.capabilities())} capabilities.")

    def get_adapter(self, app_id: str) -> Optional[ApplicationAdapter]:
        """Retrieves an adapter by application ID."""
        return self._adapters.get(app_id.lower().strip())

    def get_adapter_for_capability(self, capability: str) -> Optional[ApplicationAdapter]:
        """Finds the adapter responsible for a specific capability."""
        app_id = self._capability_to_app.get(capability)
        if app_id:
            return self._adapters.get(app_id)
        return None

    def list_adapters(self) -> List[str]:
        """Returns list of registered adapter app IDs."""
        return list(self._adapters.keys())

    def list_available_apps(self) -> List[Dict[str, Any]]:
        """Lists all registered applications and their availability status."""
        return [
            {
                "app_id": a.app_id,
                "display_name": a.display_name,
                "is_available": a.is_available(),
                "is_running": a.is_running(),
                "capabilities_count": len(a.capabilities()),
            }
            for a in self._adapters.values()
        ]

    def get_all_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Returns consolidated capability map across all registered adapters."""
        all_caps = {}
        for a in self._adapters.values():
            all_caps.update(a.capabilities())
        return all_caps

    async def execute_capability(
        self,
        capability: str,
        arguments: Dict[str, Any],
        session_id: str = "default",
    ) -> Dict[str, Any]:
        """Dispatches capability execution to its registered adapter."""
        adapter = self.get_adapter_for_capability(capability)
        if not adapter:
            raise CapabilityNotSupportedError(capability, "unknown")

        if not adapter.is_available():
            raise AdapterUnavailableError(f"Application '{adapter.display_name}' is not available on this system.", app_id=adapter.app_id)

        return await adapter.execute_capability(capability, arguments, session_id=session_id)

    def verify_capability(
        self,
        capability: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
    ) -> VerificationResult:
        """Dispatches empirical post-action verification to the responsible adapter."""
        from ultron.tasks.models import VerificationResult
        adapter = self.get_adapter_for_capability(capability)
        if adapter:
            return adapter.verify(capability, arguments, result)

        return VerificationResult(
            verified=True,
            method="untracked_capability_verification",
            details={"capability": capability},
        )

    async def shutdown_all(self):
        """Cleanly terminates and releases all active application sessions."""
        logger.info("[App Registry] Shutting down all registered application adapters...")
        for a in self._adapters.values():
            try:
                await a.shutdown()
            except Exception as e:
                logger.warning(f"[App Registry] Error shutting down adapter '{a.app_id}': {e}")
