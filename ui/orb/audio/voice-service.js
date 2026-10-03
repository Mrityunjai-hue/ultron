/**
 * ULTRON VOICE SERVICE v2.0
 * Deep ElevenLabs Neural Voice Integration
 * Voice ID: 5vpfPL62TWuqhC30bkVm
 *
 * Connects directly to Web Audio API:
 * - Real-time frequency / RMS amplitude extraction via AnalyserNode
 * - Live synchronization with UltronEngine character mouth & core luminosity
 * - Seamless fallback with speech synthesis when offline or awaiting API key
 */
'use strict';

class UltronVoiceService {
  constructor(options = {}) {
    this.voiceId = options.voiceId || '5vpfPL62TWuqhC30bkVm';
    this.apiKey = localStorage.getItem('ultron_elevenlabs_key') || '';
    this.audioCtx = null;
    this.analyser = null;
    this.dataArray = null;
    this.currentSource = null;
    this.isSpeaking = false;
    this._rafId = null;
    this.onAmplitudeCallback = null;
  }

  _initAudioContext() {
    if (!this.audioCtx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        this.audioCtx = new AudioCtx();
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

  setApiKey(key) {
    this.apiKey = (key || '').trim();
    if (this.apiKey) {
      localStorage.setItem('ultron_elevenlabs_key', this.apiKey);
    } else {
      localStorage.removeItem('ultron_elevenlabs_key');
    }
  }

  getApiKey() {
    return this.apiKey;
  }

  onAmplitude(cb) {
    this.onAmplitudeCallback = cb;
  }

  /**
   * Speak response using ElevenLabs stream or calibrated fallback
   */
  async speak(text, onComplete) {
    this._initAudioContext();
    this.isSpeaking = true;

    if (this.apiKey) {
      try {
        const audioBuffer = await this._fetchElevenLabsStream(text);
        if (audioBuffer) {
          this._playBuffer(audioBuffer, onComplete);
          return;
        }
      } catch (err) {
        console.warn('[ULTRON Voice] ElevenLabs stream error, using synthesis fallback:', err);
      }
    }

    // Calibrated Speech Fallback
    this._speakFallback(text, onComplete);
  }

  async _fetchElevenLabsStream(text) {
    const url = `https://api.elevenlabs.io/v1/text-to-speech/${this.voiceId}/stream`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Accept': 'audio/mpeg',
        'Content-Type': 'application/json',
        'xi-api-key': this.apiKey,
      },
      body: JSON.stringify({
        text: text,
        model_id: 'eleven_multilingual_v2',
        voice_settings: {
          stability: 0.65,
          similarity_boost: 0.85,
          style: 0.15,
          use_speaker_boost: true,
        },
      }),
    });

    if (!res.ok) {
      throw new Error(`ElevenLabs HTTP ${res.status}: ${res.statusText}`);
    }

    const arrayBuf = await res.arrayBuffer();
    return await this.audioCtx.decodeAudioData(arrayBuf);
  }

  _playBuffer(buffer, onComplete) {
    if (this.currentSource) {
      try { this.currentSource.stop(); } catch (e) {}
    }

    this.currentSource = this.audioCtx.createBufferSource();
    this.currentSource.buffer = buffer;

    this.currentSource.connect(this.analyser);
    this.analyser.connect(this.audioCtx.destination);

    this._startAmplitudeTracking();

    this.currentSource.onended = () => {
      this._stopAmplitudeTracking();
      this.isSpeaking = false;
      if (onComplete) onComplete();
    };

    this.currentSource.start(0);
  }

  _speakFallback(text, onComplete) {
    if (!window.speechSynthesis) {
      setTimeout(() => {
        this.isSpeaking = false;
        if (onComplete) onComplete();
      }, text.length * 50);
      return;
    }

    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text);

    // Deep calm robotic cadence matching ULTRON
    utt.rate = 0.95;
    utt.pitch = 0.72;

    const voices = window.speechSynthesis.getVoices();
    const deepVoice = voices.find(
      (v) =>
        v.name.toLowerCase().includes('david') ||
        v.name.toLowerCase().includes('george') ||
        v.name.toLowerCase().includes('male') ||
        v.name.toLowerCase().includes('natural')
    );
    if (deepVoice) utt.voice = deepVoice;

    // Simulate realistic vocal amplitude pattern
    const startTime = performance.now();
    const speakDur = text.length * 55 + 500;

    const trackSimulated = () => {
      if (!this.isSpeaking) return;
      const elapsed = performance.now() - startTime;
      if (elapsed > speakDur) {
        this._stopAmplitudeTracking();
        this.isSpeaking = false;
        if (onComplete) onComplete();
        return;
      }

      // Rhythmic speech cadence waveform
      const syllable = Math.sin(elapsed * 0.016);
      const breath = Math.sin(elapsed * 0.004) * 0.2;
      const noise = (Math.random() - 0.5) * 0.15;
      const amp = Math.max(0.08, Math.min(0.85, 0.35 + syllable * 0.3 + breath + noise));

      if (this.onAmplitudeCallback) {
        this.onAmplitudeCallback(amp);
      }

      this._rafId = requestAnimationFrame(trackSimulated);
    };

    utt.onend = () => {
      this._stopAmplitudeTracking();
      this.isSpeaking = false;
      if (onComplete) onComplete();
    };

    utt.onerror = () => {
      this._stopAmplitudeTracking();
      this.isSpeaking = false;
      if (onComplete) onComplete();
    };

    this._rafId = requestAnimationFrame(trackSimulated);
    window.speechSynthesis.speak(utt);
  }

  _startAmplitudeTracking() {
    const track = () => {
      if (!this.isSpeaking) return;
      if (this.analyser && this.dataArray) {
        this.analyser.getByteFrequencyData(this.dataArray);
        let sum = 0;
        for (let i = 0; i < this.dataArray.length; i++) {
          sum += this.dataArray[i];
        }
        const avg = sum / this.dataArray.length;
        const normalized = Math.min(1.0, avg / 128);
        if (this.onAmplitudeCallback) {
          this.onAmplitudeCallback(normalized);
        }
      }
      this._rafId = requestAnimationFrame(track);
    };
    this._rafId = requestAnimationFrame(track);
  }

  _stopAmplitudeTracking() {
    if (this._rafId) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
    if (this.onAmplitudeCallback) {
      this.onAmplitudeCallback(0);
    }
  }

  stop() {
    this.isSpeaking = false;
    this._stopAmplitudeTracking();
    if (this.currentSource) {
      try { this.currentSource.stop(); } catch (e) {}
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }
}

if (typeof window !== 'undefined') {
  window.UltronVoiceService = UltronVoiceService;
}
