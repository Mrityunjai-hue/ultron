/**
 * ULTRON v2.0 — SVG Character Geometry & DOM Rig
 * ─────────────────────────────────────────────────────────────────────────────
 * Authoritative Visual Specification:
 * - Two expressive optical eyes (88 x 145 px, rx=28) at (250, 145) and (390, 145)
 * - Two thin luminous expression/brow lines above the eyes
 * - Organic acoustic waveform across x=80 -> 560 at y=235
 * - Restrained status pill at x=320, y=370 (width=205, height=34, rx=17)
 * - Pure black negative space
 * ─────────────────────────────────────────────────────────────────────────────
 */

class SvgCharacter {
  constructor(containerElement) {
    this.container = containerElement;
    this.svg = null;
    this.leftEye = null;
    this.rightEye = null;
    this.leftCore = null;
    this.rightCore = null;
    this.leftBrow = null;
    this.rightBrow = null;
    this.wavePrimary = null;
    this.waveSecondary = null;
    this.statusPillGroup = null;
    this.statusText = null;
    this.statusBg = null;

    this.buildSvg();
  }

  buildSvg() {
    this.container.innerHTML = `
      <svg id="ultron-svg" viewBox="0 0 640 420" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <!-- 1. Primary Sovereign Optical Gradient (White -> Lavender -> Deep Purple) -->
          <linearGradient id="core-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#FFFFFF" stop-opacity="1.0" />
            <stop offset="35%" stop-color="#FFFFFF" stop-opacity="0.95" />
            <stop offset="68%" stop-color="#E0AAFF" stop-opacity="0.85" />
            <stop offset="88%" stop-color="#B96CFF" stop-opacity="0.75" />
            <stop offset="100%" stop-color="#7B2CFF" stop-opacity="0.55" />
          </linearGradient>

          <!-- 2. Warning / Error Optical Gradient -->
          <linearGradient id="core-gradient-error" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#FFFFFF" stop-opacity="1.0" />
            <stop offset="35%" stop-color="#FFF0F0" stop-opacity="0.95" />
            <stop offset="70%" stop-color="#FF5252" stop-opacity="0.85" />
            <stop offset="100%" stop-color="#FF1744" stop-opacity="0.6" />
          </linearGradient>

          <!-- 3. Offline Optical Gradient (Desaturated Slate) -->
          <linearGradient id="core-gradient-offline" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#9AA0A6" stop-opacity="0.6" />
            <stop offset="50%" stop-color="#5F6368" stop-opacity="0.4" />
            <stop offset="100%" stop-color="#3C4043" stop-opacity="0.25" />
          </linearGradient>

          <!-- 4. Soft Optical Bloom Filter -->
          <filter id="core-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="6" result="blur1" />
            <feGaussianBlur stdDeviation="2" result="blur2" />
            <feMerge>
              <feMergeNode in="blur1" />
              <feMergeNode in="blur2" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <!-- 5. Expression Line Glow Filter -->
          <filter id="line-glow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <!-- 6. Clip Paths for Eyes (88 x 145 px, rx=28) -->
          <clipPath id="left-eye-clip">
            <rect x="206" y="72.5" width="88" height="145" rx="28" ry="28" />
          </clipPath>
          <clipPath id="right-eye-clip">
            <rect x="346" y="72.5" width="88" height="145" rx="28" ry="28" />
          </clipPath>
        </defs>

        <!-- ── Eyebrows / Expression Lines ────────────────────────── -->
        <g id="brows-group">
          <!-- Left Brow: x 185 -> 285, y 105 -> 112 -->
          <path id="left-brow"
                d="M 185 105 L 285 112"
                stroke="#C77DFF"
                stroke-width="2.5"
                stroke-linecap="round"
                filter="url(#line-glow)" />

          <!-- Right Brow: x 355 -> 455, y 112 -> 105 -->
          <path id="right-brow"
                d="M 355 112 L 455 105"
                stroke="#C77DFF"
                stroke-width="2.5"
                stroke-linecap="round"
                filter="url(#line-glow)" />
        </g>

        <!-- ── Left Eye Group ────────────────────────────────────── -->
        <g id="left-eye" transform-origin="250 145">
          <!-- Outer Housing (Dark near-black fill, subtle purple border) -->
          <rect id="left-eye-housing"
                x="206" y="72.5"
                width="88" height="145"
                rx="28" ry="28"
                fill="#07040D"
                stroke="#4C1D95"
                stroke-width="2.2"
                filter="url(#line-glow)" />

          <!-- Inner Optical Chamber (Clipped) -->
          <g clip-path="url(#left-eye-clip)">
            <g id="left-eye-content" transform-origin="250 145">
              <!-- Luminous Vertical Optical Core -->
              <rect id="left-optical-core"
                    x="233" y="85"
                    width="34" height="120"
                    rx="17" ry="17"
                    fill="url(#core-gradient)"
                    filter="url(#core-glow)" />

              <!-- Brilliant White Center Hotspot -->
              <ellipse id="left-core-hotspot"
                       cx="250" cy="115"
                       rx="7" ry="22"
                       fill="#FFFFFF"
                       opacity="0.95" />
            </g>
          </g>
        </g>

        <!-- ── Right Eye Group ───────────────────────────────────── -->
        <g id="right-eye" transform-origin="390 145">
          <!-- Outer Housing -->
          <rect id="right-eye-housing"
                x="346" y="72.5"
                width="88" height="145"
                rx="28" ry="28"
                fill="#07040D"
                stroke="#4C1D95"
                stroke-width="2.2"
                filter="url(#line-glow)" />

          <!-- Inner Optical Chamber (Clipped) -->
          <g clip-path="url(#right-eye-clip)">
            <g id="right-eye-content" transform-origin="390 145">
              <!-- Luminous Vertical Optical Core -->
              <rect id="right-optical-core"
                    x="373" y="85"
                    width="34" height="120"
                    rx="17" ry="17"
                    fill="url(#core-gradient)"
                    filter="url(#core-glow)" />

              <!-- Brilliant White Center Hotspot -->
              <ellipse id="right-core-hotspot"
                       cx="390" cy="115"
                       rx="7" ry="22"
                       fill="#FFFFFF"
                       opacity="0.95" />
            </g>
          </g>
        </g>

        <!-- ── Acoustic Waveforms (y ≈ 235) ──────────────────────── -->
        <g id="waveform-group">
          <!-- Faint secondary ambient wave -->
          <path id="wave-secondary"
                stroke="#7B2CFF"
                stroke-width="1.2"
                fill="none"
                opacity="0.25"
                stroke-linecap="round" />

          <!-- Primary fluid organic wave -->
          <path id="wave-primary"
                stroke="#D9A7FF"
                stroke-width="2.0"
                fill="none"
                stroke-linecap="round"
                filter="url(#line-glow)" />
        </g>

        <!-- ── Status Pill (x=320, y≈370, w=205, h=34) ─────────── -->
        <g id="status-pill-group">
          <rect id="status-pill-bg"
                x="217.5" y="353"
                width="205" height="34"
                rx="17" ry="17"
                fill="rgba(8, 4, 15, 0.85)"
                stroke="#7B2CFF"
                stroke-width="1.2"
                filter="url(#line-glow)" />

          <text id="status-text"
                x="320" y="374.5"
                text-anchor="middle"
                font-family="'JetBrains Mono', 'Segoe UI', monospace"
                font-size="11.5"
                font-weight="600"
                letter-spacing="1.5"
                fill="#E0AAFF">◇ THINKING...</text>
        </g>
      </svg>
    `;

    // Cache elements
    this.svg = this.container.querySelector("#ultron-svg");
    this.leftEye = this.container.querySelector("#left-eye");
    this.rightEye = this.container.querySelector("#right-eye");
    this.leftCore = this.container.querySelector("#left-eye-content");
    this.rightCore = this.container.querySelector("#right-eye-content");
    this.leftBrow = this.container.querySelector("#left-brow");
    this.rightBrow = this.container.querySelector("#right-brow");
    this.wavePrimary = this.container.querySelector("#wave-primary");
    this.waveSecondary = this.container.querySelector("#wave-secondary");
    this.statusPillGroup = this.container.querySelector("#status-pill-group");
    this.statusText = this.container.querySelector("#status-text");
    this.statusBg = this.container.querySelector("#status-pill-bg");
  }
}

// Export for ES modules and browser global
if (typeof module !== "undefined" && module.exports) {
  module.exports = SvgCharacter;
}
if (typeof window !== "undefined") {
  window.SvgCharacter = SvgCharacter;
}
