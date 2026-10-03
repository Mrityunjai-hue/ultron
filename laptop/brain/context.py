"""
ULTRON Context Assembler v2.0
─────────────────────────────────────────────────────────────────────────────
Bounded prompt context builder (<1500 tokens):
- Merges persona, active user, relationship tier, selective memory facts,
  and active operational status without exceeding context windows.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List
try:
    from laptop.brain.persona import build_ultron_system_prompt
    from laptop.brain.mood import MoodEngine
    from laptop.core.states import ActivityState, MoodState
except ImportError:
    from brain.persona import build_ultron_system_prompt
    from brain.mood import MoodEngine
    from core.states import ActivityState, MoodState

MAX_ESTIMATED_TOKENS = 1500
AVG_CHARS_PER_TOKEN = 4

class ContextAssembler:
    """Assembles tightly bounded prompt contexts for LLM inference."""

    def __init__(self, mood_engine: Optional[MoodEngine] = None):
        self.mood_engine = mood_engine or MoodEngine()

    def assemble(
        self,
        utterance: str,
        user: Optional[str] = None,
        confidence: float = 0.0,
        scene: str = "",
        relationship_mode: str = "STRANGER",
        interaction_count: int = 0,
        trust_score: float = 0.0,
        last_seen: str = "never",
        recent_history: Optional[List[Dict[str, Any]]] = None,
        known_facts: Optional[Dict[str, str]] = None,
        allowed_workspace: Optional[str] = None,
        activity: ActivityState = ActivityState.THINKING,
    ) -> Dict[str, Any]:
        """
        Builds the complete context payload, ensuring total characters remain
        comfortably within the 1500 token ceiling (~6000 characters).
        """
        mood = self.mood_engine.evaluate(
            activity=activity,
            utterance=utterance,
        )

        # Budget management: Limit memory facts if they are too large
        bounded_facts = {}
        if known_facts:
            total_fact_chars = 0
            for k, v in known_facts.items():
                fact_str = f"{k}: {v}"
                if total_fact_chars + len(fact_str) > 1000:
                    break
                bounded_facts[k] = v
                total_fact_chars += len(fact_str)

        # Budget management: Limit dialogue history to last 3 entries
        bounded_history = (recent_history or [])[-3:]

        system_prompt = build_ultron_system_prompt(
            user=user,
            confidence=confidence,
            scene=scene,
            relationship_mode=relationship_mode,
            interaction_count=interaction_count,
            trust_score=trust_score,
            last_seen=last_seen,
            recent_history=bounded_history,
            known_facts=bounded_facts,
            allowed_workspace=allowed_workspace,
        )

        return {
            "system_prompt": system_prompt,
            "utterance": utterance,
            "mood": mood,
            "relationship_mode": relationship_mode,
            "user": user,
            "estimated_tokens": len(system_prompt) // AVG_CHARS_PER_TOKEN,
        }
