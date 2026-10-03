"""
ULTRON V3 — Presence State Coordinator & Runtime Bridge
─────────────────────────────────────────────────────────────────────────────
Subscribes directly to authoritative UltronRuntime events without duplicating
the AI state machine or safety gateway. Translates core events into
visual presence states, tool action pods, and security confirmation cards.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import logging
import time
from typing import Optional, Dict, Any

from ultron.core.events import ActivityState, EngineEvent
from ultron.presence.animation import SpringChoreographer
from ultron.presence.audio_visualizer import AudioVisualizer
from ultron.presence.renderer import PresenceRenderer

logger = logging.getLogger("ultron.presence.states")

class PresenceStateCoordinator:
    """Bridges runtime events to UI animation states and telemetry."""

    def __init__(
        self,
        choreographer: SpringChoreographer,
        audio_visualizer: AudioVisualizer,
        renderer: PresenceRenderer,
        on_wake_callback: Optional[callable] = None,
    ):
        self.ch = choreographer
        self.audio_viz = audio_visualizer
        self.renderer = renderer
        self.on_wake = on_wake_callback

        self.last_state: ActivityState = ActivityState.IDLE
        self.last_transition_time = time.time()
        self.interruption_reaction_ms = 0.0

        # Pending confirmation cache from local gateway
        self.current_pending_token: Optional[str] = None

    def on_engine_event(self, event: EngineEvent):
        """Authoritative listener subscribed to UltronRuntime event bus."""
        t0 = time.perf_counter()
        state = event.state
        op = event.operation
        msg = event.message
        self.last_state = state
        self.last_transition_time = time.time()

        logger.info(f"[Presence Bridge] Event: {state.value} | Op: {op} | Msg: {msg}")

        # 1. Map Core State to Visual Choreographer
        if state == ActivityState.IDLE:
            self.ch.set_state("IDLE")

        elif state == ActivityState.LISTENING:
            self.ch.set_state("LISTENING")

        elif state == ActivityState.THINKING:
            if op and op not in ("none", "reconnecting"):
                # Tool invocation starting -> Show Action Pod
                self.renderer.set_tool_context(
                    tool_name=op.upper(),
                    target=msg or "Executing substrate action",
                    status="running",
                    progress=0.5,
                )
                self.ch.set_state("TOOL_EXEC")
            else:
                self.ch.set_state("THINKING")

        elif state == ActivityState.RESPONDING:
            self.ch.set_state("RESPONDING")

        elif state == ActivityState.INTERRUPTED:
            # Sub-40ms Instant Interruption Snub
            t_inter = (time.perf_counter() - t0) * 1000.0
            self.interruption_reaction_ms = round(t_inter, 2)
            self.audio_viz.reset()
            self.ch.snap_interruption()
            logger.info(f"[Presence Bridge] Interruption visual snap resolved in {self.interruption_reaction_ms:.2f}ms")

        elif state == ActivityState.OFFLINE:
            self.ch.set_state("RETRACTED")

        # Wake up render loop if asleep
        if self.on_wake:
            self.on_wake()

    def on_tool_complete(self, tool_name: str, target: str, result: Dict[str, Any]):
        """Called when ToolExecutor finishes execution."""
        status = "complete" if result.get("success", False) else "failed"
        self.renderer.set_tool_context(
            tool_name=tool_name,
            target=target,
            status=status,
            progress=1.0,
        )
        self.ch.set_state("TOOL_COMPLETE")
        if self.on_wake:
            self.on_wake()

    def on_confirmation_required(self, action: str, target: str, token: str, message: str = ""):
        """Called when Safety Gateway issues a CONFIRM_REQUIRED token."""
        self.current_pending_token = token
        self.renderer.set_vault_context(
            action=action,
            target=target,
            message=message or f"Confirm '{action}' on '{target}'",
        )
        self.ch.set_state("CONFIRMATION")
        if self.on_wake:
            self.on_wake()

    def dismiss_confirmation(self):
        """User dismissed confirmation dialog."""
        self.current_pending_token = None
        self.ch.set_state("IDLE")
        if self.on_wake:
            self.on_wake()
