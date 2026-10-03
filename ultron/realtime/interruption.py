"""
ULTRON V3 — Local Barge-In & Interruption Protection
─────────────────────────────────────────────────────────────────────────────
Lightweight energy detector for instant local playback cancellation.
Server-side VAD in Gemini Live remains the primary conversational turn detector.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import logging
import time
from typing import Callable, Optional

from ultron.realtime.audio_stream import AudioStreamEngine

logger = logging.getLogger("ultron.realtime.interruption")

class InterruptionManager:
    """Detects user speech during model playback to trigger instant cancellation."""

    def __init__(
        self,
        audio_engine: AudioStreamEngine,
        rms_threshold: float = 0.20,
        consecutive_frames_required: int = 4,
        on_interruption: Optional[Callable[[float], None]] = None,
        enabled: bool = True,
    ):
        self.audio_engine = audio_engine
        self.rms_threshold = rms_threshold
        self.consecutive_frames_required = consecutive_frames_required
        self.on_interruption = on_interruption
        self.enabled = enabled

        self._consecutive_loud_frames = 0
        self.last_interruption_timestamp = 0.0
        self.last_detection_latency_ms = 0.0

    def process_input_frame(self, pcm_bytes: bytes, rms_energy: float):
        """Evaluates incoming input frame for barge-in if model is actively speaking."""
        # Only evaluate barge-in if enabled and ULTRON is currently outputting sound
        if not self.enabled or not self.audio_engine.is_playing:
            self._consecutive_loud_frames = 0
            return

        t0 = time.perf_counter()

        if rms_energy >= self.rms_threshold:
            self._consecutive_loud_frames += 1
        else:
            self._consecutive_loud_frames = max(0, self._consecutive_loud_frames - 1)

        if self._consecutive_loud_frames >= self.consecutive_frames_required:
            self._consecutive_loud_frames = 0
            t_detect = (time.perf_counter() - t0) * 1000.0
            self.last_detection_latency_ms = round(t_detect, 2)
            self.last_interruption_timestamp = time.time()

            logger.info(f"[Barge-In] User speech detected during playback (RMS: {rms_energy:.4f}, Detect Latency: {self.last_detection_latency_ms}ms)")

            # 1. Immediately halt local audio hardware output
            flush_latency = self.audio_engine.clear_playback()

            # 2. Trigger interruption callback to notify cloud session
            if self.on_interruption:
                self.on_interruption(self.last_detection_latency_ms + flush_latency)
