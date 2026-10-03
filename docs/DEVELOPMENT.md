# ULTRON Developer Guide

This document covers local setup, test execution, CLI commands, and code layout for contributing to ULTRON.

---

## 1. Environment Setup

```powershell
# 1. Clone repository
git clone https://github.com/Mrityunjai-hue/ultron.git
cd ultron

# 2. Create isolated virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-build.txt
```

---

## 2. CLI Capabilities & Runtime Modes

ULTRON provides built-in CLI commands via `ultron.main`:

```powershell
# Launch full cinematic experience (Top notch + dynamic presence overlay)
python run.py

# Launch in voice-only CLI mode (No overlay window)
python -m ultron.main --no-ui

# Run comprehensive system health check
python -m ultron.main --health

# Output machine-readable diagnostics report (redacted)
python -m ultron.main --diagnostics

# Run performance and latency benchmark
python -m ultron.main --benchmark

# Store Gemini API Key securely in Windows DPAPI vault
python -m ultron.main --set-api-key "your_api_key_here"

# Register / Unregister Windows startup
python -m ultron.main --enable-startup
python -m ultron.main --disable-startup
```

---

## 3. Running the Test Suite

The regression test suite covers core runtime, audio streaming, tools, tasks, browser automation, adversarial security, onboarding, and release packaging:

```powershell
# Run complete test suite
python -m pytest tests -v

# Run specific test modules
python -m pytest tests/test_phase10_adversarial.py -v       # 80 Adversarial Security Tests
python -m pytest tests/test_phase11_onboarding.py -v        # 20 Liquid Onboarding Tests
python -m pytest tests/test_phase11_release_pipeline.py -v   # 9 Supply Chain Security Tests
```

---

## 4. Running the Secret Discovery Scanner

The repository includes an automated scanner to prevent accidental credential leakage:

```powershell
python scripts/secret_scanner.py . --fail-on-findings
```

---

## 5. Development & Visual Utility Scripts

Organized utility scripts reside in `scripts/`:
- **`scripts/build_windows_dist.py`**: Compiles standalone Windows executable with PyInstaller.
- **`scripts/build_installer.py`**: Generates self-contained Windows setup package.
- **`scripts/generate_release_manifest.py`**: Computes SHA256 hashes and release manifests.
- **`scripts/secret_scanner.py`**: Automated repository secret detector.
- **`scripts/verify_clean_install_e2e.py`**: Sandboxed end-to-end installation test.
- **`scripts/visual/`**: Kinetic animation and screenshot generation utilities.
- **`scripts/verification/`**: Standalone live verification harnesses.
- **`scripts/dev/`**: Development prototypes and mock servers.
