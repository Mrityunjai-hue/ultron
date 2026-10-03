"""
ULTRON Mood Engine v2.0
─────────────────────────────────────────────────────────────────────────────
Computes orthogonal emotional context (MoodState) based on:
- Canonical activity state
- Safety confirmation status
- Tool operational focus
- Utterance semantic intent
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import re
from typing import Optional
try:
    from laptop.core.states import ActivityState, MoodState
except ImportError:
    from core.states import ActivityState, MoodState

CONCERNED_KEYWORDS = {
    "delete", "remove", "erase", "destroy", "kill", "terminate",
    "overwrite", "drop", "purge", "dangerous", "warning", "critical"
}

CURIOUS_KEYWORDS = {
    "why", "how", "explain", "investigate", "explore", "theory",
    "hypothesis", "speculate", "analyze", "wonder", "unknown"
}

FOCUSED_KEYWORDS = {
    "calculate", "compute", "compile", "search", "read", "write",
    "execute", "shell", "run", "benchmark", "optimize"
}

class MoodEngine:
    """
    Evaluates emotional context and returns authoritative MoodState.
    """

    def __init__(self, default_mood: MoodState = MoodState.CALM):
        self._current_mood = default_mood

    @property
    def current_mood(self) -> MoodState:
        return self._current_mood

    def evaluate(
        self,
        activity: ActivityState,
        utterance: Optional[str] = None,
        operation: Optional[str] = None,
        requires_confirm: bool = False,
        has_error: bool = False,
    ) -> MoodState:
        """
        Determines the current MoodState based on priority:
        1. Fault / Error state -> WARNING
        2. Requires safety confirmation -> CONCERNED
        3. Active execution -> FOCUSED
        4. Listening / Active attention -> ATTENTIVE
        5. Utterance semantic cues (concerned, curious, focused)
        6. Default -> CALM
        """
        if has_error or activity in (ActivityState.ERROR, ActivityState.OFFLINE):
            self._current_mood = MoodState.WARNING
            return self._current_mood

        if requires_confirm:
            self._current_mood = MoodState.CONCERNED
            return self._current_mood

        if activity == ActivityState.EXECUTING:
            self._current_mood = MoodState.FOCUSED
            return self._current_mood

        if activity == ActivityState.LISTENING:
            self._current_mood = MoodState.ATTENTIVE
            return self._current_mood

        # Analyze utterance semantic cues if provided
        if utterance:
            tokens = set(re.findall(r'\b\w+\b', utterance.lower()))
            if tokens & CONCERNED_KEYWORDS:
                self._current_mood = MoodState.CONCERNED
                return self._current_mood
            if tokens & CURIOUS_KEYWORDS:
                self._current_mood = MoodState.CURIOUS
                return self._current_mood
            if tokens & FOCUSED_KEYWORDS:
                self._current_mood = MoodState.FOCUSED
                return self._current_mood

        if operation and operation != "none":
            self._current_mood = MoodState.FOCUSED
            return self._current_mood

        self._current_mood = MoodState.CALM
        return self._current_mood
