"""
ULTRON Laptop Orchestrator v2.0
─────────────────────────────────────────────────────────────────────────────
Central Autonomous Coordinator implementing the Single Brain & Authoritative Event Model:
Context -> Brain -> Real Tool -> Safety Engine -> Result -> Brain -> Response
Emits AuthoritativeEvent to Rive Character Engine & Native Desktop Notch.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import asyncio
import logging
import time
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Dict, Any, List

try:
    from laptop.core.states import ActivityState, MoodState, AuthoritativeEvent
    from laptop.brain.mood import MoodEngine
    from laptop.brain.task_planner import TaskSupervisor
    from laptop.tools.registry import ToolRegistry
except ImportError:
    from core.states import ActivityState, MoodState, AuthoritativeEvent
    from brain.mood import MoodEngine
    from brain.task_planner import TaskSupervisor
    from tools.registry import ToolRegistry

logger = logging.getLogger("ultron.orchestrator")

class State(str, Enum):
    IDLE        = "idle"
    LISTEN      = "listen"
    THINK       = "think"
    EXECUTING   = "executing"
    SPEAK       = "speak"
    RESPONSE    = "response"
    REFLEX      = "reflex"
    SLEEP       = "sleep"
    SHUTDOWN    = "shutdown"

@dataclass
class OrchestratorContext:
    """Shared context passed between states."""
    current_user: Optional[str] = None
    user_confidence: float = 0.0
    utterance: str = ""
    response: str = ""
    scene_description: str = ""
    mood: MoodState = MoodState.CALM
    operation: str = "none"
    gaze_x: float = 0.0
    gaze_y: float = 0.0
    voice_amplitude: float = 0.0
    face_embedding: Optional[list] = None
    timestamp: float = field(default_factory=time.time)

class UltronOrchestrator:
    """
    Core Autonomous Orchestrator driving Real Tools, Safety, and Rive Presence.
    """

    def __init__(self, ports, config: dict):
        self.ports = ports
        self.config = config
        self.ctx = OrchestratorContext()
        self.state = State.IDLE
        self._running = False
        self._last_face_check = 0.0

        # Subsystems
        self.mood_engine = MoodEngine()
        self.supervisor = TaskSupervisor(max_steps=6)
        self.tools = ToolRegistry()

        self._state_handlers: dict[State, Callable] = {
            State.IDLE:      self._handle_idle,
            State.LISTEN:    self._handle_listen,
            State.THINK:     self._handle_think,
            State.EXECUTING: self._handle_executing,
            State.SPEAK:     self._handle_speak,
            State.RESPONSE:  self._handle_response,
            State.REFLEX:    self._handle_reflex,
            State.SLEEP:     self._handle_sleep,
            State.SHUTDOWN:  self._handle_shutdown,
        }

        # Hook orb callbacks
        if hasattr(self.ports.orb, "set_callbacks"):
            self.ports.orb.set_callbacks(
                on_utterance=self._on_ui_utterance,
                on_wake=self._on_ui_wake,
            )

    def _on_ui_wake(self):
        """Triggered when browser, notch, or hardware signals wake word."""
        logger.info("Signal: Wake word detected. Transitioning to LISTEN.")
        if hasattr(self.ports.mic, "trigger_wake_word"):
            self.ports.mic.trigger_wake_word()

    def _on_ui_utterance(self, text: str):
        """Triggered when user speaks or enters text."""
        cleaned = text.strip() if text else ""
        if not cleaned:
            return
        if cleaned.lower() == "ultron":
            logger.info("Ignoring bare wake trigger 'ultron'.")
            return

        now = time.time()
        last_text = getattr(self, "_last_utterance_text", None)
        last_time = getattr(self, "_last_utterance_time", 0.0)
        if cleaned == last_text and (now - last_time) < 1.5:
            logger.debug(f"Deduplicating twin utterance: {cleaned!r}")
            return
        self._last_utterance_text = cleaned
        self._last_utterance_time = now

        logger.info(f"Utterance received: {cleaned!r}")
        self.ctx.utterance = cleaned

        if hasattr(self.ports.mic, "push_utterance"):
            self.ports.mic.push_utterance(cleaned)

        if self.state in (State.IDLE, State.SLEEP):
            asyncio.create_task(self._transition(State.THINK))

    async def run(self):
        """Main orchestrator event loop."""
        self._running = True
        logger.info("ULTRON v2.0 Autonomous Orchestrator running.")
        await self._transition(State.IDLE)

        while self._running:
            handler = self._state_handlers.get(self.state)
            if handler:
                next_state = await handler()
                if next_state and next_state != self.state:
                    await self._transition(next_state)
            await asyncio.sleep(0.01)

    def stop(self):
        self._running = False

    async def _transition(self, new_state: State, operation: str = "none"):
        """Performs state transition and broadcasts AuthoritativeEvent."""
        logger.info(f"State transition: {self.state.value} -> {new_state.value} [Op: {operation}]")
        self.state = new_state
        self.ctx.operation = operation

        # Map internal State to canonical ActivityState
        act_map = {
            State.IDLE: ActivityState.IDLE,
            State.LISTEN: ActivityState.LISTENING,
            State.THINK: ActivityState.THINKING,
            State.EXECUTING: ActivityState.EXECUTING,
            State.SPEAK: ActivityState.RESPONDING,
            State.RESPONSE: ActivityState.RESPONDING,
            State.REFLEX: ActivityState.EXECUTING,
            State.SLEEP: ActivityState.IDLE,
            State.SHUTDOWN: ActivityState.OFFLINE,
        }
        activity = act_map.get(new_state, ActivityState.IDLE)

        # Evaluate emotional context
        mood = self.mood_engine.evaluate(
            activity=activity,
            utterance=self.ctx.utterance,
            operation=operation,
            requires_confirm=bool(self.tools.confirm_manager.get_latest_pending()),
        )
        self.ctx.mood = mood

        # Construct AuthoritativeEvent
        event = AuthoritativeEvent(
            activity=activity,
            operation=operation,
            mood=mood,
            gaze_x=self.ctx.gaze_x,
            gaze_y=self.ctx.gaze_y,
            attention=0.8 if activity != ActivityState.IDLE else 0.5,
            voice_amplitude=self.ctx.voice_amplitude,
        )

        # Dispatch AuthoritativeEvent to Rive engine
        if hasattr(self.ports.orb, "emit_authoritative_event"):
            await self.ports.orb.emit_authoritative_event(event)
        elif hasattr(self.ports.orb, "set_state"):
            await self.ports.orb.set_state(event.to_legacy_ui_state())

        if hasattr(self.ports, "arduino") and self.ports.arduino:
            try:
                await self.ports.arduino.send_state(new_state.value)
            except Exception:
                pass

    # ── State Handlers ───────────────────────────────────────────────────────
    async def _handle_idle(self) -> Optional[State]:
        """Standby mode: tracks passive gaze and awaits wake trigger."""
        await asyncio.sleep(0.1)

        if await self.ports.mic.wake_word_detected():
            self.ctx.timestamp = time.time()
            return State.LISTEN

        # Passive face recognition & gaze tracking (every 1.2s)
        now = time.time()
        if now - self._last_face_check < 1.2:
            return None
        self._last_face_check = now

        frame = await self.ports.camera.capture_frame()
        if frame is not None:
            result = await self.ports.perception.face_recognize(frame)
            if result:
                self.ctx.current_user = result["name"]
                self.ctx.user_confidence = result["confidence"]
                if "gaze_x" in result and "gaze_y" in result:
                    self.ctx.gaze_x = result["gaze_x"]
                    self.ctx.gaze_y = result["gaze_y"]
                    if hasattr(self.ports.orb, "set_gaze"):
                        await self.ports.orb.set_gaze(result["gaze_x"], result["gaze_y"])

                if result["name"] != "UNKNOWN" and result["confidence"] >= 0.65:
                    if hasattr(self.ports.orb, "notify_user"):
                        await self.ports.orb.notify_user(result["name"], result["confidence"])
        return None

    async def _handle_listen(self) -> Optional[State]:
        """Captures voice input from microphone."""
        timeout_val = self.config.get("listen_timeout", 8.5)
        timeout = float(timeout_val.get("seconds", 8.5)) if isinstance(timeout_val, dict) else float(timeout_val or 8.5)
        logger.info(f"Listening for directive (up to {timeout}s)...")

        utterance = await self.ports.mic.capture_utterance(timeout=timeout)
        if not utterance:
            return State.IDLE

        self.ctx.utterance = utterance
        logger.info(f"Utterance captured: {utterance!r}")
        return State.THINK

    async def _handle_think(self) -> Optional[State]:
        """Reasoning Authority: Evaluates intent, safety, tools, and response."""
        if hasattr(self.ports.mic, "clear_pending"):
            self.ports.mic.clear_pending()

        u = self.ctx.utterance.strip().lower()

        # 1. Handle Pending Safety Confirmation Resolution
        pending = self.tools.confirm_manager.get_latest_pending()
        if pending:
            if any(w in u for w in ["yes", "confirm", "proceed", "do it", "approve"]):
                logger.info(f"User approved pending confirmation [{pending.id}]")
                res = await self.tools.confirm_manager.resolve(pending.id, approved=True)
                self.ctx.response = f"Directive confirmed. Action executed with status: {res.get('message', 'Complete')}."
                return State.SPEAK
            elif any(w in u for w in ["no", "cancel", "deny", "abort", "stop", "nevermind"]):
                logger.info(f"User declined pending confirmation [{pending.id}]")
                await self.tools.confirm_manager.resolve(pending.id, approved=False)
                self.ctx.response = "Action aborted per your instructions."
                return State.SPEAK

        # 2. Context & Episodic Memory Retrieval
        if u.startswith("remember that ") or u.startswith("remember "):
            fact_str = re.sub(r'^remember(?:\s+that)?\s+', '', u).strip()
            if " is " in fact_str:
                k, v = fact_str.split(" is ", 1)
            elif " = " in fact_str:
                k, v = fact_str.split(" = ", 1)
            else:
                k, v = "note", fact_str
            active_user = self.ctx.current_user or "User"
            await self.ports.memory.remember_fact(active_user, k.strip(), v.strip())
            self.ctx.response = f"Catalogued into episodic memory for {active_user}: {k.strip()} = {v.strip()}."
            return State.SPEAK

        if "forget me" in u or "purge my memory" in u or "delete my data" in u:
            active_user = self.ctx.current_user or "User"
            await self.ports.memory.forget_user(active_user)
            self.ctx.response = f"All episodic memory, biometric templates, and interaction history for {active_user} have been permanently purged."
            return State.SPEAK

        user_ctx = await self.ports.memory.get_full_context(self.ctx.current_user)

        # 3. LLM Inference Loop with sub-second sentence-boundary TTS dispatch
        def on_sentence_chunk(clause: str):
            logger.info(f"TTS Stream Dispatch: {clause!r}")
            if hasattr(self.ports.orb, "dispatch_tts"):
                asyncio.create_task(self.ports.orb.dispatch_tts(clause))

        async def execute_tool_with_safety(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
            logger.info(f"[BRAIN] Tool required: {tool_name}")
            await self._transition(State.EXECUTING, operation=tool_name)
            return await self.tools.execute(tool_name, arguments, user=self.ctx.current_user)

        schemas = self.tools.get_schemas()
        self.ctx.response = await self.ports.brain.generate_response(
            utterance=self.ctx.utterance,
            user=self.ctx.current_user,
            confidence=self.ctx.user_confidence,
            scene=self.ctx.scene_description,
            relationship_mode=user_ctx.get("relationship_mode", "STRANGER"),
            interaction_count=user_ctx.get("interaction_count", 0),
            trust_score=user_ctx.get("trust_score", 0.0),
            last_seen=user_ctx.get("last_seen", "never"),
            recent_history=user_ctx.get("recent_history", []),
            known_facts=user_ctx.get("facts", {}),
            tools=schemas,
            tool_executor=execute_tool_with_safety,
            on_sentence=on_sentence_chunk,
        )

        return State.SPEAK

    async def _handle_executing(self) -> Optional[State]:
        """Intermediary state while asynchronous tools execute."""
        await asyncio.sleep(0.05)
        return State.SPEAK

    async def _handle_speak(self) -> Optional[State]:
        """Speech tracking, audio amplitude broadcasting, and interaction logging."""
        if not self.ctx.response:
            return State.IDLE

        # Log to memory database
        await self.ports.memory.log_interaction(
            user_id=self.ctx.current_user,
            user_said=self.ctx.utterance,
            ultron_said=self.ctx.response,
            mood=self.ctx.mood.value if hasattr(self.ctx.mood, "value") else str(self.ctx.mood),
            scene=self.ctx.scene_description,
        )

        self.ctx.utterance = ""
        return State.RESPONSE

    async def _handle_response(self) -> Optional[State]:
        """Brief response hold, then return to IDLE."""
        await asyncio.sleep(0.5)
        if hasattr(self.ports.mic, "clear_pending"):
            self.ports.mic.clear_pending()
        return State.IDLE

    async def _handle_reflex(self) -> Optional[State]:
        await asyncio.sleep(0.1)
        return State.IDLE

    async def _handle_sleep(self) -> Optional[State]:
        await asyncio.sleep(1.0)
        if await self.ports.mic.wake_word_detected():
            return State.IDLE
        return None

    async def _handle_shutdown(self) -> Optional[State]:
        self._running = False
        logger.info("Orchestrator loop terminated.")
        return None
