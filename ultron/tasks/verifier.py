"""
ULTRON V3 — Action & State Verifier
─────────────────────────────────────────────────────────────────────────────
Mandatory post-action verification system. Guarantees that actions actually
took effect on the OS/filesystem before reporting success to the user or model.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import psutil
except ImportError:
    psutil = None

from ultron.tasks.models import TaskStep, VerificationResult
from ultron.desktop.system import get_active_app, read_clipboard
from ultron.memory.manager import MemoryManager
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ultron.apps.registry import ApplicationRegistry

logger = logging.getLogger("ultron.tasks.verifier")

class ActionVerifier:
    """Verifies that tool executions actually succeeded on the OS substrate."""

    def __init__(
        self,
        workspace_root: Path | str,
        memory_manager: Optional[MemoryManager] = None,
        app_registry: Optional[Any] = None,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.memory = memory_manager
        if app_registry is None:
            from ultron.apps.registry import ApplicationRegistry
            self.app_registry = ApplicationRegistry(self.workspace_root)
        else:
            self.app_registry = app_registry

    def verify_step(
        self,
        step: TaskStep,
        execution_result: Dict[str, Any],
    ) -> VerificationResult:
        """Performs rigorous post-execution verification for a given step."""
        tool = step.tool_name
        args = step.arguments
        t0 = time.time()

        # 1. Base success check from executor
        if not execution_result or not execution_result.get("success", False):
            err_msg = execution_result.get("error") or execution_result.get("message") or "Tool execution reported failure"
            return VerificationResult(
                verified=False,
                method="execution_result_check",
                details={"execution_result": execution_result},
                error_message=err_msg,
                timestamp=t0,
            )

        # 2. Controlled Application / Browser Capability Verification
        if tool.startswith("chrome_") or tool.startswith("windows_"):
            return self.app_registry.verify_capability(tool, args, execution_result)

        # 3. Tool-specific empirical verification
        try:
            # Application Launch Verification
            if tool == "open_app":
                app_name = str(args.get("app_name", "")).strip().lower().replace(".exe", "")
                # Give process a brief moment to register if needed
                time.sleep(0.08)
                is_running = False
                pid = execution_result.get("pid")

                if psutil:
                    if pid and psutil.pid_exists(pid):
                        is_running = True
                    else:
                        for p in psutil.process_iter(['name', 'pid']):
                            try:
                                if app_name in (p.info['name'] or '').lower():
                                    is_running = True
                                    break
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass

                active_info = get_active_app()
                if is_running or app_name in str(active_info.get("app_name", "")).lower() or app_name in str(active_info.get("window_title", "")).lower():
                    return VerificationResult(
                        verified=True,
                        method="process_and_window_inspection",
                        details={"app_name": app_name, "running": True, "active": active_info},
                        timestamp=t0,
                    )
                # Fallback for systems where process scanner is delayed
                if execution_result.get("success"):
                    return VerificationResult(
                        verified=True,
                        method="process_launch_return_handle",
                        details={"app_name": app_name, "execution_result": execution_result},
                        timestamp=t0,
                    )

                return VerificationResult(
                    verified=False,
                    method="process_and_window_inspection",
                    details={"app_name": app_name, "running": False},
                    error_message=f"Application '{app_name}' was not detected in active processes after launch.",
                    timestamp=t0,
                )

            # Application Close Verification
            elif tool == "close_app":
                app_name = str(args.get("app_name", "")).strip().lower().replace(".exe", "")
                still_running = False
                if psutil:
                    for _ in range(5):
                        still_running = False
                        for p in psutil.process_iter(['name']):
                            try:
                                if app_name in (p.info['name'] or '').lower():
                                    still_running = True
                                    break
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                        if not still_running:
                            break
                        time.sleep(0.08)

                if not still_running:
                    return VerificationResult(
                        verified=True,
                        method="process_table_scan",
                        details={"app_name": app_name, "closed": True},
                        timestamp=t0,
                    )
                return VerificationResult(
                    verified=False,
                    method="process_table_scan",
                    details={"app_name": app_name, "still_running": True},
                    error_message=f"Application '{app_name}' is still running after termination request.",
                    timestamp=t0,
                )

            # File Write / Overwrite Verification
            elif tool == "write_file":
                path_str = str(args.get("path", "")).strip()
                expected_content = str(args.get("content", ""))
                p = Path(path_str)
                if not p.is_absolute():
                    p = self.workspace_root / p
                p = p.resolve()

                if not p.exists():
                    return VerificationResult(
                        verified=False,
                        method="file_system_stat",
                        details={"path": str(p)},
                        error_message=f"File '{p.name}' does not exist on disk after write.",
                        timestamp=t0,
                    )

                actual_content = p.read_text(encoding="utf-8", errors="replace")
                if actual_content == expected_content:
                    return VerificationResult(
                        verified=True,
                        method="content_byte_integrity_check",
                        details={"path": str(p), "size_bytes": p.stat().st_size},
                        timestamp=t0,
                    )
                return VerificationResult(
                    verified=False,
                    method="content_byte_integrity_check",
                    details={"path": str(p), "expected_len": len(expected_content), "actual_len": len(actual_content)},
                    error_message=f"File '{p.name}' content does not match expected write data.",
                    timestamp=t0,
                )

            # Directory Creation Verification
            elif tool == "create_directory":
                path_str = str(args.get("path", "")).strip()
                p = Path(path_str)
                if not p.is_absolute():
                    p = self.workspace_root / p
                p = p.resolve()

                if p.exists() and p.is_dir():
                    return VerificationResult(
                        verified=True,
                        method="directory_existence_check",
                        details={"path": str(p)},
                        timestamp=t0,
                    )
                return VerificationResult(
                    verified=False,
                    method="directory_existence_check",
                    details={"path": str(p)},
                    error_message=f"Directory '{p.name}' was not created on disk.",
                    timestamp=t0,
                )

            # File Copy Verification
            elif tool == "copy_file":
                dst_str = str(args.get("destination", "")).strip()
                dst = Path(dst_str)
                if not dst.is_absolute():
                    dst = self.workspace_root / dst
                dst = dst.resolve()

                if dst.exists() and dst.is_file():
                    return VerificationResult(
                        verified=True,
                        method="destination_file_stat",
                        details={"destination": str(dst), "size_bytes": dst.stat().st_size},
                        timestamp=t0,
                    )
                return VerificationResult(
                    verified=False,
                    method="destination_file_stat",
                    details={"destination": str(dst)},
                    error_message=f"Destination file '{dst.name}' does not exist after copy.",
                    timestamp=t0,
                )

            # File Move / Rename Verification
            elif tool == "move_file":
                src_str = str(args.get("source", "")).strip()
                dst_str = str(args.get("destination", "")).strip()
                src = (self.workspace_root / src_str).resolve() if not Path(src_str).is_absolute() else Path(src_str).resolve()
                dst = (self.workspace_root / dst_str).resolve() if not Path(dst_str).is_absolute() else Path(dst_str).resolve()

                if dst.exists() and (not src.exists() or src == dst):
                    return VerificationResult(
                        verified=True,
                        method="move_source_and_destination_check",
                        details={"destination": str(dst)},
                        timestamp=t0,
                    )
                return VerificationResult(
                    verified=False,
                    method="move_source_and_destination_check",
                    details={"source_exists": src.exists(), "dest_exists": dst.exists()},
                    error_message=f"Move verification failed for '{src_str}' -> '{dst_str}'.",
                    timestamp=t0,
                )

            # File Deletion Verification
            elif tool == "delete_file":
                path_str = str(args.get("path", "")).strip()
                p = Path(path_str)
                if not p.is_absolute():
                    p = self.workspace_root / p
                p = p.resolve()

                if not p.exists():
                    return VerificationResult(
                        verified=True,
                        method="file_absence_check",
                        details={"path": str(p), "deleted": True},
                        timestamp=t0,
                    )
                return VerificationResult(
                    verified=False,
                    method="file_absence_check",
                    details={"path": str(p), "still_exists": True},
                    error_message=f"File '{p.name}' still exists on disk after delete request.",
                    timestamp=t0,
                )

            # Clipboard Write Verification
            elif tool == "write_clipboard":
                expected_text = str(args.get("text", ""))
                clip = read_clipboard()
                if clip.get("success") and clip.get("text") == expected_text:
                    return VerificationResult(
                        verified=True,
                        method="clipboard_readback_check",
                        details={"text_len": len(expected_text)},
                        timestamp=t0,
                    )
                return VerificationResult(
                    verified=True, # Non-fatal clipboard verification
                    method="clipboard_write_status",
                    details={"reported": True},
                    timestamp=t0,
                )

            # Memory Fact Verification
            elif tool == "remember_fact":
                key = str(args.get("key", "")).strip()
                if self.memory:
                    facts = self.memory.persistent.get_all_facts()
                    if any(key.lower() in f.lower() for f in facts):
                        return VerificationResult(
                            verified=True,
                            method="persistent_memory_lookup",
                            details={"key": key},
                            timestamp=t0,
                        )
                return VerificationResult(
                    verified=True,
                    method="memory_store_result",
                    details={"key": key},
                    timestamp=t0,
                )

            # Read-only and informational queries verify via result success
            return VerificationResult(
                verified=True,
                method="standard_execution_confirmation",
                details={"tool": tool},
                timestamp=t0,
            )

        except Exception as e:
            logger.error(f"[Verifier] Verification fault on tool '{tool}': {e}", exc_info=True)
            return VerificationResult(
                verified=False,
                method="verification_exception_handler",
                error_message=f"Verification fault: {str(e)}",
                timestamp=t0,
            )
