"""
ULTRON v2.0 — Canonical Activity States & Authoritative Event Model
─────────────────────────────────────────────────────────────────────────────
Strict separation between:
1. ActivityState: What phase ULTRON is in (IDLE, LISTENING, THINKING, EXECUTING, RESPONDING, ERROR, OFFLINE, RECONNECTING)
2. MoodState: How the character expresses that state (CALM, ATTENTIVE, FOCUSED, CURIOUS, CONCERNED, WARNING)
3. Operation: What specific tool is running (search_files, read_file, open_app, shell, etc.)
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import time
from enum import Enum
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field

class ActivityState(str, Enum):
    IDLE = "IDLE"                    # Standby, listening for wake trigger, compact notch (320x36)
    LISTENING = "LISTENING"          # Capturing speech input (640x420)
    THINKING = "THINKING"            # LLM reasoning / generating (640x420)
    EXECUTING = "EXECUTING"          # Running a verified tool action (640x420)
    RESPONDING = "RESPONDING"        # Playing synthesized TTS speech (640x420)
    ERROR = "ERROR"                  # Real fault occurred (hardware, network, tool failure)
    OFFLINE = "OFFLINE"              # Local LLM unavailable (Ollama unreachable)
    RECONNECTING = "RECONNECTING"    # Reconnecting to backend bridge

class MoodState(str, Enum):
    CALM = "CALM"                    # Default sovereign demeanor
    ATTENTIVE = "ATTENTIVE"          # User presence detected, listening closely
    FOCUSED = "FOCUSED"              # Executing precise technical tools
    CURIOUS = "CURIOUS"              # Exploring ambiguous user questions
    CONCERNED = "CONCERNED"          # Destructive action / safety alert
    WARNING = "WARNING"              # Hardware error or rate limit

class AuthoritativeEvent(BaseModel):
    """
    Single source of truth emitted by the Core Orchestrator.
    Consumed independently by:
    1. Rive Character Engine (animation, eye shape, acoustic layer)
    2. Native Launcher (notch window resizing 320x36 ↔ 640x420)
    """
    activity: ActivityState = Field(..., description="Canonical activity state")
    operation: str = Field(default="none", description="Active operation metadata")
    mood: MoodState = Field(default=MoodState.CALM, description="Orthogonal emotional context")
    attention: float = Field(default=0.5, ge=0.0, le=1.0, description="Attentiveness factor")
    gaze_x: float = Field(default=0.0, ge=-1.0, le=1.0, description="Horizontal gaze offset")
    gaze_y: float = Field(default=0.0, ge=-1.0, le=1.0, description="Vertical gaze offset")
    voice_amplitude: float = Field(default=0.0, ge=0.0, le=1.0, description="ElevenLabs vocal RMS amplitude")
    progress: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Optional task completion progress")
    detail: Optional[str] = Field(default=None, description="Human-readable status detail")
    error: Optional[str] = Field(default=None, description="Error message if in ERROR or OFFLINE state")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp of event generation")

    def to_legacy_ui_state(self) -> str:
        """
        Maps canonical backend activity and operation to legacy UI state names
        for backward-compatibility with ui/orb/ until Rive is fully active.
        Zero fake states are generated: 'searching' is only returned when
        operation == 'search_files'.
        """
        if self.activity == ActivityState.IDLE:
            return "idle"
        elif self.activity == ActivityState.LISTENING:
            return "listening"
        elif self.activity == ActivityState.THINKING:
            return "thinking"
        elif self.activity == ActivityState.EXECUTING:
            if self.operation == "search_files":
                return "searching"
            return "processing"
        elif self.activity == ActivityState.RESPONDING:
            return "speaking"
        elif self.activity == ActivityState.ERROR:
            return "error"
        elif self.activity == ActivityState.OFFLINE:
            return "warning"
        elif self.activity == ActivityState.RECONNECTING:
            return "idle"
        return "idle"

    def to_rive_inputs(self) -> Dict[str, Any]:
        """
        Converts the authoritative event to typed inputs for the Rive state machine ULTRON_SM.
        """
        activity_numeric = {
            ActivityState.IDLE: 0,
            ActivityState.LISTENING: 1,
            ActivityState.THINKING: 2,
            ActivityState.EXECUTING: 3,
            ActivityState.RESPONDING: 4,
            ActivityState.ERROR: 5,
            ActivityState.OFFLINE: 6,
            ActivityState.RECONNECTING: 7,
        }.get(self.activity, 0)

        operation_numeric = {
            "none": 0,
            "search_files": 1,
            "read_file": 2,
            "write_file": 3,
            "open_app": 4,
            "close_app": 4,
            "shell": 5,
        }.get(self.operation, 0)

        mood_numeric = {
            MoodState.CALM: 0,
            MoodState.ATTENTIVE: 1,
            MoodState.FOCUSED: 2,
            MoodState.CURIOUS: 3,
            MoodState.CONCERNED: 4,
            MoodState.WARNING: 5,
        }.get(self.mood, 0)

        return {
            "activity": activity_numeric,
            "operationId": operation_numeric,
            "moodId": mood_numeric,
            "gazeX": self.gaze_x,
            "gazeY": self.gaze_y,
            "attention": self.attention,
            "voiceAmplitude": self.voice_amplitude,
        }
