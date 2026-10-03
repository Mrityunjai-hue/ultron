/**
 * ULTRON v2.0 — Production Living Presence Orchestrator
 * ─────────────────────────────────────────────────────────────────────────────
 * Unifies SVG Character, Waveform, Gaze, Blink, Audio, and State Controllers
 * with the backend WebSocket event stream, Web Speech STT, and pywebview Notch API.
 * ─────────────────────────────────────────────────────────────────────────────
 */

class UltronPresence {
  constructor(containerId = "presence-stage") {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`Container #${containerId} not found.`);
      return;
    }

    // 1. Initialize Subsystems
    this.character = new SvgCharacter(this.container);
    this.waveform = new WaveformController(this.character);
    this.gaze = new GazeController(this.character);
    this.blink = new BlinkController(this.character);
    this.audio = new AudioReactivityProcessor();
    this.state = new StateController(this.character, this.waveform, this.audio);

    this.ws = null;
    this.lastFrameTime = performance.now();
    this.isExpanded = false;
    this.recognition = null;
    this.isListening = false;
    this.collapseTimeout = null;
    this.audioContext = null;
    this.analyser = null;

    // 2. Start Animation Loop
    this.startLoop();

    // 3. Connect Authoritative WebSocket
    this.connectWebSocket();

    // 4. Initialize Living Notch Interactions & STT
    this.initInteractions();
    this.initSpeechRecognition();
  }

  startLoop() {
    const loop = (now) => {
      const dt = now - this.lastFrameTime;
      this.lastFrameTime = now;

      // Update Audio Reactivity
      const smoothedAmp = this.audio.update();

      // Update Waveform
      this.waveform.setMode(this.state.activity, smoothedAmp);
      this.waveform.update(dt);

      // Update Gaze
      this.gaze.update();

      // Update Blink
      this.blink.update(now);

      // Update State Dynamics (eyebrows, glow)
      this.state.update(dt);

      requestAnimationFrame(loop);
    };

    requestAnimationFrame(loop);
  }

  // ── Authoritative State API ───────────────────────────────────────────────
  setState({ activity, mood, operation, attention, gaze_x, gaze_y, voice_amplitude }) {
    if (activity !== undefined || mood !== undefined || operation !== undefined) {
      const prevActivity = this.state.activity;
      this.state.setAuthoritativeState({ activity, mood, operation, attention });

      // Handle Desktop Notch Auto-Resize (Standby 320x48 <-> Active 640x420)
      if (activity && activity !== prevActivity) {
        this.handleNotchResize(activity);
      }
    }

    if (gaze_x !== undefined && gaze_y !== undefined) {
      this.gaze.setTarget(gaze_x, gaze_y);
    }

    if (voice_amplitude !== undefined) {
      this.audio.setRawAmplitude(voice_amplitude);
    }
  }

  handleNotchResize(activity) {
    if (this.collapseTimeout) {
      clearTimeout(this.collapseTimeout);
      this.collapseTimeout = null;
    }

    const isNowIdle = activity === "IDLE";
    if (!isNowIdle && !this.isExpanded) {
      this.expandNotch();
    } else if (isNowIdle && this.isExpanded) {
      // Allow a brief settling period (1.5s) before collapsing to standby
      this.collapseTimeout = setTimeout(() => {
        this.collapseNotch();
      }, 1500);
    }
  }

  expandNotch() {
    this.isExpanded = true;
    document.body.classList.remove("compact-mode");
    if (window.pywebview && window.pywebview.api && window.pywebview.api.expand) {
      window.pywebview.api.expand();
    }
  }

  collapseNotch() {
    this.isExpanded = false;
    document.body.classList.add("compact-mode");
    if (window.pywebview && window.pywebview.api && window.pywebview.api.collapse) {
      window.pywebview.api.collapse();
    }
  }

  // ── Living Interaction System ─────────────────────────────────────────────
  initInteractions() {
    // Click on compact notch expands and triggers speech capture
    this.container.addEventListener("click", () => {
      if (!this.isExpanded) {
        this.expandNotch();
        this.startListening();
      }
    });

    // Press Escape to collapse
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        this.collapseNotch();
        if (this.recognition && this.isListening) {
          this.recognition.stop();
        }
      }
    });

    // Mouse proximity gaze tracking
    window.addEventListener("mousemove", (e) => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const normX = Math.max(-1, Math.min(1, (e.clientX / w) * 2 - 1));
      const normY = Math.max(-1, Math.min(1, (e.clientY / h) * 2 - 1));
      this.gaze.setTarget(normX * 0.45, normY * 0.45);
    });
  }

  // ── Speech-to-Text (STT) Integration ──────────────────────────────────────
  initSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      console.info("[Presence STT] Web Speech Recognition not supported in this client environment.");
      return;
    }

    try {
      this.recognition = new SpeechRec();
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      this.recognition.lang = "en-US";

      this.recognition.onstart = () => {
        this.isListening = true;
        this.setState({ activity: "LISTENING", attention: 0.9 });
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: "USER_SPEECH_START" }));
        }
      };

      this.recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        console.log("[Presence STT] Transcript:", transcript);
        this.setState({ activity: "THINKING" });
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: "USER_UTTERANCE", text: transcript }));
        }
      };

      this.recognition.onerror = (e) => {
        console.warn("[Presence STT] Recognition fault:", e.error);
        this.isListening = false;
      };

      this.recognition.onend = () => {
        this.isListening = false;
      };
    } catch (e) {
      console.warn("[Presence STT] Init error:", e);
    }
  }

  startListening() {
    // Notify backend to activate physical microphone listening loop
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "WAKE_WORD_DETECTED" }));
    }
    this.setState({ activity: "LISTENING", attention: 0.85 });

    if (this.recognition && !this.isListening) {
      try {
        this.recognition.start();
      } catch (e) {
        console.debug("Web speech recognition note:", e);
      }
    }

    // Safety timeout: auto-revert to IDLE if no response occurs within 7s
    if (this.listenSafetyTimer) {
      clearTimeout(this.listenSafetyTimer);
    }
    this.listenSafetyTimer = setTimeout(() => {
      if (this.state.activity === "LISTENING") {
        console.info("[Presence] Listening window closed without input. Reverting to IDLE.");
        this.setState({ activity: "IDLE", attention: 0.5 });
      }
    }, 7000);
  }


  // ── Text-to-Speech (TTS) & Acoustic Reactivity ────────────────────────────
  async playTTSStream(text) {
    try {
      const resp = await fetch("/api/tts/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text }),
      });

      if (resp.ok && resp.status === 200) {
        const blob = await resp.blob();
        const audioUrl = URL.createObjectURL(blob);
        const audioEl = new Audio(audioUrl);

        // Setup Web Audio Analyser for accurate waveform reactivity
        if (!this.audioContext) {
          this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (this.audioContext.state === "suspended") {
          await this.audioContext.resume();
        }

        const source = this.audioContext.createMediaElementSource(audioEl);
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
        source.connect(this.analyser);
        this.analyser.connect(this.audioContext.destination);

        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        const updateAmp = () => {
          if (!audioEl.paused && !audioEl.ended) {
            this.analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i];
            }
            const avg = sum / dataArray.length;
            const normAmp = Math.min(1.0, avg / 85.0);
            this.audio.setRawAmplitude(normAmp);
            requestAnimationFrame(updateAmp);
          } else {
            this.audio.setRawAmplitude(0.0);
          }
        };

        audioEl.onplay = () => {
          this.setState({ activity: "RESPONDING" });
          updateAmp();
        };

        audioEl.onended = () => {
          this.setState({ activity: "IDLE" });
        };

        await audioEl.play();
      } else {
        // Fallback to client synthesis if ElevenLabs server key is unconfigured
        this.playClientSpeechFallback(text);
      }
    } catch (e) {
      this.playClientSpeechFallback(text);
    }
  }

  playClientSpeechFallback(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();

    const utter = new SpeechSynthesisUtterance(text);
    utter.rate = 0.95;
    utter.pitch = 0.85;

    // Oscillate amplitude during synthesis
    let pulseTimer = null;
    utter.onstart = () => {
      this.setState({ activity: "RESPONDING" });
      pulseTimer = setInterval(() => {
        const simAmp = 0.25 + Math.random() * 0.6;
        this.audio.setRawAmplitude(simAmp);
      }, 80);
    };

    utter.onend = () => {
      if (pulseTimer) clearInterval(pulseTimer);
      this.audio.setRawAmplitude(0.0);
      this.setState({ activity: "IDLE" });
    };

    utter.onerror = () => {
      if (pulseTimer) clearInterval(pulseTimer);
      this.audio.setRawAmplitude(0.0);
      this.setState({ activity: "IDLE" });
    };

    window.speechSynthesis.speak(utter);
  }

  // ── WebSocket Connection ──────────────────────────────────────────────────
  connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host || "localhost:8080";
    const url = `${protocol}//${host}/ws`;

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log("[Presence] Authoritative WebSocket linked to backend.");
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleServerEvent(data);
        } catch (e) {
          console.error("[Presence] WebSocket parse fault:", e);
        }
      };

      this.ws.onclose = () => {
        console.warn("[Presence] WebSocket link lost. Reconnecting in 2s...");
        this.setState({ activity: "RECONNECTING" });
        setTimeout(() => this.connectWebSocket(), 2000);
      };
    } catch (e) {
      console.error("[Presence] WebSocket initialization fault:", e);
    }
  }

  handleServerEvent(data) {
    if (data.type === "AUTHORITATIVE_EVENT") {
      this.setState({
        activity: data.activity_name || data.activity,
        mood: data.mood,
        operation: data.operation,
        attention: data.attention,
        gaze_x: data.gaze_x,
        gaze_y: data.gaze_y,
        voice_amplitude: data.voice_amplitude,
      });
    } else if (data.type === "STATE_CHANGE") {
      const stateMap = {
        idle: "IDLE",
        listening: "LISTENING",
        thinking: "THINKING",
        executing: "EXECUTING",
        processing: "EXECUTING",
        searching: "EXECUTING",
        speaking: "RESPONDING",
        error: "ERROR",
        offline: "OFFLINE",
        warning: "ERROR",
      };
      const act = stateMap[data.state] || data.state.toUpperCase();
      const op = data.state === "searching" ? "search_files" : "none";
      this.setState({ activity: act, operation: op });
    } else if (data.type === "GAZE_TARGET") {
      this.setState({ gaze_x: data.x, gaze_y: data.y });
    } else if (data.type === "VOICE_AMPLITUDE") {
      this.audio.setRawAmplitude(data.amplitude || 0.0);
    } else if (data.type === "TTS_DISPATCH") {
      if (data.text) {
        this.playTTSStream(data.text);
      }
    }
  }
}

// Auto-boot in production view
window.addEventListener("DOMContentLoaded", () => {
  window.ultron = new UltronPresence("presence-stage");
});
