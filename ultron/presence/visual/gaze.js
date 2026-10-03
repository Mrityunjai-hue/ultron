/**
 * ULTRON v2.0 — Optical Gaze Tracking Controller
 * ─────────────────────────────────────────────────────────────────────────────
 * Smooth spring-damped 2D interpolation for optical cores inside housing apertures.
 * ─────────────────────────────────────────────────────────────────────────────
 */

class GazeController {
  constructor(character) {
    this.character = character;
    this.targetX = 0.0;
    this.targetY = 0.0;
    this.currentX = 0.0;
    this.currentY = 0.0;

    this.maxDisplacementX = 18.0; // px inside 88px aperture
    this.maxDisplacementY = 14.0; // px inside 145px aperture
    this.damping = 0.12;
    this.lastTargetTime = Date.now();
  }

  setTarget(x, y) {
    this.targetX = Math.max(-1.0, Math.min(1.0, x));
    this.targetY = Math.max(-1.0, Math.min(1.0, y));
    this.lastTargetTime = Date.now();
  }

  update() {
    // If no target updated in 3.5s, slowly drift back to neutral center
    if (Date.now() - this.lastTargetTime > 3500) {
      this.targetX = 0.0;
      this.targetY = 0.0;
    }

    // Spring interpolation
    this.currentX += (this.targetX - this.currentX) * this.damping;
    this.currentY += (this.targetY - this.currentY) * this.damping;

    const pxX = (this.currentX * this.maxDisplacementX).toFixed(2);
    const pxY = (this.currentY * this.maxDisplacementY).toFixed(2);

    if (this.character.leftCore) {
      this.character.leftCore.setAttribute("transform", `translate(${pxX}, ${pxY})`);
    }
    if (this.character.rightCore) {
      this.character.rightCore.setAttribute("transform", `translate(${pxX}, ${pxY})`);
    }
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = GazeController;
}
if (typeof window !== "undefined") {
  window.GazeController = GazeController;
}
