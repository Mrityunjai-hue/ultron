"""
ULTRON V3 — Controlled Application & Browser Adapter Layer
"""
from ultron.apps.base import ApplicationAdapter
from ultron.apps.errors import (
    ApplicationError,
    AdapterUnavailableError,
    CapabilityNotSupportedError,
    URLSecurityError,
    DownloadSecurityError,
    PromptInjectionBlockedError,
    BrowserTimeoutError,
    BrowserSessionError,
)
from ultron.apps.chrome import ChromeAdapter, validate_url, sanitize_webpage_content
from ultron.apps.windows import WindowsAppAdapter
from ultron.apps.registry import ApplicationRegistry

__all__ = [
    "ApplicationAdapter",
    "ApplicationError",
    "AdapterUnavailableError",
    "CapabilityNotSupportedError",
    "URLSecurityError",
    "DownloadSecurityError",
    "PromptInjectionBlockedError",
    "BrowserTimeoutError",
    "BrowserSessionError",
    "ChromeAdapter",
    "WindowsAppAdapter",
    "ApplicationRegistry",
    "validate_url",
    "sanitize_webpage_content",
]
