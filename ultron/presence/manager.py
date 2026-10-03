"""
ULTRON V3 — Presence Subsystem Manager & Failure Isolation Gateway
─────────────────────────────────────────────────────────────────────────────
Orchestrates the entire visual desktop presence layer:
- Subscribes to runtime event bus without modifying core business logic
- Streams microphone and output audio PCM to the visualizer with zero locks
- Provides failure isolation: if window/GDI fails, voice agent continues 100%
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import logging
import sys
from typing import Optional, TYPE_CHECKING

from ultron.presence.animation import SpringChoreographer
from ultron.presence.audio_visualizer import AudioVisualizer
from ultron.presence.window import UltronOverlayWindow
from ultron.presence.states import PresenceStateCoordinator
from ultron.presence.onboarding_controller import OnboardingController
from ultron.core.user_config import is_first_run_required, UserConfig

if TYPE_CHECKING:
    from ultron.core.runtime import UltronRuntime

logger = logging.getLogger("ultron.presence.manager")

class PresenceManager:
    """Central supervisor for ULTRON desktop presence."""

    def __init__(self, runtime: Optional[UltronRuntime] = None):
        self.runtime = runtime
        self.choreographer = SpringChoreographer()
        self.audio_viz = AudioVisualizer()
        self.window: Optional[UltronOverlayWindow] = None
        self.coordinator: Optional[PresenceStateCoordinator] = None
        self.onboarding_ctrl: Optional[OnboardingController] = None
        self.is_active = False

    def attach_to_runtime(self, runtime: UltronRuntime):
        """Binds presence observers to active runtime."""
        self.runtime = runtime
        if self.window and self.window.renderer:
            self.coordinator = PresenceStateCoordinator(
                choreographer=self.choreographer,
                audio_visualizer=self.audio_viz,
                renderer=self.window.renderer,
                on_wake_callback=self.window.wake,
            )
            # 1. Subscribe to core event bus
            self.runtime.event_bus.subscribe(self.coordinator.on_engine_event)

            # 2. Hook audio telemetry (input & output)
            self._hook_audio_pipeline()

            # 3. Hook Tool and Confirmation Gateway
            self._hook_tool_gateway()

    def _hook_audio_pipeline(self):
        """Hooks audio buffers for real-time visualization without duplicate devices."""
        if not self.runtime or not self.runtime.audio:
            return

        original_input_chunk = self.runtime.audio.on_audio_chunk
        def _visualizer_input_wrapper(pcm: bytes, rms: float):
            self.audio_viz.push_input_chunk(rms)
            if self.window:
                self.window.wake()
            if original_input_chunk:
                original_input_chunk(pcm, rms)

        self.runtime.audio.on_audio_chunk = _visualizer_input_wrapper

        # Output audio hook on playback enqueue
        original_enqueue = self.runtime.audio.enqueue_playback
        def _visualizer_output_wrapper(pcm_bytes: bytes):
            self.audio_viz.push_output_pcm(pcm_bytes)
            if self.window:
                self.window.wake()
            original_enqueue(pcm_bytes)

        self.runtime.audio.enqueue_playback = _visualizer_output_wrapper

    def _hook_tool_gateway(self):
        """Observes tool executions and confirmations."""
        if not self.runtime or not self.runtime.tools:
            return

        original_execute = self.runtime.tools.execute
        async def _monitored_execute(tool_name: str, arguments: dict, session_id: str = "default"):
            target_str = str(arguments.get("path") or arguments.get("app_name") or arguments.get("key") or "")
            if self.coordinator:
                self.coordinator.renderer.set_tool_context(tool_name, target_str, status="running", progress=0.4)
                self.choreographer.set_state("TOOL_EXEC")
                if self.window:
                    self.window.wake()

            result = await original_execute(tool_name, arguments, session_id)

            if isinstance(result, dict) and result.get("status") == "CONFIRM_REQUIRED":
                # Trigger Security Confirmation Vault
                action = result.get("action", tool_name)
                target = result.get("target", target_str)
                token = result.get("confirmation_token", "")
                msg = result.get("message", "")
                if self.coordinator:
                    self.coordinator.on_confirmation_required(action, target, token, msg)
            elif self.coordinator:
                self.coordinator.on_tool_complete(tool_name, target_str, result)

            return result

        self.runtime.tools.execute = _monitored_execute

    def start(self, force_onboarding: bool = False):
        """Starts native desktop overlay with strict failure isolation."""
        if sys.platform != "win32":
            logger.warning("[Presence] Non-Windows platform detected; desktop overlay disabled.")
            return

        try:
            self.window = UltronOverlayWindow(
                choreographer=self.choreographer,
                audio_visualizer=self.audio_viz,
                on_allow_click=self._on_allow_click,
                on_dismiss_click=self._on_dismiss_click,
                on_notch_click=self._on_notch_click,
            )

            # Check if First-Run Liquid Onboarding is required or requested
            if force_onboarding or is_first_run_required():
                logger.info("[Presence] Launching Liquid Onboarding / Configuration Experience")
                self.start_onboarding()
            else:
                self.choreographer.set_state("IDLE")

            self.window.start()
            self.is_active = True

            if self.runtime:
                self.attach_to_runtime(self.runtime)

            logger.info("[Presence] ULTRON Desktop Presence initialized successfully.")
        except Exception as e:
            logger.error(f"[Presence] Failed to initialize overlay window: {e}. Voice engine remains active.", exc_info=True)
            self.is_active = False

    def start_onboarding(self):
        """Manually triggers or re-opens the onboarding / configuration window."""
        self.onboarding_ctrl = OnboardingController(
            on_complete=self._on_onboarding_completed,
            on_wake=self.window.wake if self.window else None,
        )
        if self.window:
            self.window.set_onboarding_controller(self.onboarding_ctrl)
            self.window.wake()
        # Liquid expansion from top notch into onboarding container
        self.choreographer.set_state("ONBOARDING")

    def _on_onboarding_completed(self, cfg: UserConfig):
        """Called when user finalizes setup: updates runtime and executes liquid collapse."""
        logger.info("[Presence] Onboarding completed -> Applying configuration and initiating liquid collapse to notch")

        # 1. Update runtime identity & system instruction
        if self.runtime and self.runtime.config:
            self.runtime.config.user = cfg
            if cfg.voice_preference:
                self.runtime.config.model.voice_name = cfg.voice_preference
            assistant_name = cfg.assistant_name or "ULTRON"
            owner_name = cfg.owner_name or "User"
            addressing = cfg.addressing_name or owner_name
            self.runtime.config.model.system_instruction = (
                f"You are {assistant_name}, a sovereign, concise, calculating AI entity assisting {owner_name} (addressed as {addressing}). "
                "Speak naturally in short, authoritative sentences. "
                "Never use markdown, lists, or conversational filler. "
                "Use provided tools whenever system status, time, files, or applications are requested."
            )

        # 2. Update Windows Startup preference
        try:
            from ultron.core.startup import StartupManager
            sm = StartupManager()
            if cfg.start_with_windows:
                sm.enable_startup()
            else:
                sm.disable_startup()
        except Exception as ex:
            logger.warning(f"[Presence] Error applying startup setting: {ex}")

        # 3. Liquid Collapse: physically contract back into the top-bezel resting notch
        self.choreographer.set_state("IDLE")
        if self.window:
            self.window.wake()

    def _on_allow_click(self):
        """Handles user clicking Allow on Confirmation Vault."""
        logger.info("[Presence] User approved pending action via UI Vault.")
        if self.coordinator and self.coordinator.current_pending_token:
            token = self.coordinator.current_pending_token
            if self.runtime:
                self.runtime.memory.record_turn(
                    role="user",
                    content=f"Confirmed action with token {token}",
                )
            self.coordinator.dismiss_confirmation()

    def _on_dismiss_click(self):
        """Handles user clicking Dismiss on Confirmation Vault."""
        logger.info("[Presence] User dismissed pending action via UI Vault.")
        if self.coordinator:
            if self.runtime and self.coordinator.current_pending_token:
                self.runtime.memory.record_turn(
                    role="user",
                    content="Rejected pending confirmation action.",
                )
            self.coordinator.dismiss_confirmation()

    def _on_notch_click(self):
        """Handles user clicking the compact notch body: opens setup dropdown."""
        logger.info("[Presence] Notch body clicked -> Toggling configuration dropdown")
        if self.choreographer.current_state_name in ("IDLE", "RETRACTED", "TOOL_COMPLETE"):
            self.start_onboarding()
        elif self.choreographer.current_state_name == "ONBOARDING":
            if self.window:
                self.window.wake()

    def stop(self):
        """Gracefully halts overlay window."""
        if self.window:
            self.window.stop()
            self.window = None
        self.is_active = False
        logger.info("[Presence] Manager stopped.")
