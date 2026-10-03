"""
ULTRON V3 — Onboarding Controller & Step State Machine
─────────────────────────────────────────────────────────────────────────────
Manages the 6-stage physical onboarding sequence inside the single liquid
surface container. Coordinates input focus, text entry, keyboard navigation,
validation, step transition springs, and configuration finalization.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import logging
import time
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass

from ultron.core.user_config import UserConfig, save_user_config
from ultron.presence.animation import SpringValue, SpringConfig

logger = logging.getLogger("ultron.presence.onboarding")

SPRING_STEP_FADE = SpringConfig(stiffness=280.0, damping=26.0, mass=1.0)
SPRING_STEP_OFFSET = SpringConfig(stiffness=320.0, damping=22.0, mass=1.0)

VOICE_OPTIONS = [
    ("Puck", "Clear & Direct"),
    ("Charon", "Deep & Authoritative"),
    ("Aoede", "Warm & Precise"),
    ("Fenrir", "Dynamic & Bold"),
    ("Kore", "Calm & Focused"),
]

STYLE_OPTIONS = [
    "Concise & Authoritative",
    "Analytical & Detailed",
    "Minimal",
]


class OnboardingController:
    """State coordinator for the 6-step liquid onboarding experience."""

    def __init__(
        self,
        on_complete: Optional[Callable[[UserConfig], None]] = None,
        on_wake: Optional[Callable[[], None]] = None,
    ):
        self.on_complete = on_complete
        self.on_wake = on_wake

        self.current_step: int = 1
        self.total_steps: int = 6

        # Step 01: Owner
        self.owner_name: str = ""
        self.pronunciation_hint: str = ""

        # Step 02: Addressing
        self.addressing_mode: str = "preferred"  # 'preferred' or 'custom'
        self.custom_address: str = ""

        # Step 03: Identity
        self.identity_mode: str = "ultron"  # 'ultron' or 'custom'
        self.custom_assistant_name: str = ""

        # Step 04: Interaction & Voice
        self.voice_name: str = "Puck"
        self.response_style: str = "Concise & Authoritative"
        self.language: str = "English (US)"

        # Step 05: Privacy & Memory
        self.allow_memory: bool = True

        # Step 06: Startup
        self.start_with_windows: bool = False

        # Input focus tracking
        self.active_field: str = "owner_name"  # 'owner_name', 'pronunciation_hint', 'custom_address', 'custom_assistant_name'
        self.cursor_pos: int = 0
        self.validation_error: str = ""

        # Transition Animation Springs
        self.content_alpha = SpringValue(1.0, SPRING_STEP_FADE)
        self.content_offset_y = SpringValue(0.0, SPRING_STEP_OFFSET)

        # Cursor blink timing
        self._last_cursor_time = time.time()
        self._cursor_visible = True

        # Completion state
        self.is_finalized = False
        self.is_collapsing = False

    def wake(self):
        if self.on_wake:
            self.on_wake()

    def update(self, dt: float):
        """Updates transition springs and cursor blinking."""
        self.content_alpha.update(dt)
        self.content_offset_y.update(dt)

        now = time.time()
        if now - self._last_cursor_time > 0.53:
            self._cursor_visible = not self._cursor_visible
            self._last_cursor_time = now

    @property
    def cursor_visible(self) -> bool:
        return self._cursor_visible

    def set_active_field(self, field_name: str):
        self.active_field = field_name
        text = self._get_field_text(field_name)
        self.cursor_pos = len(text)
        self._cursor_visible = True
        self._last_cursor_time = time.time()
        self.wake()

    def _get_field_text(self, field_name: str) -> str:
        if field_name == "owner_name":
            return self.owner_name
        elif field_name == "pronunciation_hint":
            return self.pronunciation_hint
        elif field_name == "custom_address":
            return self.custom_address
        elif field_name == "custom_assistant_name":
            return self.custom_assistant_name
        return ""

    def _set_field_text(self, field_name: str, val: str):
        if field_name == "owner_name":
            self.owner_name = val
        elif field_name == "pronunciation_hint":
            self.pronunciation_hint = val
        elif field_name == "custom_address":
            self.custom_address = val
        elif field_name == "custom_assistant_name":
            self.custom_assistant_name = val

    def handle_char(self, char: str):
        """Processes typed text character into active input field."""
        if not self.active_field or self.is_finalized:
            return
        if ord(char) < 32:  # Ignore control characters
            return

        text = self._get_field_text(self.active_field)
        if len(text) >= 40:  # Sensible length cap
            return

        pos = max(0, min(len(text), self.cursor_pos))
        new_text = text[:pos] + char + text[pos:]
        self._set_field_text(self.active_field, new_text)
        self.cursor_pos = pos + 1
        self.validation_error = ""
        self._cursor_visible = True
        self._last_cursor_time = time.time()
        self.wake()

    def handle_backspace(self):
        """Handles backspace key in active input field."""
        if not self.active_field or self.is_finalized:
            return
        text = self._get_field_text(self.active_field)
        if not text or self.cursor_pos <= 0:
            return
        pos = min(len(text), self.cursor_pos)
        new_text = text[:pos - 1] + text[pos:]
        self._set_field_text(self.active_field, new_text)
        self.cursor_pos = max(0, pos - 1)
        self.validation_error = ""
        self._cursor_visible = True
        self._last_cursor_time = time.time()
        self.wake()

    def handle_paste(self, text_to_paste: str):
        """Pastes clipboard text into active input field."""
        if not self.active_field or not text_to_paste or self.is_finalized:
            return
        # Sanitize single-line text
        clean = "".join(c for c in text_to_paste if c.isprintable()).strip()[:40]
        if not clean:
            return
        text = self._get_field_text(self.active_field)
        pos = max(0, min(len(text), self.cursor_pos))
        new_text = (text[:pos] + clean + text[pos:])[:40]
        self._set_field_text(self.active_field, new_text)
        self.cursor_pos = min(len(new_text), pos + len(clean))
        self.validation_error = ""
        self.wake()

    def handle_key_left(self):
        if self.cursor_pos > 0:
            self.cursor_pos -= 1
            self._cursor_visible = True
            self._last_cursor_time = time.time()
            self.wake()

    def handle_key_right(self):
        text = self._get_field_text(self.active_field)
        if self.cursor_pos < len(text):
            self.cursor_pos += 1
            self._cursor_visible = True
            self._last_cursor_time = time.time()
            self.wake()

    def handle_tab(self, shift: bool = False):
        """Tab navigation between input fields inside active step."""
        if self.current_step == 1:
            if self.active_field == "owner_name":
                self.set_active_field("pronunciation_hint")
            else:
                self.set_active_field("owner_name")
        self.wake()

    def go_next(self) -> bool:
        """Validates current step and transitions to the next step or finalizes."""
        if self.is_finalized:
            return False

        # Validate step requirements
        if self.current_step == 1:
            if not self.owner_name.strip():
                self.validation_error = "Please enter your name to continue."
                self.wake()
                return False

        elif self.current_step == 2:
            if self.addressing_mode == "custom" and not self.custom_address.strip():
                self.validation_error = "Please enter how ULTRON should address you."
                self.wake()
                return False

        elif self.current_step == 3:
            if self.identity_mode == "custom" and not self.custom_assistant_name.strip():
                self.validation_error = "Please enter an assistant name."
                self.wake()
                return False

        self.validation_error = ""

        if self.current_step < self.total_steps:
            self.current_step += 1
            self._on_enter_step(self.current_step, forward=True)
            return True
        else:
            # Finalize setup on last step completion
            self.finalize()
            return True

    def go_back(self) -> bool:
        """Returns to previous step safely without discarding entered values."""
        if self.is_finalized or self.current_step <= 1:
            return False

        self.validation_error = ""
        self.current_step -= 1
        self._on_enter_step(self.current_step, forward=False)
        return True

    def _on_enter_step(self, step: int, forward: bool):
        """Animates step change with subtle vertical displacement and opacity blend."""
        # Spring animation entrance
        offset = 12.0 if forward else -12.0
        self.content_offset_y.snap_to(offset)
        self.content_offset_y.set_target(0.0)
        self.content_alpha.snap_to(0.35)
        self.content_alpha.set_target(1.0)

        # Update active focus
        if step == 1:
            self.set_active_field("owner_name")
        elif step == 2:
            if self.addressing_mode == "custom":
                self.set_active_field("custom_address")
            else:
                self.active_field = ""
        elif step == 3:
            if self.identity_mode == "custom":
                self.set_active_field("custom_assistant_name")
            else:
                self.active_field = ""
        else:
            self.active_field = ""

        self.wake()

    def finalize(self):
        """Validates all values, persists UserConfig atomically, and triggers complete flow."""
        if self.is_finalized:
            return

        owner = self.owner_name.strip()
        address = self.custom_address.strip() if self.addressing_mode == "custom" else owner
        assistant = self.custom_assistant_name.strip() if self.identity_mode == "custom" else "ULTRON"

        cfg = UserConfig(
            owner_name=owner,
            pronunciation_hint=self.pronunciation_hint.strip(),
            addressing_name=address,
            assistant_name=assistant or "ULTRON",
            preferred_language=self.language,
            voice_preference=self.voice_name,
            response_style=self.response_style,
            presence_enabled=True,
            allow_explicit_memory=self.allow_memory,
            start_with_windows=self.start_with_windows,
            first_run_completed=True,
        )

        ok = save_user_config(cfg)
        if not ok:
            self.validation_error = "Could not save configuration. Retrying..."
            self.wake()
            return

        self.is_finalized = True
        logger.info("[Onboarding] Successfully finalized configuration and persisted user preferences.")

        if self.on_complete:
            self.on_complete(cfg)
