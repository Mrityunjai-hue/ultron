"""
ULTRON Laptop Microphone Adapter v2.0 — Dual-Path Native & WebSocket STT
─────────────────────────────────────────────────────────────────────────────
Captures speech via:
1. Web Speech API events from the WebSocket UI bridge (if available)
2. Native SoundDevice recording & SpeechRecognition transcription from physical mic
3. Non-blocking queue management with clean timeout handling (never hangs)
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import asyncio
import io
import wave
import logging
import time
from typing import Optional

import numpy as np

logger = logging.getLogger("ultron.adapters.laptop.mic")

class SoundDeviceMic:
    """
    Unified microphone adapter supporting both local SoundDevice audio capture
    and WebSocket-bridged speech recognition events.
    """

    def __init__(self, config: dict):
        self.config = config
        self.sr = config.get("mic", {}).get("sample_rate", 16000)
        self._wake_q: asyncio.Queue[bool] = asyncio.Queue()
        self._utterance_q: asyncio.Queue[str] = asyncio.Queue()
        self._is_recording = False

    async def wake_word_detected(self) -> bool:
        """Non-blocking check if wake word was flagged by UI or hardware companion."""
        try:
            return self._wake_q.get_nowait()
        except asyncio.QueueEmpty:
            return False

    async def capture_utterance(self, timeout: float = 7.0) -> Optional[str]:
        """
        Captures user speech from either WebSocket UI queue or physical microphone.
        Never hangs indefinitely — returns None if timeout expires without speech.
        """
        # 1. If an utterance is already in the queue, return immediately
        try:
            queued = self._utterance_q.get_nowait()
            if queued and queued.strip():
                logger.info(f"[STT] Queued utterance consumed: {queued!r}")
                return queued.strip()
        except asyncio.QueueEmpty:
            pass

        logger.info(f"[VOICE] Listening window active (up to {timeout}s)...")

        # 2. Race between WebSocket queue and Native Microphone STT
        queue_task = asyncio.create_task(self._wait_queue(timeout))
        mic_task = asyncio.create_task(self._record_and_transcribe(timeout))

        done, pending = await asyncio.wait(
            [queue_task, mic_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        for task in done:
            try:
                res = task.result()
                if res and res.strip():
                    logger.info(f"[STT] Transcript captured: {res!r}")
                    return res.strip()
            except Exception as e:
                logger.debug(f"[STT] Capture task error: {e}")

        logger.info(f"[VOICE] Listening window ({timeout}s) expired without speech.")
        return None

    async def _wait_queue(self, timeout: float) -> Optional[str]:
        """Waits for utterance pushed from WebSocket."""
        try:
            text = await asyncio.wait_for(self._utterance_q.get(), timeout=timeout)
            return text if text and text.strip() else None
        except (asyncio.TimeoutError, asyncio.CancelledError):
            return None

    async def _record_and_transcribe(self, timeout: float) -> Optional[str]:
        """Records from local sounddevice and transcribes via speech_recognition."""
        try:
            import sounddevice as sd
            import speech_recognition as sr
        except ImportError:
            return None

        def _record_sync():
            try:
                fs = 16000
                record_sec = min(timeout, 5.0)
                logger.debug(f"[STT] Physical microphone recording for {record_sec}s...")
                audio = sd.rec(int(record_sec * fs), samplerate=fs, channels=1, dtype="int16")
                sd.wait()

                max_amp = np.max(np.abs(audio)) if len(audio) > 0 else 0
                if max_amp < 600:  # Silence threshold
                    logger.debug(f"[STT] Mic input below voice threshold (max amp: {max_amp}).")
                    return None

                # Convert to WAV in-memory
                wav_io = io.BytesIO()
                with wave.open(wav_io, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(fs)
                    wf.writeframes(audio.tobytes())
                wav_bytes = wav_io.getvalue()

                r = sr.Recognizer()
                with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
                    audio_data = r.record(source)
                    try:
                        transcript = r.recognize_google(audio_data)
                        return transcript
                    except (sr.UnknownValueError, sr.RequestError) as se:
                        logger.debug(f"[STT] SpeechRecognition note: {se}")
                        return None
            except Exception as e:
                logger.debug(f"[STT] Native audio capture error: {e}")
                return None

        return await asyncio.to_thread(_record_sync)

    async def has_pending_audio(self) -> bool:
        return not self._utterance_q.empty()

    def trigger_wake_word(self):
        try:
            self._wake_q.put_nowait(True)
        except Exception:
            pass

    def push_utterance(self, text: str):
        cleaned = text.strip() if text else ""
        if cleaned:
            try:
                self._utterance_q.put_nowait(cleaned)
                logger.info(f"[Mic Port] Utterance queued: {cleaned!r}")
            except Exception as e:
                logger.warning(f"[Mic Port] Queue error: {e}")

    def clear_pending(self):
        while not self._utterance_q.empty():
            try:
                self._utterance_q.get_nowait()
            except Exception:
                break

    async def release(self):
        pass

def create(config: dict) -> SoundDeviceMic:
    return SoundDeviceMic(config)
