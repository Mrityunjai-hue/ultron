/**
 * ULTRON SPHERICAL AVATAR ENGINE v2.0
 * 1:1 Implementation of the Master Reference Design:
 *
 * 1. 3D Segmented Obsidian Sphere Core:
 *    - Perfect circular silhouette with directional spherical shading
 *    - Vertical centerline seam and curved robotic shell panels
 *    - Satin obsidian & graphite texture with Fresnel edge rim lighting
 * 2. Embedded Cyan Vector Face:
 *    - Two glowing vertical capsule eyes with rounded ends
 *    - Horizontal slit mouth that reacts dynamically to voice amplitude
 *    - Eyelid clipping for 20 states, organic blinking, and micro-saccades
 * 3. Delicate 3D Orbital Rings with Glowing Bead Nodes:
 *    - Three thin perspective wire rings tilted around the sphere
 *    - Glowing white and cyan orbital node beads drifting smoothly along paths
 * 4. Cinematic Chamber Environment:
 *    - Overhead curved architectural light bar in ceiling
 *    - Neon blue circular floor pedestal ring beneath the sphere
 *    - Inverted soft floor reflection
 */
'use strict';

class UltronVectorCharacter {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');

    this.dpr = window.devicePixelRatio || 1;
    this.width = 900;
    this.height = 700;

    this.lastTime = performance.now();
    this.totalTime = 0;

    this.currentState = 'listening'; // Default to active listening matching reference
    this.previousState = 'idle';
    this.transitionProgress = 1.0;
    this.transitionDuration = 400;
    this.transitionStartTime = 0;
    this.transientTimer = null;

    this.rig = this._cloneConfigFace(ULTRON_STATE_CONFIGS.listening);
    this.fromRig = this._cloneConfigFace(ULTRON_STATE_CONFIGS.listening);
    this.targetRig = this._cloneConfigFace(ULTRON_STATE_CONFIGS.listening);

    // Gaze System
    this.gaze = {
      targetX: 0.02,
      targetY: -0.01,
      currentX: 0.02,
      currentY: -0.01,
      velX: 0,
      velY: 0,
      damping: 0.85,
      stiffness: 0.1,
      maxOffset: 18,
      saccadeTimer: 0,
      nextSaccade: 2800,
    };

    // Blink System
    this.blink = {
      active: false,
      progress: 0,
      duration: 150,
      timer: 0,
      nextBlink: 3600,
    };

    // Audio Reactivity
    this.audio = {
      amplitude: 0.21,
      targetAmplitude: 0.21,
      smoothedAmplitude: 0.21,
      isSpeaking: false,
      isListening: true,
    };

    this.motion = {
      breathPhase: 0,
      orbitPhase: 0,
      squash: 1.0,
      squashVel: 0,
    };

    // Orbital Bead Nodes along the 3 rings (12 nodes matching Runtime Metrics)
    this.orbitalNodes = [
      { ring: 0, angle: 0.2, speed: 0.25, color: '#ffffff', radius: 4 },
      { ring: 0, angle: 2.1, speed: 0.25, color: '#00d4ff', radius: 3 },
      { ring: 0, angle: 4.3, speed: 0.25, color: '#ffffff', radius: 3.5 },
      { ring: 0, angle: 5.7, speed: 0.25, color: '#00e5ff', radius: 2.8 },
      { ring: 1, angle: 1.0, speed: -0.2, color: '#00e5ff', radius: 3.8 },
      { ring: 1, angle: 3.4, speed: -0.2, color: '#ffffff', radius: 3.2 },
      { ring: 1, angle: 4.8, speed: -0.2, color: '#55ccff', radius: 2.5 },
      { ring: 1, angle: 5.9, speed: -0.2, color: '#ffffff', radius: 3.0 },
      { ring: 2, angle: 0.8, speed: 0.18, color: '#ffffff', radius: 3 },
      { ring: 2, angle: 2.6, speed: 0.18, color: '#00bfff', radius: 4 },
      { ring: 2, angle: 3.9, speed: 0.18, color: '#ffffff', radius: 3.2 },
      { ring: 2, angle: 5.4, speed: 0.18, color: '#00e5ff', radius: 3.5 },
    ];

    this.onStateChangeCallbacks = [];

    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    if (!this.canvas) return;
    const rect = this.canvas.getBoundingClientRect();
    this.width = rect.width || 900;
    this.height = rect.height || 700;
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);

    this.canvas.width = Math.round(this.width * this.dpr);
    this.canvas.height = Math.round(this.height * this.dpr);
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
  }

  _cloneConfigFace(cfg) {
    return {
      eyeWidth: cfg.face.eyeWidth,
      eyeHeight: cfg.face.eyeHeight,
      eyeRadius: cfg.face.eyeRadius,
      eyeGap: cfg.face.eyeGap,
      leftTilt: cfg.face.leftTilt,
      rightTilt: cfg.face.rightTilt,
      eyelidTop: cfg.face.eyelidTop,
      eyelidBottom: cfg.face.eyelidBottom,
      browY: cfg.face.browY,
      leftBrowAngle: cfg.face.leftBrowAngle,
      rightBrowAngle: cfg.face.rightBrowAngle,
      browOpacity: cfg.face.browOpacity,
      mouthWidth: cfg.face.mouthWidth,
      mouthHeight: cfg.face.mouthHeight,
      mouthCurve: cfg.face.mouthCurve,
      mouthOpacity: cfg.face.mouthOpacity,
      headTilt: cfg.face.headTilt,
      scaleX: cfg.face.scaleX,
      scaleY: cfg.face.scaleY,
      energy: cfg.energy.base,
      primaryColor: cfg.colors.primary,
      accentColor: cfg.colors.accent,
      chassisColor: cfg.colors.chassis,
      faceplateColor: cfg.colors.faceplate,
      borderColor: cfg.colors.border,
      glowColor: cfg.colors.glow,
      mouthColor: cfg.colors.mouth,
      accessory: cfg.accessory,
    };
  }

  setState(stateName) {
    if (!ULTRON_STATE_CONFIGS[stateName]) return;
    if (this.currentState === stateName && this.transitionProgress >= 1.0) return;

    if (this.transientTimer) {
      clearTimeout(this.transientTimer);
      this.transientTimer = null;
    }

    const prev = this.currentState;
    this.previousState = prev;
    this.currentState = stateName;

    this.fromRig = Object.assign({}, this.rig);
    this.targetRig = this._cloneConfigFace(ULTRON_STATE_CONFIGS[stateName]);

    this.transitionDuration = ULTRON_TRANSITIONS.getDuration(prev, stateName);
    this.transitionStartTime = performance.now();
    this.transitionProgress = 0.0;

    const targetCfg = ULTRON_STATE_CONFIGS[stateName];
    if (targetCfg.isTransient && targetCfg.duration > 0) {
      this.transientTimer = setTimeout(() => {
        this.setState(targetCfg.returnState || 'idle');
      }, targetCfg.duration);
    }

    this.motion.squashVel = 0.03;

    this.onStateChangeCallbacks.forEach((cb) => {
      try { cb({ state: stateName, previousState: prev }); } catch (e) {}
    });
  }

  getState() {
    return this.currentState;
  }

  onStateChange(cb) {
    this.onStateChangeCallbacks.push(cb);
  }

  setGaze(x, y) {
    this.gaze.targetX = Math.max(-1, Math.min(1, x));
    this.gaze.targetY = Math.max(-1, Math.min(1, y));
  }

  setAudio(amplitude, isSpeaking = false, isListening = false) {
    this.audio.targetAmplitude = Math.max(0, Math.min(1, amplitude));
    this.audio.isSpeaking = isSpeaking;
    this.audio.isListening = isListening;
  }

  react(type) {
    if (type === 'slap' || type === 'poke') {
      this.motion.squashVel = -0.08;
      this.gaze.currentX = (Math.random() - 0.5) * 0.6;
      this.setState('confused');
    } else if (type === 'success') {
      this.motion.squashVel = 0.05;
      this.setState('success');
    } else if (type === 'error') {
      this.motion.squashVel = -0.04;
      this.setState('error');
    } else if (type === 'alert') {
      this.setState('alert');
    }
  }

  update(time) {
    const dt = Math.min((time - this.lastTime) / 1000, 0.1);
    this.lastTime = time;
    this.totalTime += dt;

    const currCfg = ULTRON_STATE_CONFIGS[this.currentState];

    if (this.transitionProgress < 1.0) {
      const elapsed = time - this.transitionStartTime;
      const t = Math.min(1.0, elapsed / this.transitionDuration);
      const ease = 1 - Math.pow(1 - t, 3);
      this.transitionProgress = t;
      this._interpolateRig(ease);
    } else {
      this._copyRig(this.targetRig, this.rig);
    }

    // Gaze spring smoothing
    if (currCfg.gaze.enabled) {
      if (currCfg.gaze.saccades) {
        this.gaze.saccadeTimer += dt * 1000;
        if (this.gaze.saccadeTimer > this.gaze.nextSaccade) {
          this.gaze.saccadeTimer = 0;
          this.gaze.nextSaccade = 2400 + Math.random() * 3000;
          this.gaze.targetX += (Math.random() - 0.5) * 0.15;
          this.gaze.targetY += (Math.random() - 0.5) * 0.1;
          this.gaze.targetX = Math.max(-1, Math.min(1, this.gaze.targetX));
          this.gaze.targetY = Math.max(-1, Math.min(1, this.gaze.targetY));
        }
      }
      const fx = (this.gaze.targetX - this.gaze.currentX) * this.gaze.stiffness;
      this.gaze.velX = this.gaze.velX * this.gaze.damping + fx;
      this.gaze.currentX += this.gaze.velX;

      const fy = (this.gaze.targetY - this.gaze.currentY) * this.gaze.stiffness;
      this.gaze.velY = this.gaze.velY * this.gaze.damping + fy;
      this.gaze.currentY += this.gaze.velY;
    }

    // Blink timer
    if (currCfg.blink.enabled) {
      this.blink.timer += dt * 1000;
      if (!this.blink.active && this.blink.timer > this.blink.nextBlink) {
        this.blink.active = true;
        this.blink.progress = 0;
        this.blink.duration = currCfg.blink.duration || 150;
      }
      if (this.blink.active) {
        this.blink.progress += (dt * 1000) / this.blink.duration;
        if (this.blink.progress >= 1.0) {
          this.blink.active = false;
          this.blink.progress = 0;
          this.blink.timer = 0;
          this.blink.nextBlink = 3000 + Math.random() * 3500;
        }
      }
    }

    // Audio smoothing
    this.audio.smoothedAmplitude +=
      (this.audio.targetAmplitude - this.audio.smoothedAmplitude) * 0.25;

    // Breathing & Motion
    const breathFreq = currCfg.breathing.freq || 0.35;
    this.motion.breathPhase += dt * breathFreq * Math.PI * 2;
    this.motion.orbitPhase += dt;

    const squashForce = (1.0 - this.motion.squash) * 0.18;
    this.motion.squashVel = this.motion.squashVel * 0.8 + squashForce;
    this.motion.squash += this.motion.squashVel;

    // Update Orbital Bead Nodes
    this.orbitalNodes.forEach((node) => {
      node.angle += node.speed * dt;
    });
  }

  _interpolateRig(t) {
    const f = this.fromRig;
    const tgt = this.targetRig;
    const lerp = (a, b) => a + (b - a) * t;

    this.rig.eyeWidth = lerp(f.eyeWidth, tgt.eyeWidth);
    this.rig.eyeHeight = lerp(f.eyeHeight, tgt.eyeHeight);
    this.rig.eyeRadius = lerp(f.eyeRadius, tgt.eyeRadius);
    this.rig.eyeGap = lerp(f.eyeGap, tgt.eyeGap);
    this.rig.leftTilt = lerp(f.leftTilt, tgt.leftTilt);
    this.rig.rightTilt = lerp(f.rightTilt, tgt.rightTilt);
    this.rig.eyelidTop = lerp(f.eyelidTop, tgt.eyelidTop);
    this.rig.eyelidBottom = lerp(f.eyelidBottom, tgt.eyelidBottom);
    this.rig.browY = lerp(f.browY, tgt.browY);
    this.rig.leftBrowAngle = lerp(f.leftBrowAngle, tgt.leftBrowAngle);
    this.rig.rightBrowAngle = lerp(f.rightBrowAngle, tgt.rightBrowAngle);
    this.rig.browOpacity = lerp(f.browOpacity, tgt.browOpacity);
    this.rig.mouthWidth = lerp(f.mouthWidth, tgt.mouthWidth);
    this.rig.mouthHeight = lerp(f.mouthHeight, tgt.mouthHeight);
    this.rig.mouthCurve = lerp(f.mouthCurve, tgt.mouthCurve);
    this.rig.mouthOpacity = lerp(f.mouthOpacity, tgt.mouthOpacity);
    this.rig.headTilt = lerp(f.headTilt, tgt.headTilt);
    this.rig.scaleX = lerp(f.scaleX, tgt.scaleX);
    this.rig.scaleY = lerp(f.scaleY, tgt.scaleY);
    this.rig.energy = lerp(f.energy, tgt.energy);

    this.rig.primaryColor = t > 0.5 ? tgt.primaryColor : f.primaryColor;
    this.rig.accentColor = t > 0.5 ? tgt.accentColor : f.accentColor;
    this.rig.chassisColor = t > 0.5 ? tgt.chassisColor : f.chassisColor;
    this.rig.faceplateColor = t > 0.5 ? tgt.faceplateColor : f.faceplateColor;
    this.rig.borderColor = t > 0.5 ? tgt.borderColor : f.borderColor;
    this.rig.glowColor = t > 0.5 ? tgt.glowColor : f.glowColor;
    this.rig.mouthColor = t > 0.5 ? tgt.mouthColor : f.mouthColor;
    this.rig.accessory = t > 0.5 ? tgt.accessory : f.accessory;
  }

  _copyRig(src, dest) {
    Object.assign(dest, src);
  }

  /* ─── Render Pipeline (1:1 Reference Reproduction) ─────────────────────── */
  render() {
    const ctx = this.ctx;
    if (!ctx) return;

    ctx.clearRect(0, 0, this.width, this.height);

    const cx = this.width / 2;
    const cy = this.height / 2 - 20;

    const currCfg = ULTRON_STATE_CONFIGS[this.currentState];
    const breathAmp = currCfg.breathing.amp || 0.015;
    const breathOffset = Math.sin(this.motion.breathPhase) * (breathAmp * 90);
    const audioY = this.audio.smoothedAmplitude * -4;
    const audioEnergy = this.audio.smoothedAmplitude * 0.45;

    // Master Sphere Radius (~150px on 900x700 stage)
    const r = Math.min(this.width, this.height) * 0.235;

    // ── 1. Overhead Ceiling Light Bar & Atmosphere ──────────────────────────
    this._renderChamberAtmosphere(ctx, cx, cy, r);

    // ── 2. Glowing Blue Floor Pedestal Ring & Inverted Reflection ──────────
    this._renderFloorPedestalRing(ctx, cx, cy, r, breathOffset);

    // ── 3. Back Segments of 3D Orbital Rings (Behind Sphere) ──────────────
    this._renderOrbitalRings(ctx, cx, cy + breathOffset + audioY, r, 'back');

    // ── 4. Main 3D Segmented Sphere Body ──────────────────────────────────
    ctx.save();
    ctx.translate(cx, cy + breathOffset + audioY);

    // Soft volumetric corona glow
    this._renderCoronaGlow(ctx, r, audioEnergy);

    // Segmented Obsidian Shell with Seams & 3D Shading
    this._renderSegmentedObsidianSphere(ctx, r, audioEnergy);

    // Embedded Glowing Vector Face
    this._renderEmbeddedFace(ctx, r);

    // 3D Fresnel Edge Rim Lighting & Specular Curves
    this._renderFresnelAndRimHighlights(ctx, r);

    ctx.restore();

    // ── 5. Front Segments of 3D Orbital Rings & Glowing Bead Nodes ────────
    this._renderOrbitalRings(ctx, cx, cy + breathOffset + audioY, r, 'front');

    // ── 6. State Accessories ──────────────────────────────────────────────
    ctx.save();
    ctx.translate(cx, cy + breathOffset + audioY);
    this._renderAccessories(ctx, r);
    ctx.restore();
  }

  /**
   * 1. Chamber Atmosphere & Overhead Ceiling Light Bar (Matches Reference)
   */
  _renderChamberAtmosphere(ctx, cx, cy, r) {
    ctx.save();

    // A. Vertical Structural Chamber Pillars in Background
    const pillarPositions = [-2.4, -1.7, 1.7, 2.4];
    pillarPositions.forEach((pos) => {
      const px = cx + r * pos;
      const pGrad = ctx.createLinearGradient(px - 15, 0, px + 15, 0);
      pGrad.addColorStop(0, 'rgba(0, 0, 0, 0.45)');
      pGrad.addColorStop(0.5, 'rgba(18, 30, 48, 0.25)');
      pGrad.addColorStop(1, 'rgba(0, 0, 0, 0.45)');
      ctx.fillStyle = pGrad;
      ctx.fillRect(px - 15, 0, 30, this.height);

      ctx.strokeStyle = 'rgba(0, 190, 255, 0.06)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(px, 0);
      ctx.lineTo(px, this.height);
      ctx.stroke();
    });

    // B. Soft Atmospheric Background Lighting Wash Behind Sphere
    const bgGlow = ctx.createRadialGradient(cx, cy, r * 0.4, cx, cy, r * 2.4);
    bgGlow.addColorStop(0, 'rgba(0, 160, 240, 0.08)');
    bgGlow.addColorStop(0.5, 'rgba(0, 80, 160, 0.02)');
    bgGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = bgGlow;
    ctx.fillRect(0, 0, this.width, this.height);

    // C. Overhead Curved White/Blue Architectural Light Bar
    const barY = cy - r * 1.55;
    const barW = r * 1.7;
    const barH = r * 0.16;

    // Soft ceiling glow
    const barGrad = ctx.createLinearGradient(cx - barW, barY, cx + barW, barY);
    barGrad.addColorStop(0, 'rgba(0, 180, 240, 0)');
    barGrad.addColorStop(0.2, 'rgba(150, 220, 255, 0.4)');
    barGrad.addColorStop(0.5, 'rgba(255, 255, 255, 0.9)');
    barGrad.addColorStop(0.8, 'rgba(150, 220, 255, 0.4)');
    barGrad.addColorStop(1, 'rgba(0, 180, 240, 0)');

    ctx.strokeStyle = barGrad;
    ctx.lineWidth = 3.5;
    ctx.beginPath();
    ctx.ellipse(cx, barY, barW, barH, 0, Math.PI * 0.1, Math.PI * 0.9);
    ctx.stroke();

    // Soft feathered aura behind the sphere
    const aura = ctx.createRadialGradient(cx, cy, r * 0.2, cx, cy, r * 2.2);
    aura.addColorStop(0, 'rgba(0, 160, 230, 0.12)');
    aura.addColorStop(0.4, 'rgba(0, 80, 150, 0.03)');
    aura.addColorStop(1, 'rgba(0, 0, 0, 0)');

    ctx.fillStyle = aura;
    ctx.beginPath();
    ctx.arc(cx, cy, r * 2.2, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  /**
   * 2. Glowing Blue Floor Pedestal Ring & Inverted Reflection (Matches Reference)
   */
  _renderFloorPedestalRing(ctx, cx, cy, r, breathOffset) {
    const floorY = cy + r * 1.48;
    const ringRadiusX = r * 1.6;
    const ringRadiusY = r * 0.34;

    ctx.save();

    // 1. Soft Floor Glow Pool
    const poolGrad = ctx.createRadialGradient(
      cx,
      floorY,
      0,
      cx,
      floorY,
      ringRadiusX * 1.15
    );
    poolGrad.addColorStop(0, 'rgba(0, 180, 255, 0.22)');
    poolGrad.addColorStop(0.45, 'rgba(0, 120, 200, 0.06)');
    poolGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');

    ctx.fillStyle = poolGrad;
    ctx.beginPath();
    ctx.ellipse(cx, floorY, ringRadiusX * 1.15, ringRadiusY * 1.15, 0, 0, Math.PI * 2);
    ctx.fill();

    // 2. Inverted Soft Mirror Reflection of Sphere & Cyan Face on Floor
    const reflectGrad = ctx.createRadialGradient(
      cx,
      floorY + 12,
      0,
      cx,
      floorY + 12,
      r * 0.75
    );
    reflectGrad.addColorStop(0, 'rgba(0, 212, 255, 0.16)');
    reflectGrad.addColorStop(0.5, 'rgba(0, 140, 220, 0.04)');
    reflectGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');

    ctx.fillStyle = reflectGrad;
    ctx.beginPath();
    ctx.ellipse(cx, floorY + 12, r * 0.8, r * 0.24, 0, 0, Math.PI * 2);
    ctx.fill();

    // Inverted soft eye reflection blurs
    const scaleFactor = r / 140;
    const halfGap = 24 * scaleFactor;
    ctx.save();
    ctx.shadowColor = '#00d4ff';
    ctx.shadowBlur = 12;
    ctx.fillStyle = 'rgba(0, 212, 255, 0.28)';
    ctx.beginPath();
    ctx.ellipse(cx - halfGap, floorY + 8, 4 * scaleFactor, 10 * scaleFactor, 0, 0, Math.PI * 2);
    ctx.ellipse(cx + halfGap, floorY + 8, 4 * scaleFactor, 10 * scaleFactor, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // 3. Bright Blue Pedestal Ring (Neon Edge)
    ctx.shadowColor = '#00aaff';
    ctx.shadowBlur = 18;
    ctx.strokeStyle = '#00c3ff';
    ctx.lineWidth = 2.4;

    ctx.beginPath();
    ctx.ellipse(cx, floorY, ringRadiusX, ringRadiusY, 0, 0, Math.PI * 2);
    ctx.stroke();

    // Inner thin ring
    ctx.shadowBlur = 6;
    ctx.lineWidth = 1.0;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.45)';
    ctx.beginPath();
    ctx.ellipse(cx, floorY, ringRadiusX * 0.88, ringRadiusY * 0.88, 0, 0, Math.PI * 2);
    ctx.stroke();

    ctx.restore();
  }

  /**
   * 3 & 5. Delicate 3D Orbital Rings with Glowing Bead Nodes (Matches Reference)
   */
  _renderOrbitalRings(ctx, cx, cy, r, layer) {
    ctx.save();
    ctx.translate(cx, cy);

    // 3 Distinct Orbital Wire Rings (Tilted in 3D perspective around sphere)
    const ringConfigs = [
      { rx: r * 1.85, ry: r * 0.72, tilt: 26 * Math.PI / 180 },  // Ring 0 (Tilted Up-Right)
      { rx: r * 1.78, ry: r * 0.68, tilt: -24 * Math.PI / 180 }, // Ring 1 (Tilted Down-Right)
      { rx: r * 1.95, ry: r * 0.52, tilt: 6 * Math.PI / 180 },   // Ring 2 (Near-Equatorial)
    ];

    ringConfigs.forEach((cfg, idx) => {
      ctx.save();
      ctx.rotate(cfg.tilt);

      // We split each ring into back (top half: behind sphere) and front (bottom half: in front)
      const startAngle = layer === 'back' ? Math.PI : 0;
      const endAngle = layer === 'back' ? Math.PI * 2 : Math.PI;

      ctx.strokeStyle = layer === 'front' ? 'rgba(0, 200, 255, 0.38)' : 'rgba(0, 160, 220, 0.16)';
      ctx.lineWidth = layer === 'front' ? 1.0 : 0.75;

      ctx.beginPath();
      ctx.ellipse(0, 0, cfg.rx, cfg.ry, 0, startAngle, endAngle);
      ctx.stroke();

      // Render Bead Nodes belonging to this ring and layer
      this.orbitalNodes
        .filter((n) => n.ring === idx)
        .forEach((node) => {
          // Normalize angle to [0, 2PI]
          const normAngle = ((node.angle % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
          const isFront = normAngle >= 0 && normAngle < Math.PI;

          if ((layer === 'front' && isFront) || (layer === 'back' && !isFront)) {
            const nx = Math.cos(node.angle) * cfg.rx;
            const ny = Math.sin(node.angle) * cfg.ry;

            // Glowing Node Bead
            ctx.save();
            ctx.shadowColor = node.color;
            ctx.shadowBlur = layer === 'front' ? 12 : 5;
            ctx.fillStyle = node.color;
            ctx.beginPath();
            ctx.arc(nx, ny, node.radius, 0, Math.PI * 2);
            ctx.fill();

            // Delicate light filament connecting to sphere edge
            if (layer === 'front') {
              ctx.shadowBlur = 0;
              ctx.strokeStyle = 'rgba(0, 212, 255, 0.15)';
              ctx.lineWidth = 0.5;
              ctx.beginPath();
              ctx.moveTo(nx, ny);
              ctx.lineTo(nx * 0.65, ny * 0.65);
              ctx.stroke();
            }
            ctx.restore();
          }
        });

      ctx.restore();
    });

    ctx.restore();
  }

  /**
   * Subtle Corona Glow
   */
  _renderCoronaGlow(ctx, r, audioBoost) {
    const energy = Math.min(1.0, this.rig.energy + audioBoost);
    const coronaR = r * (1.2 + energy * 0.1);

    const grad = ctx.createRadialGradient(0, 0, r * 0.75, 0, 0, coronaR);
    grad.addColorStop(0, 'rgba(0, 212, 255, 0.28)');
    grad.addColorStop(0.5, 'rgba(0, 160, 240, 0.08)');
    grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

    ctx.save();
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(0, 0, coronaR, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  /**
   * 4. Segmented 3D Obsidian Sphere (Matches Reference Screenshot)
   */
  _renderSegmentedObsidianSphere(ctx, r, audioBoost) {
    ctx.save();

    // 1. Contact shadow behind sphere
    ctx.shadowColor = 'rgba(0, 0, 0, 0.85)';
    ctx.shadowBlur = 40;
    ctx.shadowOffsetY = 20;

    // 2. Base Sphere Spherical Shading (Graphite/Titanium Key Light to Deep Obsidian)
    const keyLightX = -r * 0.25;
    const keyLightY = -r * 0.3;

    const baseGrad = ctx.createRadialGradient(
      keyLightX,
      keyLightY,
      r * 0.05,
      0,
      0,
      r
    );
    baseGrad.addColorStop(0, '#243248');       // Satin titanium upper highlight
    baseGrad.addColorStop(0.2, '#141d2c');      // Upper shell
    baseGrad.addColorStop(0.55, '#080d16');     // Mid graphite
    baseGrad.addColorStop(0.85, '#020407');     // Deep obsidian shadow
    baseGrad.addColorStop(1, '#060e1a');        // Ambient bounce rim

    ctx.fillStyle = baseGrad;
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, Math.PI * 2);
    ctx.fill();

    ctx.shadowColor = 'transparent';

    // 3. Central Dark Visor Area (Where the glowing face lives)
    const visorR = r * 0.76;
    const visorGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, visorR);
    visorGrad.addColorStop(0, '#04070e');
    visorGrad.addColorStop(0.7, '#070c16');
    visorGrad.addColorStop(1, '#020407');

    ctx.fillStyle = visorGrad;
    ctx.beginPath();
    ctx.arc(0, 0, visorR, 0, Math.PI * 2);
    ctx.fill();

    // 4. Segmented Robotic Shell Plates & Seams (Crucial Reference Feature!)
    this._renderSphereSegmentSeams(ctx, r);

    // 5. Internal Subsurface Glow behind the eyes
    const energy = Math.min(1.0, this.rig.energy + audioBoost);
    const coreGlow = ctx.createRadialGradient(0, 0, 0, 0, 0, r * 0.55);
    coreGlow.addColorStop(0, 'rgba(0, 190, 255, 0.3)');
    coreGlow.addColorStop(0.5, 'rgba(0, 140, 220, 0.08)');
    coreGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');

    ctx.fillStyle = coreGlow;
    ctx.globalAlpha = 0.5 * energy;
    ctx.beginPath();
    ctx.arc(0, 0, r * 0.55, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1.0;

    ctx.restore();
  }

  /**
   * Curved Robotic Shell Seams (Exact Reference Feature)
   */
  _renderSphereSegmentSeams(ctx, r) {
    ctx.save();
    // Clip strictly within the sphere silhouette
    ctx.beginPath();
    ctx.arc(0, 0, r - 1, 0, Math.PI * 2);
    ctx.clip();

    // A. Vertical Centerline Seam (Top pole down to bottom pole)
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.85)';
    ctx.lineWidth = 2.0;
    ctx.beginPath();
    ctx.moveTo(0, -r);
    ctx.lineTo(0, r);
    ctx.stroke();

    // Highlight line right beside the seam
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(1, -r * 0.95);
    ctx.lineTo(1, r * 0.95);
    ctx.stroke();

    // B. Left Curved Shell Panel Arc
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.75)';
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.arc(-r * 0.45, 0, r * 0.88, -Math.PI * 0.42, Math.PI * 0.42);
    ctx.stroke();

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.arc(-r * 0.45 + 1, 0, r * 0.88, -Math.PI * 0.4, Math.PI * 0.4);
    ctx.stroke();

    // C. Right Curved Shell Panel Arc
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.75)';
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.arc(r * 0.45, 0, r * 0.88, Math.PI * 0.58, Math.PI * 1.42);
    ctx.stroke();

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.arc(r * 0.45 - 1, 0, r * 0.88, Math.PI * 0.6, Math.PI * 1.4);
    ctx.stroke();

    // D. Subtle Curved Equatorial Shell Seam
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.65)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.ellipse(0, r * 0.06, r * 0.98, r * 0.32, 0, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
    ctx.lineWidth = 0.75;
    ctx.beginPath();
    ctx.ellipse(0, r * 0.06 + 1, r * 0.98, r * 0.32, 0, 0, Math.PI * 2);
    ctx.stroke();

    ctx.restore();
  }

  /**
   * Embedded Glowing Vector Face (Glowing Cyan Capsule Eyes & Slit Mouth)
   */
  _renderEmbeddedFace(ctx, r) {
    ctx.save();

    // Smooth spherical gaze projection
    const gazeOffsetX = this.gaze.currentX * this.gaze.maxOffset;
    const gazeOffsetY = this.gaze.currentY * (this.gaze.maxOffset * 0.7);

    ctx.translate(gazeOffsetX, gazeOffsetY);

    const scaleFactor = r / 140;
    const halfGap = (24 * scaleFactor);

    // Eye Capsule Dimensions matching reference (tall, clean glowing cyan capsules)
    const eyeW = 14 * scaleFactor;
    const eyeH = 46 * scaleFactor;
    const eyeR = eyeW / 2;

    let blinkClosure = 0;
    if (this.blink.active) {
      blinkClosure = Math.sin(this.blink.progress * Math.PI);
    }

    const effectiveTopLid = Math.min(1.0, this.rig.eyelidTop + blinkClosure);
    const effectiveBottomLid = Math.min(1.0, this.rig.eyelidBottom + blinkClosure * 0.4);

    // ── Glowing Cyan Eyes ──────────────────────────────────────────────────
    this._renderReferenceEye(ctx, -halfGap, -8 * scaleFactor, eyeW, eyeH, eyeR, effectiveTopLid, effectiveBottomLid);
    this._renderReferenceEye(ctx, halfGap, -8 * scaleFactor, eyeW, eyeH, eyeR, effectiveTopLid, effectiveBottomLid);

    // ── Sleek Glowing Cyan Slit Mouth ──────────────────────────────────────
    this._renderReferenceMouth(ctx, 0, 36 * scaleFactor, 26 * scaleFactor, scaleFactor);

    ctx.restore();
  }

  _renderReferenceEye(ctx, x, y, w, h, radius, lidTop, lidBot) {
    ctx.save();
    ctx.translate(x, y);

    const halfW = w / 2;
    const halfH = h / 2;

    // Outer Cyan Glow
    ctx.shadowColor = '#00d4ff';
    ctx.shadowBlur = 14;

    // 1. Clipping Path
    ctx.beginPath();
    this._drawPill(ctx, -halfW, -halfH, w, h, radius);
    ctx.clip();

    // 2. Bright Cyan-White Gradient Fill
    const eyeGrad = ctx.createLinearGradient(0, -halfH, 0, halfH);
    eyeGrad.addColorStop(0, '#ffffff');
    eyeGrad.addColorStop(0.3, '#70e4ff');
    eyeGrad.addColorStop(1, '#00b8eb');

    ctx.fillStyle = eyeGrad;
    ctx.fill();

    // 3. Eyelid Closure Overlays (Matching dark visor background)
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#060b14';

    if (lidTop > 0.01) {
      const topCover = h * lidTop;
      ctx.fillRect(-halfW - 2, -halfH - 2, w + 4, topCover);
    }
    if (lidBot > 0.01) {
      const botCover = h * lidBot;
      ctx.fillRect(-halfW - 2, halfH - botCover, w + 4, botCover + 2);
    }

    ctx.restore();
  }

  _renderReferenceMouth(ctx, x, y, baseW, scaleFactor) {
    if (this.rig.mouthOpacity <= 0.05) return;

    ctx.save();
    ctx.translate(x, y);

    let baseH = 3.5 * scaleFactor;
    if (this.audio.isSpeaking || this.audio.smoothedAmplitude > 0.05) {
      baseH += this.audio.smoothedAmplitude * 16 * scaleFactor;
    }

    const halfW = baseW / 2;
    const halfH = baseH / 2;

    ctx.shadowColor = '#00d4ff';
    ctx.shadowBlur = 10;

    const mouthGrad = ctx.createLinearGradient(0, -halfH, 0, halfH);
    mouthGrad.addColorStop(0, '#ffffff');
    mouthGrad.addColorStop(0.5, '#40dcff');
    mouthGrad.addColorStop(1, '#00a8e0');

    ctx.fillStyle = mouthGrad;
    ctx.beginPath();
    this._drawPill(ctx, -halfW, -halfH, baseW, baseH, halfH);
    ctx.fill();

    ctx.restore();
  }

  /**
   * 3D Fresnel Edge Rim Lighting & Specular Curves (Reference Look)
   */
  _renderFresnelAndRimHighlights(ctx, r) {
    ctx.save();

    // 1. 3D Fresnel Rim Arc around Sphere Silhouette
    const rimGrad = ctx.createLinearGradient(-r, -r, r, r);
    rimGrad.addColorStop(0, 'rgba(255, 255, 255, 0.55)');   // Key top-left highlight
    rimGrad.addColorStop(0.3, 'rgba(0, 212, 255, 0.35)');  // Cyan grazing rim
    rimGrad.addColorStop(0.7, 'rgba(0, 0, 0, 0.1)');
    rimGrad.addColorStop(1, 'rgba(0, 200, 255, 0.25)');   // Floor reflection rim

    ctx.lineWidth = 1.6;
    ctx.strokeStyle = rimGrad;
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, Math.PI * 2);
    ctx.stroke();

    // 2. Primary Key Specular Glint (Top-Left Curved Highlight)
    const specX = -r * 0.3 + this.gaze.currentX * 6;
    const specY = -r * 0.36 + this.gaze.currentY * 6;

    const specGrad = ctx.createRadialGradient(
      specX,
      specY,
      0,
      specX,
      specY,
      r * 0.38
    );
    specGrad.addColorStop(0, 'rgba(255, 255, 255, 0.28)');
    specGrad.addColorStop(0.4, 'rgba(0, 212, 255, 0.08)');
    specGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');

    ctx.fillStyle = specGrad;
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  _renderAccessories(ctx, r) {
    const acc = this.rig.accessory;
    if (acc === 'none') return;

    if (acc === 'search-scanner') {
      const scanY = Math.sin(this.totalTime * 2.5) * (r * 0.25);
      ctx.save();
      ctx.shadowColor = '#00e5ff';
      ctx.shadowBlur = 8;
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.7)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(-r * 0.6, scanY);
      ctx.lineTo(r * 0.6, scanY);
      ctx.stroke();
      ctx.restore();
    }
  }

  _drawPill(ctx, x, y, w, h, r) {
    const radius = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
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
  window.UltronVectorCharacter = UltronVectorCharacter;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { UltronVectorCharacter };
}
