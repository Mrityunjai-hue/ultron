# ULTRON v2.0 — Rive State Machine Specification: `ULTRON_SM`

## State Machine Inputs
| Input Name | Type | Range | Description |
| :--- | :--- | :--- | :--- |
| `activity` | Number | `0 - 7` | Canonical Activity: 0=IDLE, 1=LISTENING, 2=THINKING, 3=EXECUTING, 4=RESPONDING, 5=ERROR, 6=OFFLINE, 7=RECONNECTING |
| `operationId` | Number | `0 - 5` | Active Tool: 0=none, 1=search_files, 2=read_file, 3=write_file, 4=app_control, 5=shell |
| `moodId` | Number | `0 - 5` | Emotional State: 0=CALM, 1=ATTENTIVE, 2=FOCUSED, 3=CURIOUS, 4=CONCERNED, 5=WARNING |
| `gazeX` | Number | `-1.0 to 1.0`| Horizontal optical tracking offset |
| `gazeY` | Number | `-1.0 to 1.0`| Vertical optical tracking offset |
| `attention` | Number | `0.0 to 1.0`| Sensory focus factor |
| `voiceAmplitude`| Number | `0.0 to 1.0`| Real-time ElevenLabs audio RMS amplitude |
| `onWake` | Trigger | — | Triggers wake expansion animation |
| `onSleep` | Trigger | — | Triggers notch collapse and ocular slumber |
| `onInterrupt` | Trigger | — | Immediate visual snap upon speech interruption |
| `onConfirmNeeded`| Trigger| — | Visual warning pulse for pending safety confirmation |
| `onActionComplete`| Trigger| — | Flash of mechanical resolution upon tool completion |

---

## State Machine Layers
### Layer 1: Canonical Activity Layer
- **State 0 (IDLE)**: Subtle breathing cycle (3.5s period). Low ambient ocular glow (30% intensity).
- **State 1 (LISTENING)**: Apertures dilate 15%. Outer acoustic rings activate with blue/amber tint.
- **State 2 (THINKING)**: Core orbits with high-frequency telemetry scan. Brow plates angle inward.
- **State 3 (EXECUTING)**: Optical beam locks onto center focal point. Secondary chassis rings tick mechanically.
- **State 4 (RESPONDING)**: Real-time acoustic flare modulated by `voiceAmplitude`. Apertures pulse in cadence.
- **State 5 (ERROR)**: Sudden chromatic aberration / glitch pulse. Color shifts to alert red/orange.
- **State 6 (OFFLINE)**: Eyes close/dim to desaturated titanium grey (`#4A4D54`). Breathing cycle ceases.
- **State 7 (RECONNECTING)**: Periodic faint heartbeat pulse waiting for backend socket.

### Layer 2: Gaze IK Blend Layer
- Continuous 2D blend tree mapping `[gazeX, gazeY]` directly to optical pupil constraints with non-linear spring damping.

### Layer 3: Mood Emotion Layer
- Modulates brow angle and eye aspect ratio:
  - `CALM`: Standard sovereign level.
  - `ATTENTIVE`: Eye aperture vertical expansion (+10%).
  - `FOCUSED`: Eye aperture narrows vertically (-15%), brow sharpens.
  - `CONCERNED`: Asymmetric brow slant, warning amber undertone.
  - `WARNING`: Rapid pulse, maximum contrast.

### Layer 4: Voice Amplitude Layer
- Driven additively by `voiceAmplitude` (`0.0 - 1.0`) during `activity == 4 (RESPONDING)`.
