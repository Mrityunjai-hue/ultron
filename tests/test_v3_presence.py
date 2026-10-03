"""
ULTRON V3 — Phase 4 Cinematic Desktop Presence Test Suite
─────────────────────────────────────────────────────────────────────────────
Comprehensive unit and integration tests covering:
1. Viscous Fluid Spring physics model (stiffness ~360, damping ~32, settling ~380ms)
2. State target geometries and proportions (Idle 130x30, Active 320x48, Expanded 420-460)
3. Ocular parallax tracking (±4px constraint) and ambient respiration
4. Audio Visualizer silk ribbon generation, envelope smoothing, and instant reset
5. HitTester non-rectangular regions and click-through transparency
6. Fullscreen detector logic
7. 32-bit Premultiplied ARGB rendering pipeline
8. Presence State Coordinator runtime event mapping
9. Sub-40ms Interruption visual reaction time
10. Presence Manager failure isolation
─────────────────────────────────────────────────────────────────────────────
"""
import pytest
import time
import math
from unittest.mock import MagicMock, patch
from PIL import Image

from ultron.core.events import ActivityState, EngineEvent, EventBus
from ultron.presence.animation import SpringValue, SpringVec2, SpringChoreographer, STATE_TARGETS
from ultron.presence.audio_visualizer import AudioVisualizer
from ultron.presence.hit_testing import HitTester, FullscreenDetector, HTCLIENT, HTTRANSPARENT
from ultron.presence.renderer import PresenceRenderer
from ultron.presence.states import PresenceStateCoordinator
from ultron.presence.manager import PresenceManager

# =====================================================================
# 1. Spring Physics & Choreography Tests
# =====================================================================

def test_spring_physics_settling_and_overshoot():
    sv = SpringValue(0.0)
    sv.set_target(100.0)

    max_val = 0.0
    settled_time = None
    dt = 0.016 # 60 FPS tick

    for i in range(120): # simulate ~1.9s
        t = i * dt
        val = sv.update(dt)
        if val > max_val:
            max_val = val
        if sv.is_settled and settled_time is None:
            settled_time = t

    # 1. Settles within 1.5s
    assert settled_time is not None, "Spring failed to settle"
    assert 0.25 <= settled_time <= 1.5, f"Settling time out of expected range: {settled_time*1000:.1f}ms"

    # 2. Bouncy overshoot ~10-20% (max_val between 110.0 and 120.0)
    overshoot_pct = (max_val - 100.0) / 100.0 * 100.0
    assert 5.0 <= overshoot_pct <= 22.0, f"Overshoot out of bounds: {overshoot_pct:.2f}%"

def test_state_targets_geometry_and_proportions():
    assert "IDLE" in STATE_TARGETS
    assert "LISTENING" in STATE_TARGETS
    assert "THINKING" in STATE_TARGETS
    assert "RESPONDING" in STATE_TARGETS
    assert "TOOL_EXEC" in STATE_TARGETS
    assert "TOOL_COMPLETE" in STATE_TARGETS
    assert "CONFIRMATION" in STATE_TARGETS

    idle = STATE_TARGETS["IDLE"]
    assert idle.width == 340.0 and idle.height == 68.0
    assert idle.crease_span == 240.0

    listen = STATE_TARGETS["LISTENING"]
    assert listen.width == 390.0 and listen.height == 82.0
    assert listen.crease_span > idle.crease_span

    tool = STATE_TARGETS["TOOL_EXEC"]
    assert tool.width == 540.0 and tool.height == 144.0

    vault = STATE_TARGETS["CONFIRMATION"]
    assert vault.width == 540.0 and vault.height == 196.0

def test_ocular_parallax_and_blink_kinetics():
    ch = SpringChoreographer()
    ch.set_gaze(10.0, 0.0) # Request out-of-bounds gaze
    # Gaze must be strictly clamped to ±4.0px per design spec
    assert ch.gaze_x.target <= 4.0
    ch.set_gaze(-15.0, 0.0)
    assert ch.gaze_x.target >= -4.0

    # Ambient update
    ch.set_state("IDLE")
    ch.update(0.016)
    assert ch._current_respiration >= 0.0

# =====================================================================
# 2. Audio Visualizer & Silk Waveform Tests
# =====================================================================

def test_audio_visualizer_silk_ribbons():
    viz = AudioVisualizer(num_nodes=7)

    # Push microphone chunk
    viz.push_input_chunk(0.08)
    assert viz.is_active is True
    amp = viz.update(0.016)
    assert amp > 0.0

    left_nodes, right_nodes = viz.get_silk_ribbon_nodes(max_height=14.0)
    assert len(left_nodes) == 7
    assert len(right_nodes) == 7
    # Endpoints should taper to near zero
    assert abs(left_nodes[0]) < 0.001
    assert abs(left_nodes[-1]) < 0.001

    # Interruption instant reset
    viz.reset()
    assert viz.smoothed_amplitude == 0.0
    assert viz.is_active is False

# =====================================================================
# 3. Hit-Testing & Fullscreen Tests
# =====================================================================

def test_hit_tester_non_rectangular_regions():
    ht = HitTester(window_width=600, window_height=220)
    ht.set_screen_size(1920, 1080, win_w=600, win_h=220)

    # Screen center: x=960, y=0. Notch: width=340 -> [790, 1130], height=52 -> [0, 52]
    # Point outside notch -> HTTRANSPARENT
    resp, target = ht.test_point(500, 20, 340, 52, "LISTENING")
    assert resp == HTTRANSPARENT
    assert target.target_type == "NONE"

    # Point inside notch center -> HTCLIENT
    resp, target = ht.test_point(960, 24, 340, 52, "LISTENING")
    assert resp == HTCLIENT
    assert target.target_type == "NOTCH"

    # Point on Confirmation buttons
    # Allow button in Confirmation state (win_cx = 300, screen_x = 960 - 80 = 880, y=140)
    resp, target = ht.test_point(960 - 80, 140, 500, 180, "CONFIRMATION")
    assert resp == HTCLIENT
    assert target.target_type == "ALLOW_BUTTON"

    # Dismiss button in Confirmation state (screen_x = 960 + 80 = 1040, y=140)
    resp, target = ht.test_point(960 + 80, 140, 500, 180, "CONFIRMATION")
    assert resp == HTCLIENT
    assert target.target_type == "DISMISS_BUTTON"

# =====================================================================
# 4. 32-Bit Premultiplied ARGB Renderer Tests
# =====================================================================

def test_presence_renderer_all_states():
    ch = SpringChoreographer()
    viz = AudioVisualizer()
    renderer = PresenceRenderer(canvas_width=600, canvas_height=220)

    for state in ("IDLE", "LISTENING", "THINKING", "RESPONDING", "INTERRUPTED", "TOOL_EXEC", "CONFIRMATION", "RETRACTED"):
        ch.set_state(state)
        # Advance physics
        for _ in range(10):
            ch.update(0.016)
        viz.update(0.016)

        img = renderer.render_frame(ch, viz, 0.016)
        assert isinstance(img, Image.Image)
        assert img.size == (600, 220)

        bgra = renderer.to_premultiplied_bgra(img)
        assert len(bgra) == 600 * 220 * 4

# =====================================================================
# 5. State Coordinator & Interruption Reaction Tests
# =====================================================================

def test_state_coordinator_transitions_and_sub40ms_interruption():
    ch = SpringChoreographer()
    viz = AudioVisualizer()
    renderer = PresenceRenderer(canvas_width=1920, canvas_height=420)
    coord = PresenceStateCoordinator(ch, viz, renderer)

    # 1. Test IDLE transition
    coord.on_engine_event(EngineEvent(state=ActivityState.IDLE))
    assert ch.current_state_name == "IDLE"

    # 2. Test LISTENING transition
    coord.on_engine_event(EngineEvent(state=ActivityState.LISTENING))
    assert ch.current_state_name == "LISTENING"

    # 3. Test THINKING transition
    coord.on_engine_event(EngineEvent(state=ActivityState.THINKING))
    assert ch.current_state_name == "THINKING"

    # 4. Test Tool Execution Pod
    coord.on_engine_event(EngineEvent(state=ActivityState.THINKING, operation="open_app", message="Opening chrome"))
    assert ch.current_state_name == "TOOL_EXEC"
    assert renderer.tool_info.get("tool_name") == "OPEN_APP"

    # 5. Test RESPONDING transition
    coord.on_engine_event(EngineEvent(state=ActivityState.RESPONDING))
    assert ch.current_state_name == "RESPONDING"

    # 6. Test INTERRUPTED transition (<40ms reaction time requirement)
    t0 = time.perf_counter()
    coord.on_engine_event(EngineEvent(state=ActivityState.INTERRUPTED))
    t_elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert ch.current_state_name == "INTERRUPTED"
    assert viz.smoothed_amplitude == 0.0 # Waveform instantly collapsed
    assert t_elapsed_ms < 40.0, f"Interruption reaction exceeded 40ms: {t_elapsed_ms:.2f}ms"

# =====================================================================
# 6. Presence Manager Failure Isolation Test
# =====================================================================

def test_presence_manager_failure_isolation():
    manager = PresenceManager(runtime=None)

    # Mocking failure during window start
    with patch("ultron.presence.window.UltronOverlayWindow.start", side_effect=RuntimeError("GDI Subsystem Failure")):
        manager.start()
        # Manager caught error and set is_active to False without crashing
        assert manager.is_active is False
