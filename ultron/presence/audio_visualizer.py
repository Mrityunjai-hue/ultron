"""
ULTRON V3 — Presence Audio Visualizer & Silk Ribbon Harmonic Generator
─────────────────────────────────────────────────────────────────────────────
Lightweight amplitude/envelope analyzer hooking into existing PCM streams.
Produces smooth multi-node harmonic control points for twin silk ribbons
without duplicate microphone streams, audio devices, or heavy FFT overhead.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import math
import time
import numpy as np
from typing import List, Tuple

class AudioVisualizer:
    """Computes smooth envelope telemetry and silk wave harmonic nodes."""

    def __init__(self, num_nodes: int = 7):
        self.num_nodes = num_nodes
        self.raw_amplitude = 0.0
        self.smoothed_amplitude = 0.0
        self.peak_amplitude = 0.0

        # Dynamics filter parameters
        self.attack_coef = 0.45    # Fast rise
        self.decay_coef = 0.08     # Smooth fall
        self.floor_threshold = 0.008

        # Harmonic wave parameters
        self._phase = 0.0
        self._last_time = time.time()
        self.is_active = False

    def push_input_chunk(self, rms_energy: float):
        """Called when microphone chunk arrives."""
        self.raw_amplitude = max(0.0, min(1.0, rms_energy * 4.5))
        self.is_active = True

    def push_output_pcm(self, pcm_bytes: bytes):
        """Called when model playback PCM chunk is enqueued."""
        if not pcm_bytes:
            return
        try:
            arr = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            rms = float(np.sqrt(np.mean(arr ** 2))) if len(arr) > 0 else 0.0
            self.raw_amplitude = max(0.0, min(1.0, rms * 5.0))
            self.is_active = True
        except Exception:
            pass

    def reset(self):
        """Instant zero-latency dampening on interruption."""
        self.raw_amplitude = 0.0
        self.smoothed_amplitude = 0.0
        self.peak_amplitude = 0.0
        self.is_active = False

    def update(self, dt: float) -> float:
        """Applies asymmetric attack/decay envelope smoothing."""
        now = time.time()
        self._phase += dt * (3.5 + self.smoothed_amplitude * 4.0)

        # Smooth toward raw amplitude
        if self.raw_amplitude > self.smoothed_amplitude:
            self.smoothed_amplitude += (self.raw_amplitude - self.smoothed_amplitude) * self.attack_coef
        else:
            self.smoothed_amplitude += (self.raw_amplitude - self.smoothed_amplitude) * self.decay_coef

        # Floor noise gate
        if self.smoothed_amplitude < self.floor_threshold:
            self.smoothed_amplitude = 0.0
            self.is_active = False

        self.peak_amplitude = max(self.smoothed_amplitude, self.peak_amplitude * 0.96)
        # Gradually decay raw input
        self.raw_amplitude *= 0.88
        return self.smoothed_amplitude

    def get_silk_ribbon_nodes(self, max_height: float = 14.0) -> Tuple[List[float], List[float]]:
        """
        Generates harmonic vertical offsets for Left and Right flanking silk ribbons.
        Returns (left_nodes, right_nodes) normalized from -max_height to +max_height.
        """
        amp = self.smoothed_amplitude
        if amp <= 0.001:
            return [0.0] * self.num_nodes, [0.0] * self.num_nodes

        left_nodes = []
        right_nodes = []

        for i in range(self.num_nodes):
            t = i / (self.num_nodes - 1) # 0.0 to 1.0
            # Bell envelope so edges taper gracefully to 0
            taper = math.sin(t * math.pi)

            # Dual harmonic frequencies (fundamental + 2nd harmonic)
            harm1 = math.sin(self._phase + t * 2.8)
            harm2 = math.cos(self._phase * 1.6 - t * 3.4) * 0.4
            offset_left = (harm1 + harm2) * taper * amp * max_height

            # Right side with subtle counter-phase for natural bilateral balance
            harm1_r = math.sin(self._phase + t * 2.8 + math.pi * 0.4)
            harm2_r = math.cos(self._phase * 1.6 - t * 3.4 + math.pi * 0.2) * 0.4
            offset_right = (harm1_r + harm2_r) * taper * amp * max_height

            left_nodes.append(offset_left)
            right_nodes.append(offset_right)

        return left_nodes, right_nodes
