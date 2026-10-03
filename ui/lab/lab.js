/**
 * ULTRON v2.0 — Animation Lab Controller
 * ─────────────────────────────────────────────────────────────────────────────
 * Drives the exact production SvgCharacter presence engine with developer controls.
 * ─────────────────────────────────────────────────────────────────────────────
 */

window.addEventListener("DOMContentLoaded", () => {
  const presence = window.ultron;
  if (!presence) {
    console.error("UltronPresence instance not found.");
    return;
  }

  // Ensure stage is rendered in full expanded mode in Lab
  document.body.classList.remove("compact-mode");
  presence.isExpanded = true;

  const telemetryBox = document.getElementById("telemetry-display");

  function refreshTelemetry() {
    if (!telemetryBox) return;
    const data = {
      activity: presence.state.activity,
      mood: presence.state.mood,
      operation: presence.state.operation,
      attention: presence.state.attention,
      gazeX: presence.gaze.targetX,
      gazeY: presence.gaze.targetY,
      voiceAmplitude: presence.audio.rawAmplitude,
    };
    telemetryBox.textContent = JSON.stringify(data, null, 2);
  }

  // 1. Activity Buttons
  document.querySelectorAll("#activity-buttons button").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#activity-buttons button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const act = btn.dataset.act;
      presence.setState({ activity: act });
      refreshTelemetry();
    });
  });

  // 2. Operation Buttons
  document.querySelectorAll("#operation-buttons button").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#operation-buttons button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const op = btn.dataset.op;
      presence.setState({ operation: op });
      refreshTelemetry();
    });
  });

  // 3. Mood Buttons
  document.querySelectorAll("#mood-buttons button").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#mood-buttons button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const mood = btn.dataset.mood;
      presence.setState({ mood: mood });
      refreshTelemetry();
    });
  });

  // 4. Gaze Joystick
  const joyBox = document.getElementById("gaze-joystick-box");
  const joyPuck = document.getElementById("joystick-puck");
  const gazeXLabel = document.getElementById("gaze-x-label");
  const gazeYLabel = document.getElementById("gaze-y-label");

  let isDraggingGaze = false;
  const updateGaze = (e) => {
    if (!isDraggingGaze) return;
    const rect = joyBox.getBoundingClientRect();
    const cx = e.clientX || (e.touches && e.touches[0].clientX);
    const cy = e.clientY || (e.touches && e.touches[0].clientY);

    const relX = Math.max(0, Math.min(rect.width, cx - rect.left));
    const relY = Math.max(0, Math.min(rect.height, cy - rect.top));

    joyPuck.style.left = `${relX - 11}px`;
    joyPuck.style.top = `${relY - 11}px`;

    const normX = ((relX / rect.width) * 2 - 1).toFixed(2);
    const normY = ((relY / rect.height) * 2 - 1).toFixed(2);

    gazeXLabel.textContent = `gazeX: ${normX}`;
    gazeYLabel.textContent = `gazeY: ${normY}`;

    presence.setState({ gaze_x: parseFloat(normX), gaze_y: parseFloat(normY) });
    refreshTelemetry();
  };

  joyBox.addEventListener("mousedown", (e) => { isDraggingGaze = true; updateGaze(e); });
  window.addEventListener("mousemove", updateGaze);
  window.addEventListener("mouseup", () => { isDraggingGaze = false; });

  // 5. Voice Amplitude Slider
  const ampSlider = document.getElementById("amp-slider");
  const ampLabel = document.getElementById("amp-label");
  ampSlider.addEventListener("input", () => {
    const val = parseFloat(ampSlider.value);
    ampLabel.textContent = val.toFixed(2);
    presence.setState({ voice_amplitude: val });
    refreshTelemetry();
  });

  // Pulse Simulated Audio button
  let oscInterval = null;
  const pulseBtn = document.getElementById("btn-pulse-audio");
  pulseBtn.addEventListener("click", () => {
    if (oscInterval) {
      clearInterval(oscInterval);
      oscInterval = null;
      pulseBtn.classList.remove("active");
      ampSlider.value = 0;
      ampLabel.textContent = "0.00";
      presence.setState({ voice_amplitude: 0.0 });
    } else {
      pulseBtn.classList.add("active");
      oscInterval = setInterval(() => {
        const simAmp = 0.15 + Math.random() * 0.75;
        ampSlider.value = simAmp;
        ampLabel.textContent = simAmp.toFixed(2);
        presence.setState({ voice_amplitude: simAmp });
        refreshTelemetry();
      }, 90);
    }
  });

  // 6. Action Triggers
  document.getElementById("btn-trigger-blink").addEventListener("click", () => {
    presence.blink.triggerBlink();
  });

  document.getElementById("btn-trigger-success").addEventListener("click", () => {
    presence.setState({ activity: "RESPONDING", mood: "CALM" });
    refreshTelemetry();
  });

  document.getElementById("btn-trigger-error").addEventListener("click", () => {
    presence.setState({ activity: "ERROR", mood: "WARNING" });
    refreshTelemetry();
  });

  refreshTelemetry();
});
