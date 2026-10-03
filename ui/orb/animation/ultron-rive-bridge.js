/**
 * ULTRON RIVE BRIDGE & MASTER CONTROLLER v2.0
 *
 * Implements the Rive-First Architecture:
 * - Direct integration with @rive-app/canvas runtime
 * - Artboard: 'UltronArtboard' (or default artboard)
 * - State Machine: 'ULTRON_SM'
 * - Inputs Contract:
 *     - state: Number (0..19 mapping to ULTRON_STATE_IDS)
 *     - gazeX: Number (-1.0 to 1.0)
 *     - gazeY: Number (-1.0 to 1.0)
 *     - energy: Number (0.0 to 1.0)
 *     - amplitude: Number (0.0 to 1.0)
 *     - attention: Number (0.0 to 1.0)
 *     - isListening: Boolean
 *     - isSpeaking: Boolean
 *     - isFocused: Boolean
 *   Triggers:
 *     - boot, success, warning, error, alert, reconnect, shutdown
 *
 * When a compiled .riv asset is provided at `assets/ultron.riv`, it binds natively to Rive.
 * When the binary .riv is not present, it seamlessly routes to the HiDPI Vector Engine
 * (UltronVectorCharacter) with zero code rewrites needed.
 */
'use strict';

class UltronRiveBridge {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.options = Object.assign(
      {
        rivSrc: 'assets/ultron.riv',
        stateMachine: 'ULTRON_SM',
        artboard: undefined,
        autoplay: true,
      },
      options
    );

    // Active Engine Mode: 'rive' | 'vector'
    this.mode = 'vector';
    this.riveInstance = null;
    this.riveInputs = {};
    this.isRiveReady = false;

    // Vector Fallback Engine
    this.vectorEngine = new UltronVectorCharacter(canvas);

    // Current State & Metric Cache
    this.currentState = 'idle';
    this.gazeX = 0;
    this.gazeY = 0;
    this.energy = 0.45;
    this.amplitude = 0;
    this.attention = 0.5;

    // Listeners
    this.listeners = {
      stateChange: [],
      modeChange: [],
      frame: [],
    };

    // Forward vector engine state changes
    this.vectorEngine.onStateChange((e) => {
      this.currentState = e.state;
      this._emit('stateChange', e);
    });

    // Attempt to load Rive
    this._initRive();

    // Start RAF loop
    this.isRunning = false;
    this._rafId = null;
    this._boundLoop = this._loop.bind(this);
  }

  /**
   * Initialize Rive runtime if available
   */
  async _initRive() {
    if (typeof window.rive === 'undefined') {
      console.log(
        '[ULTRON Rive Bridge] Rive runtime not yet loaded; using Vector Engine.'
      );
      this.mode = 'vector';
      return;
    }

    try {
      // Check if .riv asset exists via HEAD request
      const res = await fetch(this.options.rivSrc, { method: 'HEAD' });
      if (!res.ok) {
        console.info(
          `[ULTRON Rive Bridge] External asset "${this.options.rivSrc}" not found. Running in native Vector Engine mode with full ULTRON_SM contract.`
        );
        this.mode = 'vector';
        return;
      }

      // Instantiate Rive
      this.riveInstance = new window.rive.Rive({
        src: this.options.rivSrc,
        canvas: this.canvas,
        artboard: this.options.artboard,
        stateMachines: this.options.stateMachine,
        autoplay: true,
        onLoad: () => {
          console.log('[ULTRON Rive Bridge] Successfully loaded .riv asset!');
          this._bindRiveInputs();
          this.mode = 'rive';
          this.isRiveReady = true;
          this._emit('modeChange', { mode: 'rive' });
        },
        onError: (err) => {
          console.warn(
            '[ULTRON Rive Bridge] Rive failed to load, falling back to Vector Engine:',
            err
          );
          this.mode = 'vector';
        },
      });
    } catch (e) {
      console.info(
        '[ULTRON Rive Bridge] Running with HiDPI Vector Engine (no external .riv asset found).'
      );
      this.mode = 'vector';
    }
  }

  /**
   * Bind Rive State Machine Inputs
   */
  _bindRiveInputs() {
    if (!this.riveInstance) return;
    try {
      const inputs = this.riveInstance.stateMachineInputs(this.options.stateMachine);
      if (!inputs) return;

      inputs.forEach((input) => {
        this.riveInputs[input.name] = input;
      });

      console.log(
        '[ULTRON Rive Bridge] Bound Rive Inputs:',
        Object.keys(this.riveInputs)
      );

      // Initial sync
      this.setState(this.currentState);
      this.setGaze(this.gazeX, this.gazeY);
      this.setEnergy(this.energy);
    } catch (e) {
      console.error('[ULTRON Rive Bridge] Error binding inputs:', e);
    }
  }

  start() {
    if (this.isRunning) return;
    this.isRunning = true;
    this._rafId = requestAnimationFrame(this._boundLoop);
  }

  stop() {
    this.isRunning = false;
    if (this._rafId) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
  }

  _loop(time) {
    if (!this.isRunning) return;

    if (this.mode === 'vector') {
      this.vectorEngine.update(time);
      this.vectorEngine.render();
    }

    this._emit('frame', {
      time,
      state: this.currentState,
      gazeX: this.gazeX,
      gazeY: this.gazeY,
      energy: this.energy,
      amplitude: this.amplitude,
      mode: this.mode,
    });

    this._rafId = requestAnimationFrame(this._boundLoop);
  }

  /* ─── State Machine Control ─────────────────────────────────────────────── */

  setState(stateName) {
    if (!ULTRON_STATE_CONFIGS[stateName]) {
      console.warn(`[ULTRON] Unknown state: "${stateName}"`);
      return;
    }

    this.currentState = stateName;

    // Vector Engine update
    this.vectorEngine.setState(stateName);

    // Rive State Machine update
    if (this.isRiveReady && this.riveInputs) {
      const stateId = ULTRON_STATE_IDS[stateName];
      if (this.riveInputs.state && stateId !== undefined) {
        this.riveInputs.state.value = stateId;
      }
      if (this.riveInputs.isListening) {
        this.riveInputs.isListening.value = stateName === 'listening';
      }
      if (this.riveInputs.isSpeaking) {
        this.riveInputs.isSpeaking.value = stateName === 'speaking';
      }
      if (this.riveInputs.isFocused) {
        this.riveInputs.isFocused.value = stateName === 'focused';
      }
    }
  }

  getState() {
    return this.currentState;
  }

  /**
   * Set Gaze position [-1, 1]
   */
  setGaze(x, y) {
    this.gazeX = Math.max(-1, Math.min(1, x));
    this.gazeY = Math.max(-1, Math.min(1, y));

    this.vectorEngine.setGaze(this.gazeX, this.gazeY);

    if (this.isRiveReady && this.riveInputs) {
      if (this.riveInputs.gazeX) this.riveInputs.gazeX.value = this.gazeX;
      if (this.riveInputs.gazeY) this.riveInputs.gazeY.value = this.gazeY;
    }
  }

  /**
   * Set Energy level [0, 1]
   */
  setEnergy(val) {
    this.energy = Math.max(0, Math.min(1, val));
    if (this.isRiveReady && this.riveInputs && this.riveInputs.energy) {
      this.riveInputs.energy.value = this.energy;
    }
  }

  /**
   * Set Audio amplitude [0, 1] and flags
   */
  setAudio(amplitude, isSpeaking = false, isListening = false) {
    this.amplitude = Math.max(0, Math.min(1, amplitude));
    this.vectorEngine.setAudio(this.amplitude, isSpeaking, isListening);

    if (this.isRiveReady && this.riveInputs) {
      if (this.riveInputs.amplitude) this.riveInputs.amplitude.value = this.amplitude;
      if (this.riveInputs.isSpeaking) this.riveInputs.isSpeaking.value = isSpeaking;
      if (this.riveInputs.isListening) this.riveInputs.isListening.value = isListening;
    }
  }

  /**
   * Trigger named event or transient state
   */
  trigger(triggerName) {
    // If it corresponds to a state name, set state
    if (ULTRON_STATE_CONFIGS[triggerName]) {
      this.setState(triggerName);
    }

    // Fire Rive Trigger input if defined
    if (this.isRiveReady && this.riveInputs && this.riveInputs[triggerName]) {
      if (typeof this.riveInputs[triggerName].fire === 'function') {
        this.riveInputs[triggerName].fire();
      }
    }

    // Reaction in vector engine
    this.vectorEngine.react(triggerName);
  }

  react(type) {
    this.trigger(type);
  }

  play(stateOrAction) {
    this.trigger(stateOrAction);
  }

  /* ─── Event Handling ────────────────────────────────────────────────────── */

  on(event, cb) {
    if (this.listeners[event]) {
      this.listeners[event].push(cb);
    }
  }

  off(event, cb) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter((fn) => fn !== cb);
    }
  }

  _emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach((cb) => {
        try {
          cb(data);
        } catch (err) {
          console.error(err);
        }
      });
    }
  }
}

// Export
if (typeof window !== 'undefined') {
  window.UltronRiveBridge = UltronRiveBridge;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { UltronRiveBridge };
}
