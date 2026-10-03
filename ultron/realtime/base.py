"""
ULTRON V3 — Realtime Provider Abstract Interface
─────────────────────────────────────────────────────────────────────────────
Standardized provider abstraction for realtime voice/multimodal sessions.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Callable, Dict, Any, Optional

from ultron.core.events import ActivityState

class RealtimeProvider(ABC):
    """Abstract interface for bidirectional streaming speech sessions."""

    @abstractmethod
    async def connect(self) -> None:
        """Establishes bidirectional streaming session with the cloud engine."""
        pass

    @abstractmethod
    async def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        """Streams a chunk of 16kHz PCM16 microphone audio to the model."""
        pass

    @abstractmethod
    async def receive_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Yields incoming events from the cloud model:
        - audio: {"type": "audio", "data": pcm_bytes_24k}
        - text: {"type": "text", "content": str}
        - tool_call: {"type": "tool_call", "name": str, "args": dict, "id": str}
        - interrupted: {"type": "interrupted"}
        - turn_complete: {"type": "turn_complete"}
        """
        pass

    @abstractmethod
    async def send_tool_response(self, call_id: str, name: str, response: Dict[str, Any]) -> None:
        """Sends the local execution result of a tool back to the cloud model."""
        pass

    @abstractmethod
    async def interrupt(self) -> None:
        """Notifies the cloud engine to immediately cancel its active generation turn."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully closes the realtime cloud session."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the cloud streaming session is active."""
        pass
