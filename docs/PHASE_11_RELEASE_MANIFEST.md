# ULTRON — OFFICIAL RELEASE MANIFEST
**Application Version:** 0.1.0  
**Product Name:** ULTRON  
**Build Date:** 2026-10-03  
**Target Platform:** Windows 10 / 11 (x86_64 / AMD64)  
**CI/CD Pipeline:** GitHub Actions Windows Runner  
**Provenance Verification:** SHA256 Immutable Digest  
**Git Commit:** `N/A (Release Distribution Build)`  

---

## 1. Distribution Artifacts & Checksums

| Artifact | File Name | Size | SHA256 Digest |
| :--- | :--- | :--- | :--- |
| **Primary Setup Installer** | `Ultron-Setup-0.1.0.py` | N/A | `N/A` |
| **Portable Standalone Bundle** | `Ultron-v0.1.0-windows-x64.zip` | 59.91 MB | `9cde70382b0efc7b2f210cf3d2ad5a091bfd3d3164c92a4300ce08a5bdeb6c1e` |
| **Executable Binary** | `ultron.exe` | 22.08 MB | `a7f0db42b8a1589aafada4fe6596f44b7a6fe9268bbe06e4ade1b44c931ebc98` |
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
