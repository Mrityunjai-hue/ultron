"""
ULTRON — Windows Startup & Relaunch Loop Mitigation
─────────────────────────────────────────────────────────────────────────────
Manages non-admin Windows startup registration in HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.
Includes an automated Crash Circuit-Breaker to prevent infinite relaunch loops
if the application crashes repeatedly on startup.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any

from ultron.core.paths import get_config_dir

logger = logging.getLogger("ultron.core.startup")

REG_RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "ULTRON"
MAX_CONSECUTIVE_STARTUP_FAILURES = 3
CRASH_WINDOW_SECONDS = 120.0


class StartupManager:
    """Manages user-controlled Windows startup registration and crash circuit breakers."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or get_config_dir()
        self.state_file = self.config_dir / "startup_state.json"

    def _load_state(self) -> Dict[str, Any]:
        if not self.state_file.exists():
            return {
                "consecutive_failures": 0,
                "last_startup_time": 0.0,
                "last_success_time": 0.0,
                "circuit_breaker_tripped": False,
            }
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {
                "consecutive_failures": 0,
                "last_startup_time": 0.0,
                "last_success_time": 0.0,
                "circuit_breaker_tripped": False,
            }

    def _save_state(self, state: Dict[str, Any]) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"[Startup Manager] Failed saving startup state: {e}")

    def is_startup_enabled(self) -> bool:
        """Queries HKCU registry to check if startup launch is active."""
        if sys.platform != "win32":
            return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, APP_REG_NAME)
                return bool(val)
        except (FileNotFoundError, OSError):
            return False
        except Exception as e:
            logger.debug(f"[Startup Manager] Registry query notice: {e}")
            return False

    def enable_startup(self, executable_path: Optional[str | Path] = None, minimized: bool = True) -> bool:
        """Registers application to launch on user login via HKCU Run key."""
        if sys.platform != "win32":
            return False
        try:
            import winreg
            target_path = Path(executable_path or sys.executable).resolve()
            cmd = f'"{target_path}"'
            if minimized:
                cmd += " --minimized"

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH) as key:
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
            logger.info(f"[Startup Manager] Successfully registered startup command: {cmd}")
            return True
        except Exception as e:
            logger.error(f"[Startup Manager] Failed enabling Windows startup: {e}")
            return False

    def disable_startup(self) -> bool:
        """Removes application from HKCU Run key."""
        if sys.platform != "win32":
            return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, APP_REG_NAME)
            logger.info("[Startup Manager] Successfully removed Windows startup entry.")
            return True
        except FileNotFoundError:
            return True
        except Exception as e:
            logger.error(f"[Startup Manager] Failed disabling Windows startup: {e}")
            return False

    def check_circuit_breaker(self) -> bool:
        """
        Evaluates recent startup attempts.
        Returns True if safe to start, False if tripped by repeated crash loops.
        """
        state = self._load_state()
        if state.get("circuit_breaker_tripped"):
            logger.critical("[Startup Manager] STARTUP CIRCUIT BREAKER ACTIVE: Aborting launch to prevent boot crash loop.")
            return False

        consecutive = state.get("consecutive_failures", 0)
        last_start = state.get("last_startup_time", 0.0)
        now = time.time()

        if consecutive >= MAX_CONSECUTIVE_STARTUP_FAILURES and (now - last_start) < CRASH_WINDOW_SECONDS:
            state["circuit_breaker_tripped"] = True
            self._save_state(state)
            logger.critical(
                f"[Startup Manager] Tripped circuit breaker after {consecutive} crashes within {CRASH_WINDOW_SECONDS}s."
            )
            return False

        # Record new startup attempt
        state["last_startup_time"] = now
        state["consecutive_failures"] = consecutive + 1
        self._save_state(state)
        return True

    def record_successful_startup(self) -> None:
        """Resets the failure counter once runtime reaches READY state."""
        state = self._load_state()
        state["consecutive_failures"] = 0
        state["last_success_time"] = time.time()
        state["circuit_breaker_tripped"] = False
        self._save_state(state)
        logger.debug("[Startup Manager] Startup success recorded. Circuit breaker reset.")

    def reset_circuit_breaker(self) -> None:
        """Manually clears circuit breaker."""
        state = self._load_state()
        state["consecutive_failures"] = 0
        state["circuit_breaker_tripped"] = False
        self._save_state(state)
