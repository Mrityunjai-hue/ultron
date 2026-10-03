# ULTRON — PHASE 11: REPOSITORY & RUNTIME ARCHITECTURE AUDIT

## 1. Executive Summary

This document establishes the empirical, forensics-verified architecture audit of the **ULTRON** codebase prior to Phase 11 release engineering and distribution packaging. The audit maps all entrypoints, runtime boundaries, configuration models, credential flows, persistence subsystems, UI isolation layers, and packaging assumptions.

---

## 2. Entrypoint Forensics

| Entrypoint | File Path | Type | Role & Behavior |
| :--- | :--- | :--- | :--- |
| **CLI / Main Entrypoint** | `ultron/main.py` | Python Script / Win32 CLI | Initializes CLI parser, health check (`--health`), diagnostics (`--diagnostics`), performance benchmark (`--benchmark`), or launches `UltronRuntime`. |
| **Runtime Orchestrator** | `ultron/core/runtime.py` | Core Engine Class | Orchestrates audio input/output, Gemini Live bidirectional WebSocket session, state machine, task planning engine, and tool execution gateway. |
| **Desktop Presence UI** | `ultron/presence/window.py` | Win32 Layered Window | Native GDI/UpdateLayeredWindow 32-bit transparent overlay running on dedicated thread. Zero web browser dependency. Completely isolated from core runtime crashes. |
| **Tool Execution Gateway** | `ultron/tools/executor.py` | Execution Subsystem | Executes 4-tier security-gated tools (read-only, confirmed, side-effect, and destructive operations) with argument sanitization and timeout enforcement. |
| **Browser Controller** | `ultron/apps/chrome.py` | CDP Automation Subsystem | Gated Chrome DevTools Protocol automation with sandboxed isolated user data directory and safety bounds. |

---

## 3. Configuration & Credential Architecture

### 3.1 Separation of Concerns
1. **Immutable Application Configuration (`ultron/core/config.py`):**
   - Audio sample rates (16kHz in, 24kHz out, PCM16 mono).
   - Audio frame sizing (512 samples / 32ms frames).
   - Model identifier (`gemini-2.5-flash-native-audio-latest`).
   - Voice character (`Puck`).
   - Core system prompt instructions.
2. **Non-Sensitive User Configuration (`%LOCALAPPDATA%/ULTRON/config/settings.json`):**
   - UI presence position and visual mode.
   - Hotkey bindings.
   - Startup behavior preferences.
3. **Secrets & Credentials (`ultron/core/credentials.py`):**
   - Gemini API Key protected via **Windows DPAPI (Data Protection API) / Credential Manager**.
   - Development & CI fallback via `GEMINI_API_KEY` environment variable.
   - Decrypted only at the exact point of `genai.Client(api_key=...)` initialization.
   - Zero exposure to prompts, planners, memory, UI, logs, diagnostics, or persistence.
4. **Runtime State & Persistence (`%LOCALAPPDATA%/ULTRON/`):**
   - Task execution state, goals, plans, journal, and evidence chains.
   - Persistent memory JSON store.
   - Application rotating log files.

---

## 4. Local Filesystem Architecture (Production vs Development)

The installed production application MUST NOT depend on the Git repository, developer Python PATH, or repository-relative `.env` files.

### 4.1 Production Directory Hierarchy
```
%LOCALAPPDATA%/ULTRON/
├── config/
│   └── settings.json            # Non-sensitive user preferences
├── memory/
│   └── memory.json              # Long-term conversational memory
├── tasks/
│   ├── goal_*.json              # Checkpoint and active goal states
│   ├── evidence_*.json          # Verifiable execution evidence chains
│   └── journal.jsonl            # Append-only execution journal
├── logs/
│   ├── ultron.log               # Secret-sanitized rotating log (10MB max, 5 backups)
│   └── ultron_crash.log         # Sanitized crash forensics
└── cache/
    └── chrome_profile/          # Isolated browser automation profile
```

### 4.2 Application Binary Installation Directory
```
%LOCALAPPDATA%/Programs/ULTRON/  (or C:\Program Files\ULTRON)
├── ultron.exe                   # Self-contained Windows PE executable
├── ultron_cli.exe               # Console-attached diagnostic / CLI executable
├── resources/                   # Built-in visual assets / icons
├── LICENSE
└── unins000.exe                 # Clean Windows uninstaller
```

---

## 5. Security & Isolation Forensics

1. **Memory Isolation:** `ultron/memory/persistent.py` actively validates memory entries, refusing passwords, bearer tokens, API keys, and high-entropy secret patterns.
2. **Persistence Sanitization:** `ultron/tasks/persistence.py` recursively scrubs all keys and values against `SECRET_PATTERNS` prior to disk writing.
3. **Journal Scrubbing:** `ultron/tasks/journal.py` redacts any authorization tokens or credential keys from journal event metadata.
4. **UI Isolation:** `ultron/presence/window.py` executes on an independent thread, rendering via pure Win32 GDI calls. If the presence UI thread faults, the voice agent and task executor continue unabated.
5. **Log Sanitization:** All log handlers pass through `SecretSanitizingFilter`, intercepting any accidental API key or password leakage before writing to disk or stdout.

---

## 6. Build, Packaging, & GitHub CI/CD Audit

- **Authoritative Version:** `ultron/__version__.py` defines `__version__ = "0.1.0"`.
- **Packaging Strategy:** Standalone Windows binary via PyInstaller (`packaging/ultron.spec`), bundled into an installer executable via Inno Setup / custom Windows installer builder.
- **CI Gating:** GitHub Actions workflow executes complete static analysis, secret scans, and all 219 regression tests across Phases 5–10 + Phase 11 productization test suite before release creation.
