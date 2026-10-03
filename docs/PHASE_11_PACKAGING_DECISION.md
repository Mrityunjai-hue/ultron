# ULTRON — PHASE 11: PACKAGING & DISTRIBUTION DECISION MATRIX

## 1. Context & Architectural Requirements

ULTRON requires:
- Low-latency (<50ms) bidirectional WASAPI / PortAudio streaming.
- Native Win32 GDI layered transparent overlay (`WS_EX_LAYERED`, `UpdateLayeredWindow`, non-rectangular click-through hit testing).
- Chrome CDP process spawning and loopback socket control.
- Atomic disk persistence in `%LOCALAPPDATA%/ULTRON/`.
- Non-admin Windows startup registration (`HKCU\...\Run`) with crash loop circuit-breaking.
- Deterministic, verifiable checksums and reproducible distribution.

---

## 2. Packaging Options Evaluation

| Criterion | Option A: Portable Standalone (`.zip`) | Option B: Traditional Windows Installer (`.exe`) | Option C: MSIX / Modern App Package | Option D: Hybrid (Installer + Portable) |
| :--- | :--- | :--- | :--- | :--- |
| **Win32 Layered Overlay** | **Full (Native)** | **Full (Native)** | Restricted / Containerized | **Full (Native)** |
| **Low-Latency WASAPI** | **Full (<10ms)** | **Full (<10ms)** | Sandboxed / Routing overhead | **Full (<10ms)** |
| **Browser CDP Control** | **Unconstrained** | **Unconstrained** | AppContainer loopback blocked | **Unconstrained** |
| **Start Menu / Shortcuts** | Manual | **Automated** | System Managed | **Automated** |
| **Startup Registration** | Manual | **Automated (HKCU)** | AppX Startup Extension | **Automated (HKCU)** |
| **Clean Uninstall** | Manual directory delete | **Deterministic uninstaller** | System managed | **Deterministic uninstaller** |
| **User Data Isolation** | Full (`%LOCALAPPDATA%`) | **Full (`%LOCALAPPDATA%`)** | Virtualized VFS redirect | **Full (`%LOCALAPPDATA%`)** |
| **Code Signing / Provenance**| SHA256 / Authenticode | **SHA256 / Authenticode** | Mandatory Store/Sign cert | **SHA256 / Authenticode** |

---

## 3. Authoritative Packaging Decision

**SELECTED STRATEGY: Hybrid Distribution Architecture (Option D)**

1. **Primary Distribution Artifact:** Self-Contained Windows Installer (`Ultron-Setup-0.1.0.exe`).
   - Installs standalone, hermetic application payload to `%LOCALAPPDATA%\Programs\ULTRON` (per-user, no UAC elevation required).
   - Creates Start Menu shortcut and optional Desktop icon.
   - Registers non-looping startup entry if selected.
   - Provides clean, standard `unins000.exe` uninstaller.
2. **Secondary Distribution Artifact:** Portable Archive (`Ultron-v0.1.0-windows-x64.zip`).
   - Self-contained directory for power users or air-gapped environments.
   - Zero installation required. Resolves user data to `%LOCALAPPDATA%\ULTRON`.
3. **Rejection of MSIX:**
   - MSIX's virtualized filesystem (VFS) and AppContainer network loopback isolation interfere with low-level CDP automation and Win32 layered click-through hit testing. Traditional per-user Win32 installer provides superior security, predictability, and auditability.
