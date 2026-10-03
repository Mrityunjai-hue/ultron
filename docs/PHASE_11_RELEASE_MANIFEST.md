# ULTRON — OFFICIAL RELEASE MANIFEST
**Application Version:** 0.1.0  
**Product Name:** ULTRON  
**Build Date:** 2026-10-03  
**Target Platform:** Windows 10 / 11 (x86_64 / AMD64)  
**CI/CD Pipeline:** GitHub Actions Windows Runner  
**Provenance Verification:** SHA256 Immutable Digest  
**Git Commit:** `a2cc6a25105fc5c2f954009f75a7ead39d0c2463`  

---

## 1. Distribution Artifacts & Checksums

| Artifact | File Name | Size | SHA256 Digest |
| :--- | :--- | :--- | :--- |
| **Primary Setup Installer** | `Ultron-Setup-0.1.0.py` | 79.87 MB | `f5c6261df4b16905a8ef1483481ca6db92d32a0034bc38e2c3e70eb6f391431b` |
| **Portable Standalone Bundle** | `Ultron-v0.1.0-windows-x64.zip` | 59.93 MB | `22065614b2ff2d4201005131749ab259e24b75206a0fc3c773fce30a62988fb1` |
| **Executable Binary** | `ultron.exe` | 22.09 MB | `7c97f89f607f4d2116c22ec77b6208a18cb3856cb6033bf6ac87ef952450a6e4` |
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
