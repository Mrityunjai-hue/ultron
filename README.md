<div align="center">

# ULTRON
### Sovereign Realtime Voice AI Desktop Agent for Windows

[![Windows 10/11](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-3776AB?logo=python&logoColor=white)](https://python.org)
[![Gemini Live](https://img.shields.io/badge/Model-Gemini%202.5%20Live-8E75B2?logo=google&logoColor=white)](https://ai.google.dev)
[![Safety 3-Tier](https://img.shields.io/badge/Security-3--Tier%20Gateway-10B981)](#safety-model)
[![Tests Passing](https://img.shields.io/badge/Tests-265%2F265%20Passed-10B981)](#development)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

<br/>

<img src="docs/assets/hero.jpg" alt="ULTRON Native Desktop Presence" width="100%" style="border-radius: 12px; box-shadow: 0 16px 40px rgba(0,0,0,0.6);" />

<br/><br/>

| ⚡ Gemini Live | 🎙️ Realtime Voice | 💻 Local Tools | 🛡️ Safety First |
| :---: | :---: | :---: | :---: |
| Native Bidirectional WebSockets via `gemini-2.5-flash-native-audio` | ~15.5ms Local Barge-In Interruption & 32ms Audio Frame Streaming | Direct Win32 Desktop Control & CDP Browser Automation | 3-Tier Security Gateway & Single-Use Cryptographic Auth Tokens |

</div>

<br/>

---

## 📖 Table of Contents

- [What is ULTRON?](#-what-is-ultron)
- [Product Gallery](#-product-gallery)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [How It Works](#-how-it-works)
  - [1. Realtime Audio Loop](#1-realtime-audio-loop)
  - [2. Sub-50ms Barge-In Interruption](#2-sub-50ms-barge-in-interruption)
  - [3. The Singularity Crease Presence UI](#3-the-singularity-crease-presence-ui)
- [Safety Model](#-safety-model)
- [Tasks & Browser Automation](#-tasks--browser-automation)
- [Development](#-development)
- [Release Engineering](#-release-engineering)
- [Security & Privacy](#-security--privacy)
- [Contributing](#-contributing)

---

## 🌌 What is ULTRON?

**ULTRON** is not a web app in a browser tab or an Electron wrapper. It is a **sovereign, native Windows desktop AI agent** engineered from the ground up for instantaneous voice communication, autonomous multi-step desktop task planning, and zero-compromise security.

Living as an obsidian liquid glass dynamic presence anchored to your screen bezel, ULTRON provides:

- **True Bidirectional Conversational Streaming**: Speak naturally and interrupt at any millisecond with **~15.5ms local barge-in response** without turn delays or latency lags.
- **Autonomous Multi-Step Task Execution**: Decomposes complex human intents (*"Open Chrome, navigate to GitHub, extract issues, and summarize to a file"*) into verified, dependency-resolved task graphs.
- **Pure Native Win32 Performance**: Consumes **<0.2% CPU** at idle and **~85 MB RAM** in standalone Windows x64 execution using Win32 layered windows (`WS_EX_LAYERED`) and GDI+ rendering.
- **Zero-Trust Security Boundary**: 3-tier execution policy (`SAFE`, `CONFIRM_REQUIRED`, `BLOCKED`) where destructive file operations require single-use HMAC-SHA256 confirmation tokens. Shell access (`cmd`, `powershell`, `bash`) is permanently blocked.

---

## 🖼️ Product Gallery

ULTRON features the **Liquid Onboarding Experience**: a seamless transformation where the compact top-bezel notch physically deforms and expands downward into an obsidian configuration surface, guides the user through setup, and collapses back into the resting notch.

<div align="center">

| 1. Resting Top Notch | 2. Liquid Downward Expansion |
| :---: | :---: |
| <img src="docs/assets/01_resting_notch.png" width="380" /> | <img src="docs/assets/02_expansion_beginning.png" width="380" /> |

| 3. Step 01: Owner Identity | 4. Step 02: Conversational Addressing |
| :---: | :---: |
| <img src="docs/assets/03_step01_owner.png" width="380" /> | <img src="docs/assets/04_step02_addressing.png" width="380" /> |

| 5. Step 03: Assistant Identity | 6. Step 04: Voice & Response Style |
| :---: | :---: |
| <img src="docs/assets/05_step03_identity.png" width="380" /> | <img src="docs/assets/06_step04_interaction.png" width="380" /> |

| 7. Step 05: Privacy & Local Memory | 8. Step 06: Startup & Finish |
| :---: | :---: |
| <img src="docs/assets/07_step05_privacy.png" width="380" /> | <img src="docs/assets/08_step06_startup.png" width="380" /> |

| 9. Liquid Collapse Sequence | 10. Restored Resting Notch |
| :---: | :---: |
| <img src="docs/assets/09_collapse_beginning.png" width="380" /> | <img src="docs/assets/10_notch_restored.png" width="380" /> |

</div>

---

## 🏛️ Architecture

```mermaid
flowchart TD
    subgraph AudioEngine [" 🎙️ Realtime Audio Pipeline "]
        MIC["Microphone (16kHz PCM16 Mono)"] --> AudioIn["Audio Input Ring Buffer\n(32ms / 512 Sample Frames)"]
        AudioIn --> BargeInDetector["Local RMS Energy Detector\n(~9.59ms Detection)"]
        AudioOut["Audio Output Ring Buffer\n(24kHz PCM16 Mono)"] --> Speaker["Speaker Output"]
        BargeInDetector -- "Immediate Flush\n(~5.96ms)" --> AudioOut
    end

    subgraph GeminiStream [" 🧠 Gemini Live Core "]
        AudioIn --> BidiSession["Google Gemini Live Bidi Session\n(gemini-2.5-flash-native-audio)"]
        BidiSession --> AudioOut
        BidiSession --> Transcript["Transcript Stream"]
        BidiSession --> ToolCall["Tool Call Request"]
    end

    subgraph MemoryLayer [" 💾 Memory & Context "]
        Transcript --> SessionMem["Bounded Turn Memory\n(Pronoun Resolution Tracker)"]
        Transcript --> SemanticMem["Long-Term Semantic Graph\n(%LOCALAPPDATA%/ULTRON/memory/)"]
    end

    subgraph SafetyGateway [" 🛡️ 3-Tier Security Gateway "]
        ToolCall --> Classifier{"Policy\nClassification"}
        Classifier -- "Tier 1: SAFE" --> Executor["Local Tool Executor"]
        Classifier -- "Tier 2: CONFIRM_REQUIRED" --> Vault["Confirmation Vault\n(HMAC-SHA256 Single-Use Token)"]
        Classifier -- "Tier 3: BLOCKED" --> Reject["Security Exception\n(Shells, Injections, System Paths)"]
        Vault -- "User Confirmed" --> Executor
    end

    subgraph PresenceUI [" 🖥️ Native Windows Presence Overlay "]
        BargeInDetector --> Choreographer["Spring Kinetic Choreographer\n(Exact Damped Harmonic Oscillator)"]
        Transcript --> Choreographer
        Executor --> Choreographer
        Choreographer --> LayeredWin["Win32 Layered Overlay Window\n(WS_EX_LAYERED | WS_EX_TOPMOST)"]
    end

    Executor --> BidiSession
```

---

## 📦 Installation

### Option A: Standalone Windows Installer (Recommended)
Download the latest standalone distribution from [**GitHub Releases**](https://github.com/Mrityunjai-hue/ultron/releases):
- **Portable ZIP**: `Ultron-v0.1.0-windows-x64.zip` (Extract and run `ultron.exe`)
- **Setup Package**: `Ultron-Setup-0.1.0.py`

*Zero external dependencies on Python, Git, or compilers required for standalone binary.*

### Option B: Build & Run from Source
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

## 🚀 Quick Start

### 1. Store Your Gemini API Key
ULTRON stores credentials locally using hardware-bound **Windows DPAPI** encryption:
```powershell
# Store API Key securely in Windows DPAPI vault (Never stored in plaintext)
python -m ultron.main --set-api-key "AIzaSyYourApiKeyHere"
```
*(Alternatively, create a local `.env` file containing `GEMINI_API_KEY="AIzaSy..."` for development).*

### 2. Launch ULTRON
```powershell
# Launch full cinematic experience with dynamic desktop presence
python run.py

# Launch in voice-only CLI mode (No overlay window)
python -m ultron.main --no-ui

# Run system health check
python -m ultron.main --health

# Run machine-readable diagnostics
python -m ultron.main --diagnostics

# Run performance & latency benchmark
python -m ultron.main --benchmark
```

---

## ⚙️ Configuration

User preferences are persisted atomically to `%LOCALAPPDATA%\ULTRON\config\user_config.json`, completely isolated from application binaries:

```json
{
  "owner_name": "<REDACTED>",
  "pronunciation_hint": "<REDACTED>",
  "addressing_name": "<REDACTED>",
  "assistant_name": "ULTRON",
  "preferred_language": "English (US)",
  "voice_preference": "Puck",
  "response_style": "Concise & Authoritative",
  "presence_enabled": true,
  "allow_explicit_memory": true,
  "start_with_windows": false,
  "first_run_completed": true
}
```

### Physical Storage Boundaries
| Category | File Path | Security Guarantee |
| :--- | :--- | :--- |
| **Application Binaries** | `C:\Program Files\ULTRON\` | Read-only application code |
| **User Configuration** | `%LOCALAPPDATA%\ULTRON\config\user_config.json` | Atomic swap write, corruption self-healing |
| **Encrypted Credentials** | `%LOCALAPPDATA%\ULTRON\config\credentials.dpapi` | User-bound Windows DPAPI encryption |
| **Task Checkpoints & Logs** | `%LOCALAPPDATA%\ULTRON\tasks\` | Append-only execution journal & evidence chains |
| **Semantic Memory** | `%LOCALAPPDATA%\ULTRON\memory\` | Bounded facts store with active regex secret scrub |
| **Sanitized Logs** | `%LOCALAPPDATA%\ULTRON\logs\` | 10MB rotating logs with real-time secret redaction |
| **Runtime Cache** | `%LOCALAPPDATA%\ULTRON\cache\` | Temporary cache & CDP browser session profiles |

---

## 🔬 How It Works

### 1. Realtime Audio Loop
- **Input Stream**: Captures microphone audio at `16,000 Hz` (16-bit PCM Mono) in `32ms` frames (512 samples) and streams directly to Gemini Live WebSockets with zero disk buffering.
- **Output Stream**: Receives synthesized speech at `24,000 Hz` (16-bit PCM Mono) and feeds an adaptive ring buffer with continuous underflow protection.

### 2. Sub-50ms Barge-In Interruption
When you speak while ULTRON is responding, a dual-tier interruption triggers:
1. **Local RMS Energy Detector**: Senses voice onset in **~9.59ms** and flushes local hardware audio playback in **~5.96ms** (~15.55ms total local latency).
2. **Server-Side Interruption Signal**: Sends client cancellation to the Gemini Live session, halting cloud audio generation without turn delay.

### 3. The Singularity Crease Presence UI
The top-bezel overlay window uses **underdamped harmonic oscillator spring physics**:
$$\ddot{x} + 2\zeta\omega_0 \dot{x} + \omega_0^2 (x - x_{\text{target}}) = 0$$
- **Obsidian Dark Material**: Solid capsule attaching seamlessly to the top screen bezel.
- **Parametric Laser Crease**: Incandescent core that breathes during listening, pulses while thinking, and undulates with voice amplitude during speaking.
- **Non-Rectangular Click-Through**: Transparent areas pass mouse clicks to background applications via `WM_NCHITTEST` (`HTTRANSPARENT`), capturing input only on opaque controls (`HTCLIENT`).

---

## 🛡️ Safety Model

ULTRON operates under a **3-Tier Local Security Policy** (`SAFE`, `CONFIRM_REQUIRED`, `BLOCKED`):

| Tool Category | Tools | Safety Tier | Enforcement Mechanism |
| :--- | :--- | :--- | :--- |
| **System Telemetry** | `get_current_time`, `get_system_status` | `SAFE` | Read-only telemetry, immediate execution. |
| **App Launch** | `open_app`, `windows_open_app` | `SAFE` | Launched via safe Win32 API without shell execution. |
| **File Read** | `read_file`, `list_directory` | `SAFE` | Sandboxed to workspace; rejects OS system folders. |
| **File Modification / Delete** | `write_file`, `delete_file`, `move_file` | `CONFIRM_REQUIRED` | Single-use cryptographic token required. |
| **App Termination** | `close_app`, `windows_close_app` | `CONFIRM_REQUIRED` | Confirmation token required; critical system processes protected. |
| **File Download** | `chrome_download_file` | `CONFIRM_REQUIRED` | Sandboxed to workspace; blocks executable extensions (`.exe`, `.bat`, `.ps1`). |
| **Arbitrary Shells** | `cmd`, `powershell`, `pwsh`, `bash`, `wsl` | `BLOCKED` | Permanently rejected by static analysis. |
| **Command Injection** | `&`, `\|`, `;`, `>`, `<`, `` ` ``, `$`, `\n` | `BLOCKED` | Rejected before execution. |

### Cryptographic Confirmation Tokens
Destructive actions generate a unique token:
$$\text{Token} = \text{HMAC-SHA256}(\text{Tool} \parallel \text{Target} \parallel \text{SessionID} \parallel \text{Salt})$$
- Valid for 60 seconds (TTL expiration).
- Single-use only (burned immediately upon evaluation).
- Replay and parameter tampering immune.

---

## 🧭 Tasks & Browser Automation

ULTRON features an integrated autonomous task planning and execution engine:

- **Goal Planner**: Converts high-level natural language goals into acyclic dependency graphs (DAGs).
- **Chrome DevTools Protocol (CDP)**: Controls existing or headless browser instances to perform authentic navigation, DOM extraction, text entry, and clicking.
- **Mandatory Verification**: Every action step undergoes automated post-action evidence verification before proceeding to dependent steps.

---

## 💻 Development

### Running the Test Suite
The repository includes **265 comprehensive tests** covering core runtime, streaming, tools, tasks, browser CDP, adversarial security, onboarding, and release packaging:

```powershell
# Run full test suite
python -m pytest tests -v

# Run specific test modules
python -m pytest tests/test_phase10_adversarial.py -v     # 80 Adversarial Security Tests
python -m pytest tests/test_phase11_onboarding.py -v      # 20 Liquid Onboarding Tests
python -m pytest tests/test_phase11_release_pipeline.py -v # 9 Supply Chain Security Tests
```

### Running the Automated Secret Scanner
```powershell
python scripts/secret_scanner.py . --fail-on-findings
```

---

## 🚢 Release Engineering

The release supply chain enforces an immutable pipeline from tagged commit to signed Windows binary:

```powershell
# 1. Compile standalone PE binary and scan artifacts
python scripts/build_windows_dist.py

# 2. Generate self-contained setup installer
python scripts/build_installer.py

# 3. Compute SHA256 checksums and release manifests
python scripts/generate_release_manifest.py

# 4. Verify clean sandbox installation E2E
python scripts/verify_clean_install_e2e.py
```

### GitHub Actions Release Automation
Releases are triggered exclusively via version tags (`v0.1.0`):
- 40-character commit SHA pinned actions (`actions/checkout`, `actions/setup-python`, `actions/attest-build-provenance`).
- Automatic generation of CycloneDX 1.4 SBOM (`sbom.json`) and SHA256 digests (`SHA256SUMS.txt`).
- GitHub Artifact Build Provenance Attestation.

---

## 🔒 Security & Privacy

1. **Local-Only User Data**: Your name, conversational preferences, memories, task history, and encryption keys never leave your machine.
2. **Zero Plaintext Credentials**: API keys are encrypted with Windows DPAPI.
3. **Redacted Diagnostics**: All system diagnostics, health checks, and logs omit personal identifiers and secret values.
4. **No Raw Audio Storage**: Microphone input and speaker playback are processed strictly in volatile memory.

---

## 🤝 Contributing

Contributions are welcome! Please ensure that:
1. All changes maintain **100% pass rate** on the 265-test suite (`python -m pytest`).
2. The automated secret scanner passes with **0 findings** (`python scripts/secret_scanner.py .`).
3. Security invariants (3-tier safety gateway, confirmation tokens, shell blocking) are strictly preserved.

---

<div align="center">

**ULTRON — Sovereign Windows AI Desktop Agent**  
*Engineered for speed, built for autonomy, designed for privacy.*

</div>
