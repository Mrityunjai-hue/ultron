"""
ULTRON Voice Subsystem v2.0 — ElevenLabs Streaming TTS with Real-Time Amplitude
─────────────────────────────────────────────────────────────────────────────
Voice Profile:
- Engine: ElevenLabs Streaming via Server Bridge (POST /api/tts/stream)
- Voice ID: 5vpfPL62TWuqhC30bkVm (Deep, resonant, cold machine intellect)
- Latency Mode: optimize_streaming_latency=3 (<300ms time-to-first-chunk)
- Acoustic Telemetry: Real-time RMS amplitude calculation for Rive visualizer
- Fallback: Local pyttsx3 when ElevenLabs API key is unavailable
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import os
import io
import math
import struct
import asyncio
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any

import httpx

logger = logging.getLogger("ultron.voice.tts")

DEFAULT_VOICE_ID = "5vpfPL62TWuqhC30bkVm"

class TTS:
    """Unified ElevenLabs streaming TTS client with acoustic amplitude telemetry."""

    def __init__(self, speaker, config: dict):
        self.speaker = speaker
        self.config = config
        voice_cfg = config.get("voice", {})
        self.engine = voice_cfg.get("engine", "elevenlabs")
        self.voice_id = voice_cfg.get("voice_id", DEFAULT_VOICE_ID)
        self.server_url = voice_cfg.get("server_url", "http://localhost:8080")
        self.client = httpx.AsyncClient(timeout=15.0)

        self._pyttsx3 = None
        self._is_speaking = False
        self._current_amplitude = 0.0

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    @property
    def current_amplitude(self) -> float:
        return self._current_amplitude

    def _calculate_chunk_amplitude(self, chunk: bytes) -> float:
        """Estimates normalized RMS amplitude [0.0 - 1.0] from raw audio bytes."""
        if not chunk or len(chunk) < 4:
            return 0.0
        try:
            # Sample every 16 bytes for speed
            samples = [abs(b - 128) / 128.0 for b in chunk[::16]]
            if not samples:
                return 0.0
            rms = math.sqrt(sum(s * s for s in samples) / len(samples))
            return min(1.0, max(0.0, rms * 1.8))
        except Exception:
            return 0.0

    async def synthesize_stream(
        self,
        text: str,
        on_chunk: Optional[Callable[[bytes, float], None]] = None,
    ) -> Optional[bytes]:
        """
        Streams audio chunks from the server ElevenLabs endpoint:
        POST /api/tts/stream
        Calls on_chunk(data, amplitude) as each chunk arrives.
        """
        clean_text = text.strip()
        if not clean_text:
            return None

        # Try server-side ElevenLabs streaming
        try:
            url = f"{self.server_url}/api/tts/stream"
            payload = {
                "text": clean_text,
                "voice_id": self.voice_id,
            }

            accumulated = bytearray()
            async with self.client.stream("POST", url, json=payload, timeout=12.0) as resp:
                if resp.status_code == 200:
                    self._is_speaking = True
                    async for chunk in resp.aiter_bytes():
                        if chunk:
                            accumulated.extend(chunk)
                            amp = self._calculate_chunk_amplitude(chunk)
                            self._current_amplitude = amp
                            if on_chunk:
                                on_chunk(chunk, amp)

                    self._is_speaking = False
                    self._current_amplitude = 0.0
                    return bytes(accumulated)

                elif resp.status_code == 401:
                    logger.info("ElevenLabs API key not active on server; falling back to pyttsx3.")
                else:
                    logger.warning(f"Server TTS stream returned {resp.status_code}")
        except Exception as e:
            logger.debug(f"Server TTS stream error (falling back to pyttsx3): {e}")

        # Fallback to local pyttsx3
        self._is_speaking = False
        self._current_amplitude = 0.0
        return None

    async def play(self, audio_or_text, on_amplitude: Optional[Callable[[float], None]] = None):
        """Plays synthesized audio bytes or speaks text directly via fallback."""
        if isinstance(audio_or_text, bytes):
            self._is_speaking = True
            try:
                if self.speaker and hasattr(self.speaker, "play"):
                    await self.speaker.play(audio_or_text)
            finally:
                self._is_speaking = False
                self._current_amplitude = 0.0
        elif isinstance(audio_or_text, str):
            # Text passed directly: Attempt ElevenLabs stream first, else fallback
            audio = await self.synthesize_stream(
                audio_or_text,
                on_chunk=lambda chunk, amp: on_amplitude(amp) if on_amplitude else None,
            )
            if audio and self.speaker:
                await self.speaker.play(audio)
            else:
                await self._play_pyttsx3(audio_or_text)

    async def _play_pyttsx3(self, text: str):
        """Local desktop speech synthesizer fallback."""
        self._is_speaking = True
        try:
            if not self._pyttsx3:
                import pyttsx3
                engine = pyttsx3.init()
                voices = engine.getProperty("voices")
                for v in voices:
                    if "david" in v.name.lower() or "male" in v.name.lower():
                        engine.setProperty("voice", v.id)
                        break
                engine.setProperty("rate", 155)
                engine.setProperty("volume", 0.95)
                self._pyttsx3 = engine

            def _speak():
                self._pyttsx3.say(text)
                self._pyttsx3.runAndWait()

            await asyncio.to_thread(_speak)
        except Exception as e:
            logger.error(f"pyttsx3 speech error: {e}")
        finally:
            self._is_speaking = False
            self._current_amplitude = 0.0

    async def close(self):
        await self.client.aclose()
