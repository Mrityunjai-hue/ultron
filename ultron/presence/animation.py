"""
ULTRON V3 — Presence Kinetic Physics & Bouncy Spring Choreography
─────────────────────────────────────────────────────────────────────────────
Implements exact analytical damped harmonic oscillator physics (Euler/Exact)
with specialized bouncy spring profiles for organic, fluid transitions,
elastic card pop-ups, staggered UI reveals, and optical singularity kinetics.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import math
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple

@dataclass
class SpringConfig:
    """Spring physical parameters."""
    stiffness: float = 320.0    # Tension / Speed (k)
    damping: float = 18.0       # Resistance (c) -> zeta = c / (2 * sqrt(k * m))
    mass: float = 1.0           # Inertia (m)
    precision: float = 0.001    # Settling threshold

# ─── Specialized Spring Profiles ─────────────────────────────────────────────
# 1. Bouncy Container: ~16% elastic overshoot for notch expansions
SPRING_BOUNCY_CONTAINER = SpringConfig(stiffness=310.0, damping=18.0, mass=1.0)

# 2. Elastic Pop-up Content: ~14% bounce for card scale & offset transitions
SPRING_ELASTIC_POPUP    = SpringConfig(stiffness=360.0, damping=18.5, mass=1.0)

# 3. Snappy Button & Badge Pop: ~12% bouncy pop for interactive buttons & icons
SPRING_BUTTON_POP       = SpringConfig(stiffness=420.0, damping=20.0, mass=1.0)

# 4. Fluid Singularity Horizon: Smooth, organic magnetic tension morphing
SPRING_FLUID_HORIZON    = SpringConfig(stiffness=250.0, damping=19.0, mass=1.0)

# 5. Fast Optical Flare Burst: Snappy energy pulse and settle
SPRING_BURST_FLARE      = SpringConfig(stiffness=460.0, damping=24.0, mass=1.0)

# 6. Smooth Alpha Fade: Non-overshooting critically damped blend
SPRING_SMOOTH_FADE      = SpringConfig(stiffness=260.0, damping=28.0, mass=1.0)

# 7. Gaze Parallax: Fast responsive cursor tracking
SPRING_GAZE             = SpringConfig(stiffness=340.0, damping=24.0, mass=1.0)


class SpringValue:
    """
    Exact Analytical 1D Damped Harmonic Oscillator Simulator.
    Completely stable at any frame rate / delta-time, delivering mathematically
    pure spring trajectories with zero numerical drift or jitter.
    """

    def __init__(self, initial_value: float = 0.0, config: Optional[SpringConfig] = None):
        self.config = config or SPRING_BOUNCY_CONTAINER
        self.current = float(initial_value)
        self.target = float(initial_value)
        self.velocity = 0.0
        self.is_settled = True

    def set_target(self, target: float, initial_velocity: Optional[float] = None):
        if abs(self.target - target) > self.config.precision or initial_velocity is not None:
            self.target = float(target)
            self.is_settled = False
            if initial_velocity is not None:
                self.velocity = float(initial_velocity)

    def snap_to(self, value: float):
        self.current = float(value)
        self.target = float(value)
        self.velocity = 0.0
        self.is_settled = True

    def update(self, dt: float) -> float:
        if self.is_settled:
            return self.current

        # Cap dt to avoid extreme step jumps
        dt = min(max(dt, 0.0001), 0.08)

        k = self.config.stiffness
        c = self.config.damping
        m = self.config.mass

        w0 = math.sqrt(k / m)
        zeta = c / (2.0 * math.sqrt(k * m))
        x0 = self.current - self.target
        v0 = self.velocity

        if zeta < 0.999:  # Underdamped (Bouncy spring with natural oscillation)
            wd = w0 * math.sqrt(1.0 - zeta * zeta)
            alpha = zeta * w0
            exp_term = math.exp(-alpha * dt)
            cos_term = math.cos(wd * dt)
            sin_term = math.sin(wd * dt)
            a = x0
            b = (v0 + alpha * x0) / wd
            new_x = self.target + exp_term * (a * cos_term + b * sin_term)
            new_v = exp_term * ((b * wd - alpha * a) * cos_term - (a * wd + alpha * b) * sin_term)
        elif zeta > 1.001:  # Overdamped
            mu = w0 * math.sqrt(zeta * zeta - 1.0)
            r1 = -zeta * w0 + mu
            r2 = -zeta * w0 - mu
            c2 = (v0 - r1 * x0) / (r2 - r1)
            c1 = x0 - c2
            exp1 = math.exp(r1 * dt)
            exp2 = math.exp(r2 * dt)
            new_x = self.target + c1 * exp1 + c2 * exp2
            new_v = c1 * r1 * exp1 + c2 * r2 * exp2
        else:  # Critically damped
            a = x0
            b = v0 + w0 * x0
            exp_term = math.exp(-w0 * dt)
            new_x = self.target + exp_term * (a + b * dt)
            new_v = exp_term * (v0 - w0 * b * dt)

        self.current = new_x
        self.velocity = new_v

        if abs(self.current - self.target) < self.config.precision and abs(self.velocity) < (self.config.precision * 10.0):
            self.current = self.target
            self.velocity = 0.0
            self.is_settled = True

        return self.current


class SpringVec2:
    """2D analytical spring simulator for width/height or position pairs."""

    def __init__(self, x: float = 0.0, y: float = 0.0, config: Optional[SpringConfig] = None):
        cfg = config or SPRING_BOUNCY_CONTAINER
        self.sx = SpringValue(x, cfg)
        self.sy = SpringValue(y, cfg)

    @property
    def x(self) -> float:
        return self.sx.current

    @property
    def y(self) -> float:
        return self.sy.current

    @property
    def is_settled(self) -> bool:
        return self.sx.is_settled and self.sy.is_settled

    def set_target(self, tx: float, ty: float, vx: Optional[float] = None, vy: Optional[float] = None):
        self.sx.set_target(tx, vx)
        self.sy.set_target(ty, vy)

    def snap_to(self, x: float, y: float):
        self.sx.snap_to(x)
        self.sy.snap_to(y)

    def update(self, dt: float) -> Tuple[float, float]:
        return self.sx.update(dt), self.sy.update(dt)


@dataclass
class VisualStateTargets:
    """Target geometric and optical properties for a specific UI state."""
    width: float
    height: float
    corner_radius: float
    crease_span: float           # Horizontal width of laser crease
    white_core_intensity: float  # 0.0 to 1.0
    violet_aura_intensity: float # 0.0 to 1.0
    specular_rim_opacity: float  # 0.0 to 1.0
    action_pod_alpha: float = 0.0
    vault_alpha: float = 0.0
    onboarding_alpha: float = 0.0


# Authoritative visual state definitions matching Concept A ("The Singularity Crease")
STATE_TARGETS: Dict[str, VisualStateTargets] = {
    "IDLE": VisualStateTargets(
        width=340.0,
        height=68.0,
        corner_radius=24.0,
        crease_span=240.0,
        white_core_intensity=0.88,
        violet_aura_intensity=0.70,
        specular_rim_opacity=0.06,
    ),
    "HOVER": VisualStateTargets(
        width=356.0,
        height=72.0,
        corner_radius=25.0,
        crease_span=256.0,
        white_core_intensity=0.98,
        violet_aura_intensity=0.88,
        specular_rim_opacity=0.10,
    ),
    "LISTENING": VisualStateTargets(
        width=390.0,
        height=82.0,
        corner_radius=26.0,
        crease_span=280.0,
        white_core_intensity=1.0,
        violet_aura_intensity=0.98,
        specular_rim_opacity=0.12,
    ),
    "THINKING": VisualStateTargets(
        width=340.0,
        height=68.0,
        corner_radius=24.0,
        crease_span=240.0,
        white_core_intensity=1.0,
        violet_aura_intensity=0.98,
        specular_rim_opacity=0.11,
    ),
    "RESPONDING": VisualStateTargets(
        width=390.0,
        height=82.0,
        corner_radius=26.0,
        crease_span=280.0,
        white_core_intensity=1.0,
        violet_aura_intensity=0.98,
        specular_rim_opacity=0.12,
    ),
    "INTERRUPTED": VisualStateTargets(
        width=360.0,
        height=74.0,
        corner_radius=25.0,
        crease_span=260.0,
        white_core_intensity=1.0,
        violet_aura_intensity=1.0,
        specular_rim_opacity=0.15,
    ),
    "TOOL_EXEC": VisualStateTargets(
        width=540.0,
        height=144.0,
        corner_radius=24.0,
        crease_span=180.0,
        white_core_intensity=0.92,
        violet_aura_intensity=0.70,
        specular_rim_opacity=0.10,
        action_pod_alpha=1.0,
    ),
    "TOOL_COMPLETE": VisualStateTargets(
        width=540.0,
        height=144.0,
        corner_radius=24.0,
        crease_span=180.0,
        white_core_intensity=0.96,
        violet_aura_intensity=0.78,
        specular_rim_opacity=0.10,
        action_pod_alpha=1.0,
    ),
    "CONFIRMATION": VisualStateTargets(
        width=540.0,
        height=196.0,
        corner_radius=24.0,
        crease_span=180.0,
        white_core_intensity=1.0,
        violet_aura_intensity=0.88,
        specular_rim_opacity=0.16,
        vault_alpha=1.0,
    ),
    "ONBOARDING": VisualStateTargets(
        width=580.0,
        height=480.0,
        corner_radius=26.0,
        crease_span=320.0,
        white_core_intensity=0.96,
        violet_aura_intensity=0.88,
        specular_rim_opacity=0.12,
        onboarding_alpha=1.0,
    ),
    "RETRACTED": VisualStateTargets(
        width=160.0,
        height=16.0,
        corner_radius=8.0,
        crease_span=80.0,
        white_core_intensity=0.85,
        violet_aura_intensity=0.60,
        specular_rim_opacity=0.0,
    ),
}


class SpringChoreographer:
    """Coordinates fluid spring animation between states, popups, and micro-kinetics."""

    def __init__(self):
        # 1. Primary Container Size Spring (Bouncy ~16% overshoot on resize)
        self.size = SpringVec2(340.0, 68.0, SPRING_BOUNCY_CONTAINER)
        self.corner_radius = SpringValue(24.0, SPRING_FLUID_HORIZON)

        # 2. Singularity Crease Optical Geometry Springs
        self.crease_span = SpringValue(240.0, SPRING_FLUID_HORIZON)
        self.crease_flare = SpringValue(1.0, SPRING_BURST_FLARE) # Dynamic flare burst
        self.wave_energy = SpringValue(0.0, SPRING_FLUID_HORIZON)  # Kinetic wave energy

        # 3. Optical Intensity Springs
        self.white_core = SpringValue(0.88, SPRING_FLUID_HORIZON)
        self.violet_aura = SpringValue(0.70, SPRING_FLUID_HORIZON)
        self.specular_rim = SpringValue(0.06, SPRING_FLUID_HORIZON)

        # 4. Expanded Panel Pop-up Kinetics (Elastic scale & vertical drop)
        self.content_scale = SpringValue(1.0, SPRING_ELASTIC_POPUP)
        self.content_offset_y = SpringValue(0.0, SPRING_ELASTIC_POPUP)
        self.button_scale = SpringValue(1.0, SPRING_BUTTON_POP)
        self.icon_bounce = SpringValue(1.0, SPRING_BUTTON_POP)

        # 5. Opacity Channels
        self.action_pod_alpha = SpringValue(0.0, SPRING_SMOOTH_FADE)
        self.vault_alpha = SpringValue(0.0, SPRING_SMOOTH_FADE)
        self.onboarding_alpha = SpringValue(0.0, SPRING_SMOOTH_FADE)
        self.content_alpha = SpringValue(0.0, SPRING_SMOOTH_FADE)

        # 6. Gaze Tracking & Hover
        self.gaze_x = SpringValue(0.0, SPRING_GAZE)
        self.gaze_y = SpringValue(0.0, SPRING_GAZE)
        self.hover_lift = SpringValue(0.0, SPRING_GAZE)

        # 7. Ambient Timing & Voice Resonance
        self._start_time = time.time()
        self._last_blink_time = time.time()
        self._next_blink_interval = 35.0
        self._blink_val = 0.0
        self._audio_resonance = 0.0

        self.current_state_name = "IDLE"

    def set_state(self, state_name: str):
        """Morphs spring targets to new visual state with physical choreography and elastic pop."""
        prev_state = self.current_state_name
        target = STATE_TARGETS.get(state_name, STATE_TARGETS["IDLE"])
        self.current_state_name = state_name

        is_becoming_expanded = (target.action_pod_alpha > 0.0 or target.vault_alpha > 0.0 or target.onboarding_alpha > 0.0)
        was_expanded = (prev_state in ("TOOL_EXEC", "TOOL_COMPLETE", "CONFIRMATION", "ONBOARDING"))

        # Trigger Bouncy Pop-up Kinetic Entrance when opening panels
        if is_becoming_expanded and not was_expanded:
            self.content_scale.snap_to(0.86)
            self.content_scale.set_target(1.0, initial_velocity=1.6)
            self.content_offset_y.snap_to(-14.0)
            self.content_offset_y.set_target(0.0, initial_velocity=12.0)
            self.button_scale.snap_to(0.74)
            self.button_scale.set_target(1.0, initial_velocity=2.4)
            self.icon_bounce.snap_to(0.60)
            self.icon_bounce.set_target(1.0, initial_velocity=3.2)
        elif is_becoming_expanded and was_expanded:
            # Switching between tool/vault/onboarding: give subtle bounce
            self.button_scale.snap_to(0.88)
            self.button_scale.set_target(1.0, initial_velocity=1.8)
            self.icon_bounce.snap_to(0.82)
            self.icon_bounce.set_target(1.0, initial_velocity=2.0)

        # Trigger Optical Flare Flash on state transition
        if state_name != prev_state:
            self.crease_flare.snap_to(1.75)
            self.crease_flare.set_target(1.0)
            self.wave_energy.snap_to(1.0)
            self.wave_energy.set_target(0.0)

        # Container & Geometric Spring Targets
        self.size.set_target(target.width, target.height)
        self.corner_radius.set_target(target.corner_radius)
        self.crease_span.set_target(target.crease_span)

        # Optical Intensity Targets
        self.white_core.set_target(target.white_core_intensity)
        self.violet_aura.set_target(target.violet_aura_intensity)
        self.specular_rim.set_target(target.specular_rim_opacity)

        # Alpha Blend Targets
        self.action_pod_alpha.set_target(target.action_pod_alpha)
        self.vault_alpha.set_target(target.vault_alpha)
        self.onboarding_alpha.set_target(target.onboarding_alpha)
        self.content_alpha.set_target(1.0 if is_becoming_expanded else 0.0)

    def set_hover(self, is_hovered: bool):
        self.hover_lift.set_target(14.0 if is_hovered else 0.0)

    def set_gaze(self, offset_x: float, offset_y: float = 0.0):
        clamped_x = max(-4.0, min(4.0, offset_x))
        clamped_y = max(-2.0, min(2.0, offset_y))
        self.gaze_x.set_target(clamped_x)
        self.gaze_y.set_target(clamped_y)

    def snap_interruption(self):
        """High-velocity instantaneous snub on interruption (<40ms reaction)."""
        self.set_state("INTERRUPTED")
        self.crease_flare.snap_to(2.2)
        self.crease_flare.set_target(1.0)
        self.white_core.snap_to(1.0)
        self.violet_aura.snap_to(1.0)
        self.content_alpha.snap_to(0.0)

    def is_all_settled(self) -> bool:
        """Returns True when all springs have reached resting equilibrium."""
        return (
            self.size.is_settled
            and self.corner_radius.is_settled
            and self.crease_span.is_settled
            and self.crease_flare.is_settled
            and self.wave_energy.is_settled
            and self.white_core.is_settled
            and self.violet_aura.is_settled
            and self.specular_rim.is_settled
            and self.content_scale.is_settled
            and self.content_offset_y.is_settled
            and self.button_scale.is_settled
            and self.icon_bounce.is_settled
            and self.action_pod_alpha.is_settled
            and self.vault_alpha.is_settled
            and self.onboarding_alpha.is_settled
            and self.content_alpha.is_settled
            and self.gaze_x.is_settled
            and self.gaze_y.is_settled
            and self.hover_lift.is_settled
            and self._blink_val == 0.0
        )

    def update(self, dt: float, audio_amp: float = 0.0):
        """Advances physics simulation, audio resonance, and ambient clock."""
        now = time.time()
        self.size.update(dt)
        self.corner_radius.update(dt)
        self.crease_span.update(dt)
        self.crease_flare.update(dt)
        self.wave_energy.update(dt)
        self.white_core.update(dt)
        self.violet_aura.update(dt)
        self.specular_rim.update(dt)
        self.content_scale.update(dt)
        self.content_offset_y.update(dt)
        self.button_scale.update(dt)
        self.icon_bounce.update(dt)
        self.action_pod_alpha.update(dt)
        self.vault_alpha.update(dt)
        self.onboarding_alpha.update(dt)
        self.content_alpha.update(dt)
        self.gaze_x.update(dt)
        self.gaze_y.update(dt)
        self.hover_lift.update(dt)

        self._audio_resonance = max(0.0, min(1.0, audio_amp))

        # Ambient Idle Kinetics (Sentient respiration & rare micro-blinks)
        if self.current_state_name == "IDLE":
            elapsed = now - self._start_time
            respiration = 0.5 + 0.5 * math.sin(elapsed * (2.0 * math.pi / 8.0))
            self._current_respiration = respiration

            time_since_blink = now - self._last_blink_time
            if time_since_blink > self._next_blink_interval:
                if time_since_blink < self._next_blink_interval + 0.14:
                    phase = (time_since_blink - self._next_blink_interval) / 0.14
                    self._blink_val = math.sin(phase * math.pi)
                else:
                    self._blink_val = 0.0
                    self._last_blink_time = now
                    self._next_blink_interval = 30.0 + (hash(str(now)) % 15)
            else:
                self._blink_val = 0.0
        else:
            self._current_respiration = 0.0
            self._blink_val = 0.0

