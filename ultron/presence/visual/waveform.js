/**
 * ULTRON v2.0 — Living Acoustic Waveform Engine
 * ─────────────────────────────────────────────────────────────────────────────
 * Fluid, organic, continuous acoustic curve spanning x=80 -> 560 at y=235.
 * Driven strictly by:
 * - Activity state (IDLE, LISTENING, THINKING, EXECUTING)
 * - Real ElevenLabs voice amplitude RMS during RESPONDING
 * ─────────────────────────────────────────────────────────────────────────────
 */

class WaveformController {
  constructor(character) {
    this.character = character;
    this.startX = 80;
    this.endX = 560;
    this.baseY = 235;
    this.numPoints = 28;

    this.amplitude = 3.0; // Current rendered amplitude
    this.targetAmplitude = 3.0;
    this.time = 0.0;
    this.speed = 0.02;

    this.activeMode = "IDLE";
    this.realRms = 0.0;
  }

  setMode(activityState, voiceAmplitude = 0.0) {
    this.activeMode = activityState;
    this.realRms = Math.max(0.0, Math.min(1.0, voiceAmplitude));

    if (activityState === "RESPONDING" || this.realRms > 0.02) {
      // Modulated by real voice RMS
      this.targetAmplitude = 5.0 + this.realRms * 48.0;
      this.speed = 0.05 + this.realRms * 0.06;
    } else if (activityState === "THINKING") {
      this.targetAmplitude = 12.0;
      this.speed = 0.038;
    } else if (activityState === "LISTENING") {
      this.targetAmplitude = 7.5;
      this.speed = 0.028;
    } else if (activityState === "EXECUTING") {
      this.targetAmplitude = 10.0;
      this.speed = 0.045;
    } else if (activityState === "OFFLINE") {
      this.targetAmplitude = 0.5;
      this.speed = 0.005;
    } else if (activityState === "RECONNECTING") {
      this.targetAmplitude = 1.5;
      this.speed = 0.008;
    } else {
      // IDLE
      this.targetAmplitude = 3.2;
      this.speed = 0.018;
    }
  }

  update(deltaTime) {
    this.time += this.speed * (deltaTime / 16.6);

    // Smooth exponential decay toward target amplitude (no jitter)
    this.amplitude += (this.targetAmplitude - this.amplitude) * 0.14;

    const pointsPrimary = [];
    const pointsSecondary = [];

    const span = this.endX - this.startX;
    const midX = (this.startX + this.endX) / 2;

    for (let i = 0; i <= this.numPoints; i++) {
      const x = this.startX + (i / this.numPoints) * span;

      // Gaussian bell-curve window to anchor wave to y=235 at endpoints
      const normX = (x - midX) / 185.0;
      const envelope = Math.exp(-normX * normX);

      // Multi-harmonic synthesized organic curve
      const harmonic1 = Math.sin(x * 0.024 + this.time);
      const harmonic2 = Math.sin(x * 0.048 - this.time * 1.4) * 0.55;
      const harmonic3 = Math.cos(x * 0.012 + this.time * 0.7) * 0.35;

      const offsetPrimary = (harmonic1 + harmonic2 + harmonic3) * this.amplitude * envelope;
      pointsPrimary.push({ x, y: this.baseY + offsetPrimary });

      // Secondary faint wave with phase offset
      const secH1 = Math.sin(x * 0.028 - this.time * 0.85);
      const secH2 = Math.cos(x * 0.052 + this.time * 1.1) * 0.5;
      const offsetSecondary = (secH1 + secH2) * (this.amplitude * 0.65) * envelope;
      pointsSecondary.push({ x, y: this.baseY + offsetSecondary });
    }

    // Convert points to smooth cubic Bezier SVG path
    const pathDPrimary = this._pointsToBezier(pointsPrimary);
    const pathDSecondary = this._pointsToBezier(pointsSecondary);

    if (this.character.wavePrimary) {
      this.character.wavePrimary.setAttribute("d", pathDPrimary);
    }
    if (this.character.waveSecondary) {
      this.character.waveSecondary.setAttribute("d", pathDSecondary);
    }
  }

  _pointsToBezier(points) {
    if (!points || points.length === 0) return "";
    let d = `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;

    for (let i = 0; i < points.length - 1; i++) {
      const p0 = i > 0 ? points[i - 1] : points[i];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = i !== points.length - 2 ? points[i + 2] : p2;

      // Catmull-Rom to Cubic Bezier control points
      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;

      d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
    }
    return d;
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = WaveformController;
}
if (typeof window !== "undefined") {
  window.WaveformController = WaveformController;
}
