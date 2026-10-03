"""
ULTRON V3 — Unified Memory Manager
─────────────────────────────────────────────────────────────────────────────
Orchestrates bounded session memory and persistent local facts/preferences.
Feeds memory context into centralized identity and tool gateway.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional, List, Dict, Any

from ultron.memory.session import SessionMemory
from ultron.memory.persistent import PersistentMemory
from ultron.core.identity import build_system_instruction

class MemoryManager:
    """Unified memory subsystem managing session context and persistent state."""

    def __init__(
        self,
        storage_path: Optional[Path | str] = None,
        max_session_turns: int = 40,
        max_persistent_items: int = 50,
    ):
        self.session = SessionMemory(max_turns=max_session_turns)
        self.persistent = PersistentMemory(
            storage_path=storage_path,
            max_items=max_persistent_items,
        )

    def record_turn(
        self,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        tool_result: Optional[Dict[str, Any]] = None,
        **metadata,
    ):
        """Records a turn in ephemeral session memory."""
        self.session.record_turn(
            role=role,
            content=content,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
            **metadata,
        )

    def remember(self, key: str, value: str, category: str = "preference"):
        """Persists a fact or preference."""
        return self.persistent.remember(key, value, category)

    def forget(self, key_or_pattern: str):
        """Forgets a persistent fact."""
        return self.persistent.forget(key_or_pattern)

    def list_memories(self) -> List[Dict[str, Any]]:
        """Lists all persistent memories."""
        return self.persistent.list_memories()

    def get_system_instruction(self) -> str:
        """Builds active system instruction with injected persistent facts and context."""
        facts = self.persistent.get_all_facts()
        context = self.session.get_context_summary()
        return build_system_instruction(persistent_facts=facts, recent_context_summary=context)

    def clear_session(self):
        """Clears ephemeral session state."""
        self.session.clear()
