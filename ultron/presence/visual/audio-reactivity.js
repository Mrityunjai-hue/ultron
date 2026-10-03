/**
 * ULTRON v2.0 — Audio Reactivity Processor
 * ─────────────────────────────────────────────────────────────────────────────
 * Smooths real ElevenLabs RMS telemetry and feeds acoustic waveform & bloom.
 * ─────────────────────────────────────────────────────────────────────────────
 */

class AudioReactivityProcessor {
  constructor() {
    this.rawAmplitude = 0.0;
    this.smoothedAmplitude = 0.0;
    this.attack = 0.35; // Fast rise
    this.decay = 0.15;  // Smooth fall
  }

  setRawAmplitude(amp) {
    this.rawAmplitude = Math.max(0.0, Math.min(1.0, amp));
  }

  update() {
    const diff = this.rawAmplitude - this.smoothedAmplitude;
    const factor = diff > 0 ? this.attack : this.decay;
    this.smoothedAmplitude += diff * factor;
    return this.smoothedAmplitude;
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = AudioReactivityProcessor;
}
if (typeof window !== "undefined") {
  window.AudioReactivityProcessor = AudioReactivityProcessor;
}
