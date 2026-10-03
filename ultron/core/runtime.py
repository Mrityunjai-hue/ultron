"""
ULTRON V3 — Core Realtime Runtime Coordinator
─────────────────────────────────────────────────────────────────────────────
Orchestrates the ultra-lightweight real-time conversation loop:
Microphone -> Non-blocking Audio Stream -> Gemini Live -> Playback Stream
Includes Sub-50ms Barge-In and Local Tool Safety Gateway.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import asyncio
import logging
import time
from typing import Optional

from ultron.core.config import UltronConfig, get_config
from ultron.core.events import ActivityState, EngineEvent, EventBus
from ultron.core.identity import build_system_instruction
from ultron.realtime.audio_stream import AudioStreamEngine
from ultron.realtime.interruption import InterruptionManager
from ultron.realtime.gemini_live import GeminiLiveProvider
from ultron.tools.confirmation import ConfirmationManager
from ultron.tools.executor import ToolExecutor
from ultron.memory.manager import MemoryManager
from ultron.tasks.planner import TaskPlanner
from ultron.tasks.executor import TaskExecutionEngine
from ultron.tasks.models import Task

logger = logging.getLogger("ultron.core.runtime")

class UltronRuntime:
    """Central orchestrator for ULTRON V3 real-time voice pipeline and desktop task execution."""

    def __init__(self, config: Optional[UltronConfig] = None):
        self.config = config or get_config()
        self.session_id = f"session-{int(time.time())}"
        self.event_bus = EventBus()
        self.state = ActivityState.IDLE

        # Memory & Security Subsystems
        self.confirmation = ConfirmationManager()
        self.memory = MemoryManager()
        self.tools = ToolExecutor(
            workspace_root=self.config.workspace_root,
            confirmation_manager=self.confirmation,
            memory_manager=self.memory,
        )

        # Task Planning & Multi-Step Execution Subsystems
        self.task_planner = TaskPlanner(workspace_root=self.config.workspace_root)
        self.tasks = TaskExecutionEngine(
            tool_executor=self.tools,
            confirmation_manager=self.confirmation,
            memory_manager=self.memory,
            event_bus=self.event_bus,
            workspace_root=self.config.workspace_root,
        )

        # Inject updated identity instructions with persistent memory
        self.config.model.system_instruction = self.memory.get_system_instruction()

        # Telemetry metrics
        self.metrics = {
            "startup_time_ms": 0.0,
            "first_response_latency_ms": 0.0,
            "interruption_latency_ms": 0.0,
            "cancellation_latency_ms": 0.0,
            "reconnect_time_ms": 0.0,
            "turns_completed": 0,
        }

        # Initialize subcomponents
        self.audio = AudioStreamEngine(
            input_sample_rate=self.config.audio.input_sample_rate,
            output_sample_rate=self.config.audio.output_sample_rate,
            chunk_size=self.config.audio.chunk_size,
            on_audio_chunk=self._on_input_audio_chunk,
            on_playback_finished=self._on_playback_finished,
        )

        self.interruption = InterruptionManager(
            audio_engine=self.audio,
            rms_threshold=self.config.audio.barge_in_rms_threshold,
            consecutive_frames_required=self.config.audio.barge_in_consecutive_frames,
            on_interruption=self._on_barge_in_detected,
            enabled=getattr(self.config.audio, "enable_local_barge_in", True),
        )

        self.provider = GeminiLiveProvider(self.config)

        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._input_audio_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=100)
        self._send_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._speech_start_time = 0.0
        self._awaiting_first_response = False
        self._pending_turn_complete = False

    @property
    def is_running(self) -> bool:
        """Returns True if the realtime engine audio and connection loops are active."""
        return self._running

    def _transition(self, new_state: ActivityState, operation: str = "none", message: str = ""):
        """Publishes state change event."""
        if self.state != new_state:
            self.state = new_state
            logger.info(f"[State Transition] -> {new_state.value} [Op: {operation}] {message}")
            self.event_bus.publish(EngineEvent(
                state=new_state,
                operation=operation,
                message=message,
            ))

    def _on_playback_finished(self):
        """Called when audio engine speaker queue is completely drained."""
        if self._pending_turn_complete or self.state == ActivityState.RESPONDING:
            if not self.audio.is_playing:
                self._transition(ActivityState.IDLE)
                self._pending_turn_complete = False

    def _queue_audio_chunk(self, pcm_bytes: bytes):
        """Places audio frame into queue without blocking."""
        if not self._input_audio_queue.full():
            self._input_audio_queue.put_nowait(pcm_bytes)
        else:
            try:
                self._input_audio_queue.get_nowait()
            except (asyncio.QueueEmpty, ValueError):
                pass
            self._input_audio_queue.put_nowait(pcm_bytes)

    def _on_input_audio_chunk(self, pcm_bytes: bytes, rms_energy: float):
        """Processes incoming microphone frame on audio thread."""
        if not self._running:
            return

        # 1. Evaluate local barge-in if ULTRON is currently speaking
        self.interruption.process_input_frame(pcm_bytes, rms_energy)

        # 2. Track speech onset for first-response latency measurement
        if rms_energy >= self.config.audio.barge_in_rms_threshold:
            if self.state == ActivityState.IDLE:
                self._speech_start_time = time.perf_counter()
                self._awaiting_first_response = True
                self._transition(ActivityState.LISTENING)

        # 3. Stream chunk to Gemini Live via thread-safe audio pump queue
        if self._running and self._loop and not self._loop.is_closed():
            try:
                self._loop.call_soon_threadsafe(self._queue_audio_chunk, pcm_bytes)
            except Exception:
                pass

    def _on_barge_in_detected(self, total_latency_ms: float):
        """Called when user speaks during model output."""
        self._pending_turn_complete = False
        self.metrics["interruption_latency_ms"] = round(total_latency_ms, 2)
        self.metrics["cancellation_latency_ms"] = self.audio.cancellation_latency_ms
        self._transition(ActivityState.INTERRUPTED, message=f"Interrupted in {total_latency_ms:.1f}ms")
        self._transition(ActivityState.LISTENING)
        if self._loop and not self._loop.is_closed():
            try:
                self._loop.call_soon_threadsafe(lambda: asyncio.create_task(self.provider.interrupt()))
            except Exception:
                pass

    async def _audio_sender_loop(self):
        """High-performance non-blocking audio streamer loop."""
        while self._running:
            try:
                pcm_bytes = await self._input_audio_queue.get()
                if self.provider.is_connected:
                    await self.provider.send_audio_chunk(pcm_bytes)
                self._input_audio_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"[Audio Sender] Stream error: {e}")
                await asyncio.sleep(0.01)

    async def start(self):
        """Starts real-time session and streaming audio loops."""
        t0 = time.perf_counter()
        logger.info("Initializing ULTRON V3 Realtime Engine...")
        self._running = True
        self._loop = asyncio.get_running_loop()

        # 1. Connect to Gemini Live
        await self.provider.connect()

        # 2. Start hardware audio streams
        await self.audio.start()

        # 3. Start cloud event listener & audio sender tasks
        self._send_task = asyncio.create_task(self._audio_sender_loop())
        self._receive_task = asyncio.create_task(self._event_receive_loop())

        self.metrics["startup_time_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        self._transition(ActivityState.IDLE, message=f"Online (Ready in {self.metrics['startup_time_ms']}ms)")

    async def _event_receive_loop(self):
        """Handles incoming server events (audio, text, tools, interruptions)."""
        while self._running:
            try:
                if not self.provider.is_connected:
                    # Automatic reconnection if session expired
                    t_recon = time.perf_counter()
                    logger.warning("[Runtime] Reconnecting Gemini Live session...")
                    self._transition(ActivityState.THINKING, operation="reconnecting")
                    await self.provider.connect()
                    self.metrics["reconnect_time_ms"] = round((time.perf_counter() - t_recon) * 1000.0, 2)
                    self._transition(ActivityState.IDLE, message="Reconnected")

                async for event in self.provider.receive_events():
                    event_type = event.get("type")

                    # A. Audio Output Stream Chunk (24kHz PCM)
                    if event_type == "audio":
                        self._pending_turn_complete = False
                        if self._awaiting_first_response and self._speech_start_time > 0:
                            latency = (time.perf_counter() - self._speech_start_time) * 1000.0
                            self.metrics["first_response_latency_ms"] = round(latency, 1)
                            self._awaiting_first_response = False
                            logger.info(f"[Telemetry] First response latency: {latency:.1f}ms")

                        self._transition(ActivityState.RESPONDING)
                        self.audio.enqueue_playback(event["data"])

                    # B. Spoken Text Transcription Chunk
                    elif event_type == "text":
                        text = event.get("content", "")
                        self.memory.record_turn(role="model", content=text)

                    # C. Cloud Model Requested Local Tool
                    elif event_type == "tool_call":
                        call_id = event["id"]
                        tool_name = event["name"]
                        tool_args = event["args"]

                        self._transition(ActivityState.THINKING, operation=tool_name)
                        try:
                            if tool_name == "execute_task_plan":
                                intent = str(tool_args.get("user_intent", "")).strip()
                                steps = tool_args.get("steps", [])
                                task = self.task_planner.plan_multi_step_task(
                                    user_intent=intent,
                                    steps_spec=steps,
                                    session_id=self.session_id,
                                )
                                result = await self.tasks.execute_task(task)
                            elif tool_name == "cancel_active_task":
                                reason = str(tool_args.get("reason", "Voice cancellation requested"))
                                ok = self.cancel_active_task(reason=reason)
                                result = {
                                    "success": True,
                                    "cancelled": ok,
                                    "message": "Active desktop task has been cancelled." if ok else "No active task was running.",
                                }
                            else:
                                result = await self.tools.execute(
                                    tool_name=tool_name,
                                    arguments=tool_args,
                                    session_id=self.session_id,
                                )
                        except Exception as tool_err:
                            logger.error(f"[Runtime] Tool '{tool_name}' execution exception: {tool_err}", exc_info=True)
                            result = {"success": False, "error": f"Tool execution failed: {str(tool_err)}"}

                        self.memory.record_turn(
                            role="tool",
                            content=str(result),
                            tool_name=tool_name,
                            tool_args=tool_args,
                            tool_result=result,
                        )
                        await self.provider.send_tool_response(call_id, tool_name, result)

                    # D. Server-Side Interruption Notification
                    elif event_type == "interrupted":
                        self._pending_turn_complete = False
                        self.audio.clear_playback()
                        self._transition(ActivityState.LISTENING, message="Server confirmed turn interruption")

                    # E. Model Turn Completed
                    elif event_type == "turn_complete":
                        self.metrics["turns_completed"] += 1
                        if not self.audio.is_playing:
                            self._transition(ActivityState.IDLE)
                            self._pending_turn_complete = False
                        else:
                            self._pending_turn_complete = True

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Runtime Loop] Event processing fault: {e}", exc_info=True)
                await asyncio.sleep(1.0)

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """Convenience method to execute a validated Task object."""
        return await self.tasks.execute_task(task)

    async def execute_plan(self, user_intent: str, steps: list[dict[str, Any]]) -> Dict[str, Any]:
        """Convenience method to build and execute a multi-step task plan."""
        task = self.task_planner.plan_multi_step_task(user_intent, steps, session_id=self.session_id)
        return await self.tasks.execute_task(task)

    def cancel_active_task(self, reason: str = "User voice cancellation") -> bool:
        """Immediately halts any running desktop task and transitions state."""
        return self.tasks.cancel_active_task(reason=reason)

    async def resume_task_confirmation(self, task_id: str, confirmation_token: str) -> Dict[str, Any]:
        """Resumes a paused task waiting for user confirmation."""
        return await self.tasks.resume_task_with_confirmation(task_id, confirmation_token)

    async def stop(self):
        """Gracefully shuts down engine."""
        self._running = False
        self.cancel_active_task(reason="Runtime shutdown")
        await self.tools.app_registry.shutdown_all()
        if self._send_task:
            self._send_task.cancel()
            try:
                await self._send_task
            except asyncio.CancelledError:
                pass

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        await self.audio.stop()
        await self.provider.disconnect()
        self._transition(ActivityState.OFFLINE, message="ULTRON offline")
        logger.info("ULTRON V3 Engine stopped.")
