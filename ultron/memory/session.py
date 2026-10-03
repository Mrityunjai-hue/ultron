"""
ULTRON V3 — Ephemeral Session Memory & Context Tracker
─────────────────────────────────────────────────────────────────────────────
Stores structured in-memory conversation turns and tracks tool context
(active applications, referenced files, recent tool results) for pronoun/
reference resolution without raw audio or heavy database overhead.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ConversationTurn:
    role: str                       # 'user' | 'model' | 'tool'
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

class SessionMemory:
    """Bounded, high-efficiency in-memory conversation & context tracker."""

    def __init__(self, max_turns: int = 40):
        self.max_turns = max_turns
        self.turns: List[ConversationTurn] = []
        self.session_start = time.time()

        # Contextual target tracking for reference resolution ('it', 'that file', 'that page', 'that url')
        self.last_active_app: Optional[str] = None
        self.last_referenced_file: Optional[str] = None
        self.last_referenced_url: Optional[str] = None
        self.last_search_query: Optional[str] = None
        self.last_tool_executed: Optional[str] = None

    def record_turn(
        self,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        tool_result: Optional[Dict[str, Any]] = None,
        **metadata,
    ):
        """Records a structured turn and updates active contextual targets."""
        # 1. Update contextual targets
        if tool_name in ("open_app", "close_app", "windows_open_app", "windows_close_app") and tool_args:
            app = tool_args.get("app_name")
            if app:
                self.last_active_app = str(app).strip()

        elif tool_name in ("read_file", "write_file", "delete_file", "chrome_download_file") and tool_args:
            path = tool_args.get("path") or tool_args.get("destination")
            if path:
                self.last_referenced_file = str(path).strip()

        elif tool_name in ("chrome_navigate", "chrome_download_file") and tool_args:
            url = tool_args.get("url")
            if url:
                self.last_referenced_url = str(url).strip()
                self.last_active_app = "chrome"

        elif tool_name == "chrome_search" and tool_args:
            query = tool_args.get("query")
            if query:
                self.last_search_query = str(query).strip()
                self.last_active_app = "chrome"

        elif tool_name and tool_name.startswith("chrome_"):
            self.last_active_app = "chrome"

        if tool_name:
            self.last_tool_executed = tool_name

        # 2. Append turn
        turn = ConversationTurn(
            role=role,
            content=content,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
            metadata=metadata,
        )
        self.turns.append(turn)

        # 3. Enforce strict bounded capacity
        while len(self.turns) > self.max_turns:
            self.turns.pop(0)

    def track_target(self, entity_type: str, target: str):
        """Manually records an active target for pronoun resolution."""
        if entity_type in ("app", "application"):
            self.last_active_app = str(target).strip()
        elif entity_type in ("file", "path", "document", "download"):
            self.last_referenced_file = str(target).strip()
        elif entity_type in ("url", "link", "page", "website"):
            self.last_referenced_url = str(target).strip()
        elif entity_type in ("query", "search"):
            self.last_search_query = str(target).strip()

    def resolve_target(self, entity_type: str) -> Optional[str]:
        """Resolves pronouns ('it', 'that file', 'the app', 'that url') to active session targets."""
        if entity_type in ("app", "application"):
            return self.last_active_app
        elif entity_type in ("file", "path", "document", "download"):
            return self.last_referenced_file
        elif entity_type in ("url", "link", "page", "website"):
            return self.last_referenced_url
        elif entity_type in ("query", "search"):
            return self.last_search_query
        return None

    def get_recent_history(self, count: int = 8) -> List[ConversationTurn]:
        """Returns the most recent N structured turns."""
        return self.turns[-count:]

    def get_context_summary(self) -> str:
        """Constructs a concise summary string of active session context."""
        parts = []
        if self.last_active_app:
            parts.append(f"Last active application: {self.last_active_app}")
        if self.last_referenced_file:
            parts.append(f"Last referenced file: {self.last_referenced_file}")
        if self.last_referenced_url:
            parts.append(f"Last referenced URL: {self.last_referenced_url}")
        if self.last_tool_executed:
            parts.append(f"Last executed tool: {self.last_tool_executed}")
        return " | ".join(parts) if parts else "No active contextual targets."

    def clear(self):
        """Clears all session turns and targets."""
        self.turns.clear()
        self.last_active_app = None
        self.last_referenced_file = None
        self.last_referenced_url = None
        self.last_search_query = None
        self.last_tool_executed = None
