# ULTRON — OFFICIAL RELEASE MANIFEST
**Application Version:** 0.1.0  
**Product Name:** ULTRON  
**Build Date:** 2026-10-03  
**Target Platform:** Windows 10 / 11 (x86_64 / AMD64)  
**CI/CD Pipeline:** GitHub Actions Windows Runner  
**Provenance Verification:** SHA256 Immutable Digest  
**Git Commit:** `8a99c02fb5cf441c066a041a9dd5d957d4e87262`  

---

## 1. Distribution Artifacts & Checksums

| Artifact | File Name | Size | SHA256 Digest |
| :--- | :--- | :--- | :--- |
| **Primary Setup Installer** | `Ultron-Setup-0.1.0.py` | 79.86 MB | `74d13e560a41883ea07f516d9914fbbe96ecd6953ece68f9824ac67a53fcbe07` |
| **Portable Standalone Bundle** | `Ultron-v0.1.0-windows-x64.zip` | 59.93 MB | `ab09277b95038797ab76fabf4782042600f13fe044992fda3e66dc0acae28687` |
| **Executable Binary** | `ultron.exe` | 22.09 MB | `a77892dc6b5a9855a74ceb4ec090d1800cfec808c80d3ead4eb8770bfb603a92` |
| **Software Bill of Materials** | `sbom.json` | 0.23 MB | `48e4ca6477cff27750119d96f8b27e4531d583c10385d0882c5f7c22019d8f1f` |

---

## 2. Security & Compliance Verification

- **Repository Secret Audit:** PASSED (Zero detected API keys, tokens, or credentials)
- **Artifact Quarantine Scan:** PASSED (Compiled PE binary tree inspected for high-entropy tokens)
- **Regression Test Baseline:** 256/256 Tests Passed (Phases 5–11 + Onboarding)
- **Release Gating:** Fail-closed security validation
- **Local Isolation Guarantee:** Zero dependencies on repository checkout, developer Python, or Git.

---

## 3. Core Runtime Dependencies

- `google-genai` (2.28.0)
- `sounddevice` (0.5.6)
- `numpy` (2.4.2)
- `pillow` (12.1.0)
- `pywin32` (312)
- `psutil` (7.2.2)
- `requests` (2.32.5)
- `websockets` (16.0)
- `pydantic` (2.12.5)
