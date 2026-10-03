/**
 * ULTRON STATE MACHINE v2.0
 * 24 complete states with entry/loop/exit/FX definitions
 */
'use strict';

const UltronStateMachine = {
  STATES: {
    // ── BOOT ──────────────────────────────────────────────────
    boot: {
      bodyColor: 0x000008, coreColor: 0x001144,
      lightColor: 0x001144, lightIntensity: 0.5,
      energy: 0.1, orbitSpeed: 0.1, orbitOpacity: 0.1,
      eyeExpression: 'sleepy', eyeColor: 0x001144,
      bodyParams: { scaleX: 0.7, scaleY: 0.7 },
      icon: '◌', label: 'BOOT', mood: 'DORMANT',
      entry: 'boot-sequence',
    },

    // ── IDLE ──────────────────────────────────────────────────
    idle: {
      bodyColor: 0x000d2e, coreColor: 0x00aaff,
      lightColor: 0x00aaff, lightIntensity: 1.8,
      energy: 0.45, orbitSpeed: 0.35, orbitOpacity: 0.7,
      eyeExpression: 'normal', eyeColor: 0x00aaff,
      bodyParams: { scaleX: 1.0, scaleY: 1.0 },
      icon: '◉', label: 'IDLE', mood: 'CALM',
    },

    // ── AWAKE ─────────────────────────────────────────────────
    awake: {
      bodyColor: 0x001133, coreColor: 0x00ccff,
      lightColor: 0x00ccff, lightIntensity: 2.0,
      energy: 0.6, orbitSpeed: 0.5, orbitOpacity: 0.8,
      eyeExpression: 'wide', eyeColor: 0x00ccff,
      burstFX: true, burstCount: 20,
      bodyParams: { scaleX: 1.0, scaleY: 1.0 },
      icon: '◎', label: 'AWAKE', mood: 'ATTENTIVE',
    },

    // ── LISTENING ─────────────────────────────────────────────
    listening: {
      bodyColor: 0x2a1a00, coreColor: 0xffcc00,
      lightColor: 0xffcc00, lightIntensity: 2.2,
      energy: 0.65, orbitSpeed: 0.6, orbitOpacity: 0.85,
      eyeExpression: 'focused', eyeColor: 0xffcc00,
      bodyParams: { scaleX: 1.02, scaleY: 1.02 },
      icon: '◐', label: 'LISTENING', mood: 'ATTENTIVE',
    },

    // ── THINKING ──────────────────────────────────────────────
    thinking: {
      bodyColor: 0x1a1a2e, coreColor: 0xd8daff,
      lightColor: 0xaaaaff, lightIntensity: 2.0,
      energy: 0.6, orbitSpeed: 0.45, orbitOpacity: 0.75,
      eyeExpression: 'focused', eyeColor: 0xd8daff,
      bodyParams: { scaleX: 0.98, scaleY: 1.02 },
      icon: '◑', label: 'THINKING', mood: 'ANALYTICAL',
    },

    // ── PROCESSING ────────────────────────────────────────────
    processing: {
      bodyColor: 0x001528, coreColor: 0x0088ff,
      lightColor: 0x0088ff, lightIntensity: 2.5,
      energy: 0.8, orbitSpeed: 1.0, orbitOpacity: 1.0,
      eyeExpression: 'wide', eyeColor: 0x0088ff,
      bodyParams: { scaleX: 1.0, scaleY: 1.0 },
      icon: '◒', label: 'PROCESSING', mood: 'ENGAGED',
    },

    // ── WORKING ───────────────────────────────────────────────
    working: {
      bodyColor: 0x001020, coreColor: 0x0066cc,
      lightColor: 0x0066cc, lightIntensity: 2.0,
      energy: 0.75, orbitSpeed: 0.9, orbitOpacity: 0.9,
      eyeExpression: 'focused', eyeColor: 0x0066cc,
      bodyParams: { scaleX: 1.01, scaleY: 0.99 },
      icon: '◓', label: 'WORKING', mood: 'FOCUSED',
    },

    // ── SEARCHING ─────────────────────────────────────────────
    searching: {
      bodyColor: 0x001a22, coreColor: 0x00bbcc,
      lightColor: 0x00bbcc, lightIntensity: 2.2,
      energy: 0.7, orbitSpeed: 0.8, orbitOpacity: 0.9,
      eyeExpression: 'alert', eyeColor: 0x00bbcc,
      scanFX: true, scanDuration: 99,
      bodyParams: { scaleX: 1.0, scaleY: 1.0 },
      icon: '◈', label: 'SEARCHING', mood: 'SCANNING',
    },

    // ── GENERATING ────────────────────────────────────────────
    generating: {
      bodyColor: 0x001133, coreColor: 0x00eeff,
      lightColor: 0x00eeff, lightIntensity: 3.0,
      energy: 0.9, orbitSpeed: 1.2, orbitOpacity: 1.0,
      eyeExpression: 'wide', eyeColor: 0x00eeff,
      bodyParams: { scaleX: 1.04, scaleY: 1.04 },
      icon: '◩', label: 'GENERATING', mood: 'CREATING',
    },

    // ── SPEAKING ──────────────────────────────────────────────
    speaking: {
      bodyColor: 0x001a0d, coreColor: 0x00cc66,
      lightColor: 0x00cc66, lightIntensity: 2.2,
      energy: 0.7, orbitSpeed: 0.6, orbitOpacity: 0.8,
      eyeExpression: 'normal', eyeColor: 0x00cc66,
      bodyParams: { scaleX: 1.0, scaleY: 1.0 },
      icon: '◪', label: 'SPEAKING', mood: 'RESPONDING',
    },

    // ── SUCCESS ───────────────────────────────────────────────
    success: {
      bodyColor: 0x001a0d, coreColor: 0x00ff88,
      lightColor: 0x00ff88, lightIntensity: 3.5,
      energy: 1.0, orbitSpeed: 1.5, orbitOpacity: 1.0,
      eyeExpression: 'wide', eyeColor: 0x00ff88,
      burstFX: true, burstCount: 60, shockFX: true,
      bodyParams: { scaleX: 1.08, scaleY: 1.08 },
      icon: '◆', label: 'SUCCESS', mood: 'SATISFIED',
    },

    // ── WARNING ───────────────────────────────────────────────
    warning: {
      bodyColor: 0x1f1000, coreColor: 0xff8800,
      lightColor: 0xff8800, lightIntensity: 2.5,
      energy: 0.75, orbitSpeed: 0.9, orbitOpacity: 0.9,
      eyeExpression: 'alert', eyeColor: 0xff8800,
      bodyParams: { scaleX: 0.98, scaleY: 1.0 },
      icon: '◬', label: 'WARNING', mood: 'ALERT',
    },

    // ── ERROR ─────────────────────────────────────────────────
    error: {
      bodyColor: 0x1a0000, coreColor: 0xcc2200,
      lightColor: 0xcc2200, lightIntensity: 2.0,
      energy: 0.6, orbitSpeed: 0.4, orbitOpacity: 0.6,
      eyeExpression: 'narrow', eyeColor: 0xcc2200,
      bodyParams: { scaleX: 0.96, scaleY: 0.96 },
      icon: '◫', label: 'ERROR', mood: 'DISRUPTED',
    },

    // ── INTERRUPTED ───────────────────────────────────────────
    interrupted: {
      bodyColor: 0x0d0a00, coreColor: 0xaaaa00,
      lightColor: 0xaaaa00, lightIntensity: 1.5,
      energy: 0.4, orbitSpeed: 0.3, orbitOpacity: 0.5,
      eyeExpression: 'focused', eyeColor: 0xaaaa00,
      bodyParams: { scaleX: 0.97, scaleY: 0.97 },
      icon: '◭', label: 'INTERRUPTED', mood: 'PAUSED',
    },

    // ── SLEEP ─────────────────────────────────────────────────
    sleep: {
      bodyColor: 0x000406, coreColor: 0x001133,
      lightColor: 0x000820, lightIntensity: 0.3,
      energy: 0.05, orbitSpeed: 0.05, orbitOpacity: 0.08,
      eyeExpression: 'sleepy', eyeColor: 0x001133,
      bodyParams: { scaleX: 0.92, scaleY: 0.92 },
      icon: '◔', label: 'SLEEP', mood: 'DORMANT',
    },

    // ── DISCONNECTED ──────────────────────────────────────────
    disconnected: {
      bodyColor: 0x0d0008, coreColor: 0x330022,
      lightColor: 0x220011, lightIntensity: 0.5,
      energy: 0.15, orbitSpeed: 0.1, orbitOpacity: 0.15,
      eyeExpression: 'narrow', eyeColor: 0x550033,
      bodyParams: { scaleX: 0.9, scaleY: 0.9 },
      icon: '◕', label: 'OFFLINE', mood: 'DEGRADED',
    },

    // ── RECONNECTING ──────────────────────────────────────────
    reconnecting: {
      bodyColor: 0x0a0a14, coreColor: 0x3355ff,
      lightColor: 0x3355ff, lightIntensity: 1.2,
      energy: 0.4, orbitSpeed: 0.5, orbitOpacity: 0.5,
      eyeExpression: 'focused', eyeColor: 0x3355ff,
      scanFX: true, scanDuration: 99,
      bodyParams: { scaleX: 0.95, scaleY: 0.95 },
      icon: '◖', label: 'RECONNECTING', mood: 'RESTORING',
    },

    // ── SHUTDOWN ──────────────────────────────────────────────
    shutdown: {
      bodyColor: 0x000408, coreColor: 0x000a22,
      lightColor: 0x000a22, lightIntensity: 0.2,
      energy: 0.0, orbitSpeed: 0.0, orbitOpacity: 0.0,
      eyeExpression: 'sleepy', eyeColor: 0x000a22,
      bodyParams: { scaleX: 0.5, scaleY: 0.5 },
      icon: '◗', label: 'SHUTDOWN', mood: 'OFFLINE',
    },

    // ── EXCITED ───────────────────────────────────────────────
    excited: {
      bodyColor: 0x1a0800, coreColor: 0xff6600,
      lightColor: 0xff6600, lightIntensity: 3.0,
      energy: 0.95, orbitSpeed: 1.4, orbitOpacity: 1.0,
      eyeExpression: 'alert', eyeColor: 0xff8800,
      burstFX: true, burstCount: 40,
      bodyParams: { scaleX: 1.06, scaleY: 1.06 },
      icon: '◇', label: 'EXCITED', mood: 'ENERGIZED',
    },

    // ── FOCUSED ───────────────────────────────────────────────
    focused: {
      bodyColor: 0x000820, coreColor: 0x0044ff,
      lightColor: 0x0044ff, lightIntensity: 2.4,
      energy: 0.8, orbitSpeed: 0.7, orbitOpacity: 0.85,
      eyeExpression: 'focused', eyeColor: 0x0066ff,
      bodyParams: { scaleX: 0.97, scaleY: 1.03 },
      icon: '◈', label: 'FOCUSED', mood: 'CONCENTRATED',
    },

    // ── ALERT ─────────────────────────────────────────────────
    alert: {
      bodyColor: 0x1a0000, coreColor: 0xff3300,
      lightColor: 0xff3300, lightIntensity: 2.8,
      energy: 0.85, orbitSpeed: 1.1, orbitOpacity: 1.0,
      eyeExpression: 'wide', eyeColor: 0xff3300,
      shockFX: true,
      bodyParams: { scaleX: 1.0, scaleY: 1.0 },
      icon: '◉', label: 'ALERT', mood: 'THREAT_DETECTED',
    },

    // ── CONFUSED ──────────────────────────────────────────────
    confused: {
      bodyColor: 0x110a1a, coreColor: 0xaa44cc,
      lightColor: 0xaa44cc, lightIntensity: 1.8,
      energy: 0.5, orbitSpeed: 0.6, orbitOpacity: 0.7,
      eyeExpression: 'wide', eyeColor: 0xcc55ee,
      bodyParams: { scaleX: 0.99, scaleY: 1.01 },
      icon: '◎', label: 'CONFUSED', mood: 'UNCERTAIN',
    },

    // ── COMMAND_RECEIVED ──────────────────────────────────────
    command_received: {
      bodyColor: 0x001530, coreColor: 0x00aaff,
      lightColor: 0x00aaff, lightIntensity: 2.6,
      energy: 0.8, orbitSpeed: 1.0, orbitOpacity: 0.95,
      eyeExpression: 'alert', eyeColor: 0x00ccff,
      shockFX: true,
      bodyParams: { scaleX: 1.04, scaleY: 1.04 },
      icon: '◍', label: 'COMMAND', mood: 'EXECUTING',
    },

    // ── COMMAND_COMPLETED ─────────────────────────────────────
    command_completed: {
      bodyColor: 0x001a0a, coreColor: 0x44ff88,
      lightColor: 0x44ff88, lightIntensity: 2.5,
      energy: 0.75, orbitSpeed: 0.8, orbitOpacity: 0.9,
      eyeExpression: 'normal', eyeColor: 0x44ff88,
      burstFX: true, burstCount: 25, shockFX: true,
      bodyParams: { scaleX: 1.03, scaleY: 1.03 },
      icon: '◌', label: 'COMPLETE', mood: 'ACCOMPLISHED',
    },
  },
};

window.UltronStateMachine = UltronStateMachine;
