"""
ULTRON V3 — Presence Package
─────────────────────────────────────────────────────────────────────────────
Exposes the cinematic desktop presence manager and visual engine.
─────────────────────────────────────────────────────────────────────────────
"""
from ultron.presence.animation import SpringChoreographer, SpringValue, SpringVec2
from ultron.presence.audio_visualizer import AudioVisualizer
from ultron.presence.hit_testing import HitTester, FullscreenDetector
from ultron.presence.renderer import PresenceRenderer
from ultron.presence.window import UltronOverlayWindow
from ultron.presence.states import PresenceStateCoordinator
from ultron.presence.manager import PresenceManager

__all__ = [
    "SpringChoreographer",
    "SpringValue",
    "SpringVec2",
    "AudioVisualizer",
    "HitTester",
    "FullscreenDetector",
    "PresenceRenderer",
    "UltronOverlayWindow",
    "PresenceStateCoordinator",
    "PresenceManager",
]
