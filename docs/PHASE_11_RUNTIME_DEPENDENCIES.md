# ULTRON — PHASE 11: RUNTIME DEPENDENCY AUDIT & SBOM SPECIFICATION

## 1. Dependency Philosophy

ULTRON prioritizes **minimal attack surface**, **zero unvetted dependencies**, and **strictly pinned packages** for all production distributions. Development dependencies (`pytest`, `pyinstaller`) are strictly partitioned from the production runtime.

---

## 2. Production Runtime Inventory

| Package | Pinned Version | License | Security Evaluation & Runtime Justification |
| :--- | :--- | :--- | :--- |
| `google-genai` | `2.28.0` | Apache-2.0 | Official Google GenAI SDK for asynchronous bidirectional Gemini Live streaming over TLS WebSocket. Zero telemetry leakage. |
| `sounddevice` | `0.5.6` | MIT | Lightweight PortAudio wrapper for high-performance non-blocking PCM16 audio input and output streams on Windows WASAPI / DirectSound. |
| `numpy` | `2.4.2` | BSD-3-Clause | Hardware-accelerated vectorized audio RMS computation and frame pacing for sub-50ms barge-in detection. |
| `pillow` | `12.1.0` | HPND | 32-bit RGBA pixel rendering and composition for native Win32 `UpdateLayeredWindow` desktop presence overlay. |
| `pywin32` | `312` | PSF | Direct Win32 API bindings (`win32gui`, `win32con`, `win32api`, `winreg`) for non-rectangular click-through hit testing and startup registry control. |
| `psutil` | `7.2.2` | BSD-3-Clause | Process health monitoring, safe resource diagnostics, and single-instance PID tracking. |
| `requests` | `2.32.5` | Apache-2.0 | Outbound HTTP requests for tool integrations with strict timeout controls. |
| `websockets` | `16.0` | BSD-3-Clause | Async WebSocket protocol implementation for internal and external tool telemetry. |
| `pydantic` | `2.12.5` | MIT | High-performance schema validation for task models and goal specifications. |
| `python-dotenv`| `1.2.2` | BSD-3-Clause | Development-only fallback environment loader (inactive in frozen release builds). |

---

## 3. Build & Packaging Dependencies

| Package | Version Range | Purpose |
| :--- | :--- | :--- |
| `pyinstaller` | `>=6.4.0` | Hermetic PE binary creation and CPython runtime bundling. |
| `pytest` | `9.1.1` | Regression and productization test runner. |
| `anyio` | `4.12.1` | Structured asynchronous concurrency harness for test suites. |
| `setuptools` | `>=68.0.0` | Standard package metadata build backend. |

---

## 4. Software Bill of Materials (SBOM)

An automated SBOM manifest is generated at build time (`build/sbom.json`), conforming to standard CycloneDX / SPDX JSON schema without containing any private paths, usernames, or sensitive keys.
