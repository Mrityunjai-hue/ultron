/**
 * ULTRON v2.0 — Rive Presence Controller & Vector Rig
 * ─────────────────────────────────────────────────────────────────────────────
 * Binds WebSocket Authoritative Events to Rive State Machine Inputs:
 * - activity: 0=IDLE, 1=LISTENING, 2=THINKING, 3=EXECUTING, 4=RESPONDING, 5=ERROR, 6=OFFLINE, 7=RECONNECTING
 * - operationId: 0=none, 1=search, 2=read, 3=write, 4=app, 5=shell
 * - moodId: 0=CALM, 1=ATTENTIVE, 2=FOCUSED, 3=CURIOUS, 4=CONCERNED, 5=WARNING
 * - gazeX, gazeY: [-1.0, 1.0]
 * - voiceAmplitude: [0.0, 1.0]
 * ─────────────────────────────────────────────────────────────────────────────
 */

class UltronRiveController {
  constructor() {
    this.canvas = document.getElementById("rive-canvas");
    this.stateText = document.getElementById("state-text");
    this.operationText = document.getElementById("operation-text");
    this.socketDot = document.getElementById("socket-dot");

    // Authoritative State Machine Inputs
    this.inputs = {
      activity: 0,
      operationId: 0,
      moodId: 0,
      gazeX: 0.0,
      gazeY: 0.0,
      attention: 0.5,
      voiceAmplitude: 0.0,
    };

    // Smooth interpolated tracking values
    this.interpolated = {
      gazeX: 0.0,
      gazeY: 0.0,
      amplitude: 0.0,
      browAngle: 0.0,
      coreRadius: 32.0,
    };

    this.riveInstance = null;
    this.riveInputs = {};
    this.isNativeRive = false;
    this.ws = null;
    this.animFrameId = null;

    this.init();
  }

  async init() {
    // Attempt to load compiled .riv file if present
    const rivLoaded = await this.tryLoadNativeRive();
    if (!rivLoaded) {
      console.log("[Presence] Native .riv not detected. Running authoritative vector rig.");
      this.startVectorLoop();
    }

    this.connectWebSocket();
  }

  async tryLoadNativeRive() {
    if (typeof rive === "undefined") return false;
    try {
      const resp = await fetch("ultron.riv", { method: "HEAD" });
      if (resp.status !== 200) return false;

      this.riveInstance = new rive.Rive({
        src: "ultron.riv",
        canvas: this.canvas,
        autoplay: true,
        stateMachines: "ULTRON_SM",
        onLoad: () => {
          this.isNativeRive = true;
          const smInputs = this.riveInstance.stateMachineInputs("ULTRON_SM");
          if (smInputs) {
            for (const input of smInputs) {
              this.riveInputs[input.name] = input;
            }
          }
          console.log("[Presence] Official Rive runtime initialized with state machine ULTRON_SM.");
        },
      });
      return true;
    } catch {
      return false;
    }
  }

  setInputs(newInputs) {
    Object.assign(this.inputs, newInputs);

    // If native Rive is loaded, sync to Rive input nodes
    if (this.isNativeRive) {
      for (const [key, val] of Object.entries(newInputs)) {
        if (this.riveInputs[key]) {
          this.riveInputs[key].value = val;
        }
      }
    }

    this.updateStatusBadge();
  }

  trigger(name) {
    if (this.isNativeRive && this.riveInputs[name]) {
      this.riveInputs[name].fire();
    }
  }

  updateStatusBadge() {
    const activityNames = ["IDLE", "LISTENING", "THINKING", "EXECUTING", "RESPONDING", "ERROR", "OFFLINE", "RECONNECTING"];
    const opNames = ["", "SEARCH", "READ", "WRITE", "APP", "SHELL"];

    const actName = activityNames[this.inputs.activity] || "IDLE";
    if (this.stateText) this.stateText.textContent = actName;

    const opName = opNames[this.inputs.operationId] || "";
    if (this.operationText) {
      if (opName) {
        this.operationText.textContent = `// ${opName}`;
        this.operationText.style.display = "inline";
      } else {
        this.operationText.style.display = "none";
      }
    }

    if (this.socketDot) {
      this.socketDot.className = "status-dot";
      if (this.inputs.activity === 6) this.socketDot.classList.add("offline");
      else if (this.inputs.activity === 5) this.socketDot.classList.add("warning");
    }
  }

  connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host || "localhost:8080";
    const url = `${protocol}//${host}/ws`;

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log("[Presence] WebSocket connected.");
        if (this.socketDot) this.socketDot.classList.remove("offline");
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleServerEvent(data);
        } catch (e) {
          console.error("[Presence] Error parsing event:", e);
        }
      };

      this.ws.onclose = () => {
        console.warn("[Presence] WebSocket disconnected. Retrying in 2s...");
        if (this.socketDot) this.socketDot.classList.add("offline");
        setTimeout(() => this.connectWebSocket(), 2000);
      };
    } catch (e) {
      console.error("[Presence] WebSocket error:", e);
    }
  }

  handleServerEvent(data) {
    if (data.type === "AUTHORITATIVE_EVENT") {
      this.setInputs({
        activity: data.activity ?? this.inputs.activity,
        operationId: data.operationId ?? this.inputs.operationId,
        moodId: data.moodId ?? this.inputs.moodId,
        gazeX: data.gazeX ?? this.inputs.gazeX,
        gazeY: data.gazeY ?? this.inputs.gazeY,
        attention: data.attention ?? this.inputs.attention,
        voiceAmplitude: data.voiceAmplitude ?? this.inputs.voiceAmplitude,
      });
    } else if (data.type === "STATE_CHANGE") {
      const stateMap = {
        idle: 0,
        listening: 1,
        thinking: 2,
        executing: 3,
        processing: 3,
        searching: 3,
        speaking: 4,
        error: 5,
        offline: 6,
        warning: 5,
      };
      const act = stateMap[data.state] ?? 0;
      const op = data.state === "searching" ? 1 : 0;
      this.setInputs({ activity: act, operationId: op });
    } else if (data.type === "GAZE_TARGET") {
      this.setInputs({ gazeX: data.x, gazeY: data.y });
    } else if (data.type === "VOICE_AMPLITUDE") {
      this.setInputs({ voiceAmplitude: data.amplitude });
    } else if (data.type === "INTERRUPT_TRIGGERED") {
      this.trigger("onInterrupt");
    }
  }

  // ── Procedural Vector Rig Renderer ─────────────────────────────────────────
  startVectorLoop() {
    const ctx = this.canvas.getContext("2d");
    const width = 1024;
    const height = 1024;

    const render = (time) => {
      // Damped interpolation for gaze & voice amplitude
      this.interpolated.gazeX += (this.inputs.gazeX - this.interpolated.gazeX) * 0.12;
      this.interpolated.gazeY += (this.inputs.gazeY - this.interpolated.gazeY) * 0.12;
      this.interpolated.amplitude += (this.inputs.voiceAmplitude - this.interpolated.amplitude) * 0.25;

      ctx.clearRect(0, 0, width, height);
      this.drawUltronChassis(ctx, width, height, time);
      this.animFrameId = requestAnimationFrame(render);
    };

    this.animFrameId = requestAnimationFrame(render);
  }

  drawUltronChassis(ctx, w, h, time) {
    const cx = w / 2;
    const cy = h / 2;
    const act = this.inputs.activity;
    const isOffline = act === 6;
    const isThinking = act === 2;
    const isExecuting = act === 3;
    const isSpeaking = act === 4;
    const isWarning = act === 5 || this.inputs.moodId === 5;

    // Optical Core Color Palette
    let coreColor = "#E50914";
    let glowColor = "rgba(229, 9, 20, 0.6)";

    if (isOffline) {
      coreColor = "#4A4D54";
      glowColor = "rgba(74, 77, 84, 0.2)";
    } else if (isWarning) {
      coreColor = "#FFA000";
      glowColor = "rgba(255, 160, 0, 0.8)";
    } else if (isThinking || isExecuting) {
      coreColor = "#FF2A36";
      glowColor = "rgba(255, 42, 54, 0.85)";
    }

    // 1. Acoustic Radial Emitters (Voice Amplitude driven)
    if (isSpeaking && this.interpolated.amplitude > 0.05) {
      const radius = 220 + this.interpolated.amplitude * 160;
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(229, 9, 20, ${0.15 + this.interpolated.amplitude * 0.5})`;
      ctx.lineWidth = 4 + this.interpolated.amplitude * 8;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(cx, cy, radius * 0.75, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(255, 42, 54, ${0.2 + this.interpolated.amplitude * 0.4})`;
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.restore();
    }

    // 2. Chiseled Hexagonal Titanium Silhouette Plate
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(cx - 260, cy - 80);
    ctx.lineTo(cx - 200, cy - 200);
    ctx.lineTo(cx, cy - 240);
    ctx.lineTo(cx + 200, cy - 200);
    ctx.lineTo(cx + 260, cy - 80);
    ctx.lineTo(cx + 180, cy + 180);
    ctx.lineTo(cx, cy + 240);
    ctx.lineTo(cx - 180, cy + 180);
    ctx.closePath();

    ctx.fillStyle = "#121316";
    ctx.fill();
    ctx.strokeStyle = isOffline ? "#24272D" : "#2A2D34";
    ctx.lineWidth = 3;
    ctx.stroke();

    // Specular Rim Accents
    ctx.strokeStyle = isOffline ? "#1F2126" : "rgba(255, 255, 255, 0.12)";
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();

    // 3. Dual Optical Apertures
    const eyeOffsetX = 120;
    const eyeOffsetY = -20;
    const gazePxX = this.interpolated.gazeX * 24;
    const gazePxY = this.interpolated.gazeY * 16;

    this.drawOpticalAperture(ctx, cx - eyeOffsetX, cy + eyeOffsetY, gazePxX, gazePxY, coreColor, glowColor, false, time);
    this.drawOpticalAperture(ctx, cx + eyeOffsetX, cy + eyeOffsetY, gazePxX, gazePxY, coreColor, glowColor, true, time);
  }

  drawOpticalAperture(ctx, x, y, gazeX, gazeY, coreColor, glowColor, mirrored, time) {
    const act = this.inputs.activity;
    const isOffline = act === 6;
    const isThinking = act === 2;

    ctx.save();
    ctx.translate(x, y);

    // Eye Socket Cavity
    ctx.beginPath();
    const dir = mirrored ? -1 : 1;
    ctx.moveTo(-65 * dir, -25);
    ctx.lineTo(55 * dir, -30);
    ctx.lineTo(75 * dir, 20);
    ctx.lineTo(-45 * dir, 32);
    ctx.closePath();
    ctx.fillStyle = "#08090A";
    ctx.fill();
    ctx.strokeStyle = "#252830";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.clip(); // Clip pupil inside socket

    // Multi-blade Iris Shutter Ring
    ctx.beginPath();
    ctx.arc(0, 0, 48, 0, Math.PI * 2);
    ctx.strokeStyle = "#1A1C22";
    ctx.lineWidth = 4;
    ctx.stroke();

    // Pupil Core (Tracks gaze)
    if (!isOffline) {
      const pupilX = gazeX;
      const pupilY = gazeY;

      // Thinking orbital rotation
      let orbitOffsetX = 0;
      let orbitOffsetY = 0;
      if (isThinking) {
        const angle = (time / 240) + (mirrored ? Math.PI : 0);
        orbitOffsetX = Math.cos(angle) * 8;
        orbitOffsetY = Math.sin(angle) * 8;
      }

      ctx.beginPath();
      ctx.arc(pupilX + orbitOffsetX, pupilY + orbitOffsetY, 18, 0, Math.PI * 2);
      ctx.fillStyle = coreColor;
      ctx.shadowColor = glowColor;
      ctx.shadowBlur = 24;
      ctx.fill();

      // Slit Focus Inner Hotspot
      ctx.beginPath();
      ctx.ellipse(pupilX + orbitOffsetX, pupilY + orbitOffsetY, 6, 12, 0, 0, Math.PI * 2);
      ctx.fillStyle = "#FFFFFF";
      ctx.fill();
    } else {
      // Cold offline slit
      ctx.beginPath();
      ctx.moveTo(-30 * dir, 0);
      ctx.lineTo(30 * dir, 0);
      ctx.strokeStyle = "#3A3D44";
      ctx.lineWidth = 3;
      ctx.stroke();
    }

    ctx.restore();
  }
}

// Auto-boot controller on DOM ready
window.addEventListener("DOMContentLoaded", () => {
  window.ultronPresence = new UltronRiveController();
});
