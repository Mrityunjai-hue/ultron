/**
 * ULTRON v2.0 — MASTER VOICE ARCHITECTURE
 * ─────────────────────────────────────────────────────────────────────────────
 * Selected Voice ID: 5vpfPL62TWuqhC30bkVm
 *
 * Components:
 * 1. UltronVoiceDirector:
 *    - Markdown / Code / Artifact removal
 *    - Linguistic & technical term normalization (versions, acronyms, URLs)
 *    - Speech queue management (FIFO, cancel, interrupt)
 * 2. UltronVoiceEngine:
 *    - Server-side ElevenLabs streaming TTS client (/api/tts/stream)
 *    - Web Audio API graph + AnalyserNode (normalized 0.0 - 1.0 RMS amplitude)
 *    - Voice state synchronization: idle, listening, thinking, speaking, interrupted, error
 *    - Instant speech interruption on voice activity or cancel command
 *    - Resilient error handling without app crashes
 * ─────────────────────────────────────────────────────────────────────────────
 */
'use strict';

// ── 1. Voice Director (Sanitizer, Normalizer & Queue Manager) ─────────────────
class UltronVoiceDirector {
  constructor(engine) {
    this.engine = engine;
    this.queueItems = [];
    this.isProcessingQueue = false;
  }

  /**
   * Sanitizes markdown, code, and UI artifacts, and normalizes technical terms
   */
  sanitizeAndNormalize(text) {
    if (!text || typeof text !== 'string') return '';

    let s = text;

    // 1. Remove Markdown code blocks (```...```)
    s = s.replace(/```[\s\S]*?```/g, ' [Code segment omitted.] ');

    // 2. Remove inline code (`...`)
    s = s.replace(/`([^`]+)`/g, '$1');

    // 3. Remove Markdown links [text](url) -> keep text only
    s = s.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');

    // 4. Remove bare URLs
    s = s.replace(/https?:\/\/[^\s]+/g, 'link');

    // 5. Remove HTML tags
    s = s.replace(/<[^>]*>/g, '');

    // 6. Remove Markdown headings (### ...)
    s = s.replace(/^#{1,6}\s+/gm, '');

    // 7. Remove bold / italics / strikethrough (*, _, ~)
    s = s.replace(/[*_~]{1,3}([^*_~]+)[*_~]{1,3}/g, '$1');

    // 8. Remove bullet points and blockquotes
    s = s.replace(/^[\s]*[-*+>]\s+/gm, '');
    s = s.replace(/^[\s]*\d+\.\s+/gm, '');

    // 9. Remove emojis and unusual symbol artifacts
    s = s.replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '');

    // 10. Technical Term & Acronym Normalization for Natural Speech
    const replacements = [
      [/\bv2\.0\b/gi, 'version two point zero'],
      [/\bv1\.0\b/gi, 'version one point zero'],
      [/\bv(\d+)\.(\d+)\b/gi, 'version $1 point $2'],
      [/\bUI\b/g, 'U I'],
      [/\bAPI\b/g, 'A P I'],
      [/\bTTS\b/g, 'T T S'],
      [/\bRMS\b/g, 'R M S'],
      [/\bFPS\b/g, 'F P S'],
      [/\bVAD\b/g, 'V A D'],
      [/\bAI\b/g, 'A I'],
      [/\bCPU\b/g, 'C P U'],
      [/\bGPU\b/g, 'G P U'],
      [/\bRAM\b/gi, 'ram'],
      [/\bJSON\b/gi, 'J-son'],
      [/\bHTTP\b/g, 'H T T P'],
      [/\bHTTPS\b/g, 'H T T P S'],
      [/\bID\b/g, 'I D'],
      [/\bURL\b/g, 'U R L'],
    ];

    for (const [regex, rep] of replacements) {
      s = s.replace(regex, rep);
    }

    // Clean whitespace and excessive punctuation
    s = s.replace(/--+/g, '—');
    s = s.replace(/\s+/g, ' ').trim();

    return s;
  }

  /**
   * Queue utterance to be spoken in sequence
   */
  queue(text, options = {}) {
    const cleanText = this.sanitizeAndNormalize(text);
    if (!cleanText) return Promise.resolve();

    return new Promise((resolve, reject) => {
      this.queueItems.push({ text: cleanText, options, resolve, reject });
      if (!this.isProcessingQueue && !this.engine.isSpeaking) {
        this._processNext();
      }
    });
  }

  /**
   * Speak immediately (flushes queue unless options.preserveQueue is true)
   */
  speak(text, options = {}) {
    const cleanText = this.sanitizeAndNormalize(text);
    if (!cleanText) return Promise.resolve();

    if (!options.preserveQueue) {
      this.clearQueue();
    }

    return this.engine.speak(cleanText, options);
  }

  /**
   * Interrupt current speech immediately (e.g. when user speaks)
   */
  interrupt() {
    this.clearQueue();
    this.engine.interrupt();
  }

  /**
   * Cancel and stop all speech immediately
   */
  cancel() {
    this.clearQueue();
    this.engine.cancel();
  }

  clearQueue() {
    while (this.queueItems.length > 0) {
      const item = this.queueItems.shift();
      item.resolve({ cancelled: true });
    }
    this.isProcessingQueue = false;
  }

  async _processNext() {
    if (this.queueItems.length === 0) {
      this.isProcessingQueue = false;
      return;
    }

    this.isProcessingQueue = true;
    const item = this.queueItems.shift();

    try {
      const result = await this.engine.speak(item.text, item.options);
      item.resolve(result);
    } catch (err) {
      item.reject(err);
    } finally {
      // Small natural pause between queued utterances (300ms)
      setTimeout(() => {
        this._processNext();
      }, 300);
    }
  }
}

// ── 2. Voice Engine (Streaming Audio & Web Audio Amplitude Pipeline) ─────────
class UltronVoiceEngine {
  constructor(options = {}) {
    this.voiceId = options.voiceId || '5vpfPL62TWuqhC30bkVm';
    this.serverUrl = options.serverUrl || ''; // Uses relative /api/tts/stream

    // Web Audio Graph
    this.audioCtx = null;
    this.analyser = null;
    this.dataArray = null;
    this.currentSource = null;
    this.activeAbortController = null;

    // Voice State: 'idle' | 'listening' | 'thinking' | 'speaking' | 'interrupted' | 'error'
    this.state = 'idle';
    this.isSpeaking = false;
    this.previousState = 'idle';

    // Amplitude & Callbacks
    this.amplitude = 0.0;
    this.normalizedAmp = 0.0;
    this._rafId = null;

    this.listeners = {
      state: [],
      amplitude: [],
      error: [],
    };

    // Sub-director
    this.director = new UltronVoiceDirector(this);
  }

  /* ─── State Management ─────────────────────────────────────────────────── */
  setState(newState, meta = {}) {
    if (this.state === newState) return;
    this.previousState = this.state;
    this.state = newState;

    this.listeners.state.forEach((cb) => cb(newState, this.previousState, meta));
  }

  onStateChange(cb) {
    this.listeners.state.push(cb);
    return () => {
      this.listeners.state = this.listeners.state.filter((l) => l !== cb);
    };
  }

  onAmplitude(cb) {
    this.listeners.amplitude.push(cb);
    return () => {
      this.listeners.amplitude = this.listeners.amplitude.filter((l) => l !== cb);
    };
  }

  onError(cb) {
    this.listeners.error.push(cb);
  }

  /* ─── Web Audio Context Initialization ─────────────────────────────────── */
  _ensureAudioContext() {
    if (!this.audioCtx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        this.audioCtx = new AudioContextClass();
        this.analyser = this.audioCtx.createAnalyser();
        this.analyser.fftSize = 256;
        this.analyser.smoothingTimeConstant = 0.8;
        this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
      }
    }

    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  /* ─── Core Speech Streaming Execution ──────────────────────────────────── */
  async speak(text, options = {}) {
    if (!text || typeof text !== 'string') return;

    this._ensureAudioContext();

    // Abort any ongoing stream
    if (this.activeAbortController) {
      this.activeAbortController.abort();
      this.activeAbortController = null;
    }

    if (this.currentSource) {
      try { this.currentSource.stop(); } catch (e) {}
      this.currentSource = null;
    }

    this.setState('thinking', { text });

    const abortController = new AbortController();
    this.activeAbortController = abortController;

    const startTime = performance.now();

    try {
      // 1. Call Secure Server-Side ElevenLabs Streaming Endpoint
      const response = await fetch(`${this.serverUrl}/api/tts/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'audio/mpeg',
        },
        body: JSON.stringify({
          text: text,
          voice_id: this.voiceId,
        }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        let errJson = null;
        try { errJson = await response.json(); } catch (e) {}
        const errorMsg = errJson?.error || errJson?.details || `HTTP ${response.status}: ${response.statusText}`;
        throw new Error(errorMsg);
      }

      // Check if aborted while waiting for response headers
      if (abortController.signal.aborted) {
        return { interrupted: true };
      }

      // 2. Decode Streamed Audio Buffer
      const arrayBuffer = await response.arrayBuffer();

      if (abortController.signal.aborted) {
        return { interrupted: true };
      }

      const audioBuffer = await this.audioCtx.decodeAudioData(arrayBuffer);

      if (abortController.signal.aborted) {
        return { interrupted: true };
      }

      // 3. Play Audio Synchronously with Rive/Signal Character
      return await this._playAudioBuffer(audioBuffer, abortController, startTime);

    } catch (err) {
      if (err.name === 'AbortError' || abortController.signal.aborted) {
        return { interrupted: true };
      }

      console.error('[ULTRON VoiceEngine] TTS Error:', err.message);
      this.setState('error', { error: err.message });
      this.listeners.error.forEach((cb) => cb(err));

      // Natural return to idle on failure without crashing
      setTimeout(() => {
        if (this.state === 'error') {
          this.setState('idle');
        }
      }, 2500);

      throw err;
    } finally {
      if (this.activeAbortController === abortController) {
        this.activeAbortController = null;
      }
    }
  }

  /* ─── Web Audio Playback & Real-Time Analyser Extraction ────────────────── */
  _playAudioBuffer(audioBuffer, abortController, startTime) {
    return new Promise((resolve) => {
      const source = this.audioCtx.createBufferSource();
      source.buffer = audioBuffer;
      this.currentSource = source;

      // Connect source -> AnalyserNode -> Master Speakers
      source.connect(this.analyser);
      this.analyser.connect(this.audioCtx.destination);

      // Transition to speaking state exactly when audio starts
      this.isSpeaking = true;
      this.setState('speaking', { latencyMs: Math.round(performance.now() - startTime) });

      // Start continuous RMS amplitude tracking loop
      this._startAmplitudeLoop();

      source.onended = () => {
        this._stopAmplitudeLoop();
        this.isSpeaking = false;
        this.currentSource = null;

        if (!abortController.signal.aborted) {
          // Natural return to idle or previous state
          this.setState('idle');
          resolve({ completed: true });
        } else {
          resolve({ interrupted: true });
        }
      };

      source.start(0);
    });
  }

  _startAmplitudeLoop() {
    this._stopAmplitudeLoop();

    const track = () => {
      if (!this.isSpeaking || !this.analyser) {
        this.normalizedAmp = 0;
        this.listeners.amplitude.forEach((cb) => cb(0, false));
        return;
      }

      this.analyser.getByteFrequencyData(this.dataArray);

      // Compute RMS amplitude across frequency bins
      let sumSquares = 0;
      const count = this.dataArray.length;
      for (let i = 0; i < count; i++) {
        const val = this.dataArray[i] / 255.0; // 0.0 to 1.0
        sumSquares += val * val;
      }
      const rawRms = Math.sqrt(sumSquares / count);

      // Smooth normalized amplitude with gentle curve (for subtle facial/wave modulation)
      const targetAmp = Math.min(1.0, rawRms * 1.7);
      const diff = targetAmp - this.normalizedAmp;
      this.normalizedAmp += diff * (diff > 0 ? 0.45 : 0.15);

      this.listeners.amplitude.forEach((cb) => cb(this.normalizedAmp, true));

      this._rafId = requestAnimationFrame(track);
    };

    track();
  }

  _stopAmplitudeLoop() {
    if (this._rafId) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
    this.normalizedAmp = 0;
    this.listeners.amplitude.forEach((cb) => cb(0, false));
  }

  /* ─── Interruption & Cancellation ───────────────────────────────────────── */
  interrupt() {
    if (!this.isSpeaking && this.state !== 'thinking') return;

    if (this.activeAbortController) {
      this.activeAbortController.abort();
      this.activeAbortController = null;
    }

    if (this.currentSource) {
      try { this.currentSource.stop(); } catch (e) {}
      this.currentSource = null;
    }

    this._stopAmplitudeLoop();
    this.isSpeaking = false;

    this.setState('interrupted');

    // Switch naturally to listening state after brief interrupt acknowledgement
    setTimeout(() => {
      this.setState('listening');
    }, 180);
  }

  cancel() {
    if (this.activeAbortController) {
      this.activeAbortController.abort();
      this.activeAbortController = null;
    }

    if (this.currentSource) {
      try { this.currentSource.stop(); } catch (e) {}
      this.currentSource = null;
    }

    this._stopAmplitudeLoop();
    this.isSpeaking = false;
    this.setState('idle');
  }

  /* ─── Server Status Query ───────────────────────────────────────────────── */
  async checkServerStatus() {
    try {
      const res = await fetch(`${this.serverUrl}/api/voice/status`);
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      return { status: 'offline', error: e.message };
    }
    return { status: 'error' };
  }
}

if (typeof window !== 'undefined') {
  window.UltronVoiceDirector = UltronVoiceDirector;
  window.UltronVoiceEngine = UltronVoiceEngine;
}
