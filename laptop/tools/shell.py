"""
ULTRON Safe Shell Execution Tool v2.0
─────────────────────────────────────────────────────────────────────────────
Executes safe system commands with:
- 10-second timeout guarantee
- Strict whitelisting & destructive pattern blocking
- Safety confirmation gating for unlisted commands
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from laptop.safety.policy import (
        classify_shell_command,
        get_workspace_root,
        PolicyVerdict,
    )
except ImportError:
    from safety.policy import (
        classify_shell_command,
        get_workspace_root,
        PolicyVerdict,
    )

class ShellTool:
    """Bounded, safe shell command runner."""

    def __init__(self, workspace: Optional[Path] = None, timeout_seconds: float = 10.0):
        self.workspace = (workspace or get_workspace_root()).resolve()
        self.timeout_seconds = timeout_seconds

    def execute(self, command: str, confirmed: bool = False) -> Dict[str, Any]:
        """
        Executes a shell command after safety policy evaluation.
        """
        verdict, reason = classify_shell_command(command)

        if verdict == PolicyVerdict.BLOCKED:
            return {
                "success": False,
                "status": verdict.value,
                "error": reason,
                "command": command,
            }

        if verdict == PolicyVerdict.CONFIRM_REQUIRED and not confirmed:
            return {
                "success": False,
                "status": verdict.value,
                "message": reason,
                "command": command,
            }

        start_time = time.time()
        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            elapsed = (time.time() - start_time) * 1000.0

            return {
                "success": res.returncode == 0,
                "status": "SUCCESS" if res.returncode == 0 else "COMMAND_ERROR",
                "command": command,
                "exit_code": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "duration_ms": round(elapsed, 1),
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "status": "TIMEOUT",
                "error": f"Command timed out after {self.timeout_seconds} seconds.",
                "command": command,
            }
        except Exception as e:
            return {
                "success": False,
                "status": "EXECUTION_ERROR",
                "error": str(e),
                "command": command,
            }
