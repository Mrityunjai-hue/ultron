# ULTRON v2.0 — Animation Timeline & Motion Map

## Key Timelines & Interpolation Rules

| Timeline Name | Duration | Loop Mode | Easing Curve | Description |
| :--- | :--- | :--- | :--- | :--- |
| `idle_breath` | 3600 ms | Loop | CubicBezier(0.4, 0.0, 0.2, 1.0) | Gentle chassis elevation and pupil luminous pulsing |
| `wake_snap` | 420 ms | One-Shot | Back-Out(1.4) | Sharp mechanical eye snap open upon wake word detection |
| `sleep_recede` | 650 ms | One-Shot | CubicBezier(0.4, 0.0, 1.0, 1.0) | Eye aperture shutter close down to notch standby line |
| `thinking_orbit`| 1800 ms| Loop | Linear | Continuous orbital scan of internal core optic |
| `executing_focus`| 1200 ms| Loop | CubicBezier(0.6, 0.05, 0.2, 0.9)| Mechanical micro-aperture calibration ticks |
| `speaking_react`| Dynamic | Driven | Direct RMS | Amplitude modulated acoustic wave expansion |
| `warning_strobe`| 800 ms | Loop | Steps(4) | Stroboscopic amber pulse during confirmation needed |
| `offline_dim` | 1000 ms| Freeze | Ease-Out | Slow fade of core energy into sleep |
| `glitch_fault` | 350 ms | One-Shot | Elastic-Out | Fault twitch upon unrecoverable tool or network failure |

---

## Kinematic Constraints
- **Maximum Gaze Velocity**: `180 px/sec` to prevent unnatural visual snapping.
- **Pupil Shutter Range**: `0.2` (slit-focus) to `1.2` (wide dilation).
- **Acoustic Wave Max Radius**: `460 px` from artboard center.
