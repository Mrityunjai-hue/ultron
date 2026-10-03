"""
ULTRON — Central Filesystem & Runtime Path Resolution
─────────────────────────────────────────────────────────────────────────────
Decouples application binary installation from local mutable user state.
Ensures zero writes to Program Files or Git repository in production.
Supports Windows %LOCALAPPDATA%, custom override flags, and isolated test paths.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

def get_app_install_dir() -> Path:
    """
    Returns the immutable installation directory where binary and bundled assets reside.
    In frozen production build (PyInstaller), returns sys._MEIPASS or executable directory.
    In development, returns the repository root.
    """
    if getattr(sys, "frozen", False):
        # PyInstaller bundle directory or directory containing executable
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def get_user_data_dir() -> Path:
    """
    Returns the authoritative mutable user data root directory.
    Priority:
    1. ULTRON_DATA_DIR environment variable (for testing / custom portable mode)
    2. Windows %LOCALAPPDATA%/ULTRON (e.g. C:\\Users\\<user>\\AppData\\Local\\ULTRON)
    3. User home ~/.ultron (fallback for non-Windows systems)
    """
    custom_dir = os.environ.get("ULTRON_DATA_DIR")
    if custom_dir:
        p = Path(custom_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            p = Path(local_app_data) / "ULTRON"
            p.mkdir(parents=True, exist_ok=True)
            return p

    p = Path.home() / ".ultron"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_config_dir() -> Path:
    """Returns directory for non-sensitive user settings."""
    p = get_user_data_dir() / "config"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_memory_dir() -> Path:
    """Returns directory for persistent conversational memory."""
    p = get_user_data_dir() / "memory"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_tasks_dir() -> Path:
    """Returns directory for task checkpoints, journal logs, and evidence chains."""
    p = get_user_data_dir() / "tasks"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_logs_dir() -> Path:
    """Returns directory for sanitized application and crash logs."""
    p = get_user_data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_cache_dir() -> Path:
    """Returns directory for temporary runtime caches and browser automation profiles."""
    p = get_user_data_dir() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_runtime_directories() -> None:
    """Creates all required user data subdirectories atomically."""
    get_user_data_dir()
    get_config_dir()
    get_memory_dir()
    get_tasks_dir()
    get_logs_dir()
    get_cache_dir()
