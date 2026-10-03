"""Scene analyzer — describes what ULTRON sees via the camera."""
from __future__ import annotations
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("ultron.perception.scene_analyzer")

class SceneAnalyzer:
    def __init__(self, config: dict):
        self.config = config
        self._model = None

    async def analyze(self, frame) -> str:
        if frame is None: return "nothing"
        return await asyncio.to_thread(self._sync_analyze, frame)

    def _sync_analyze(self, frame) -> str:
        try:
            import cv2
            h, w = frame.shape[:2]
            brightness = float(frame.mean())
            desc = []
            if brightness < 50:   desc.append("a dimly lit environment")
            elif brightness > 200: desc.append("a brightly lit environment")
            else:                  desc.append("a normally lit environment")
            desc.append(f"resolution {w}x{h}")
            return ", ".join(desc)
        except Exception as e:
            logger.error(f"Scene analysis error: {e}")
            return "an indeterminate environment"
