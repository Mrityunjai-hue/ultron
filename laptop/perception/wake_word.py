"""Wake word detection stub — plug in Porcupine or Vosk."""
from __future__ import annotations
import asyncio
import logging

logger = logging.getLogger("ultron.perception.wake_word")

class WakeWordDetector:
    """Stub implementation. Replace with Porcupine or Vosk in production."""
    def __init__(self, config: dict):
        self.keyword = config.get("wake_word", {}).get("keyword", "ultron")
        self._pending = False

    async def listen(self):
        """Continuously monitor audio for wake word."""
        while True:
            await asyncio.sleep(0.1)
            # Production: check Porcupine frame result here

    def trigger(self):
        """Manual trigger for testing."""
        self._pending = True

    async def detected(self) -> bool:
        if self._pending:
            self._pending = False
            return True
        return False
