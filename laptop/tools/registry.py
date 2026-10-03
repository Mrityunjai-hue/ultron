"""
ULTRON Tool Registry & Dispatcher v2.0
─────────────────────────────────────────────────────────────────────────────
Central registry providing:
- Standard OpenAI/Ollama 0.3+ JSON tool definitions
- Type-safe dispatching
- Automated safety policy checks & audit logging
- Confirmation coordination
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import time
import json
import logging
from typing import Dict, Any, List, Optional, Callable

from laptop.tools.file_ops import FileOpsTool
from laptop.tools.app_control import AppControlTool
from laptop.tools.shell import ShellTool
from laptop.tools.system_info import SystemInfoTool
from laptop.safety.confirm import ConfirmationManager
from laptop.safety.audit_log import AuditLogger

logger = logging.getLogger("ultron.tools.registry")

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Retrieves the current system local time, date, day of week, and timezone. Use whenever the user asks for the time, date, or clock.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Retrieves hardware and operating system status (CPU, memory, platform).",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Searches for files matching a pattern in the allowed workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match, e.g. '*.py' or 'report.txt'",
                    },
                    "dir_path": {
                        "type": "string",
                        "description": "Optional relative subdirectory to search within.",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads text content from a file within the allowed workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path of the file to read.",
                    },
                    "max_bytes": {
                        "type": "integer",
                        "description": "Maximum bytes to read (default 8000).",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Creates or overwrites a file with content within the allowed workspace. Overwriting an existing file requires user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path of the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to write to the file.",
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "Set to true if user confirmed overwriting existing file.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Permanently deletes a file within the allowed workspace. Always requires user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path of the file to delete.",
                    },
                    "confirmed": {
                        "type": "boolean",
                        "description": "Must be set to true by user confirmation to proceed.",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Launches a desktop application on Windows and verifies PID initialization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name or executable of the application (e.g. 'notepad', 'calc', 'chrome').",
                    },
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_app",
            "description": "Terminates a running application on Windows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name or executable of the application to close (e.g. 'notepad', 'calc').",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Forcefully terminate process if true.",
                    },
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_running_apps",
            "description": "Lists active desktop processes running on the machine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of processes to return (default 15).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shell",
            "description": "Executes a safe shell command. Whitelisted read commands are safe; unlisted commands require confirmation. 10-second timeout.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute.",
                    },
                    "confirmed": {
                        "type": "boolean",
                        "description": "Must be true if user explicitly confirmed execution.",
                    },
                },
                "required": ["command"],
            },
        },
    },
]

class ToolRegistry:
    """Manages tool execution, safety gating, and audit logging."""

    def __init__(
        self,
        confirm_manager: Optional[ConfirmationManager] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.file_ops = FileOpsTool()
        self.app_control = AppControlTool()
        self.shell_tool = ShellTool()
        self.system_info = SystemInfoTool()
        self.confirm_manager = confirm_manager or ConfirmationManager()
        self.audit_logger = audit_logger or AuditLogger()

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns standard tool schemas for LLM prompts or API payload."""
        return TOOL_SCHEMAS

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes a registered tool by name with arguments and logs audit event.
        """
        start_time = time.time()
        result: Dict[str, Any] = {}
        verdict = "SAFE"
        error: Optional[str] = None

        try:
            if tool_name == "get_current_time":
                result = self.system_info.get_current_time()
            elif tool_name == "get_system_status":
                result = self.system_info.get_system_status()
            elif tool_name == "search_files":
                result = self.file_ops.search_files(
                    pattern=arguments.get("pattern", "*"),
                    dir_path=arguments.get("dir_path"),
                )
            elif tool_name == "read_file":
                result = self.file_ops.read_file(
                    path=arguments.get("path", ""),
                    max_bytes=arguments.get("max_bytes", 8000),
                )
            elif tool_name == "write_file":
                result = self.file_ops.write_file(
                    path=arguments.get("path", ""),
                    content=arguments.get("content", ""),
                    overwrite=arguments.get("overwrite", False),
                )
                if result.get("status") == "CONFIRM_REQUIRED":
                    verdict = "CONFIRM_REQUIRED"
                    # Register pending confirmation
                    self.confirm_manager.request_confirmation(
                        tool_name="write_file",
                        description=f"Overwrite existing file: {arguments.get('path')}",
                        arguments=arguments,
                    )
            elif tool_name == "delete_file":
                result = self.file_ops.delete_file(
                    path=arguments.get("path", ""),
                    confirmed=arguments.get("confirmed", False),
                )
                if result.get("status") == "CONFIRM_REQUIRED":
                    verdict = "CONFIRM_REQUIRED"
                    self.confirm_manager.request_confirmation(
                        tool_name="delete_file",
                        description=f"Permanently delete file: {arguments.get('path')}",
                        arguments=arguments,
                    )
            elif tool_name == "open_app":
                result = self.app_control.open_app(arguments.get("app_name", ""))
            elif tool_name == "close_app":
                result = self.app_control.close_app(
                    app_name=arguments.get("app_name", ""),
                    force=arguments.get("force", False),
                )
            elif tool_name == "list_running_apps":
                result = self.app_control.list_running_apps(
                    limit=arguments.get("limit", 15),
                )
            elif tool_name == "shell":
                result = self.shell_tool.execute(
                    command=arguments.get("command", ""),
                    confirmed=arguments.get("confirmed", False),
                )
                if result.get("status") == "CONFIRM_REQUIRED":
                    verdict = "CONFIRM_REQUIRED"
                    self.confirm_manager.request_confirmation(
                        tool_name="shell",
                        description=f"Execute shell command: {arguments.get('command')}",
                        arguments=arguments,
                    )
            else:
                error = f"Unrecognized tool: {tool_name}"
                result = {"success": False, "error": error}
                verdict = "ERROR"

        except Exception as e:
            error = str(e)
            result = {"success": False, "error": error}
            verdict = "ERROR"
        finally:
            elapsed = (time.time() - start_time) * 1000.0
            # Log audit entry
            self.audit_logger.log(
                tool_name=tool_name,
                arguments=arguments,
                verdict=verdict,
                user=user,
                success=result.get("success", False),
                duration_ms=elapsed,
                result_summary=result.get("status", "COMPLETED"),
                error=error or result.get("error"),
            )

        return result
