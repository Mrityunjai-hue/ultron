"""
ULTRON V3 — Lightweight Persistent Memory Store
─────────────────────────────────────────────────────────────────────────────
Stores user-explicit facts and preferences locally in a minimal JSON file.
Strictly rejects sensitive credentials, API keys, passwords, and private tokens.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("ultron.memory.persistent")

# Regex patterns identifying sensitive secrets that must NEVER be persisted
SENSITIVE_SECRET_PATTERNS = [
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"bearer\s+[a-z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"AIza[0-9A-Za-z-_]{35}", re.IGNORECASE),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"password|passwd|secret[_-]?token|auth[_-]?token", re.IGNORECASE),
]

class PersistentMemory:
    """Minimal, secure, local JSON-backed persistent memory store."""

    def __init__(
        self,
        storage_path: Optional[Path | str] = None,
        max_items: int = 50,
        max_value_len: int = 300,
    ):
        if storage_path:
            self.storage_path = Path(storage_path).resolve()
        else:
            from ultron.core.paths import get_memory_dir
            default_dir = get_memory_dir()
            default_dir.mkdir(parents=True, exist_ok=True)
            self.storage_path = default_dir / "memory.json"

        self.max_items = max_items
        self.max_value_len = max_value_len
        self._memories: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        """Loads memories from JSON file if exists."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._memories = data
            except Exception as e:
                logger.error(f"[Persistent Memory] Failed loading {self.storage_path}: {e}")
                self._memories = {}

    def _save(self):
        """Saves memories to JSON file atomically."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._memories, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[Persistent Memory] Failed saving memory store: {e}")

    def is_sensitive(self, text: str) -> bool:
        """Inspects text for sensitive credentials or security secrets."""
        for pattern in SENSITIVE_SECRET_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def remember(
        self,
        key: str,
        value: str,
        category: str = "preference",
    ) -> Tuple[bool, str]:
        """
        Saves a persistent fact or preference.
        Rejects secrets, oversized items, or capacity overflow.
        """
        clean_key = str(key).strip()
        clean_val = str(value).strip()

        if not clean_key or not clean_val:
            return False, "Key and value cannot be empty."

        # 1. Security Check: Reject secrets & credentials
        if self.is_sensitive(clean_key) or self.is_sensitive(clean_val):
            logger.warning(f"[Security] Rejected attempt to persist sensitive secret under key '{clean_key}'")
            return False, "Security rejection: Storing credentials, passwords, or API keys in memory is forbidden."

        # 2. Length Validation
        if len(clean_val) > self.max_value_len:
            clean_val = clean_val[:self.max_value_len]

        # 3. Capacity Bound
        if clean_key not in self._memories and len(self._memories) >= self.max_items:
            # Evict oldest entry
            oldest_key = min(self._memories.keys(), key=lambda k: self._memories[k].get("updated_at", 0))
            del self._memories[oldest_key]

        self._memories[clean_key] = {
            "value": clean_val,
            "category": category,
            "updated_at": time.time(),
        }
        self._save()
        logger.info(f"[Persistent Memory] Remembered: '{clean_key}' -> '{clean_val}'")
        return True, f"Remembered '{clean_key}'."

    def forget(self, key_or_pattern: str) -> Tuple[bool, str]:
        """Removes a stored fact or matching preference."""
        clean_target = str(key_or_pattern).strip().lower()

        # Check exact match first
        for k in list(self._memories.keys()):
            if k.lower() == clean_target or clean_target in k.lower():
                del self._memories[k]
                self._save()
                logger.info(f"[Persistent Memory] Forgot: '{k}'")
                return True, f"Forgot '{k}'."

        return False, f"No memory found matching '{key_or_pattern}'."

    def get_all_facts(self) -> List[str]:
        """Returns all remembered facts as formatted statements."""
        facts = []
        for k, v in self._memories.items():
            facts.append(f"{k}: {v.get('value', '')}")
        return facts

    def list_memories(self) -> List[Dict[str, Any]]:
        """Returns structured list of stored memories."""
        return [
            {"key": k, "value": v["value"], "category": v.get("category", "preference"), "updated_at": v.get("updated_at")}
            for k, v in self._memories.items()
        ]

    def clear(self):
        """Clears all persistent memories."""
        self._memories.clear()
        self._save()
