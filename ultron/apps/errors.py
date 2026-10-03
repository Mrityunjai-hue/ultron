"""
ULTRON V3 — Application Adapter Errors & Security Exceptions
─────────────────────────────────────────────────────────────────────────────
Structured error taxonomy for controlled application and browser interaction.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
from typing import Optional

class ApplicationError(Exception):
    """Base exception for all application adapter operations."""
    def __init__(self, message: str, app_id: Optional[str] = None):
        super().__init__(message)
        self.app_id = app_id
        self.message = message

class AdapterUnavailableError(ApplicationError):
    """Raised when the requested application is not installed or cannot be reached."""
    pass

class CapabilityNotSupportedError(ApplicationError):
    """Raised when an application adapter does not support a requested capability."""
    def __init__(self, capability: str, app_id: str):
        super().__init__(f"Application '{app_id}' does not support capability '{capability}'.", app_id=app_id)
        self.capability = capability

class URLSecurityError(ApplicationError):
    """Raised when a URL fails safety validation (dangerous scheme, malformed, or local file access)."""
    def __init__(self, url: str, reason: str):
        super().__init__(f"URL '{url}' blocked by security policy: {reason}", app_id="chrome")
        self.url = url
        self.reason = reason

class DownloadSecurityError(ApplicationError):
    """Raised when a file download operation violates workspace sandbox or safety rules."""
    def __init__(self, path: str, reason: str):
        super().__init__(f"Download destination '{path}' blocked by security policy: {reason}", app_id="chrome")
        self.path = path
        self.reason = reason

class PromptInjectionBlockedError(ApplicationError):
    """Raised when untrusted webpage content attempts to masquerade as authoritative instructions."""
    pass

class BrowserTimeoutError(ApplicationError):
    """Raised when a browser navigation, load, or CDP operation exceeds timeout threshold."""
    pass

class BrowserSessionError(ApplicationError):
    """Raised when duplicate browser sessions or stale process handles are encountered."""
    pass
