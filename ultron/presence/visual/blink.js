/**
 * ULTRON v2.0 — Natural Ocular Blink Controller
 * ─────────────────────────────────────────────────────────────────────────────
 * Random natural intervals with smooth non-linear scaleY shutter transitions.
 * ─────────────────────────────────────────────────────────────────────────────
 */

class BlinkController {
  constructor(character) {
    this.character = character;
    this.isBlinking = false;
    this.blinkProgress = 0.0;
    this.blinkDuration = 180; // ms
    this.blinkStartTime = 0;

    this.nextBlinkTimeout = null;
    this.scheduleNextBlink();
  }

  scheduleNextBlink() {
    if (this.nextBlinkTimeout) clearTimeout(this.nextBlinkTimeout);
    // Random interval between 2.8s and 6.0s
    const delay = 2800 + Math.random() * 3200;
    this.nextBlinkTimeout = setTimeout(() => {
      this.triggerBlink();
      this.scheduleNextBlink();
    }, delay);
  }

  triggerBlink() {
    if (this.isBlinking) return;
    this.isBlinking = true;
    this.blinkStartTime = performance.now();
  }

  update(now) {
    if (!this.isBlinking) return;

    const elapsed = now - this.blinkStartTime;
    const t = Math.min(1.0, elapsed / this.blinkDuration);

    let scaleY = 1.0;
    if (t < 0.5) {
      // Closing: 1.0 -> 0.05 (ease-in)
      const phase = t / 0.5;
      scaleY = 1.0 - Math.pow(phase, 2) * 0.95;
    } else {
      // Opening: 0.05 -> 1.0 (ease-out)
      const phase = (t - 0.5) / 0.5;
      scaleY = 0.05 + (1 - Math.pow(1 - phase, 2)) * 0.95;
    }

    if (this.character.leftEye) {
      this.character.leftEye.setAttribute("transform", `scale(1, ${scaleY.toFixed(3)})`);
    }
    if (this.character.rightEye) {
      this.character.rightEye.setAttribute("transform", `scale(1, ${scaleY.toFixed(3)})`);
    }

    if (t >= 1.0) {
      this.isBlinking = false;
      if (this.character.leftEye) this.character.leftEye.removeAttribute("transform");
      if (this.character.rightEye) this.character.rightEye.removeAttribute("transform");
    }
  }

  destroy() {
    if (this.nextBlinkTimeout) clearTimeout(this.nextBlinkTimeout);
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = BlinkController;
}
if (typeof window !== "undefined") {
  window.BlinkController = BlinkController;
}
