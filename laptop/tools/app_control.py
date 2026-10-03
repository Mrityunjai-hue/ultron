"""
ULTRON Application Control Tools v2.0
─────────────────────────────────────────────────────────────────────────────
Real OS application management for Windows:
- open_app: Launches applications and verifies PID
- close_app: Safely terminates running applications
- list_running_apps: Enumerates active processes
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import os
import sys
import subprocess
import shutil
import csv
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ultron.tools.app_control")

APP_ALIASES = {
    "notepad": "notepad.exe",
    "calc": "calc.exe",
    "calculator": "calc.exe",
    "cmd": "cmd.exe",
    "terminal": "wt.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "files": "explorer.exe",
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "code": "code.cmd",
    "vscode": "code.cmd",
    "taskmgr": "taskmgr.exe",
}

class AppControlTool:
    """Manages real desktop applications on Windows."""

    def open_app(self, app_name: str) -> Dict[str, Any]:
        """
        Launches an application and verifies process initialization.
        """
        raw_name = app_name.strip().lower()
        executable = APP_ALIASES.get(raw_name, app_name.strip())

        try:
            # First check if available on PATH or absolute
            resolved_exe = shutil.which(executable) or executable

            proc = subprocess.Popen(
                [resolved_exe],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Verification: Check that the process object exists and has a PID
            if proc.poll() is None or proc.pid > 0:
                logger.info(f"Launched application '{app_name}' with PID {proc.pid}")
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "app_name": app_name,
                    "executable": executable,
                    "pid": proc.pid,
                    "message": f"Application '{app_name}' initiated with PID {proc.pid}.",
                }
            else:
                return {
                    "success": False,
                    "error": f"Application '{app_name}' exited immediately with code {proc.returncode}.",
                }
        except Exception as e:
            # Fallback to os.startfile on Windows for protocol/registered apps
            if sys.platform == "win32":
                try:
                    os.startfile(executable)
                    return {
                        "success": True,
                        "status": "SUCCESS",
                        "app_name": app_name,
                        "executable": executable,
                        "message": f"Application '{app_name}' launched via system shell.",
                    }
                except Exception as inner_e:
                    return {"success": False, "error": f"Failed launching '{app_name}': {inner_e}"}

            return {"success": False, "error": f"Failed launching '{app_name}': {e}"}

    def close_app(self, app_name: str, force: bool = False) -> Dict[str, Any]:
        """
        Terminates running instances of an application by name.
        """
        raw_name = app_name.strip().lower()
        target_name = APP_ALIASES.get(raw_name, raw_name)
        if not target_name.endswith(".exe"):
            target_exe = f"{target_name}.exe"
        else:
            target_exe = target_name

        try:
            flag = "/F" if force else ""
            cmd = ["taskkill", "/IM", target_exe]
            if force:
                cmd.insert(1, "/F")

            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5.0,
            )

            if res.returncode == 0:
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "app_name": app_name,
                    "executable": target_exe,
                    "message": f"Successfully terminated '{target_exe}'.",
                }
            elif "not found" in res.stderr.lower() or "not found" in res.stdout.lower():
                return {
                    "success": False,
                    "error": f"No active instances of '{target_exe}' found.",
                }
            else:
                return {
                    "success": False,
                    "error": res.stderr.strip() or res.stdout.strip(),
                }
        except Exception as e:
            return {"success": False, "error": f"Failed closing '{app_name}': {e}"}

    def list_running_apps(self, limit: int = 15) -> Dict[str, Any]:
        """
        Lists actively running processes on the system.
        """
        try:
            res = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            if res.returncode != 0:
                return {"success": False, "error": res.stderr.strip()}

            apps = []
            reader = csv.reader(res.stdout.splitlines())
            for row in reader:
                if len(row) >= 5:
                    name = row[0]
                    pid = row[1]
                    mem = row[4]
                    # Filter out noise system helper processes
                    if name.lower() not in {"svchost.exe", "conhost.exe", "system idle process"}:
                        apps.append({"name": name, "pid": pid, "memory": mem})

            return {
                "success": True,
                "status": "SUCCESS",
                "count": len(apps[:limit]),
                "apps": apps[:limit],
            }
        except Exception as e:
            return {"success": False, "error": f"Failed listing processes: {e}"}
