"""
ULTRON V3 — 4-Tier Safety Policy & Workspace Sandboxing
─────────────────────────────────────────────────────────────────────────────
Guarantees that cloud model requests NEVER execute unauthorized actions.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import os
from enum import Enum
from pathlib import Path
from typing import Tuple, Optional

class PolicyVerdict(str, Enum):
    SAFE = "SAFE"
    CONFIRM_REQUIRED = "CONFIRM_REQUIRED"
    BLOCKED = "BLOCKED"

BLOCKED_SYSTEM_PATHS = [
    r"C:\Windows",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\Windows\System32",
]

BLOCKED_COMMAND_SUBSTRINGS = [
    "format", "del /s", "del /f", "rmdir /s", "rd /s", "drop table",
    "reg delete", "net user", "shutdown", "taskkill /f /im explorer.exe"
]

PROTECTED_SYSTEM_PROCESSES = [
    "explorer", "svchost", "csrss", "lsass", "winlogon", "services", "smss",
    "dwm", "system", "idle", "antigravity", "python", "taskmgr"
]

DANGEROUS_SHELL_EXECUTABLES = [
    "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "pwsh.exe",
    "bash", "bash.exe", "wsl", "wsl.exe", "sh", "sh.exe", "zsh", "zsh.exe",
    "regedit", "regedit.exe", "reg", "reg.exe", "format", "format.com",
    "vbs", "bat", "ps1", "wscript", "wscript.exe", "cscript", "cscript.exe",
    "rundll32", "rundll32.exe", "net", "net.exe", "shutdown", "shutdown.exe",
    "mshta", "mshta.exe", "certutil", "certutil.exe", "bitsadmin"
]

COMMAND_INJECTION_CHARS = ["&", "|", ";", ">", "<", "`", "$", "\n", "\r", "^"]

def is_within_workspace(target_path: str | Path, workspace_root: str | Path) -> bool:
    """Verifies that target_path resolves strictly within workspace_root."""
    try:
        resolved_ws = Path(workspace_root).resolve()
        resolved_target = Path(target_path).resolve()
        return resolved_target == resolved_ws or resolved_ws in resolved_target.parents
    except Exception:
        return False

def classify_file_operation(
    operation: str,
    target_path: str | Path,
    workspace_root: str | Path,
) -> Tuple[PolicyVerdict, str]:
    """
    4-Tier evaluation for file system access:
    - SAFE: Read file within workspace
    - CONFIRM_REQUIRED: Write/modify or delete file within workspace
    - BLOCKED: Access outside workspace or touching Windows system directories
    """
    try:
        p = Path(target_path)
        if not p.is_absolute():
            p = Path(workspace_root) / p
        p = p.resolve()
    except Exception as e:
        return PolicyVerdict.BLOCKED, f"Invalid path syntax: {e}"

    # Check blocked system paths
    for sys_path in BLOCKED_SYSTEM_PATHS:
        try:
            if Path(sys_path).resolve() in p.parents or p == Path(sys_path).resolve():
                return PolicyVerdict.BLOCKED, f"Access to system path blocked: {p}"
        except Exception:
            pass

    # Boundary check
    if not is_within_workspace(p, workspace_root):
        return PolicyVerdict.BLOCKED, f"Path {p} is outside allowed workspace {workspace_root}"

    op = operation.lower()
    if op in ("read", "list", "info", "stat"):
        return PolicyVerdict.SAFE, "Read operation inside workspace permitted"
    elif op in ("create_dir", "mkdir", "create_directory"):
        return PolicyVerdict.SAFE, "Directory creation inside workspace permitted"
    elif op in ("write", "modify", "create"):
        if p.exists():
            return PolicyVerdict.CONFIRM_REQUIRED, f"File '{p.name}' already exists. Overwrite requires explicit confirmation."
        return PolicyVerdict.CONFIRM_REQUIRED, f"Writing new file '{p.name}' requires explicit confirmation."
    elif op in ("copy", "copy_file"):
        return PolicyVerdict.CONFIRM_REQUIRED, f"Copying file to '{p.name}' requires explicit confirmation."
    elif op in ("move", "move_file", "rename"):
        return PolicyVerdict.CONFIRM_REQUIRED, f"Moving/renaming file to '{p.name}' requires explicit confirmation."
    elif op in ("delete", "remove", "unlink"):
        return PolicyVerdict.CONFIRM_REQUIRED, f"Deleting file '{p.name}' requires explicit confirmation."

    return PolicyVerdict.SAFE, "Permitted operation"

def classify_app_operation(app_name: str, action: str = "open") -> Tuple[PolicyVerdict, str]:
    """
    Validates application operations:
    - SAFE: Opening known desktop applications
    - CONFIRM_REQUIRED: Closing applications
    - BLOCKED: Launching shell interpreters, dangerous utilities, or terminating system processes
    """
    if not app_name or not isinstance(app_name, str):
        return PolicyVerdict.BLOCKED, "Application name must be a non-empty string."

    raw = app_name.strip()

    # 1. Block command injection characters
    for ch in COMMAND_INJECTION_CHARS:
        if ch in raw:
            return PolicyVerdict.BLOCKED, f"Command injection attempt or shell separator '{ch}' is blocked."

    # 2. Block substring commands
    for sub in BLOCKED_COMMAND_SUBSTRINGS:
        if sub in raw.lower():
            return PolicyVerdict.BLOCKED, f"Dangerous command pattern '{sub}' is blocked."

    cleaned = raw.lower().replace(".exe", "").strip()

    # 3. Block dangerous shell executables
    for d in DANGEROUS_SHELL_EXECUTABLES:
        d_clean = d.replace(".exe", "")
        if cleaned == d_clean or cleaned.startswith(f"{d_clean} ") or f"/{d_clean}" in cleaned or f"\\{d_clean}" in cleaned:
            return PolicyVerdict.BLOCKED, f"Execution of dangerous executable or shell is blocked: {app_name}"

    if action == "close":
        if any(cleaned == p for p in PROTECTED_SYSTEM_PROCESSES):
            return PolicyVerdict.BLOCKED, f"Terminating critical operating system process is prohibited: {app_name}"
        return PolicyVerdict.CONFIRM_REQUIRED, f"Closing application '{app_name}' may cause unsaved data loss and requires confirmation."

    return PolicyVerdict.SAFE, f"App execution permitted: {app_name}"
