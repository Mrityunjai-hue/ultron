/**
 * ULTRON ENGINE v3.0 (Signal Interface Architecture)
 * ─────────────────────────────────────────────────────────────────────────────
 * Master Controller coordinating:
 * - UltronSignalCharacter (Single Signal Line + Stylized Vector Eyes)
 * - 60+ FPS RAF loop with sub-pixel interpolation
 * - Voice Analyser & Microphone Audio Envelope Pipeline
 * - Real-time continuous state transitions
 * ─────────────────────────────────────────────────────────────────────────────
 */
'use strict';

class UltronEngine {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.character = new UltronSignalCharacter(canvas);

    this.isRunning = false;
    this._rafId = null;
    this.lastFrameTime = performance.now();

    // Event Listeners
    this.listeners = {
      stateChange: [],
      frame: [],
    };

    // Forward state changes
    this.character.onStateChange((e) => {
      this._emit('stateChange', e);
    });

    // Make globally accessible
    window.ultron = this;
  }

  start() {
    if (this.isRunning) return;
    this.isRunning = true;
    this.lastFrameTime = performance.now();
    this._loop();
  }

  stop() {
    this.isRunning = false;
    if (this._rafId) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
  }

  _loop() {
    if (!this.isRunning) return;

    const now = performance.now();
    const dt = Math.min((now - this.lastFrameTime) / 1000, 0.1);
    this.lastFrameTime = now;

    // Update physical wave dynamics & eye springs
    this.character.update(dt);

    // Render continuous line and stylized eyes
    this.character.render();

    // Emit frame telemetry
    this._emit('frame', {
      state: this.character.currentState,
      gazeX: this.character.current.gazeX,
      gazeY: this.character.current.gazeY,
      energy: this.character.current.signalAmplitude,
      amplitude: this.character.audio.smoothedAmp,
      fps: dt > 0 ? Math.round(1 / dt) : 60,
    });

    this._rafId = requestAnimationFrame(() => this._loop());
  }

  setState(stateName) {
    this.character.setState(stateName);
  }

  setGaze(x, y) {
    this.character.setGaze(x, y);
  }

  setAudio(amplitude, isSpeaking, isListening) {
    this.character.setAudio(amplitude, isSpeaking, isListening);
  }

  setTheme(theme) {
    this.character.setTheme(theme);
  }

  toggleTheme() {
    return this.character.toggleTheme();
  }

  on(event, cb) {
    if (this.listeners[event]) {
      this.listeners[event].push(cb);
    }
  }

  _emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach((cb) => {
        try {
          cb(data);
        } catch (e) {
          console.error(`[UltronEngine] Error in ${event} callback:`, e);
        }
      });
    }
  }
}

if (typeof window !== 'undefined') {
  window.UltronEngine = UltronEngine;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { UltronEngine };
}
