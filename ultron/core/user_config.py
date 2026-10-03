"""
ULTRON — User Configuration & Onboarding State Management
─────────────────────────────────────────────────────────────────────────────
Manages non-sensitive user identity, conversational address, assistant naming,
interaction preferences, local memory policies, and first-run completion status.

Privacy & Security Guarantees:
- Stored strictly in %LOCALAPPDATA%/ULTRON/config/user_config.json (isolated from binaries/git).
- Atomic persistence via temporary file replacement.
- Self-healing recovery: corrupted JSON resets only user configuration safely.
- Zero credential / secret storage.
- Diagnostics and telemetry export boolean presence and safe non-identifying flags only.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import json
import logging
import os
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, Optional

from ultron.core.paths import get_config_dir

logger = logging.getLogger("ultron.core.user_config")

USER_CONFIG_FILENAME = "user_config.json"


@dataclass
class UserConfig:
    """Authoritative user configuration populated during first-run onboarding."""
    # Step 01: Owner identity
    owner_name: str = ""
    pronunciation_hint: str = ""

    # Step 02: Conversational address
    addressing_name: str = ""

    # Step 03: Assistant identity
    assistant_name: str = "ULTRON"

    # Step 04: Voice & Interaction preferences
    preferred_language: str = "English (US)"
    voice_preference: str = "Puck"
    response_style: str = "Concise & Authoritative"
    presence_enabled: bool = True

    # Step 05: Privacy & Memory preferences
    allow_explicit_memory: bool = True

    # Step 06: Startup preferences
    start_with_windows: bool = False

    # Lifecycle & First-Run marker
    first_run_completed: bool = False

    def validate(self) -> tuple[bool, str]:
        """Validates configuration fields before saving."""
        if not self.owner_name or not self.owner_name.strip():
            return False, "Owner name is required."
        if not self.addressing_name or not self.addressing_name.strip():
            # Default addressing name to owner name if unset
            self.addressing_name = self.owner_name.strip()
        if not self.assistant_name or not self.assistant_name.strip():
            self.assistant_name = "ULTRON"
        if not self.voice_preference or not self.voice_preference.strip():
            self.voice_preference = "Puck"
        return True, "OK"

    def to_safe_diagnostics_dict(self) -> Dict[str, Any]:
        """
        Returns safe metadata for diagnostics / telemetry without revealing
        actual private user names or personal identifiers.
        """
        return {
            "configuration_present": True,
            "first_run_completed": self.first_run_completed,
            "assistant_name": self.assistant_name if self.assistant_name == "ULTRON" else "CUSTOM",
            "voice_preference": self.voice_preference,
            "response_style": self.response_style,
            "presence_enabled": self.presence_enabled,
            "allow_explicit_memory": self.allow_explicit_memory,
            "start_with_windows": self.start_with_windows,
        }


def get_user_config_path(config_dir: Optional[Path] = None) -> Path:
    """Returns the canonical path to user_config.json."""
    base = config_dir or get_config_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base / USER_CONFIG_FILENAME


def is_first_run_required(config_dir: Optional[Path] = None) -> bool:
    """
    Checks if first-run onboarding is required.
    Returns True if user_config.json is absent, corrupted, owner_name is empty/test placeholder, or first_run_completed is False.
    """
    path = get_user_config_path(config_dir)
    if not path.exists():
        return True
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            owner = str(data.get("owner_name", "")).strip()
            if not owner or owner in ("CleanInstallUser", "TestUser"):
                return True
            return not bool(data.get("first_run_completed", False))
    except Exception as ex:
        logger.warning(f"[UserConfig] Error reading config at {path}: {ex}. Requiring first-run setup.")
        return True


def load_user_config(config_dir: Optional[Path] = None) -> UserConfig:
    """
    Loads user configuration from disk.
    If the file is missing or corrupted, returns default UserConfig safely.
    """
    path = get_user_config_path(config_dir)
    if not path.exists():
        return UserConfig()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Filter only known fields
            valid_keys = {f for f in UserConfig.__dataclass_fields__}
            filtered = {k: v for k, v in data.items() if k in valid_keys}
            return UserConfig(**filtered)
    except Exception as ex:
        logger.error(f"[UserConfig] Corrupted user configuration file at {path}: {ex}. Resetting to defaults.")
        # Self-healing recovery: do not crash or corrupt other stores
        return UserConfig()


def save_user_config(config: UserConfig, config_dir: Optional[Path] = None) -> bool:
    """
    Atomically saves user configuration to disk using a temporary file and replace.
    Ensures zero file corruption if process terminates during write.
    """
    target_path = get_user_config_path(config_dir)
    target_dir = target_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize and validate
    is_valid, reason = config.validate()
    if not is_valid:
        logger.error(f"[UserConfig] Validation failed: {reason}")
        return False

    data = asdict(config)

    # Write atomically
    temp_fd = None
    temp_path = None
    try:
        temp_fd, temp_path = tempfile.mkstemp(
            prefix="ultron_cfg_",
            suffix=".tmp",
            dir=str(target_dir),
        )
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            temp_fd = None  # fd is now managed by f
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        # Atomic replace
        os.replace(temp_path, target_path)
        logger.info(f"[UserConfig] Successfully persisted user configuration to {target_path}")
        return True
    except Exception as ex:
        logger.error(f"[UserConfig] Failed to atomically persist user config: {ex}")
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass
        return False
    finally:
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except Exception:
                pass


def reset_user_config(config_dir: Optional[Path] = None) -> bool:
    """Resets user configuration state to defaults."""
    target_path = get_user_config_path(config_dir)
    if target_path.exists():
        try:
            target_path.unlink()
            logger.info(f"[UserConfig] Cleared user configuration file at {target_path}")
            return True
        except Exception as ex:
            logger.error(f"[UserConfig] Failed to unlink config file: {ex}")
            return False
    return True
