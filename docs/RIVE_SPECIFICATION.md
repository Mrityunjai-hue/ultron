# ULTRON v2.0 — Spherical AI Core & Rive Specification
**Document Version:** 2.1  
**Target Runtime:** `@rive-app/canvas` ^2.24+  
**Target Asset Path:** `ui/orb/assets/ultron.riv`

---

## 1. Executive Summary

This document specifies the exact artboard hierarchy, parametric rig components, state machine transitions, and data-binding contract for the **ULTRON interactive AI character**.

The ULTRON visual architecture combines:
1. **3D Spherical Core (Body)**:
   - Physical spherical AI core with true circular silhouette.
   - Multi-layer directional key lighting, ambient occlusion, Fresnel edge rim illumination, and internal subsurface luminosity.
   - Equatorial seams and precision structural arcs.
   - Suspended inside a volumetric atmospheric light field with a ground horizon reflection.
2. **Embedded Face (Intelligence & Expression)**:
   - Conforms to the front optical dome of the sphere.
   - Custom geometric pill/capsule eye apertures with independent top/bottom eyelids, tilt angles, and inner optical pupil slit.
   - Expression brows with angle and elevation control.
   - Dynamic acoustic aperture reacting in real time to ElevenLabs neural voice amplitude.
   - Controlled state accessories (e.g. `working-spinner`, `search-scanner`, `voice-brackets`, `generating-matrix`, `alert-crest`, `sleep-z`).
   - Smooth gaze tracking (-1.0 to 1.0) and natural non-periodic blinking.

---

## 2. Artboard Specification

| Attribute | Value |
|---|---|
| **Artboard Name** | `UltronArtboard` |
| **Canvas Size** | 500 × 500 px |
| **Origin** | Center (250, 250) |
| **Background Color** | Transparent / `#00000000` |
| **Coordinate Space** | `X: [-250, 250]`, `Y: [-250, 250]` |

### Artboard Node Hierarchy

```
UltronArtboard
├── Sphere_Root (Bone / Group)
│   ├── Atmosphere_Corona (Radial Gradient Shape, Feather: 32px)
│   ├── Sphere_Body (Path: Circle r: 160px, Fill: 3D Directional Radial Gradient)
│   ├── Subsurface_Core_Glow (Path: Circle r: 100px, Additive Glow)
│   ├── Equatorial_Seam (Path: Ellipse, 0.75px Subtle Stroke)
│   └── Fresnel_Rim (Path: Circle, Stroke: Grazing Angle Gradient)
│
├── Face_Root (Bone: Driven by Spherical Gaze Projection & Head Tilt)
│   ├── Brow_Group
│   │   ├── Brow_Left (Path: Line, Rotation: leftBrowAngle, Y: browY)
│   │   └── Brow_Right (Path: Line, Rotation: rightBrowAngle, Y: browY)
│   │
│   ├── Eyes_Group (Translation: Spherical Gaze Offset X/Y)
│   │   ├── Eye_Left (Group, Rotation: leftTilt, X: -24px)
│   │   │   ├── Left_Aperture_Clip (Path: Rounded Pill 18x46 r:9)
│   │   │   │   ├── Base_Fill (Linear Gradient: White -> Cyan)
│   │   │   │   ├── Pupil_Bar (Path: Optical Slit 5x30)
│   │   │   │   └── Core_Light (Accent Dot)
│   │   │   ├── Eyelid_Top_Left (Path: Curved Dropdown Lid)
│   │   │   └── Eyelid_Bot_Left (Path: Curved Rise Lid)
│   │   │
│   │   └── Eye_Right (Group, Rotation: rightTilt, X: +24px)
│   │       ├── Right_Aperture_Clip (Path: Rounded Pill 18x46 r:9)
│   │       │   ├── Base_Fill (Linear Gradient: White -> Cyan)
│   │       │   ├── Pupil_Bar (Path: Optical Slit 5x30)
│   │       │   └── Core_Light (Accent Dot)
│   │       ├── Eyelid_Top_Right (Path: Curved Dropdown Lid)
│   │       └── Eyelid_Bot_Right (Path: Curved Rise Lid)
│   │
│   └── Mouth_Group (Y: +48px)
│       └── Mouth_Path (Dynamic acoustic aperture modulated by ElevenLabs amplitude)
│
└── Accessories_Group
    ├── Working_Spinner (Arc Path, Angle driven by accessoryPhase)
    ├── Search_Scanner (Horizontal Laser Line + Reticle, Y driven by scanPhase)
    ├── Voice_Brackets (Left & Right Chevron Nodes, X offset driven by amplitude)
    ├── Generating_Matrix (Rotating Diamond Node + Core Spark)
    ├── Alert_Crest (Chevron Crest above brows)
    └── Sleep_Z (Floating glyph paths)
```

---

## 3. State Machine Specification: `ULTRON_SM`

The State Machine is named **`ULTRON_SM`**.

### Inputs Contract

| Input Name | Type | Range / Values | Description |
|---|---|---|---|
| `state` | Number | `0 .. 19` | Numeric State ID (0: idle, 1: listening, 2: thinking, etc.) |
| `gazeX` | Number | `-1.0 .. 1.0` | Horizontal gaze offset (spherical projection) |
| `gazeY` | Number | `-1.0 .. 1.0` | Vertical gaze offset (spherical projection) |
| `energy` | Number | `0.0 .. 1.0` | Internal character energy & core pulse |
| `amplitude` | Number | `0.0 .. 1.0` | Real-time audio amplitude (ElevenLabs vocal stream) |
| `attention` | Number | `0.0 .. 1.0` | Attentiveness factor |
| `isListening` | Boolean | `true / false` | True when microphone active |
| `isSpeaking` | Boolean | `true / false` | True when vocalization active |
| `isFocused` | Boolean | `true / false` | True during concentrated cognition |
| `boot` | Trigger | — | Triggers power-on sequence |
| `success` | Trigger | — | Triggers positive celebratory pulse |
| `warning` | Trigger | — | Triggers caution pulse |
| `error` | Trigger | — | Triggers disruption pulse |
| `alert` | Trigger | — | Triggers high threat/attention posture |
| `reconnect` | Trigger | — | Triggers reconnection retry loop |
| `shutdown` | Trigger | — | Triggers power-down sequence |
