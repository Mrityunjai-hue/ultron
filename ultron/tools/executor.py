"""
ULTRON V3 — Local Tool Executor Gateway
─────────────────────────────────────────────────────────────────────────────
Receives function calls from the cloud model, enforces safety validation,
executes locally on Windows, and returns structured results.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ultron.tools.safety import classify_file_operation, classify_app_operation, PolicyVerdict
from ultron.tools.confirmation import ConfirmationManager
from ultron.memory.manager import MemoryManager
from ultron.apps.errors import ApplicationError, URLSecurityError, DownloadSecurityError
from ultron.desktop.system import (
    get_current_time,
    get_system_status,
    open_application,
    close_application,
    read_workspace_file,
    write_workspace_file,
    delete_workspace_file,
    list_workspace_directory,
    get_workspace_file_info,
    create_workspace_directory,
    copy_workspace_file,
    move_workspace_file,
    get_active_app,
    get_running_apps,
    read_clipboard,
    write_clipboard,
    get_active_app as get_active_window_info,
    enumerate_windows,
)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ultron.apps.registry import ApplicationRegistry

logger = logging.getLogger("ultron.tools.executor")

class ToolExecutor:
    """Safe dispatcher mapping cloud tool requests to local OS utilities and application adapters."""

    def __init__(
        self,
        workspace_root: Path | str,
        confirmation_manager: Optional[ConfirmationManager] = None,
        memory_manager: Optional[MemoryManager] = None,
        app_registry: Optional[Any] = None,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.confirmation = confirmation_manager or ConfirmationManager()
        self.memory = memory_manager or MemoryManager()
        if app_registry is None:
            from ultron.apps.registry import ApplicationRegistry
            self.app_registry = ApplicationRegistry(self.workspace_root)
        else:
            self.app_registry = app_registry

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        session_id: str = "default",
    ) -> Dict[str, Any]:
        """Validates safety and dispatches execution."""
        logger.info(f"[Tool Gateway] Executing tool '{tool_name}' with args: {arguments}")

        # Resolve pronoun / contextual references ('it', 'that app', 'the file', 'that url')
        if tool_name in ("open_app", "close_app", "windows_open_app", "windows_close_app"):
            raw_app = str(arguments.get("app_name", "")).strip()
            if raw_app.lower() in ("it", "the app", "that app", "this app", "the application"):
                resolved = self.memory.session.resolve_target("app")
                if resolved:
                    arguments["app_name"] = resolved
                    logger.info(f"[Tool Gateway] Resolved pronoun '{raw_app}' to active app: '{resolved}'")

        elif tool_name in ("read_file", "write_file", "delete_file", "get_file_info", "list_directory", "create_directory", "chrome_download_file"):
            raw_path = str(arguments.get("path") or arguments.get("destination") or "").strip()
            if raw_path.lower() in ("it", "the file", "that file", "this file", "the document", "the folder", "the directory", "that download"):
                resolved = self.memory.session.resolve_target("file")
                if resolved:
                    if "path" in arguments:
                        arguments["path"] = resolved
                    elif "destination" in arguments:
                        arguments["destination"] = resolved
                    logger.info(f"[Tool Gateway] Resolved pronoun '{raw_path}' to active file: '{resolved}'")

        elif tool_name in ("chrome_navigate", "chrome_download_file"):
            raw_url = str(arguments.get("url", "")).strip()
            if raw_url.lower() in ("it", "that link", "that url", "that page", "the website", "the link", "this page"):
                resolved = self.memory.session.resolve_target("url")
                if resolved:
                    arguments["url"] = resolved
                    logger.info(f"[Tool Gateway] Resolved pronoun '{raw_url}' to active url: '{resolved}'")

        elif tool_name == "chrome_search":
            raw_query = str(arguments.get("query", "")).strip()
            if raw_query.lower() in ("it", "that", "the search", "the query"):
                resolved = self.memory.session.resolve_target("query")
                if resolved:
                    arguments["query"] = resolved
                    logger.info(f"[Tool Gateway] Resolved pronoun '{raw_query}' to active search query: '{resolved}'")

        try:
            # 1. Authoritative Clock
            if tool_name == "get_current_time":
                return get_current_time()

            # 2. Hardware Substrate Metrics
            elif tool_name == "get_system_status":
                return get_system_status()

            # 3. Application Awareness: Active App
            elif tool_name == "get_active_app":
                return get_active_app()

            # 4. Application Awareness: Running Apps
            elif tool_name == "get_running_apps":
                return get_running_apps()

            # 5. Application Launcher
            elif tool_name == "open_app":
                app_name = str(arguments.get("app_name", "")).strip()
                if not app_name:
                    return {"success": False, "error": "Missing required argument 'app_name'."}

                verdict, reason = classify_app_operation(app_name, action="open")
                if verdict == PolicyVerdict.BLOCKED:
                    return {"success": False, "status": "BLOCKED", "error": reason}

                return open_application(app_name)

            # 6. Application Terminator (Requires Confirmation Token)
            elif tool_name == "close_app":
                app_name = str(arguments.get("app_name", "")).strip()
                if not app_name:
                    return {"success": False, "error": "Missing required argument 'app_name'."}

                verdict, reason = classify_app_operation(app_name, action="close")
                if verdict == PolicyVerdict.BLOCKED:
                    return {"success": False, "status": "BLOCKED", "error": reason}

                token = arguments.get("confirmation_token")
                if not token:
                    pending = self.confirmation.create_pending_confirmation(
                        tool_name="close_app",
                        arguments=arguments,
                        session_id=session_id,
                    )
                    return {
                        "success": False,
                        "status": "CONFIRM_REQUIRED",
                        "action": "close_app",
                        "target": app_name,
                        "confirmation_token": pending.token,
                        "message": f"Closing '{app_name}' may discard unsaved state. Explicit confirmation required.",
                        "prompt_user": f"Ask user: 'Are you sure you want to close {app_name}?' Once confirmed, call close_app with confirmation_token='{pending.token}'.",
                    }

                valid, msg = self.confirmation.validate_and_consume(
                    token=token,
                    tool_name="close_app",
                    arguments=arguments,
                    session_id=session_id,
                )
                if not valid:
                    return {"success": False, "status": "CONFIRMATION_INVALID", "error": msg}

                return close_application(app_name)

            # 7. File Reader
            elif tool_name == "read_file":
                path_str = str(arguments.get("path", "")).strip()
                if not path_str:
                    return {"success": False, "error": "Missing required argument 'path'."}

                verdict, reason = classify_file_operation("read", path_str, self.workspace_root)
                if verdict == PolicyVerdict.BLOCKED:
                    return {"success": False, "status": "BLOCKED", "error": reason}

                return read_workspace_file(path_str, self.workspace_root)

            # 8. File Writer (Requires Confirmation Token)
            elif tool_name == "write_file":
                path_str = str(arguments.get("path", "")).strip()
                content = str(arguments.get("content", ""))
                if not path_str:
                    return {"success": False, "error": "Missing required argument 'path'."}

                verdict, reason = classify_file_operation("write", path_str, self.workspace_root)
                if verdict == PolicyVerdict.BLOCKED:
                    return {"success": False, "status": "BLOCKED", "error": reason}

                token = arguments.get("confirmation_token")
                if not token:
                    pending = self.confirmation.create_pending_confirmation(
                        tool_name="write_file",
                        arguments=arguments,
                        session_id=session_id,
                    )
                    return {
                        "success": False,
                        "status": "CONFIRM_REQUIRED",
                        "action": "write_file",
                        "target": path_str,
                        "confirmation_token": pending.token,
                        "message": f"Writing to '{path_str}' requires explicit user confirmation.",
                        "prompt_user": f"Ask user: 'Confirm writing to {path_str}?' Once confirmed, call write_file with confirmation_token='{pending.token}'.",
                    }

                valid, msg = self.confirmation.validate_and_consume(
                    token=token,
                    tool_name="write_file",
                    arguments=arguments,
                    session_id=session_id,
                )
                if not valid:
                    return {"success": False, "status": "CONFIRMATION_INVALID", "error": msg}

                return write_workspace_file(path_str, content, self.workspace_root)

            # 9. File Deleter (Requires Confirmation Token)
            elif tool_name == "delete_file":
                path_str = str(arguments.get("path", "")).strip()
                if not path_str:
                    return {"success": False, "error": "Missing required argument 'path'."}

                verdict, reason = classify_file_operation("delete", path_str, self.workspace_root)
                if verdict == PolicyVerdict.BLOCKED:
                    return {"success": False, "status": "BLOCKED", "error": reason}

                token = arguments.get("confirmation_token")
                if not token:
                    pending = self.confirmation.create_pending_confirmation(
                        tool_name="delete_file",
                        arguments=arguments,
                        session_id=session_id,
                    )
                    return {
                        "success": False,
                        "status": "CONFIRM_REQUIRED",
                        "action": "delete_file",
                        "target": path_str,
                        "confirmation_token": pending.token,
                        "message": f"Deleting '{path_str}' is permanent and requires explicit confirmation.",
                        "prompt_user": f"Ask user: 'Are you sure you want to permanently delete {path_str}?' Once confirmed, call delete_file with confirmation_token='{pending.token}'.",
                    }

                valid, msg = self.confirmation.validate_and_consume(
                    token=token,
                    tool_name="delete_file",
                    arguments=arguments,
                    session_id=session_id,
                )
                if not valid:
                    return {"success": False, "status": "CONFIRMATION_INVALID", "error": msg}

                return delete_workspace_file(path_str, self.workspace_root)

            # 10. List Directory
            elif tool_name == "list_directory":
                path_str = str(arguments.get("path", "")).strip()
                verdict, reason = classify_file_operation("list", path_str or ".", self.workspace_root)
                if verdict == PolicyVerdict.BLOCKED:
                    return {"success": False, "status": "BLOCKED", "error": reason}
                return list_workspace_directory(path_str, self.workspace_root)

            # 11. Get File Info
            elif tool_name == "get_file_info":
                path_str = str(arguments.get("path", "")).strip()
                if not path_str:
                    return {"success": False, "error": "Missing required argument 'path'."}
                verdict, reason = classify_file_operation("info", path_str, self.workspace_root)
                if verdict == PolicyVerdict.BLOCKED:
                    return {"success": False, "status": "BLOCKED", "error": reason}
                return get_workspace_file_info(path_str, self.workspace_root)

            # 12. Create Directory
            elif tool_name == "create_directory":
                path_str = str(arguments.get("path", "")).strip()
                if not path_str:
                    return {"success": False, "error": "Missing required argument 'path'."}
                verdict, reason = classify_file_operation("create_dir", path_str, self.workspace_root)
                if verdict == PolicyVerdict.BLOCKED:
                    return {"success": False, "status": "BLOCKED", "error": reason}
                return create_workspace_directory(path_str, self.workspace_root)

            # 13. Copy File (Requires Confirmation Token)
            elif tool_name == "copy_file":
                src_str = str(arguments.get("source", "")).strip()
                dst_str = str(arguments.get("destination", "")).strip()
                if not src_str or not dst_str:
                    return {"success": False, "error": "Missing required arguments 'source' and 'destination'."}

                verdict_src, _ = classify_file_operation("read", src_str, self.workspace_root)
                verdict_dst, reason_dst = classify_file_operation("copy", dst_str, self.workspace_root)
                if verdict_src == PolicyVerdict.BLOCKED or verdict_dst == PolicyVerdict.BLOCKED:
                    return {"success": False, "status": "BLOCKED", "error": reason_dst}

                token = arguments.get("confirmation_token")
                if not token:
                    pending = self.confirmation.create_pending_confirmation(
                        tool_name="copy_file",
                        arguments=arguments,
                        session_id=session_id,
                    )
                    return {
                        "success": False,
                        "status": "CONFIRM_REQUIRED",
                        "action": "copy_file",
                        "target": f"{src_str} -> {dst_str}",
                        "confirmation_token": pending.token,
                        "message": f"Copying '{src_str}' to '{dst_str}' requires explicit confirmation.",
                        "prompt_user": f"Confirm copy of '{src_str}' to '{dst_str}'?",
                    }

                valid, msg = self.confirmation.validate_and_consume(
                    token=token,
                    tool_name="copy_file",
                    arguments=arguments,
                    session_id=session_id,
                )
                if not valid:
                    return {"success": False, "status": "CONFIRMATION_INVALID", "error": msg}

                return copy_workspace_file(src_str, dst_str, self.workspace_root)

            # 14. Move File (Requires Confirmation Token)
            elif tool_name == "move_file":
                src_str = str(arguments.get("source", "")).strip()
                dst_str = str(arguments.get("destination", "")).strip()
                if not src_str or not dst_str:
                    return {"success": False, "error": "Missing required arguments 'source' and 'destination'."}

                verdict_src, _ = classify_file_operation("read", src_str, self.workspace_root)
                verdict_dst, reason_dst = classify_file_operation("move", dst_str, self.workspace_root)
                if verdict_src == PolicyVerdict.BLOCKED or verdict_dst == PolicyVerdict.BLOCKED:
                    return {"success": False, "status": "BLOCKED", "error": reason_dst}

                token = arguments.get("confirmation_token")
                if not token:
                    pending = self.confirmation.create_pending_confirmation(
                        tool_name="move_file",
                        arguments=arguments,
                        session_id=session_id,
                    )
                    return {
                        "success": False,
                        "status": "CONFIRM_REQUIRED",
                        "action": "move_file",
                        "target": f"{src_str} -> {dst_str}",
                        "confirmation_token": pending.token,
                        "message": f"Moving '{src_str}' to '{dst_str}' requires explicit confirmation.",
                        "prompt_user": f"Confirm move of '{src_str}' to '{dst_str}'?",
                    }

                valid, msg = self.confirmation.validate_and_consume(
                    token=token,
                    tool_name="move_file",
                    arguments=arguments,
                    session_id=session_id,
                )
                if not valid:
                    return {"success": False, "status": "CONFIRMATION_INVALID", "error": msg}

                return move_workspace_file(src_str, dst_str, self.workspace_root)

            # 15. Clipboard: Read Clipboard
            elif tool_name == "read_clipboard":
                return read_clipboard()

            # 16. Clipboard: Write Clipboard
            elif tool_name == "write_clipboard":
                text_val = str(arguments.get("text", ""))
                return write_clipboard(text_val)

            # 17. Window Awareness: Active Window & Window List
            elif tool_name in ("get_active_window", "get_window_title"):
                return get_active_window_info()

            elif tool_name == "enumerate_windows":
                return enumerate_windows()

            # 18. Memory Management: Remember Fact
            elif tool_name == "remember_fact":
                key = str(arguments.get("key", "")).strip()
                val = str(arguments.get("value", "")).strip()
                ok, msg = self.memory.remember(key, val)
                return {"success": ok, "message": msg}

            # 19. Memory Management: Forget Fact
            elif tool_name == "forget_fact":
                key = str(arguments.get("key", "")).strip()
                ok, msg = self.memory.forget(key)
                return {"success": ok, "message": msg}

            # 20. Memory Management: List Memories
            elif tool_name == "list_memories":
                memories = self.memory.list_memories()
                return {"success": True, "count": len(memories), "memories": memories}

            # Phase 7 — Controlled Chrome and Windows Application Adapters
            elif tool_name.startswith("chrome_") or tool_name.startswith("windows_"):
                # Confirmation Gate for sensitive operations
                if tool_name in ("chrome_download_file", "chrome_close", "windows_close_app"):
                    token = arguments.get("confirmation_token")
                    target_repr = str(arguments.get("url") or arguments.get("destination") or arguments.get("app_name") or "session")
                    if not token:
                        pending = self.confirmation.create_pending_confirmation(
                            tool_name=tool_name,
                            arguments=arguments,
                            session_id=session_id,
                        )
                        return {
                            "success": False,
                            "status": "CONFIRM_REQUIRED",
                            "action": tool_name,
                            "target": target_repr,
                            "confirmation_token": pending.token,
                            "message": f"Action '{tool_name}' on '{target_repr}' requires explicit user confirmation.",
                            "prompt_user": f"Confirm {tool_name} on {target_repr}?",
                        }

                    valid, msg = self.confirmation.validate_and_consume(
                        token=token,
                        tool_name=tool_name,
                        arguments=arguments,
                        session_id=session_id,
                    )
                    if not valid:
                        return {"success": False, "status": "CONFIRMATION_INVALID", "error": msg}

                return await self.app_registry.execute_capability(
                    capability=tool_name,
                    arguments=arguments,
                    session_id=session_id,
                )

            else:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' is not registered in ULTRON local tool gateway.",
                }

        except Exception as e:
            logger.error(f"[Tool Gateway] Tool execution error: {e}", exc_info=True)
            return {"success": False, "error": f"Local execution fault: {str(e)}"}
