"""
ULTRON V3 — Streaming Audio I/O Engine
─────────────────────────────────────────────────────────────────────────────
Full-duplex non-blocking streaming audio using sounddevice and numpy:
- Input: 16 kHz, 16-bit PCM Mono (zero disk write)
- Output: 24 kHz, 16-bit PCM Mono (streaming ring buffer)
- Sub-50ms Playback Cancellation on Interruption
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import asyncio
import logging
import time
from typing import Callable, Optional
import numpy as np
import sounddevice as sd

logger = logging.getLogger("ultron.realtime.audio")

class AudioStreamEngine:
    """Manages full-duplex non-blocking streaming audio capture and playback."""

    def __init__(
        self,
        input_sample_rate: int = 16000,
        output_sample_rate: int = 24000,
        chunk_size: int = 512,
        on_audio_chunk: Optional[Callable[[bytes, float], None]] = None,
        on_playback_finished: Optional[Callable[[], None]] = None,
    ):
        self.input_sample_rate = input_sample_rate
        self.output_sample_rate = output_sample_rate
        self.chunk_size = chunk_size
        self.on_audio_chunk = on_audio_chunk
        self.on_playback_finished = on_playback_finished

        self.input_stream: Optional[sd.InputStream] = None
        self.output_stream: Optional[sd.OutputStream] = None

        self._playback_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._is_running = False
        self._is_playing = False
        self.playback_start_time = 0.0
        self._playback_task: Optional[asyncio.Task] = None
        self._playback_epoch = 0
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Playback buffer tracking for cancellation latency measurement
        self.last_cancellation_time = 0.0
        self.cancellation_latency_ms = 0.0

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def _input_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Called by sounddevice on microphone hardware thread."""
        if status:
            logger.debug(f"[Audio In] Status: {status}")

        pcm_bytes = indata.tobytes()

        # Fast RMS energy calculation
        audio_data = indata.astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(audio_data ** 2))) if len(audio_data) > 0 else 0.0

        if self.on_audio_chunk:
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(self.on_audio_chunk, pcm_bytes, rms)
            else:
                self.on_audio_chunk(pcm_bytes, rms)

    async def start(self):
        """Starts input capture and output streaming workers."""
        if self._is_running:
            return

        self._loop = asyncio.get_running_loop()
        self._is_running = True
        logger.info(f"[Audio Engine] Starting full-duplex audio (In: {self.input_sample_rate}Hz, Out: {self.output_sample_rate}Hz)")

        # 1. Start Input Stream (16kHz PCM16 Mono)
        self.input_stream = sd.InputStream(
            samplerate=self.input_sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.chunk_size,
            callback=self._input_callback,
        )
        self.input_stream.start()

        # 2. Start Output Stream (24kHz PCM16 Mono)
        self.output_stream = sd.OutputStream(
            samplerate=self.output_sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.chunk_size,
        )
        self.output_stream.start()

        # 3. Start Playback Async Worker
        self._playback_task = asyncio.create_task(self._playback_worker())

    async def _playback_worker(self):
        """Continuously feeds output stream with received 24kHz PCM chunks."""
        while self._is_running:
            try:
                chunk = await self._playback_queue.get()
                if not chunk or not self._is_running:
                    continue

                current_epoch = self._playback_epoch
                self._is_playing = True

                # Non-blocking write to output audio stream buffer
                if self.output_stream and self.output_stream.active:
                    arr = np.frombuffer(chunk, dtype=np.int16)
                    # Check epoch before and after write to avoid playing stale data if cancelled
                    if current_epoch == self._playback_epoch:
                        try:
                            await asyncio.to_thread(self.output_stream.write, arr)
                        except Exception as e:
                            logger.debug(f"[Audio Playback] Output write exception: {e}")

                if self._playback_queue.empty():
                    # Brief debounce to prevent packet-jitter flapping during streaming model turn
                    await asyncio.sleep(0.035)
                    if self._playback_queue.empty() and current_epoch == self._playback_epoch:
                        self._is_playing = False
                        if self.on_playback_finished:
                            try:
                                if self._loop and self._loop.is_running():
                                    self._loop.call_soon_threadsafe(self.on_playback_finished)
                                else:
                                    self.on_playback_finished()
                            except Exception as cb_err:
                                logger.debug(f"[Audio Playback] on_playback_finished callback notice: {cb_err}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Audio Playback] Write error: {e}")
                self._is_playing = False

    def enqueue_playback(self, pcm_24k_bytes: bytes):
        """Enqueues cloud model speech chunk to be played."""
        if self._is_running and pcm_24k_bytes:
            if not self._is_playing:
                self.playback_start_time = time.time()
                self._is_playing = True
            self._playback_queue.put_nowait(pcm_24k_bytes)

    def clear_playback(self) -> float:
        """
        Instantly halts active playback, flushes the queue, and resets output stream.
        Returns cancellation latency in milliseconds.
        """
        t0 = time.perf_counter()
        self._playback_epoch += 1

        # 1. Drain pending playback queue
        dropped_chunks = 0
        while not self._playback_queue.empty():
            try:
                self._playback_queue.get_nowait()
                dropped_chunks += 1
            except asyncio.QueueEmpty:
                break

        # 2. Flush hardware audio output stream immediately
        if self.output_stream and self.output_stream.active:
            try:
                self.output_stream.abort()
                self.output_stream.start()
            except Exception as e:
                logger.debug(f"[Audio Engine] Output stream flush notice: {e}")

        self._is_playing = False
        self.playback_start_time = 0.0
        t_elapsed = (time.perf_counter() - t0) * 1000.0
        self.cancellation_latency_ms = round(t_elapsed, 2)
        self.last_cancellation_time = time.time()

        logger.info(f"[Audio Engine] Playback cancelled instantly ({dropped_chunks} chunks flushed in {self.cancellation_latency_ms}ms)")
        return self.cancellation_latency_ms

    async def stop(self):
        """Stops and closes audio streams safely."""
        self._is_running = False
        self.clear_playback()

        if self._playback_task:
            self._playback_task.cancel()
            try:
                await self._playback_task
            except asyncio.CancelledError:
                pass

        if self.input_stream:
            try:
                self.input_stream.stop()
                self.input_stream.close()
            except Exception as e:
                logger.debug(f"[Audio Engine] InputStream close notice: {e}")
            self.input_stream = None

        if self.output_stream:
            try:
                self.output_stream.stop()
                self.output_stream.close()
            except Exception as e:
                logger.debug(f"[Audio Engine] OutputStream close notice: {e}")
            self.output_stream = None

        logger.info("[Audio Engine] Stopped.")
