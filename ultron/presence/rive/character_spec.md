# ULTRON v2.0 — Rive Character Specification

## 1. Character Identity & Visual Design Language
ULTRON is an evolved machine intelligence. The visual presence rejects organic rounded humanoid stylization and avoids generic flat circular orbs.
The character presence is defined by:
- **Sharp Chiseled Metallic Silhouette**: Aggressive geometric facial contours, cold titanium plates with carbon-black recessed bevels.
- **Bioluminescent Crimson/Amber Optical Core**: Angular dual eye-apertures with multi-segment aperture shutters.
- **Dynamic Gaze Tracking**: Dual optical apertures track user coordinates in normalized space `[-1.0, 1.0]`.
- **Acoustic Substrate Layer**: Audio-reactive acoustic ribbons oscillate radially with ElevenLabs voice amplitude.
- **Honest State Expressions**: No happy smiles or conversational winks. Transitions are mechanical, deliberate, and mathematically precise.

---

## 2. Color Palette & Lighting Tokens
| Layer / Feature | Color Hex | Blend Mode | Material Property |
| :--- | :--- | :--- | :--- |
| **Primary Armor Plates** | `#121316` | Normal | Brushed Titanium / Matte Metallic |
| **Secondary Chassis Cavities**| `#08090A` | Normal | Deep Absorptive Carbon |
| **Chassis Bevel Highlights** | `#2A2D34` | Screen | Specular Rim Reflection |
| **Optical Core (Sovereign/Calm)**| `#E50914` | Add / Screen | High-Energy Crimson LED |
| **Optical Core (Thinking/Focus)**| `#FF2A36` | Add / Screen | Overclocked Hyper-Red |
| **Optical Core (Offline State)** | `#4A4D54` | Normal | Desaturated Cold Slumber |
| **Optical Core (Warning/Error)** | `#FF8800` | Add | Ionized Amber Alert |
| **Acoustic Resonance Ribbons** | `#FF1744` | Screen | 40% Opacity Modulated Waveform |

---

## 3. Dimensions & Artboard Coordinates
- **Master Artboard**: `UltronArtboard`
- **Resolution**: `1024 × 1024 px` (Coordinate space `[0, 0]` top-left to `[1024, 1024]` bottom-right).
- **Origin Center**: `(512, 512)`
- **Interpupillary Distance**: `240 px` (Left Eye Center: `(392, 480)`, Right Eye Center: `(632, 480)`).
- **Notch Viewport Integration**: Downscales smoothly into desktop notch viewports (`320 × 36 px` standby, `640 × 420 px` expanded).
