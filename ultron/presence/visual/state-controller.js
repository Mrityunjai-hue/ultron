/**
 * ULTRON v2.0 — Authoritative State Controller
 * ─────────────────────────────────────────────────────────────────────────────
 * Maps canonical backend ActivityState, MoodState, and operation metadata
 * directly to visual SVG attributes, eyebrow angles, color gradients, and status pill.
 * ─────────────────────────────────────────────────────────────────────────────
 */

class StateController {
  constructor(character, waveform, audioProcessor) {
    this.character = character;
    this.waveform = waveform;
    this.audioProcessor = audioProcessor;

    this.activity = "IDLE";
    this.mood = "CALM";
    this.operation = "none";
    this.attention = 0.5;

    // Eyebrow dynamics (interpolated)
    this.leftBrowAngle = 0.0;
    this.rightBrowAngle = 0.0;
    this.leftBrowOffsetY = 0.0;
    this.rightBrowOffsetY = 0.0;

    this.targetLeftAngle = 0.0;
    this.targetRightAngle = 0.0;
    this.targetOffsetY = 0.0;
  }

  setAuthoritativeState({
    activity,
    mood,
    operation,
    attention,
  }) {
    if (activity !== undefined && activity !== null) {
      this.activity = activity.toUpperCase();
    }
    if (mood !== undefined && mood !== null) {
      this.mood = mood.toUpperCase();
    }
    if (operation !== undefined && operation !== null) {
      this.operation = operation.toLowerCase();
    }
    if (attention !== undefined && attention !== null) {
      this.attention = attention;
    }

    this.updateStatusPill();
    this.updateEyebrowTargets();
    this.updateGradientsAndGlow();
  }

  updateStatusPill() {
    if (!this.character.statusText || !this.character.statusPillGroup) return;

    if (this.activity === "IDLE") {
      // In IDLE, status pill is hidden to maintain pure negative space
      this.character.statusPillGroup.style.opacity = "0";
      this.character.statusPillGroup.style.transition = "opacity 0.4s ease";
      return;
    }

    this.character.statusPillGroup.style.opacity = "1";
    this.character.statusPillGroup.style.transition = "opacity 0.3s ease";

    const pillMap = {
      THINKING:     "◇ THINKING...",
      LISTENING:    "◇ LISTENING",
      RESPONDING:   "◇ RESPONDING",
      RECONNECTING: "◇ RECONNECTING...",
      OFFLINE:      "◇ OFFLINE",
      ERROR:        "◇ ERROR",
    };
    let label = pillMap[this.activity] || `◇ ${this.activity}`;

    if (this.activity === "EXECUTING") {
      const opMap = {
        search_files: "◇ SEARCHING",
        read_file:    "◇ READING",
        write_file:   "◇ WRITING",
        open_app:     "◇ OPENING",
        close_app:    "◇ TERMINATING",
        shell:        "◇ EXECUTING",
      };
      label = opMap[this.operation] || "◇ EXECUTING";
    }

    this.character.statusText.textContent = label;

    // Pill stroke/text color by state
    if (this.activity === "ERROR" || this.mood === "WARNING") {
      this.character.statusBg.setAttribute("stroke", "#FF1744");
      this.character.statusText.setAttribute("fill", "#FF8A80");
    } else if (this.activity === "OFFLINE") {
      this.character.statusBg.setAttribute("stroke", "#5F6368");
      this.character.statusText.setAttribute("fill", "#9AA0A6");
    } else if (this.activity === "RECONNECTING") {
      this.character.statusBg.setAttribute("stroke", "#F59E0B");
      this.character.statusText.setAttribute("fill", "#FDE68A");
    } else {
      this.character.statusBg.setAttribute("stroke", "#7B2CFF");
      this.character.statusText.setAttribute("fill", "#E0AAFF");
    }
  }

  updateEyebrowTargets() {
    // 1. Activity baseline angles
    let leftA = 0.0;
    let rightA = 0.0;
    let offY = 0.0;

    switch (this.activity) {
      case "LISTENING":
        offY = -5.0; // Slightly raised
        break;
      case "THINKING":
        leftA = 6.0;   // Angled inward
        rightA = -6.0;
        offY = 1.0;
        break;
      case "EXECUTING":
        leftA = 8.0;   // Sharp focus
        rightA = -8.0;
        offY = 2.0;
        break;
      case "ERROR":
        leftA = -8.0;  // Asymmetric concern
        rightA = 4.0;
        offY = -2.0;
        break;
      case "OFFLINE":
        leftA = 0.0;
        rightA = 0.0;
        offY = 6.0;    // Lowered / sleeping
        break;
      case "RECONNECTING":
        leftA = 0.0;
        rightA = 0.0;
        offY = 3.0;    // Slightly lowered, searching
        break;
      default: // IDLE
        leftA = 0.0;
        rightA = 0.0;
        offY = 0.0;
    }

    // 2. Mood additive modulation
    switch (this.mood) {
      case "FOCUSED":
        leftA += 3.0;
        rightA -= 3.0;
        break;
      case "CURIOUS":
        leftA -= 4.0;
        rightA += 1.0; // Slight asymmetry
        break;
      case "CONCERNED":
        leftA += 5.0;
        rightA -= 5.0;
        offY += 2.0;
        break;
      case "WARNING":
        leftA += 8.0;
        rightA -= 8.0;
        break;
    }

    this.targetLeftAngle = leftA;
    this.targetRightAngle = rightA;
    this.targetOffsetY = offY;
  }

  updateGradientsAndGlow() {
    const leftCore = this.character.container.querySelector("#left-optical-core");
    const rightCore = this.character.container.querySelector("#right-optical-core");
    const leftHousing = this.character.container.querySelector("#left-eye-housing");
    const rightHousing = this.character.container.querySelector("#right-eye-housing");
    const leftBrow = this.character.leftBrow;
    const rightBrow = this.character.rightBrow;

    if (!leftCore || !rightCore) return;

    if (this.activity === "ERROR" || this.mood === "WARNING") {
      leftCore.setAttribute("fill", "url(#core-gradient-error)");
      rightCore.setAttribute("fill", "url(#core-gradient-error)");
      leftHousing.setAttribute("stroke", "#B71C1C");
      rightHousing.setAttribute("stroke", "#B71C1C");
      leftBrow.setAttribute("stroke", "#FF5252");
      rightBrow.setAttribute("stroke", "#FF5252");
    } else if (this.activity === "OFFLINE") {
      leftCore.setAttribute("fill", "url(#core-gradient-offline)");
      rightCore.setAttribute("fill", "url(#core-gradient-offline)");
      leftHousing.setAttribute("stroke", "#374151");
      rightHousing.setAttribute("stroke", "#374151");
      leftBrow.setAttribute("stroke", "#6B7280");
      rightBrow.setAttribute("stroke", "#6B7280");
    } else if (this.activity === "RECONNECTING") {
      // Amber-tinted dim pulse — between offline and active
      leftCore.setAttribute("fill", "url(#core-gradient-offline)");
      rightCore.setAttribute("fill", "url(#core-gradient-offline)");
      leftHousing.setAttribute("stroke", "#78350F");
      rightHousing.setAttribute("stroke", "#78350F");
      leftBrow.setAttribute("stroke", "#92400E");
      rightBrow.setAttribute("stroke", "#92400E");
    } else {
      leftCore.setAttribute("fill", "url(#core-gradient)");
      rightCore.setAttribute("fill", "url(#core-gradient)");
      leftHousing.setAttribute("stroke", "#4C1D95");
      rightHousing.setAttribute("stroke", "#4C1D95");
      leftBrow.setAttribute("stroke", "#C77DFF");
      rightBrow.setAttribute("stroke", "#C77DFF");
    }
  }

  update(deltaTime) {
    // RECONNECTING: slow amber pulse on eye opacity (0.35–0.75)
    if (this.activity === "RECONNECTING") {
      if (!this._reconnectPhase) this._reconnectPhase = 0;
      this._reconnectPhase += (deltaTime || 16.6) * 0.0012;
      const pulse = 0.35 + 0.4 * (0.5 + 0.5 * Math.sin(this._reconnectPhase));
      if (this.character.leftEye)  this.character.leftEye.style.opacity  = pulse.toFixed(3);
      if (this.character.rightEye) this.character.rightEye.style.opacity = pulse.toFixed(3);
    } else {
      this._reconnectPhase = 0;
      if (this.character.leftEye)  this.character.leftEye.style.opacity  = "";
      if (this.character.rightEye) this.character.rightEye.style.opacity = "";
    }

    // Smooth eyebrow interpolation
    const ease = 0.12;
    this.leftBrowAngle += (this.targetLeftAngle - this.leftBrowAngle) * ease;
    this.rightBrowAngle += (this.targetRightAngle - this.rightBrowAngle) * ease;
    this.leftBrowOffsetY += (this.targetOffsetY - this.leftBrowOffsetY) * ease;
    this.rightBrowOffsetY += (this.targetOffsetY - this.rightBrowOffsetY) * ease;

    if (this.character.leftBrow) {
      // Pivot around center of left brow: x=235, y=108.5
      this.character.leftBrow.setAttribute(
        "transform",
        `translate(0, ${this.leftBrowOffsetY.toFixed(1)}) rotate(${this.leftBrowAngle.toFixed(1)}, 235, 108.5)`
      );
    }

    if (this.character.rightBrow) {
      // Pivot around center of right brow: x=405, y=108.5
      this.character.rightBrow.setAttribute(
        "transform",
        `translate(0, ${this.rightBrowOffsetY.toFixed(1)}) rotate(${this.rightBrowAngle.toFixed(1)}, 405, 108.5)`
      );
    }
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = StateController;
}
if (typeof window !== "undefined") {
  window.StateController = StateController;
}
