"""
ULTRON V3 — Minimal Tool Registry & Declarations
─────────────────────────────────────────────────────────────────────────────
Defines minimal JSON function declarations for Gemini Live.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
from typing import List, Dict, Any

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ToolCapability:
    """Structured local capability metadata for planning and safety."""
    name: str
    description: str
    parameters: Dict[str, Any]
    safety_class: str = "SAFE"                 # SAFE | CONFIRM_REQUIRED | BLOCKED
    requires_confirmation: bool = False
    is_reversible: bool = False
    supports_verification: bool = True
    timeout_sec: float = 15.0
    cancellation_behavior: str = "safe_abort"  # safe_abort | atomic

TOOL_CAPABILITIES: Dict[str, ToolCapability] = {
    "get_current_time": ToolCapability(
        name="get_current_time",
        description="Returns the authoritative current local time, date, and timezone on the user's desktop.",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=5.0,
    ),
    "get_system_status": ToolCapability(
        name="get_system_status",
        description="Retrieves real-time system substrate statistics including CPU utilization, memory usage, and OS details.",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=5.0,
    ),
    "get_active_app": ToolCapability(
        name="get_active_app",
        description="Retrieves the current foreground desktop application name, window title, and process ID.",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=5.0,
    ),
    "get_running_apps": ToolCapability(
        name="get_running_apps",
        description="Retrieves the list of active user applications currently running on the desktop.",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=8.0,
    ),
    "open_app": ToolCapability(
        name="open_app",
        description="Opens a desktop application safely by name (e.g., 'notepad', 'calc', 'chrome').",
        parameters={
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Name or executable of the application to launch."},
            },
            "required": ["app_name"],
        },
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=15.0,
    ),
    "close_app": ToolCapability(
        name="close_app",
        description="Terminates running instances of a desktop application by name. Requires explicit user confirmation.",
        parameters={
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Name or executable of the application to close."},
                "confirmation_token": {"type": "string", "description": "One-time confirmation token."},
            },
            "required": ["app_name"],
        },
        safety_class="CONFIRM_REQUIRED",
        requires_confirmation=True,
        is_reversible=False,
        supports_verification=True,
        timeout_sec=10.0,
    ),
    "read_file": ToolCapability(
        name="read_file",
        description="Reads the text content of a file located within the active project workspace.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative or absolute path of the file to inspect."},
            },
            "required": ["path"],
        },
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=8.0,
    ),
    "write_file": ToolCapability(
        name="write_file",
        description="Writes or modifies a file located strictly within the active workspace. Requires explicit user confirmation.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path of the file inside the project workspace."},
                "content": {"type": "string", "description": "Text content to write into the file."},
                "confirmation_token": {"type": "string", "description": "One-time confirmation token."},
            },
            "required": ["path", "content"],
        },
        safety_class="CONFIRM_REQUIRED",
        requires_confirmation=True,
        is_reversible=False,
        supports_verification=True,
        timeout_sec=10.0,
    ),
    "delete_file": ToolCapability(
        name="delete_file",
        description="Deletes a file located strictly within the active workspace. Requires explicit user confirmation.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path of the file inside the project workspace."},
                "confirmation_token": {"type": "string", "description": "One-time confirmation token."},
            },
            "required": ["path"],
        },
        safety_class="CONFIRM_REQUIRED",
        requires_confirmation=True,
        is_reversible=False,
        supports_verification=True,
        timeout_sec=10.0,
    ),
    "list_directory": ToolCapability(
        name="list_directory",
        description="Lists all files and subdirectories located inside a workspace path.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path of directory inside workspace (default empty for root)."},
            },
        },
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=8.0,
    ),
    "get_file_info": ToolCapability(
        name="get_file_info",
        description="Retrieves metadata (existence, size, modified time) of a file or folder inside the workspace.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path of the file or directory inside workspace."},
            },
            "required": ["path"],
        },
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=5.0,
    ),
    "create_directory": ToolCapability(
        name="create_directory",
        description="Creates a new directory strictly inside the active workspace.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path of the directory to create inside workspace."},
            },
            "required": ["path"],
        },
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=False,
        supports_verification=True,
        timeout_sec=8.0,
    ),
    "copy_file": ToolCapability(
        name="copy_file",
        description="Copies a file from source to destination strictly within workspace. Requires confirmation.",
        parameters={
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source file path."},
                "destination": {"type": "string", "description": "Destination file path."},
                "confirmation_token": {"type": "string", "description": "One-time confirmation token."},
            },
            "required": ["source", "destination"],
        },
        safety_class="CONFIRM_REQUIRED",
        requires_confirmation=True,
        is_reversible=False,
        supports_verification=True,
        timeout_sec=10.0,
    ),
    "move_file": ToolCapability(
        name="move_file",
        description="Moves or renames a file from source to destination strictly within workspace. Requires confirmation.",
        parameters={
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source file path."},
                "destination": {"type": "string", "description": "Destination file path."},
                "confirmation_token": {"type": "string", "description": "One-time confirmation token."},
            },
            "required": ["source", "destination"],
        },
        safety_class="CONFIRM_REQUIRED",
        requires_confirmation=True,
        is_reversible=False,
        supports_verification=True,
        timeout_sec=10.0,
    ),
    "read_clipboard": ToolCapability(
        name="read_clipboard",
        description="Reads plain text content from the Windows system clipboard.",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=5.0,
    ),
    "write_clipboard": ToolCapability(
        name="write_clipboard",
        description="Writes text to the Windows system clipboard.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text content to copy to clipboard."},
            },
            "required": ["text"],
        },
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=5.0,
    ),
    "get_active_window": ToolCapability(
        name="get_active_window",
        description="Retrieves title and process ID of the active window.",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=5.0,
    ),
    "enumerate_windows": ToolCapability(
        name="enumerate_windows",
        description="Lists all currently open visible desktop application windows.",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=8.0,
    ),
    "remember_fact": ToolCapability(
        name="remember_fact",
        description="Persistently saves a user preference or fact to local memory across future sessions when explicitly requested.",
        parameters={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Concise key identifying the preference."},
                "value": {"type": "string", "description": "The factual detail or preference to remember."},
            },
            "required": ["key", "value"],
        },
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=5.0,
    ),
    "forget_fact": ToolCapability(
        name="forget_fact",
        description="Removes a previously remembered fact or preference from persistent memory.",
        parameters={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key or pattern of the fact to forget."},
            },
            "required": ["key"],
        },
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=5.0,
    ),
    "list_memories": ToolCapability(
        name="list_memories",
        description="Retrieves the list of all currently remembered user preferences and persistent facts.",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=5.0,
    ),
    "execute_task_plan": ToolCapability(
        name="execute_task_plan",
        description="Executes a multi-step sequence of desktop actions safely and atomically with step-by-step verification.",
        parameters={
            "type": "object",
            "properties": {
                "user_intent": {"type": "string", "description": "High level description of the task goal."},
                "steps": {
                    "type": "array",
                    "description": "Ordered sequence of action steps to execute.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool_name": {"type": "string", "description": "Tool capability name."},
                            "arguments": {"type": "object", "description": "Arguments dictionary for the tool."},
                            "purpose": {"type": "string", "description": "Intent of this individual step."},
                        },
                        "required": ["tool_name", "arguments"],
                    },
                },
            },
            "required": ["user_intent", "steps"],
        },
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=False,
        supports_verification=True,
        timeout_sec=60.0,
    ),
    "cancel_active_task": ToolCapability(
        name="cancel_active_task",
        description="Immediately stops and cancels any active multi-step desktop task currently executing.",
        parameters={
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Reason for cancellation."},
            },
        },
        safety_class="SAFE",
        requires_confirmation=False,
        is_reversible=True,
        supports_verification=True,
        timeout_sec=5.0,
    ),
    # Phase 7 — Chrome Browser Capabilities
    "chrome_launch": ToolCapability(
        name="chrome_launch",
        description="Launches or connects to Google Chrome in a controlled debugging session.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Optional initial URL to open (must be HTTP/HTTPS)."},
            },
        },
        safety_class="SAFE",
        requires_confirmation=False,
        timeout_sec=15.0,
    ),
    "chrome_get_active_tab": ToolCapability(
        name="chrome_get_active_tab",
        description="Retrieves the currently focused browser tab details (URL, title, tab ID).",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        timeout_sec=5.0,
    ),
    "chrome_navigate": ToolCapability(
        name="chrome_navigate",
        description="Navigates the active Chrome tab to a validated HTTP or HTTPS web address.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Safe HTTP/HTTPS URL to navigate to."},
            },
            "required": ["url"],
        },
        safety_class="SAFE",
        requires_confirmation=False,
        timeout_sec=20.0,
    ),
    "chrome_search": ToolCapability(
        name="chrome_search",
        description="Performs a web search in Chrome and navigates to the search results page.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query terms or keywords."},
            },
            "required": ["query"],
        },
        safety_class="SAFE",
        requires_confirmation=False,
        timeout_sec=15.0,
    ),
    "chrome_get_page_title": ToolCapability(
        name="chrome_get_page_title",
        description="Retrieves the title of the active document loaded in Google Chrome.",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        timeout_sec=5.0,
    ),
    "chrome_get_page_text": ToolCapability(
        name="chrome_get_page_text",
        description="Extracts readable text from the current webpage, wrapped strictly as untrusted external data.",
        parameters={
            "type": "object",
            "properties": {
                "max_chars": {"type": "integer", "description": "Maximum characters of text to extract (default 5000)."},
            },
        },
        safety_class="SAFE",
        requires_confirmation=False,
        timeout_sec=10.0,
    ),
    "chrome_find_link": ToolCapability(
        name="chrome_find_link",
        description="Finds hyperlinks on the current page matching keywords or titles.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword or link text to look for."},
            },
        },
        safety_class="SAFE",
        requires_confirmation=False,
        timeout_sec=8.0,
    ),
    "chrome_click_link": ToolCapability(
        name="chrome_click_link",
        description="Follows a verified link on the active webpage.",
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Link title or destination URL to click/follow."},
            },
            "required": ["target"],
        },
        safety_class="SAFE",
        requires_confirmation=False,
        timeout_sec=15.0,
    ),
    "chrome_go_back": ToolCapability(
        name="chrome_go_back",
        description="Navigates back to the previous page in browser history.",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        timeout_sec=10.0,
    ),
    "chrome_download_file": ToolCapability(
        name="chrome_download_file",
        description="Downloads a file from a URL strictly into the workspace sandbox. Requires user confirmation.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL of the file to download."},
                "destination": {"type": "string", "description": "Relative filename inside workspace."},
                "confirmation_token": {"type": "string", "description": "One-time confirmation token."},
            },
            "required": ["url"],
        },
        safety_class="CONFIRM_REQUIRED",
        requires_confirmation=True,
        timeout_sec=30.0,
    ),
    "chrome_close_tab": ToolCapability(
        name="chrome_close_tab",
        description="Closes the currently active browser tab in Google Chrome.",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        timeout_sec=8.0,
    ),
    "chrome_close": ToolCapability(
        name="chrome_close",
        description="Terminates the active Google Chrome browser session with user confirmation.",
        parameters={
            "type": "object",
            "properties": {
                "confirmation_token": {"type": "string", "description": "One-time confirmation token."},
            },
        },
        safety_class="CONFIRM_REQUIRED",
        requires_confirmation=True,
        timeout_sec=10.0,
    ),
    # Phase 7 — Windows Application Adapter Capabilities
    "windows_get_active_window": ToolCapability(
        name="windows_get_active_window",
        description="Returns details about the current foreground window on Windows desktop.",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        timeout_sec=5.0,
    ),
    "windows_enumerate_windows": ToolCapability(
        name="windows_enumerate_windows",
        description="Lists all visible desktop application windows currently open on Windows.",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        timeout_sec=8.0,
    ),
    "windows_get_running_apps": ToolCapability(
        name="windows_get_running_apps",
        description="Lists active user processes running on the desktop.",
        parameters={"type": "object", "properties": {}},
        safety_class="SAFE",
        requires_confirmation=False,
        timeout_sec=8.0,
    ),
    "windows_open_app": ToolCapability(
        name="windows_open_app",
        description="Opens a desktop application safely by name.",
        parameters={
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Name or executable of the application to launch."},
            },
            "required": ["app_name"],
        },
        safety_class="SAFE",
        requires_confirmation=False,
        timeout_sec=15.0,
    ),
    "windows_close_app": ToolCapability(
        name="windows_close_app",
        description="Closes a desktop application with confirmation.",
        parameters={
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Name of the application to close."},
                "confirmation_token": {"type": "string", "description": "One-time confirmation token."},
            },
            "required": ["app_name"],
        },
        safety_class="CONFIRM_REQUIRED",
        requires_confirmation=True,
        timeout_sec=10.0,
    ),
}

def get_tool_declarations() -> List[Dict[str, Any]]:
    """Returns the list of tool definitions for realtime session."""
    return [
        {
            "name": cap.name,
            "description": cap.description,
            "parameters": cap.parameters,
        }
        for cap in TOOL_CAPABILITIES.values()
    ]

def get_tool_capability(name: str) -> Optional[ToolCapability]:
    """Retrieves structured metadata for a tool."""
    return TOOL_CAPABILITIES.get(name)
