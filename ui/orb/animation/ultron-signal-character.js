/**
 * ULTRON v2.0 — MASTER PARAMETRIC SIGNAL CHARACTER ENGINE
 * ─────────────────────────────────────────────────────────────────────────────
 * "ONE LARGE, EXPRESSIVE ULTRON + ONE LIVING SIGNAL + ONE EMPTY, BEAUTIFUL CANVAS."
 *
 * Visual System & Anatomy:
 * 1. Large Expressive AI Eyes (16–22% of viewport height on desktop):
 *    - Deep multi-layered visor optics matching master reference:
 *        • Outer luminous state halo / aura (restrained, premium)
 *        • Visor outer rim with state color illumination
 *        • Deep dark inner optical chamber (#030712) with subtle radial aura
 *        • Radiant white/cyan pupil aperture that tracks gaze smoothly
 *        • Subtle angled top eyelid contour reflecting brow emotion
 *    - Sleek floating eyebrow filaments with pure white core highlight
 *    - Success state: curved upward smiling arches (^ ^)
 *    - Sleeping state: closed downward curved eyelid arcs (‿ ‿)
 *    - Confused state: asymmetric left/right eye height and cocked eyebrow
 * 2. Living Dual-Strand Signal Line:
 *    - Spans 78–88% of screen width
 *    - Majestic central energy field with bold 60–85px wave crests
 *    - Primary wave + secondary intertwining harmonic strand (exact reference match!)
 *    - Wave gracefully cradles underneath ULTRON's eyes
 *    - Settles into a serene straight horizontal line toward the outer edges
 *    - Real-time voice reactivity to ElevenLabs audio stream and microphone input
 * ─────────────────────────────────────────────────────────────────────────────
 */
'use strict';

class UltronSignalCharacter {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas ? canvas.getContext('2d') : null;

    this.width = window.innerWidth;
    this.height = window.innerHeight;
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);

    this.currentState = 'idle';
    this.targetState = 'idle';
    this.totalTime = 0;

    // Audio reactivity
    this.audio = {
      amplitude: 0.0,
      smoothedAmp: 0.0,
      isSpeaking: false,
      isListening: false,
    };

    // Mouse tracking for subtle gaze tracking
    this.mouse = {
      x: this.width / 2,
      y: this.height / 2,
      targetGazeX: 0,
      targetGazeY: 0,
    };

    // Micro-animation timers
    this.blink = {
      isBlinking: false,
      timer: 4.0,
      progress: 0.0,
      duration: 0.16,
    };

    this.saccade = {
      timer: 3.0,
      offsetX: 0,
      offsetY: 0,
    };

    // ── Continuous State Parameters (Interpolated every frame) ─────────────────
    this.current = {
      // Dimensions
      eyeHeight: 162,
      eyeWidth: 84,
      eyeSpacing: 130,
      eyeAperture: 1.0,     // 0 = closed slit, 1 = normal, 1.15 = alert
      eyeTiltLeft: 0.0,     // radians
      eyeTiltRight: 0.0,
      browAngleLeft: 0.0,
      browAngleRight: 0.0,
      browOffsetY: 26,
      browLength: 104,
      browThickness: 4.0,
      gazeX: 0.0,
      gazeY: 0.0,
      asymmetry: 0.0,       // 0 to 1 for confused state
      shapeMode: 'capsule', // 'capsule', 'smiling', 'sleeping'

      // Color (R, G, B)
      r: 255, g: 255, b: 255,
      glowIntensity: 24,
      opacity: 1.0,

      // Waveform
      waveAmp: 3.0,
      waveFreq: 0.016,
      waveSpeed: 0.8,
      waveType: 'idle-breathing',
      centerEnergyWidth: 0.32,
      glitch: 0.0,
      scanBead: -1.0,
    };

    this.target = Object.assign({}, this.current);

    // ── 12 Canonical State Definitions ──────────────────────────────────────
    this.stateDefs = {
      idle: {
        name: 'Idle',
        r: 255, g: 255, b: 255,
        glowIntensity: 20,
        aperture: 1.0,
        eyeTiltLeft: 0.0,
        eyeTiltRight: 0.0,
        browAngleLeft: 0.0,
        browAngleRight: 0.0,
        browOffsetY: 28,
        asymmetry: 0.0,
        shapeMode: 'capsule',
        waveAmp: 3.5,
        waveFreq: 0.016,
        waveSpeed: 0.8,
        waveType: 'idle-breathing',
        centerEnergyWidth: 0.28,
        glitch: 0.0,
        gazeOffsetX: 0.0,
        gazeOffsetY: 0.0,
      },
      listening: {
        name: 'Listening',
        r: 37, g: 99, b: 235, // Electric Blue (#2563eb)
        glowIntensity: 32,
        aperture: 1.10,
        eyeTiltLeft: 0.05,
        eyeTiltRight: -0.05,
        browAngleLeft: 0.16,
        browAngleRight: -0.16,
        browOffsetY: 28,
        asymmetry: 0.0,
        shapeMode: 'capsule',
        waveAmp: 64.0,       // Bold, majestic wave amplitude
        waveFreq: 0.020,
        waveSpeed: 2.2,
        waveType: 'rolling-inward',
        centerEnergyWidth: 0.38,
        glitch: 0.0,
        gazeOffsetX: 0.0,
        gazeOffsetY: 0.0,
      },
      thinking: {
        name: 'Thinking',
        r: 168, g: 85, b: 247, // Contemplative Purple (#a855f7)
        glowIntensity: 26,
        aperture: 0.84,
        eyeTiltLeft: -0.02,
        eyeTiltRight: 0.02,
        browAngleLeft: 0.10,
        browAngleRight: -0.10,
        browOffsetY: 24,
        asymmetry: 0.0,
        shapeMode: 'capsule',
        waveAmp: 36.0,
        waveFreq: 0.018,
        waveSpeed: 1.1,
        waveType: 'complex-contemplation',
        centerEnergyWidth: 0.36,
        glitch: 0.0,
        gazeOffsetX: 14.0,   // Shift gaze thoughtfully away
        gazeOffsetY: -8.0,
      },
      speaking: {
        name: 'Speaking',
        r: 16, g: 185, b: 129, // Emerald / Teal (#10b981)
        glowIntensity: 34,
        aperture: 1.08,
        eyeTiltLeft: 0.0,
        eyeTiltRight: 0.0,
        browAngleLeft: 0.0,
        browAngleRight: 0.0,
        browOffsetY: 28,
        asymmetry: 0.0,
        shapeMode: 'capsule',
        waveAmp: 68.0,
        waveFreq: 0.026,
        waveSpeed: 3.2,
        waveType: 'voice-resonance',
        centerEnergyWidth: 0.42,
        glitch: 0.0,
        gazeOffsetX: 0.0,
        gazeOffsetY: 0.0,
      },
      processing: {
        name: 'Processing',
        r: 245, g: 158, b: 11, // Warm Amber (#f59e0b)
        glowIntensity: 28,
        aperture: 0.96,
        eyeTiltLeft: 0.0,
        eyeTiltRight: 0.0,
        browAngleLeft: 0.0,
        browAngleRight: 0.0,
        browOffsetY: 26,
        asymmetry: 0.0,
        shapeMode: 'capsule',
        waveAmp: 42.0,
        waveFreq: 0.052,
        waveSpeed: 3.8,
        waveType: 'high-freq-amber',
        centerEnergyWidth: 0.36,
        glitch: 0.0,
        gazeOffsetX: 0.0,
        gazeOffsetY: 0.0,
      },
      searching: {
        name: 'Searching',
        r: 56, g: 189, b: 248, // Light Cyan (#38bdf8)
        glowIntensity: 30,
        aperture: 1.05,
        eyeTiltLeft: 0.0,
        eyeTiltRight: 0.0,
        browAngleLeft: 0.0,
        browAngleRight: 0.0,
        browOffsetY: 27,
        asymmetry: 0.0,
        shapeMode: 'capsule',
        waveAmp: 16.0,
        waveFreq: 0.018,
        waveSpeed: 1.8,
        waveType: 'search-scan',
        centerEnergyWidth: 0.38,
        glitch: 0.0,
        gazeOffsetX: 0.0,
        gazeOffsetY: 0.0,
      },
      success: {
        name: 'Success',
        r: 16, g: 185, b: 129, // Harmonious Green (#10b981)
        glowIntensity: 32,
        aperture: 1.0,
        eyeTiltLeft: 0.0,
        eyeTiltRight: 0.0,
        browAngleLeft: 0.0,
        browAngleRight: 0.0,
        browOffsetY: 30,
        asymmetry: 0.0,
        shapeMode: 'smiling', // Arched smiling eyes (^ ^)
        waveAmp: 48.0,
        waveFreq: 0.022,
        waveSpeed: 1.6,
        waveType: 'harmonic-success',
        centerEnergyWidth: 0.38,
        glitch: 0.0,
        gazeOffsetX: 0.0,
        gazeOffsetY: -3.0,
      },
      warning: {
        name: 'Warning',
        r: 249, g: 115, b: 22, // Sharp Amber / Orange (#f97316)
        glowIntensity: 30,
        aperture: 0.76,
        eyeTiltLeft: 0.08,
        eyeTiltRight: -0.08,
        browAngleLeft: 0.28,
        browAngleRight: -0.28,
        browOffsetY: 22,
        asymmetry: 0.0,
        shapeMode: 'capsule',
        waveAmp: 52.0,
        waveFreq: 0.032,
        waveSpeed: 2.4,
        waveType: 'angular-warning',
        centerEnergyWidth: 0.36,
        glitch: 0.0,
        gazeOffsetX: 0.0,
        gazeOffsetY: 0.0,
      },
      error: {
        name: 'Error',
        r: 239, g: 68, b: 68, // Red (#ef4444)
        glowIntensity: 34,
        aperture: 0.72,
        eyeTiltLeft: 0.12,
        eyeTiltRight: -0.06,
        browAngleLeft: 0.32,
        browAngleRight: -0.24,
        browOffsetY: 22,
        asymmetry: 0.25,
        shapeMode: 'capsule',
        waveAmp: 58.0,
        waveFreq: 0.036,
        waveSpeed: 4.2,
        waveType: 'error-glitch',
        centerEnergyWidth: 0.38,
        glitch: 1.0,
        gazeOffsetX: 0.0,
        gazeOffsetY: 0.0,
      },
      focused: {
        name: 'Focused',
        r: 59, g: 130, b: 246, // Intense Direct Blue (#3b82f6)
        glowIntensity: 32,
        aperture: 0.82,
        eyeTiltLeft: 0.06,
        eyeTiltRight: -0.06,
        browAngleLeft: 0.22,
        browAngleRight: -0.22,
        browOffsetY: 23,
        asymmetry: 0.0,
        shapeMode: 'capsule',
        waveAmp: 44.0,
        waveFreq: 0.030,
        waveSpeed: 2.2,
        waveType: 'focused-blue',
        centerEnergyWidth: 0.34,
        glitch: 0.0,
        gazeOffsetX: 0.0,
        gazeOffsetY: 0.0,
      },
      confused: {
        name: 'Confused',
        r: 129, g: 140, b: 248, // Indigo / Violet (#818cf8)
        glowIntensity: 28,
        aperture: 0.94,
        eyeTiltLeft: -0.04,
        eyeTiltRight: 0.08,
        browAngleLeft: 0.02,
        browAngleRight: -0.26, // Right brow cocked high!
        browOffsetY: 26,
        asymmetry: 1.0,        // Full asymmetry
        shapeMode: 'capsule',
        waveAmp: 38.0,
        waveFreq: 0.024,
        waveSpeed: 1.6,
        waveType: 'asymmetric-wave',
        centerEnergyWidth: 0.36,
        glitch: 0.0,
        gazeOffsetX: -6.0,
        gazeOffsetY: 4.0,
      },
      sleep: {
        name: 'Sleeping / Offline',
        r: 71, g: 85, b: 105, // Slate Gray (#475569)
        glowIntensity: 8,
        aperture: 0.0,
        eyeTiltLeft: 0.0,
        eyeTiltRight: 0.0,
        browAngleLeft: 0.0,
        browAngleRight: 0.0,
        browOffsetY: 16,
        asymmetry: 0.0,
        shapeMode: 'sleeping', // Closed downward curved eyelids (‿ ‿)
        waveAmp: 0.0,
        waveFreq: 0.0,
        waveSpeed: 0.0,
        waveType: 'flat',
        centerEnergyWidth: 0.0,
        glitch: 0.0,
        gazeOffsetX: 0.0,
        gazeOffsetY: 0.0,
      },
    };

    if (canvas) {
      this.resize();
      window.addEventListener('resize', () => this.resize());
      window.addEventListener('mousemove', (e) => this._onMouseMove(e));
    }

    this.setState('idle');
  }

  resize() {
    if (!this.canvas) return;
    this.width = window.innerWidth;
    this.height = window.innerHeight;
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);

    this.canvas.width = Math.round(this.width * this.dpr);
    this.canvas.height = Math.round(this.height * this.dpr);
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);

    // Responsive scaling: Eyes occupy 16–22% of viewport height on desktop
    // Reference desktop height 900px gives eyeHeight ~162px, eyeWidth ~84px
    const vScale = Math.min(1.35, Math.max(0.7, this.height / 880));
    this.scale = vScale;
    this.baseEyeH = 162 * vScale;
    this.baseEyeW = 84 * vScale;
    this.baseSpacing = 130 * vScale;
    this.baseBrowL = 104 * vScale;
    this.baseBrowOffset = 28 * vScale;
  }

  _onMouseMove(e) {
    // Subtle mouse tracking (-14px to +14px max gaze shift)
    const ndx = (e.clientX - this.width / 2) / (this.width / 2);
    const ndy = (e.clientY - this.height / 2) / (this.height / 2);
    this.mouse.targetGazeX = Math.max(-14, Math.min(14, ndx * 14));
    this.mouse.targetGazeY = Math.max(-10, Math.min(10, ndy * 10));
  }

  setState(stateName) {
    const s = this.stateDefs[stateName];
    if (!s) return;
    this.currentState = stateName;
    this.targetState = stateName;

    // Set targets for continuous lerp
    this.target.r = s.r;
    this.target.g = s.g;
    this.target.b = s.b;
    this.target.glowIntensity = s.glowIntensity;
    this.target.eyeAperture = s.aperture;
    this.target.eyeTiltLeft = s.eyeTiltLeft;
    this.target.eyeTiltRight = s.eyeTiltRight;
    this.target.browAngleLeft = s.browAngleLeft;
    this.target.browAngleRight = s.browAngleRight;
    this.target.browOffsetY = s.browOffsetY;
    this.target.asymmetry = s.asymmetry;
    this.target.shapeMode = s.shapeMode;
    this.target.waveAmp = s.waveAmp;
    this.target.waveFreq = s.waveFreq;
    this.target.waveSpeed = s.waveSpeed;
    this.target.waveType = s.waveType;
    this.target.centerEnergyWidth = s.centerEnergyWidth;
    this.target.glitch = s.glitch;
    this.target.gazeX = s.gazeOffsetX;
    this.target.gazeY = s.gazeOffsetY;
  }

  setAudio(amplitude, isSpeaking = false, isListening = false) {
    this.audio.amplitude = Math.max(0, Math.min(1, amplitude));
    this.audio.isSpeaking = isSpeaking;
    this.audio.isListening = isListening;
  }

  /* ─── Continuous Update & Physics Loop ───────────────────────────────────── */
  update(dt) {
    this.totalTime += dt;

    // Smooth audio envelope (attack / release)
    const targetAmp = this.audio.amplitude;
    const diff = targetAmp - this.audio.smoothedAmp;
    this.audio.smoothedAmp += diff * (diff > 0 ? 0.42 : 0.12);

    // 1. Natural Organic Blinking (unless in Sleeping mode)
    if (this.target.shapeMode !== 'sleeping') {
      this.blink.timer -= dt;
      if (this.blink.timer <= 0) {
        this.blink.isBlinking = true;
        this.blink.progress = 0.0;
        this.blink.timer = 3.5 + Math.random() * 4.0;
      }

      if (this.blink.isBlinking) {
        this.blink.progress += dt / this.blink.duration;
        if (this.blink.progress >= 1.0) {
          this.blink.isBlinking = false;
          this.blink.progress = 0.0;
        }
      }
    }

    let blinkFactor = 1.0;
    if (this.blink.isBlinking) {
      const p = this.blink.progress;
      blinkFactor = p < 0.5 ? 1.0 - (p / 0.5) : (p - 0.5) / 0.5;
      blinkFactor = Math.max(0.04, blinkFactor);
    }

    // 2. Micro-saccades
    this.saccade.timer -= dt;
    if (this.saccade.timer <= 0) {
      this.saccade.timer = 2.0 + Math.random() * 3.0;
      if (this.currentState === 'idle' || this.currentState === 'listening') {
        this.saccade.offsetX = (Math.random() - 0.5) * 4.5;
        this.saccade.offsetY = (Math.random() - 0.5) * 3.0;
      } else {
        this.saccade.offsetX = 0;
        this.saccade.offsetY = 0;
      }
    }

    // 3. Smooth Lerp of Continuous Parameters
    const lerpRate = Math.min(1.0, dt * 5.0);
    const colorRate = Math.min(1.0, dt * 4.0);

    this.current.r += (this.target.r - this.current.r) * colorRate;
    this.current.g += (this.target.g - this.current.g) * colorRate;
    this.current.b += (this.target.b - this.current.b) * colorRate;
    this.current.glowIntensity += (this.target.glowIntensity - this.current.glowIntensity) * lerpRate;

    this.current.eyeAperture += (this.target.eyeAperture * blinkFactor - this.current.eyeAperture) * Math.min(1.0, dt * 18.0);
    this.current.eyeTiltLeft += (this.target.eyeTiltLeft - this.current.eyeTiltLeft) * lerpRate;
    this.current.eyeTiltRight += (this.target.eyeTiltRight - this.current.eyeTiltRight) * lerpRate;
    this.current.browAngleLeft += (this.target.browAngleLeft - this.current.browAngleLeft) * lerpRate;
    this.current.browAngleRight += (this.target.browAngleRight - this.current.browAngleRight) * lerpRate;
    this.current.browOffsetY += (this.target.browOffsetY - this.current.browOffsetY) * lerpRate;
    this.current.asymmetry += (this.target.asymmetry - this.current.asymmetry) * lerpRate;

    const gazeFollowWeight = (this.currentState === 'thinking') ? 0.1 : 0.6;
    const finalTargetGazeX = this.target.gazeX + this.mouse.targetGazeX * gazeFollowWeight + this.saccade.offsetX;
    const finalTargetGazeY = this.target.gazeY + this.mouse.targetGazeY * gazeFollowWeight + this.saccade.offsetY;

    this.current.gazeX += (finalTargetGazeX - this.current.gazeX) * Math.min(1.0, dt * 4.0);
    this.current.gazeY += (finalTargetGazeY - this.current.gazeY) * Math.min(1.0, dt * 4.0);

    this.current.waveAmp += (this.target.waveAmp - this.current.waveAmp) * lerpRate;
    this.current.waveFreq += (this.target.waveFreq - this.current.waveFreq) * lerpRate;
    this.current.waveSpeed += (this.target.waveSpeed - this.current.waveSpeed) * lerpRate;
    this.current.centerEnergyWidth += (this.target.centerEnergyWidth - this.current.centerEnergyWidth) * lerpRate;
    this.current.glitch += (this.target.glitch - this.current.glitch) * lerpRate;
    this.current.shapeMode = this.target.shapeMode;
  }

  /* ─── Master Canvas Render ──────────────────────────────────────────────── */
  render() {
    if (!this.ctx) return;
    const ctx = this.ctx;

    // PURE BLACK BACKGROUND (#000000)
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, this.width, this.height);

    const cx = this.width / 2;
    // Central interaction area: baseline sits at vertical center
    const cy = this.height * 0.53;

    const r = Math.round(this.current.r);
    const g = Math.round(this.current.g);
    const b = Math.round(this.current.b);
    const colorStr = `rgb(${r}, ${g}, ${b})`;

    // 1. Render Living Signal Line (Dual-strand harmonic wave that passes around ULTRON)
    this._renderSignalLine(ctx, cx, cy, colorStr);

    // 2. Render Large Stylized Visor Eyes & Eyebrows
    this._renderEyes(ctx, cx, cy, colorStr);
  }

  /* ─── 1. Living Dual-Strand Signal Line ──────────────────────────────────── */
  _renderSignalLine(ctx, cx, cy, colorStr) {
    ctx.save();

    const spanWidth = this.width * 0.86;
    const xStart = cx - spanWidth / 2;
    const xEnd = cx + spanWidth / 2;
    const pointsCount = Math.max(160, Math.min(380, Math.floor(spanWidth / 3.2)));
    const step = spanWidth / pointsCount;

    const t = this.totalTime * this.current.waveSpeed;
    const scale = this.scale || 1.0;

    // Dynamic amplitude boosted by ElevenLabs speech audio or microphone
    let effectiveAmp = this.current.waveAmp * scale;
    if (this.audio.isSpeaking) {
      effectiveAmp += this.audio.smoothedAmp * (60.0 * scale);
    } else if (this.audio.isListening) {
      effectiveAmp += this.audio.smoothedAmp * (40.0 * scale);
    }

    const pointsPrimary = [];
    const pointsSecondary = [];
    const centerRadius = this.width * this.current.centerEnergyWidth;

    for (let i = 0; i <= pointsCount; i++) {
      const x = xStart + i * step;
      const distFromCenter = Math.abs(x - cx);

      // Central Energy Field envelope: high near ULTRON, smoothly settles to 0 at outer edges
      const u = (x - xStart) / spanWidth;
      const edgeFade = Math.sin(u * Math.PI);
      const energyDist = distFromCenter / Math.max(10, centerRadius);
      const energyEnvelope = Math.exp(-Math.pow(energyDist, 2.0)) * edgeFade;

      let dy1 = 0;
      let dy2 = 0;

      // Eye zone damping: cradle dip under the eyes
      const eyeZoneWidth = (this.baseSpacing + this.baseEyeW) * 1.35;
      const eyeZoneFactor = Math.min(1.0, Math.pow(distFromCenter / eyeZoneWidth, 1.8));

      switch (this.target.waveType) {
        case 'idle-breathing':
          dy1 = Math.sin((x - cx) * 0.015 - t * 0.9) * (3.5 * scale);
          dy2 = Math.sin((x - cx) * 0.025 + t * 0.7) * (1.8 * scale);
          break;

        case 'rolling-inward':
          // Majestic rolling blue waves with dual harmonic strands (matches master reference crop!)
          // Creates distinct crests on left and right, dipping under eyes
          const roll1 = Math.sin((x - cx) * 0.020 - t * 2.8) * effectiveAmp;
          const roll2 = Math.sin((x - cx) * 0.040 + t * 1.8) * (effectiveAmp * 0.32);
          dy1 = (roll1 + roll2) * (0.15 + eyeZoneFactor * 0.85);

          // Intertwining secondary strand
          dy2 = Math.sin((x - cx) * 0.028 - t * 2.4 + 1.2) * (effectiveAmp * 0.6) * (0.15 + eyeZoneFactor * 0.85);
          break;

        case 'complex-contemplation':
          dy1 = (Math.sin((x - cx) * 0.02 - t * 1.4) + Math.cos((x - cx) * 0.045 + t * 0.9) * 0.4) * effectiveAmp * (0.2 + eyeZoneFactor * 0.8);
          dy2 = Math.sin((x - cx) * 0.03 - t * 1.8 + 1.5) * (effectiveAmp * 0.5) * (0.2 + eyeZoneFactor * 0.8);
          break;

        case 'voice-resonance':
          const v1 = Math.sin((distFromCenter * 0.035) - t * 4.5);
          const v2 = Math.cos((distFromCenter * 0.07) - t * 3.0) * 0.5;
          dy1 = (v1 + v2) * effectiveAmp * (0.25 + eyeZoneFactor * 0.75);
          dy2 = Math.sin((distFromCenter * 0.05) - t * 3.8 + 1.0) * (effectiveAmp * 0.6) * (0.25 + eyeZoneFactor * 0.75);
          break;

        case 'high-freq-amber':
          dy1 = Math.sin((x - cx) * 0.065 - t * 4.2) * effectiveAmp * (0.2 + eyeZoneFactor * 0.8);
          dy2 = Math.sin((x - cx) * 0.09 - t * 3.5 + 0.8) * (effectiveAmp * 0.5) * (0.2 + eyeZoneFactor * 0.8);
          break;

        case 'search-scan':
          dy1 = Math.sin((x - cx) * 0.018 - t * 1.4) * effectiveAmp * eyeZoneFactor;
          dy2 = 0;
          break;

        case 'harmonic-success':
          dy1 = Math.sin((x - cx) * 0.022 - t * 2.0) * effectiveAmp * (0.25 + eyeZoneFactor * 0.75);
          dy2 = Math.sin((x - cx) * 0.044 - t * 1.6 + 1.2) * (effectiveAmp * 0.4) * (0.25 + eyeZoneFactor * 0.75);
          break;

        case 'angular-warning':
          const saw = Math.sin((x - cx) * 0.035 - t * 3.0) + Math.sin((x - cx) * 0.07 - t * 5.0) * 0.35;
          dy1 = saw * effectiveAmp * eyeZoneFactor;
          dy2 = Math.sin((x - cx) * 0.05 - t * 4.0 + 1.5) * (effectiveAmp * 0.45) * eyeZoneFactor;
          break;

        case 'error-glitch':
          if (x > cx + 40 * scale) {
            const glitchFreq = Math.sin((x - cx) * 0.15 - t * 9.5) * Math.sin(t * 35.0);
            dy1 = (Math.sin((x - cx) * 0.038 - t * 3.5) * effectiveAmp + glitchFreq * (effectiveAmp * 0.95)) * eyeZoneFactor;
            dy2 = glitchFreq * (effectiveAmp * 0.6) * eyeZoneFactor;
          } else {
            dy1 = Math.sin((x - cx) * 0.022 - t * 1.8) * (effectiveAmp * 0.45) * eyeZoneFactor;
            dy2 = 0;
          }
          break;

        case 'focused-blue':
          dy1 = Math.sin((x - cx) * 0.044 - t * 3.2) * effectiveAmp * (0.2 + eyeZoneFactor * 0.8);
          dy2 = Math.sin((x - cx) * 0.088 - t * 2.8 + 1.0) * (effectiveAmp * 0.35) * (0.2 + eyeZoneFactor * 0.8);
          break;

        case 'asymmetric-wave':
          const freq = x < cx ? 0.05 : 0.022;
          dy1 = Math.sin((x - cx) * freq - t * 2.2) * effectiveAmp * eyeZoneFactor;
          dy2 = Math.sin((x - cx) * (freq * 1.5) - t * 1.8 + 1.0) * (effectiveAmp * 0.5) * eyeZoneFactor;
          break;

        case 'flat':
        default:
          dy1 = 0;
          dy2 = 0;
          break;
      }

      // Natural cradle dip under the eyes
      const cradleDip = (this.target.waveType !== 'flat') ? Math.exp(-Math.pow(distFromCenter / (120 * scale), 2)) * (16.0 * scale) : 0;

      pointsPrimary.push({
        x: x,
        y: cy + (dy1 * energyEnvelope) + (cradleDip * edgeFade),
      });

      pointsSecondary.push({
        x: x,
        y: cy + (dy2 * energyEnvelope) + (cradleDip * edgeFade * 0.8),
      });
    }

    // ── Draw Secondary Intertwining Strand (Matches reference!) ────────────
    if (this.target.waveType !== 'flat' && this.target.waveType !== 'idle-breathing') {
      ctx.lineWidth = 1.6 * scale;
      ctx.strokeStyle = colorStr;
      ctx.shadowColor = colorStr;
      ctx.shadowBlur = 12;
      ctx.globalAlpha = 0.55;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      ctx.beginPath();
      ctx.moveTo(pointsSecondary[0].x, pointsSecondary[0].y);
      for (let i = 1; i < pointsSecondary.length - 2; i++) {
        const xc = (pointsSecondary[i].x + pointsSecondary[i + 1].x) / 2;
        const yc = (pointsSecondary[i].y + pointsSecondary[i + 1].y) / 2;
        ctx.quadraticCurveTo(pointsSecondary[i].x, pointsSecondary[i].y, xc, yc);
      }
      ctx.stroke();
      ctx.globalAlpha = 1.0;
    }

    // ── Draw Primary Living Signal Strand ──────────────────────────────────
    ctx.lineWidth = 2.6 * scale;
    ctx.strokeStyle = colorStr;
    ctx.shadowColor = colorStr;
    ctx.shadowBlur = this.current.glowIntensity * 0.85;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    ctx.beginPath();
    ctx.moveTo(pointsPrimary[0].x, pointsPrimary[0].y);

    for (let i = 1; i < pointsPrimary.length - 2; i++) {
      const xc = (pointsPrimary[i].x + pointsPrimary[i + 1].x) / 2;
      const yc = (pointsPrimary[i].y + pointsPrimary[i + 1].y) / 2;
      ctx.quadraticCurveTo(pointsPrimary[i].x, pointsPrimary[i].y, xc, yc);
    }
    ctx.quadraticCurveTo(
      pointsPrimary[pointsPrimary.length - 2].x,
      pointsPrimary[pointsPrimary.length - 2].y,
      pointsPrimary[pointsPrimary.length - 1].x,
      pointsPrimary[pointsPrimary.length - 1].y
    );
    ctx.stroke();

    // ── Razor-Thin Pure White Core Beam ────────────────────────────────────
    ctx.shadowBlur = 0;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = Math.max(0.7, 1.0 * scale);
    ctx.globalAlpha = 0.92;
    ctx.stroke();
    ctx.globalAlpha = 1.0;

    // ── Searching State: Traveling Glowing Scanning Orb + Data Dots ────────
    if (this.target.waveType === 'search-scan') {
      const scanPos = 0.5 + Math.sin(t * 1.4) * 0.38;
      const scanX = xStart + spanWidth * scanPos;
      const scanY = cy;

      ctx.save();
      ctx.shadowColor = '#00d4ff';
      ctx.shadowBlur = 24 * scale;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(scanX, scanY, 6 * scale, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 1.8 * scale;
      ctx.beginPath();
      ctx.arc(scanX, scanY, 11 * scale, 0, Math.PI * 2);
      ctx.stroke();

      ctx.shadowBlur = 4;
      ctx.fillStyle = '#7dd3fc';
      for (let j = -12; j <= 12; j++) {
        if (j === 0) continue;
        const dotX = scanX + j * (16 * scale);
        if (dotX > xStart && dotX < xEnd) {
          const dotAlpha = Math.max(0, 1 - Math.abs(j) / 13);
          ctx.globalAlpha = dotAlpha * 0.75;
          ctx.beginPath();
          ctx.arc(dotX, cy, (Math.abs(j) % 2 === 0 ? 2.4 : 1.4) * scale, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      ctx.restore();
    }

    ctx.restore();
  }

  /* ─── 2. Large Expressive Visor Eyes & Eyebrows ─────────────────────────── */
  _renderEyes(ctx, cx, cy, colorStr) {
    ctx.save();

    const scale = this.scale || 1.0;
    const baseW = this.baseEyeW;
    const baseH = this.baseEyeH;
    const spacing = this.baseSpacing;
    const browLen = this.baseBrowL;
    const browOffsetY = this.current.browOffsetY * scale;

    // Position eyes nestled right above the central signal baseline
    const eyeCenterY = cy - (baseH * 0.52);

    const leftX = cx - spacing / 2;
    const rightX = cx + spacing / 2;

    const aperture = Math.max(0.02, this.current.eyeAperture);
    const shapeMode = this.current.shapeMode;

    // ── SUCCESS STATE: Smiling Curved Upward Arches (^ ^) ───────────────────
    if (shapeMode === 'smiling') {
      const archW = baseW * 1.25;
      const archH = baseH * 0.52;

      this._drawSmilingEye(ctx, leftX + this.current.gazeX, eyeCenterY + this.current.gazeY, archW, archH, colorStr);
      this._drawSmilingEye(ctx, rightX + this.current.gazeX, eyeCenterY + this.current.gazeY, archW, archH, colorStr);

      this._drawCurvedBrow(ctx, leftX, eyeCenterY - browOffsetY, browLen, colorStr);
      this._drawCurvedBrow(ctx, rightX, eyeCenterY - browOffsetY, browLen, colorStr);

      ctx.restore();
      return;
    }

    // ── SLEEPING STATE: Closed Downward Curved Eyelids (‿ ‿) ─────────────────
    if (shapeMode === 'sleeping') {
      const archW = baseW * 1.2;
      this._drawSleepingEye(ctx, leftX, eyeCenterY, archW, colorStr);
      this._drawSleepingEye(ctx, rightX, eyeCenterY, archW, colorStr);

      ctx.restore();
      return;
    }

    // ── STANDARD / ASYMMETRIC VISOR EYES ────────────────────────────────────
    const asym = this.current.asymmetry;
    const leftH = baseH * (1.0 - 0.14 * asym) * aperture;
    const rightH = baseH * (1.0 + 0.16 * asym) * aperture;
    const leftW = baseW;
    const rightW = baseW;

    const leftEyeY = eyeCenterY + (2.0 * asym * scale);
    const rightEyeY = eyeCenterY - (4.0 * asym * scale);

    // Left Eye
    this._drawVisorEye(
      ctx,
      leftX,
      leftEyeY,
      leftW,
      leftH,
      this.current.eyeTiltLeft,
      this.current.gazeX,
      this.current.gazeY,
      colorStr
    );

    // Right Eye
    this._drawVisorEye(
      ctx,
      rightX,
      rightEyeY,
      rightW,
      rightH,
      this.current.eyeTiltRight,
      this.current.gazeX,
      this.current.gazeY,
      colorStr
    );

    // Eyebrows
    const leftBrowY = leftEyeY - (leftH / 2 + browOffsetY);
    const rightBrowY = rightEyeY - (rightH / 2 + browOffsetY);

    this._drawEyebrow(ctx, leftX, leftBrowY, browLen, this.current.browAngleLeft, colorStr);
    this._drawEyebrow(ctx, rightX, rightBrowY, browLen, this.current.browAngleRight, colorStr);

    ctx.restore();
  }

  /* ─── Visor Eye Primitive (Multi-Layer Depth Optics) ────────────────────── */
  _drawVisorEye(ctx, x, y, w, h, tiltAngle, gazeX, gazeY, colorStr) {
    ctx.save();
    ctx.translate(x, y);
    if (tiltAngle !== 0) {
      ctx.rotate(tiltAngle);
    }

    const halfW = w / 2;
    const halfH = h / 2;
    const scale = this.scale || 1.0;
    const cornerR = Math.min(halfW, 26 * scale);

    // 1. Outer Atmospheric Halo Glow (Soft, restrained)
    ctx.shadowColor = colorStr;
    ctx.shadowBlur = this.current.glowIntensity * 1.25;

    // 2. Visor Outer Rim Bezel (Glowing rounded rect with state color)
    ctx.fillStyle = colorStr;
    ctx.beginPath();
    this._roundedRect(ctx, -halfW, -halfH, w, h, cornerR);
    ctx.fill();

    // 3. Deep Optical Chamber (Recessed dark cavity)
    ctx.shadowBlur = 0;
    const inset = Math.max(3.5, 5.0 * scale);
    const chamberW = w - inset * 2;
    const chamberH = Math.max(4, h - inset * 2);
    const chamberR = Math.max(2, cornerR - inset);

    // Dark chamber background with subtle inner aura
    const grad = ctx.createRadialGradient(0, 0, 4, 0, 0, halfW);
    grad.addColorStop(0, 'rgba(8, 18, 38, 0.98)');
    grad.addColorStop(1, 'rgba(2, 6, 16, 0.99)');
    ctx.fillStyle = grad;

    ctx.beginPath();
    this._roundedRect(ctx, -chamberW / 2, -chamberH / 2, chamberW, chamberH, chamberR);
    ctx.fill();

    // 4. Radiant Inner Core / Pupil Capsule (Tracks Gaze!)
    // Matches reference: Soft bright cyan/white gradient pupil
    if (h > 18) {
      const coreW = chamberW * 0.46; // Sophisticated pupil proportion (not solid block!)
      const coreH = Math.max(4, chamberH * 0.72);
      const coreR = Math.min(coreW / 2, 16 * scale);

      // Clamp gaze within chamber
      const maxGazeX = (chamberW - coreW) * 0.42;
      const maxGazeY = (chamberH - coreH) * 0.42;
      const gx = Math.max(-maxGazeX, Math.min(maxGazeX, gazeX * 0.75));
      const gy = Math.max(-maxGazeY, Math.min(maxGazeY, gazeY * 0.75));

      // Luminous inner pupil with soft vertical gradient
      const pupilGrad = ctx.createLinearGradient(0, -coreH / 2 + gy, 0, coreH / 2 + gy);
      pupilGrad.addColorStop(0, '#ffffff');
      pupilGrad.addColorStop(0.5, '#ffffff');
      pupilGrad.addColorStop(1, colorStr);

      ctx.shadowColor = '#ffffff';
      ctx.shadowBlur = 12 * scale;
      ctx.fillStyle = pupilGrad;

      ctx.beginPath();
      this._roundedRect(ctx, -coreW / 2 + gx, -coreH / 2 + gy, coreW, coreH, coreR);
      ctx.fill();

      // Specular highlight for glassy depth
      ctx.shadowBlur = 0;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.55)';
      ctx.beginPath();
      ctx.ellipse(gx, -coreH / 2 + gy + coreW * 0.5, coreW * 0.28, coreW * 0.20, 0, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.restore();
  }

  _drawSmilingEye(ctx, x, y, w, h, colorStr) {
    ctx.save();
    ctx.translate(x, y + 8);

    const scale = this.scale || 1.0;
    ctx.shadowColor = colorStr;
    ctx.shadowBlur = this.current.glowIntensity * 1.3;
    ctx.strokeStyle = colorStr;
    ctx.lineWidth = 6.4 * scale;
    ctx.lineCap = 'round';

    // Upward curved arch (^)
    ctx.beginPath();
    ctx.arc(0, 10, w / 2, Math.PI * 1.16, Math.PI * 1.84);
    ctx.stroke();

    // White core line
    ctx.shadowBlur = 0;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2.5 * scale;
    ctx.stroke();

    ctx.restore();
  }

  _drawSleepingEye(ctx, x, y, w, colorStr) {
    ctx.save();
    ctx.translate(x, y + 2);

    const scale = this.scale || 1.0;
    ctx.shadowColor = colorStr;
    ctx.shadowBlur = 8;
    ctx.strokeStyle = colorStr;
    ctx.lineWidth = 4.0 * scale;
    ctx.lineCap = 'round';

    // Downward curved eyelid arch (‿)
    ctx.beginPath();
    ctx.arc(0, -5, w / 2, Math.PI * 0.18, Math.PI * 0.82);
    ctx.stroke();

    ctx.restore();
  }

  /* ─── Eyebrow Primitives ────────────────────────────────────────────────── */
  _drawEyebrow(ctx, x, y, len, angle, colorStr) {
    ctx.save();
    ctx.translate(x, y);
    if (angle !== 0) {
      ctx.rotate(angle);
    }

    const scale = this.scale || 1.0;
    const thickness = 4.2 * scale;

    ctx.shadowColor = colorStr;
    ctx.shadowBlur = this.current.glowIntensity * 0.9;
    ctx.strokeStyle = colorStr;
    ctx.lineWidth = thickness;
    ctx.lineCap = 'round';

    const half = len / 2;
    ctx.beginPath();
    ctx.moveTo(-half, 0);
    ctx.lineTo(half, 0);
    ctx.stroke();

    // White center highlight filament
    ctx.shadowBlur = 0;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1.4 * scale;
    ctx.globalAlpha = 0.9;
    ctx.stroke();

    ctx.restore();
  }

  _drawCurvedBrow(ctx, x, y, len, colorStr) {
    ctx.save();
    ctx.translate(x, y);

    const scale = this.scale || 1.0;
    ctx.shadowColor = colorStr;
    ctx.shadowBlur = this.current.glowIntensity * 0.9;
    ctx.strokeStyle = colorStr;
    ctx.lineWidth = 4.2 * scale;
    ctx.lineCap = 'round';

    ctx.beginPath();
    ctx.arc(0, 12, len / 2, Math.PI * 1.22, Math.PI * 1.78);
    ctx.stroke();

    ctx.restore();
  }

  _roundedRect(ctx, x, y, w, h, r) {
    const radius = Math.min(r, w / 2, h / 2);
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + w - radius, y);
    ctx.arcTo(x + w, y, x + w, y + radius, radius);
    ctx.lineTo(x + w, y + h - radius);
    ctx.arcTo(x + w, y + h, x + w - radius, y + h, radius);
    ctx.lineTo(x + radius, y + h);
    ctx.arcTo(x, y + h, x, y + h - radius, radius);
    ctx.lineTo(x, y + radius);
    ctx.arcTo(x, y, x + radius, y, radius);
    ctx.closePath();
  }
}

if (typeof window !== 'undefined') {
  window.UltronSignalCharacter = UltronSignalCharacter;
}
