/**
 * ULTRON v2.0 — MASTER APPLICATION & REAL-TIME WEBSOCKET BRIDGE
 * ─────────────────────────────────────────────────────────────────────────────
 * Unifies:
 * - Living Fullscreen Character Engine (Signal Line + Large Expressive Eyes)
 * - Server-Side ElevenLabs Voice Engine (Voice ID: 5vpfPL62TWuqhC30bkVm)
 * - UltronVoiceDirector (Markdown sanitization, queue, interruption)
 * - UltronWebSocketBridge: Real-time bi-directional connection (/ws)
 *     • Synchronizes Python FSM state changes to character
 *     • Receives TTS dispatches and gaze steering targets
 *     • Transmits user speech and interruption events to Python orchestrator
 * - Developer-Only Voice Lab (Toggle with 'V' or '~')
 * ─────────────────────────────────────────────────────────────────────────────
 */
'use strict';

class UltronWebSocketBridge {
  constructor(app) {
    this.app = app;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 30;
    this.reconnectDelay = 1500;
    this.isConnected = false;

    this.connect();
  }

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8080';
    const wsUrl = `${protocol}//${host}/ws`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnected = true;
        this.reconnectAttempts = 0;
        console.log(`[ULTRON Bridge] WebSocket connected to ${wsUrl}`);
        this.send({ type: 'CLIENT_READY' });
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (e) {
          console.warn('[ULTRON Bridge] Failed to parse message:', event.data);
        }
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        this.scheduleReconnect();
      };

      this.ws.onerror = (err) => {
        console.warn('[ULTRON Bridge] WebSocket connection issue. Reconnecting...');
        this.ws.close();
      };
    } catch (e) {
      this.scheduleReconnect();
    }
  }

  scheduleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => this.connect(), this.reconnectDelay);
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  handleMessage(msg) {
    switch (msg.type) {
      case 'HANDSHAKE':
        console.log('[ULTRON Bridge] Handshake received:', msg);
        if (msg.state) {
          this.app.character.setState(msg.state);
        }
        break;

      case 'STATE_CHANGE':
        if (msg.state) {
          console.log(`[ULTRON Bridge] State change: ${msg.state}`);
          if (msg.state === 'idle' && this.app.voiceEngine && this.app.voiceEngine.isSpeaking) {
            console.log('[ULTRON Bridge] Ignoring premature IDLE while still speaking audio.');
            break;
          }
          this.app.character.setState(msg.state);
          if (msg.state === 'listening') {
            this.app.isListening = true;
            this.app._showToast('● LISTENING... (SPEAK NOW)', 'listening', true);
          } else if (msg.state === 'thinking') {
            this.app.isListening = false;
            this.app._showToast('◈ THINKING...', 'thinking', true);
          } else if (msg.state === 'speaking') {
            this.app.isListening = false;
            this.app._showToast('◉ SPEAKING', 'speaking', false);
          } else if (msg.state === 'idle') {
            this.app.isListening = false;
            this.app._showToast('IDLE', 'idle', false);
          }
        }
        break;

      case 'TTS_DISPATCH':
        if (msg.text) {
          console.log(`[ULTRON Bridge] TTS Dispatch: "${msg.text}"`);
          if (this.app.voiceEngine && this.app.voiceEngine.isSpeaking) {
            this.app.director.queue(msg.text);
          } else {
            this.app.director.speak(msg.text);
          }
        }
        break;

      case 'GAZE_TARGET':
        if (typeof msg.x === 'number' && typeof msg.y === 'number') {
          // Steer eye gaze smoothly
          this.app.character.mouse.targetGazeX = msg.x;
          this.app.character.mouse.targetGazeY = msg.y;
        }
        break;

      case 'USER_RECOGNIZED':
        if (msg.name) {
          const pct = Math.round((msg.confidence || 0.9) * 100);
          this.app._showToast(`USER: ${msg.name.toUpperCase()} (${pct}%)`);
        }
        break;
    }
  }
}

class UltronApp {
  constructor() {
    this.canvas = document.getElementById('ultron-canvas');
    this.character = null;
    this.voiceEngine = null;
    this.director = null;
    this.bridge = null;

    // Mic & VAD & Speech Recognition
    this.isListening = false;
    this.micStream = null;
    this.micAudioCtx = null;
    this.micAnalyser = null;
    this.recognizer = null;
    this._speechRecActive = false;
    this._isMutedFromEcho = false;
    this._muteEchoTimer = null;
    this.lastTime = performance.now();
    this._listenTimer = null;
    this._toastTimer = null;

    // DOM Elements - Toast & Lab
    this.toast = document.getElementById('state-toast');
    this.ariaStatus = document.getElementById('aria-status');
    this.voiceLabModal = document.getElementById('voice-lab-modal');
    this.btnCloseVoiceLab = document.getElementById('btn-close-voice-lab');
    this.labVoiceState = document.getElementById('lab-voice-state');
    this.labServerStatus = document.getElementById('lab-server-status');
    this.labVuBar = document.getElementById('lab-vu-bar');
    this.labVuVal = document.getElementById('lab-vu-val');
    this.labCustomInput = document.getElementById('lab-custom-input');
    this.btnLabSpeak = document.getElementById('btn-lab-speak');
    this.btnLabQueue = document.getElementById('btn-lab-queue');
    this.btnLabInterrupt = document.getElementById('btn-lab-interrupt');
    this.btnLabCancel = document.getElementById('btn-lab-cancel');
    this.labApiKey = document.getElementById('lab-api-key');
    this.btnLabSaveKey = document.getElementById('btn-lab-save-key');
    this.labKeyStatus = document.getElementById('lab-key-status');

    this._init();
  }

  _init() {
    // 1. Initialize Fullscreen Living Character
    this.character = new UltronSignalCharacter(this.canvas);
    this.character.setState('idle');

    // 2. Initialize ElevenLabs Voice Engine & Director
    this.voiceEngine = new UltronVoiceEngine({
      voiceId: '5vpfPL62TWuqhC30bkVm',
      serverUrl: '', // Same origin /api/tts/stream
    });
    this.director = this.voiceEngine.director;

    // 3. Connect Real-time RMS Audio Amplitude to Character
    this.voiceEngine.onAmplitude((amp, isSpeaking) => {
      this.character.setAudio(amp, isSpeaking, this.isListening);

      // Update Voice Lab VU meter
      if (this.labVuBar) {
        this.labVuBar.style.width = `${Math.min(100, Math.round(amp * 100))}%`;
      }
      if (this.labVuVal) {
        this.labVuVal.textContent = amp.toFixed(2);
      }
    });

    // 4. Connect Voice State Changes to Character & UI
    this.voiceEngine.onStateChange((state, prevState, meta) => {
      this._handleVoiceStateChange(state, prevState, meta);
    });

    // 5. Initialize Real-Time WebSocket Bridge
    this.bridge = new UltronWebSocketBridge(this);

    // 6. Query Server Status
    this._checkServerVoiceStatus();

    // 7. Bind Interactions & Developer Lab
    this._bindInteractions();
    this._bindVoiceLab();
    this._initSpeechRecognition();

    // 8. Start Master RAF Animation Loop
    this._loop();
  }

  /* ─── 1. Voice State Synchronization ────────────────────────────────────── */
  _handleVoiceStateChange(state, prevState, meta) {
    if (this.labVoiceState) {
      this.labVoiceState.textContent = state.toUpperCase();
      this.labVoiceState.className = `telem-val state-${state}`;
    }

    // Anti-Echo Management: Mute microphone during and shortly after speech
    if (state === 'speaking') {
      this._isMutedFromEcho = true;
      this.isListening = false;
      this.character.setState('speaking');
      this._showToast('◉ SPEAKING', 'speaking', false);
    } else if (prevState === 'speaking') {
      clearTimeout(this._muteEchoTimer);
      this._muteEchoTimer = setTimeout(() => {
        this._isMutedFromEcho = false;
        console.log('[ULTRON Voice] Speaker audio completed. Mic unmuted.');
      }, 850);
    }

    switch (state) {
      case 'idle':
        this.isListening = false;
        this.character.setState('idle');
        this._showToast('IDLE', 'idle', false);
        break;

      case 'listening':
        this.isListening = true;
        this.character.setState('listening');
        this._showToast('● LISTENING... (SPEAK NOW)', 'listening', true);
        break;

      case 'thinking':
        this.isListening = false;
        this.character.setState('thinking');
        this._showToast('◈ THINKING...', 'thinking', true);
        break;

      case 'speaking':
        // Handled above
        break;

      case 'interrupted':
        this.isListening = false;
        this.character.setState('warning');
        this._showToast('INTERRUPTED', 'thinking', false);
        if (this.bridge) {
          this.bridge.send({ type: 'INTERRUPT_TRIGGERED' });
        }
        break;

      case 'error':
        this.isListening = false;
        this.character.setState('error');
        this._showToast('ERROR', 'thinking', false);
        break;
    }

    if (this.ariaStatus) {
      this.ariaStatus.textContent = `ULTRON voice state: ${state}.`;
    }
  }

  /* ─── 2. Server Voice Status Check ──────────────────────────────────────── */
  async _checkServerVoiceStatus() {
    try {
      const res = await this.voiceEngine.checkServerStatus();
      if (res && res.status === 'online') {
        const keyText = res.has_api_key ? 'ONLINE (KEY READY)' : 'ONLINE (KEY NEEDED)';
        if (this.labServerStatus) {
          this.labServerStatus.textContent = keyText;
          this.labServerStatus.style.color = res.has_api_key ? '#10b981' : '#f59e0b';
        }
      } else {
        if (this.labServerStatus) {
          this.labServerStatus.textContent = 'SERVER OFFLINE';
          this.labServerStatus.style.color = '#ef4444';
        }
      }
    } catch (e) {
      if (this.labServerStatus) {
        this.labServerStatus.textContent = 'CHECK FAILED';
        this.labServerStatus.style.color = '#ef4444';
      }
    }
  }

  /* ─── 3. User Interaction & Keymap ──────────────────────────────────────── */
  _bindInteractions() {
    if (this.canvas) {
      this.canvas.addEventListener('click', () => {
        if (this.voiceEngine.isSpeaking) {
          this.director.interrupt();
          return;
        }
        this._toggleConversation();
      });
    }

    window.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      if (e.key === 'v' || e.key === 'V' || e.key === '`' || e.key === '~') {
        e.preventDefault();
        this._toggleVoiceLab();
        return;
      }

      if (e.key === 'Escape') {
        this._closeVoiceLab();
        return;
      }

      if (e.code === 'Space') {
        e.preventDefault();
        if (this.voiceEngine.isSpeaking) {
          this.director.interrupt();
        } else {
          this._toggleConversation();
        }
        return;
      }

      const stateMap = {
        '1': 'idle',
        '2': 'listening',
        '3': 'thinking',
        '4': 'speaking',
        '5': 'processing',
        '6': 'searching',
        '7': 'success',
        '8': 'warning',
        '9': 'error',
        '0': 'focused',
        '-': 'confused',
        '=': 'sleep',
      };

      if (stateMap[e.key]) {
        e.preventDefault();
        const targetState = stateMap[e.key];
        this.character.setState(targetState);
        this._showToast(this.character.stateDefs[targetState].name);
        if (this.bridge) {
          this.bridge.send({ type: 'SET_STATE', state: targetState });
        }
      }
    });
  }

  _showToast(text, mode = null, persistent = false) {
    if (!this.toast) return;
    this.toast.className = 'state-toast';
    if (mode) {
      this.toast.classList.add(`mode-${mode}`);
    }
    this.toast.textContent = `[ ${text.toUpperCase()} ]`;
    this.toast.classList.add('visible');

    clearTimeout(this._toastTimer);
    if (!persistent) {
      this._toastTimer = setTimeout(() => {
        this.toast.classList.remove('visible');
      }, 2200);
    }
  }

  /* ─── 4. Conversational Voice Cycle with Real Interruption ───────────────── */
  _toggleConversation() {
    if (this.voiceEngine.isSpeaking) {
      this.director.interrupt();
      return;
    }
    if (!this.isListening) {
      this._startListening();
    } else {
      this._cancelListening();
    }
  }

  async _startListening() {
    if (this.voiceEngine.isSpeaking) {
      this.director.interrupt();
    }
    this.isListening = true;
    this.character.setState('listening');
    this._showToast('● LISTENING... (SPEAK NOW)', 'listening', true);
    if (this.bridge) {
      this.bridge.send({ type: 'WAKE_WORD_DETECTED' });
      this.bridge.send({ type: 'USER_SPEECH_START' });
    }

    clearTimeout(this._listenTimer);
    this._listenTimer = setTimeout(() => {
      if (this.isListening) {
        console.log('[ULTRON App] Listening silence timeout. Returning to idle.');
        this._cancelListening();
      }
    }, 9000);
  }

  async _cancelListening() {
    this.isListening = false;
    clearTimeout(this._listenTimer);
    this.character.setState('idle');
    this._showToast('IDLE', 'idle', false);
    if (this.bridge) {
      this.bridge.send({ type: 'USER_SPEECH_END' });
    }
  }

  async _stopListeningAndRespond() {
    this._cancelListening();
  }

  /* ─── 4b. Hands-Free Web Speech Recognition & Wake Word Detection ───────── */
  _initSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      console.log('[ULTRON Speech] Web Speech API not supported in this browser.');
      return;
    }

    try {
      this.recognizer = new SpeechRec();
      this.recognizer.continuous = true;
      this.recognizer.interimResults = false;
      this.recognizer.lang = 'en-US';

      this.recognizer.onresult = (event) => {
        const lastIdx = event.results.length - 1;
        if (lastIdx < 0) return;
        const raw = event.results[lastIdx][0].transcript.trim();
        const confidence = event.results[lastIdx][0].confidence;
        if (!raw) return;

        // 1. Anti-Echo Filter: Ignore speaker output while speaking
        if (this._isMutedFromEcho || (this.voiceEngine && this.voiceEngine.isSpeaking)) {
          console.log(`[ULTRON Speech] Muted acoustic feedback discarded: "${raw}"`);
          return;
        }

        console.log(`[ULTRON Speech] Heard: "${raw}" (${Math.round(confidence * 100)}%)`);

        let text = raw;
        const lower = text.toLowerCase();

        // 2. Wake Word Processing
        if (lower.includes('ultron')) {
          console.log('[ULTRON Speech] Wake keyword detected in phrase:', raw);
          const stripped = text.replace(/^.*?\bultron\b[,.!?:\s]*/i, '').trim();

          if (!stripped || stripped.length < 2) {
            // User ONLY said "Ultron" -> wake up and listen!
            this._startListening();
            return;
          } else {
            // User said "Ultron, <question>" in one breath!
            text = stripped;
          }
        }

        // 3. User Speech Dispatch
        if (this.isListening || lower.includes('ultron')) {
          console.log(`[ULTRON Speech] Processing user utterance: "${text}"`);
          this._showToast(`HEARD: "${text}"`, 'listening', true);

          clearTimeout(this._listenTimer);
          this.isListening = false;

          setTimeout(() => {
            this.character.setState('thinking');
            this._showToast('◈ THINKING...', 'thinking', true);
          }, 350);

          if (this.bridge) {
            this.bridge.send({ type: 'USER_UTTERANCE', text: text });
          }
        }
      };

      this.recognizer.onerror = (e) => {
        if (e.error !== 'no-speech') {
          console.debug('[ULTRON Speech] Recognizer notice:', e.error);
        }
      };

      this.recognizer.onend = () => {
        if (this._speechRecActive) {
          try { this.recognizer.start(); } catch (e) {}
        }
      };

      this._speechRecActive = true;
      this.recognizer.start();
      console.log('[ULTRON Speech] Continuous hands-free listener active (say "Ultron" or press Space/click).');
    } catch (e) {
      console.warn('[ULTRON Speech] Init notice:', e.message);
    }
  }

  /* ─── 5. Developer Voice Lab Controller ─────────────────────────────────── */
  _bindVoiceLab() {
    if (this.btnCloseVoiceLab) {
      this.btnCloseVoiceLab.addEventListener('click', () => this._closeVoiceLab());
    }

    document.querySelectorAll('.btn-phrase').forEach((btn) => {
      btn.addEventListener('click', () => {
        const phrase = btn.dataset.phrase;
        if (phrase) {
          this.director.speak(phrase);
        }
      });
    });

    if (this.btnLabSpeak && this.labCustomInput) {
      this.btnLabSpeak.addEventListener('click', () => {
        const text = this.labCustomInput.value.trim();
        if (text) {
          this.director.speak(text);
        }
      });
    }

    if (this.btnLabQueue) {
      this.btnLabQueue.addEventListener('click', () => {
        this.director.queue("Analysis initiated. Subsystems responding.");
        this.director.queue("Signal integrity verified at ninety-nine percent.");
        this.director.queue("Sequence finalized. ULTRON is standing by.");
      });
    }

    if (this.btnLabInterrupt) {
      this.btnLabInterrupt.addEventListener('click', () => {
        this.director.interrupt();
      });
    }

    if (this.btnLabCancel) {
      this.btnLabCancel.addEventListener('click', () => {
        this.director.cancel();
      });
    }

    if (this.btnLabSaveKey && this.labApiKey) {
      this.btnLabSaveKey.addEventListener('click', async () => {
        const key = this.labApiKey.value.trim();
        if (!key) return;

        try {
          const res = await fetch('/api/voice/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: key }),
          });
          const data = await res.json();
          if (res.ok) {
            if (this.labKeyStatus) {
              this.labKeyStatus.textContent = "✓ Key saved securely on server. Server-side TTS active.";
              this.labKeyStatus.style.color = "#10b981";
            }
            this.labApiKey.value = "";
            this._checkServerVoiceStatus();
          } else {
            if (this.labKeyStatus) {
              this.labKeyStatus.textContent = `Error: ${data.error || 'Failed to save'}`;
              this.labKeyStatus.style.color = "#ef4444";
            }
          }
        } catch (err) {
          if (this.labKeyStatus) {
            this.labKeyStatus.textContent = `Network error: ${err.message}`;
            this.labKeyStatus.style.color = "#ef4444";
          }
        }
      });
    }
  }

  _toggleVoiceLab() {
    if (!this.voiceLabModal) return;
    const isHidden = this.voiceLabModal.classList.contains('hidden');
    if (isHidden) {
      this.voiceLabModal.classList.remove('hidden');
      this._checkServerVoiceStatus();
    } else {
      this.voiceLabModal.classList.add('hidden');
    }
  }

  _closeVoiceLab() {
    if (this.voiceLabModal) {
      this.voiceLabModal.classList.add('hidden');
    }
  }

  /* ─── 6. Master Animation Loop ──────────────────────────────────────────── */
  _loop() {
    const now = performance.now();
    const dt = Math.min((now - this.lastTime) / 1000, 0.1);
    this.lastTime = now;

    this.character.update(dt);
    this.character.render();

    requestAnimationFrame(() => this._loop());
  }
}

// Launch on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.ultronApp = new UltronApp();
});
