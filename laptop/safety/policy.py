"""
ULTRON Safety Policy Engine v2.0
─────────────────────────────────────────────────────────────────────────────
Enforces the 4-tier filesystem policy and command execution safety rules:
1. create new file        -> SAFE (within workspace)
2. overwrite file         -> CONFIRM_REQUIRED
3. delete file            -> CONFIRM_REQUIRED
4. outside workspace      -> BLOCKED
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import os
import re
from enum import Enum
from pathlib import Path
from typing import Tuple, Optional

class PolicyVerdict(str, Enum):
    SAFE = "SAFE"
    CONFIRM_REQUIRED = "CONFIRM_REQUIRED"
    BLOCKED = "BLOCKED"

# Default workspace root is the project scratch root
DEFAULT_WORKSPACE = Path(__file__).resolve().parent.parent.parent

# Whitelisted non-destructive shell commands
SAFE_SHELL_COMMANDS = {
    "git status", "git diff", "git log", "git branch",
    "dir", "ls", "echo", "python --version", "python -V",
    "node --version", "node -v", "whoami", "ipconfig", "hostname",
    "date", "time", "ver", "cd"
}

# Permanently blocked destructive shell commands
BLOCKED_SHELL_PATTERNS = [
    r"\bformat\b",
    r"\brmdir\b.*[a-z]:",
    r"\bdel\b.*[a-z]:",
    r":\(\)\s*\{\s*:\|:&\s*\};:",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r"\bshutdown\b",
    r"\breboot\b",
]

def get_workspace_root(override_path: Optional[str] = None) -> Path:
    """Returns canonical absolute workspace root."""
    if override_path:
        return Path(override_path).resolve()
    env_ws = os.environ.get("ULTRON_WORKSPACE", "")
    if env_ws:
        return Path(env_ws).resolve()
    return DEFAULT_WORKSPACE.resolve()

def is_within_workspace(path: str | Path, workspace: Optional[Path] = None) -> bool:
    """
    Validates that the target path resolves strictly inside the workspace boundary.
    Prevents path traversal attacks (e.g., ../../Windows).
    """
    ws = (workspace or get_workspace_root()).resolve()
    try:
        resolved = Path(path).resolve()
        # On Windows, drive letters must match and resolved must start with ws
        return resolved == ws or ws in resolved.parents
    except Exception:
        return False

def classify_file_operation(
    op: str,
    target_path: str | Path,
    workspace: Optional[Path] = None,
) -> Tuple[PolicyVerdict, str]:
    """
    Applies 4-tier filesystem policy:
    - Outside allowed workspace -> BLOCKED
    - Create new file           -> SAFE
    - Overwrite existing file   -> CONFIRM_REQUIRED
    - Delete file               -> CONFIRM_REQUIRED
    - Read / Search file        -> SAFE
    """
    p = Path(target_path)
    op = op.lower().strip()

    if not is_within_workspace(p, workspace):
        return (
            PolicyVerdict.BLOCKED,
            f"Operation '{op}' blocked: Path '{p}' is outside the authorized workspace."
        )

    resolved = p.resolve()

    if op in ("read", "search", "list"):
        return (PolicyVerdict.SAFE, f"Read-only operation '{op}' permitted.")

    if op in ("create", "write"):
        if resolved.exists():
            return (
                PolicyVerdict.CONFIRM_REQUIRED,
                f"Modifying existing file '{resolved.name}' requires explicit confirmation."
            )
        return (PolicyVerdict.SAFE, f"Creating new file '{resolved.name}' within workspace permitted.")

    if op == "delete":
        return (
            PolicyVerdict.CONFIRM_REQUIRED,
            f"Permanent deletion of '{resolved.name}' requires explicit confirmation."
        )

    return (PolicyVerdict.CONFIRM_REQUIRED, f"Action '{op}' requires explicit confirmation.")

def classify_shell_command(command: str) -> Tuple[PolicyVerdict, str]:
    """
    Validates command line execution safety:
    - Destructive system patterns -> BLOCKED
    - Whitelisted read-only tools -> SAFE
    - All other arbitrary shell   -> CONFIRM_REQUIRED
    """
    c = command.strip().lower()

    # Check blocked patterns
    for pattern in BLOCKED_SHELL_PATTERNS:
        if re.search(pattern, c, re.IGNORECASE):
            return (
                PolicyVerdict.BLOCKED,
                f"Command blocked by system protection rule: matched pattern '{pattern}'."
            )

    # Check safe commands
    first_token = c.split()[0] if c.split() else ""
    if any(c.startswith(safe) for safe in SAFE_SHELL_COMMANDS) or first_token in {"git", "echo", "python", "node"}:
        # Sub-check: ensure git command is not destructive (e.g. git clean -fdx, git reset --hard)
        if "clean -f" in c or "reset --hard" in c:
            return (
                PolicyVerdict.CONFIRM_REQUIRED,
                f"Destructive git action requires explicit confirmation: '{command}'."
            )
        return (PolicyVerdict.SAFE, "Standard non-destructive command permitted.")

    return (
        PolicyVerdict.CONFIRM_REQUIRED,
        f"Execution of command requires explicit confirmation: '{command}'."
    )
