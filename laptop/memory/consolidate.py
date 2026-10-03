"""
ULTRON Memory Consolidation Engine v2.0
─────────────────────────────────────────────────────────────────────────────
Distills extended conversational records into compact persistent facts
and preferences to prevent context window overflow.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import logging
from typing import Dict, Any, List

logger = logging.getLogger("ultron.memory.consolidate")

class MemoryConsolidator:
    """Consolidates granular conversation turns into key semantic facts."""

    def __init__(self, memory_db):
        self.db = memory_db

    async def consolidate(self, user_name: str) -> Dict[str, Any]:
        """
        Scans older conversation turns for the user and summarizes them.
        """
        history = await self.db.get_recent_history(user_name, limit=50)
        if len(history) < 10:
            return {"status": "SKIPPED", "reason": "Insufficient dialogue history for consolidation."}

        # Analyze recurring topics or keywords
        topics = set()
        for turn in history:
            words = turn.get("user_said", "").lower().split()
            for w in words:
                if len(w) > 5 and w not in {"ultron", "please", "system", "status", "thanks"}:
                    topics.add(w)

        if topics:
            sampled_topics = ", ".join(list(topics)[:8])
            await self.db.remember_fact(user_name, "frequent_inquiry_topics", sampled_topics)
            logger.info(f"Consolidated memory for {user_name}: stored frequent_inquiry_topics = {sampled_topics}")

        return {
            "status": "SUCCESS",
            "user": user_name,
            "turns_reviewed": len(history),
            "topics_distilled": list(topics)[:8],
        }
