# ULTRON v2.0 — Artboard Hierarchy & Vector Node Rig

```
UltronArtboard (1024 × 1024 px)
├── WorldRoot (Group)
│   ├── ChassisGroup (Transform: Position [512, 512], Anchor [0.5, 0.5])
│   │   ├── OuterFramePlate (Vector Path - Hexagonal Bevel Silhouette)
│   │   ├── BrowPlatesGroup
│   │   │   ├── LeftBrowPlate (Vector Path - Angular Trapezoid, Bone IK Rotator)
│   │   │   └── RightBrowPlate (Vector Path - Mirrored Angular Trapezoid)
│   │   ├── CheekPlatesGroup
│   │   │   ├── LeftCheekPlate (Vector Path)
│   │   │   └── RightCheekPlate (Vector Path)
│   │   └── JawMechanismGroup
│   │       └── ChinPlate (Vector Path - Chiseled Lower Shield)
│   │
│   ├── OpticalChambersGroup (Clipped inside Eye Sockets)
│   │   ├── LeftEyeSocket (Clip Path)
│   │   │   ├── LeftApertureIris (Vector Star/Ring Multi-blades)
│   │   │   ├── LeftPupilCore (Vector Circle with Radial Gradient Glow)
│   │   │   └── LeftPupilGazeConstraint (IK Target [gazeX, gazeY])
│   │   │
│   │   └── RightEyeSocket (Clip Path)
│   │       ├── RightApertureIris (Vector Star/Ring Multi-blades)
│   │       ├── RightPupilCore (Vector Circle with Radial Gradient Glow)
│   │       └── RightPupilGazeConstraint (IK Target [gazeX, gazeY])
│   │
│   └── AcousticGroup (Modulated by voiceAmplitude)
│       ├── RadialWaveEmitters (8 Vector Arc Ribbons radiating outwards)
│       └── CentralPulseAura (Mesh Gradient / Radial Falloff)
```

## Node Constraints & Transform Bindings
1. **LeftPupilGazeConstraint / RightPupilGazeConstraint**:
   - Translate X: Bound to `gazeX * 42 px`.
   - Translate Y: Bound to `gazeY * 28 px`.
   - Dynamic damping: 120ms spring interpolation.
2. **BrowPlatesGroup**:
   - Rotate Z: Modulated by `moodId`:
     - CALM: `0 deg`
     - ATTENTIVE: `-2 deg`
     - FOCUSED: `+5 deg` (angular focus)
     - CONCERNED: `-6 deg`
     - WARNING: `+8 deg`
3. **RadialWaveEmitters**:
   - Scale X & Y: `1.0 + (voiceAmplitude * 0.45)`.
   - Opacity: `0.2 + (voiceAmplitude * 0.8)`.
