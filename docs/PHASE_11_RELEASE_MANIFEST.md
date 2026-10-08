# ULTRON — OFFICIAL RELEASE MANIFEST
**Application Version:** 0.1.0  
**Product Name:** ULTRON  
**Build Date:** 2026-10-03  
**Target Platform:** Windows 10 / 11 (x86_64 / AMD64)  
**CI/CD Pipeline:** GitHub Actions Windows Runner  
**Provenance Verification:** SHA256 Immutable Digest  
**Git Commit:** `a5cc96de6a453a78f579cf5b6b381c5b19ca3fab`  

---

## 1. Distribution Artifacts & Checksums

| Artifact | File Name | Size | SHA256 Digest |
| :--- | :--- | :--- | :--- |
| **Primary Setup Installer** | `Ultron-Setup-0.1.0.py` | N/A | `N/A` |
| **Portable Standalone Bundle** | `Ultron-v0.1.0-windows-x64.zip` | N/A | `N/A` |
| **Executable Binary** | `ultron.exe` | 22.10 MB | `c7e1e1262e2332ed02a5a64b2e2e2d296188c481e010d0cb71e752eed47bdf5a` |
| **Software Bill of Materials** | `sbom.json` | N/A | `N/A` |

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
