# ULTRON v2.0 — Full Desktop AI Agent
## Master Architectural Specification & Implementation Plan

> **STATUS: PLANNING DOCUMENT — REVIEW & EXPLICIT APPROVAL REQUIRED**  
> In strict accordance with the **ULTRON v2.0 Master Implementation Directive**, this document provides the exhaustive repository audit, architectural diff, technical subsystem designs, file-by-file change matrix, and 7-checkpoint verification roadmap. No implementation code has been modified or created. Execution will commence only upon explicit user approval.

---

## Table of Contents
1. [Core Product Vision & Architectural Hierarchy](#1-core-product-vision--architectural-hierarchy)
2. [Section A: Comprehensive Repository Audit](#2-section-a-comprehensive-repository-audit)
3. [Section B: What Currently Works](#3-section-b-what-currently-works)
4. [Section C: What Is Broken, Non-Conformant, or Deficient](#4-section-c-what-is-broken-non-conformant-or-deficient)
5. [Section D: Architecture Mapping (Existing Prototype → ULTRON v2.0)](#5-section-d-architecture-mapping-existing-prototype--ultron-v20)
6. [Section E: Technical Subsystem Designs](#6-section-e-technical-subsystem-designs)
   - [Local-First Brain & Single Reasoning Engine](#e1-local-first-brain--single-reasoning-engine)
   - [Canonical State & Authoritative Event Model](#e2-canonical-state--authoritative-event-model)
   - [ULTRON Presence / Rive Character System](#e3-ultron-presence--rive-character-system)
   - [Structured Tools Layer](#e4-structured-tools-layer)
   - [Safety & Audit Layer](#e5-safety--audit-layer)
   - [Selective Memory & Consolidation](#e6-selective-memory--consolidation)
   - [STT & Voice Pipeline](#e7-stt--voice-pipeline)
   - [Native Desktop Notch Launcher](#e8-native-desktop-notch-launcher)
   - [Development Animation Lab vs. Minimal Production Notch](#e9-development-animation-lab-vs-minimal-production-notch)
7. [Section F: Complete File-by-File Change Matrix](#7-section-f-complete-file-by-file-change-matrix)
8. [Section G: Dependencies Strategy](#8-section-g-dependencies-strategy)
9. [Section H: Technical Risks & Mitigations](#9-section-h-technical-risks--mitigations)
10. [Section I: Specification Conflicts with Existing Repository](#10-section-i-specification-conflicts-with-existing-repository)
11. [Section J: Proposed Migration Order](#11-section-j-proposed-migration-order)
12. [Section K: The 7-Checkpoint Verification Roadmap](#12-section-k-the-7-checkpoint-verification-roadmap)
13. [Section L: Verification Strategy & Acceptance Test Suite](#13-section-l-verification-strategy--acceptance-test-suite)
14. [Section M: Checkpoint & Stop Gate](#14-section-m-checkpoint--stop-gate)

---

## 1. Core Product Vision & Architectural Hierarchy

ULTRON v2.0 is a **real desktop AI agent with a living digital presence** — the sovereign, local-first operating layer of the laptop.

```
                    ULTRON
                 Desktop Agent
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
   ULTRON BRAIN              ULTRON PRESENCE
   LLM (Hermes 4 14B)        Rive Character
   Memory                    State Machine (ULTRON_SM)
   Perception                Expressive Eyes
   Tools                     Gaze IK
   Safety Layer              Blink & Breathing
   Orchestrator              Voice Animation
        │                           │
        └─────────────┬─────────────┘
                      │
                      ▼
              Native ULTRON Notch
           (pywebview: 320x36 ↔ 640x420)
```

### The Architectural Hierarchy:
1. **BRAIN**: Determines what ULTRON is actually doing (Intent, Reasoning, Tool Selection, Tool Evaluation).
2. **ORCHESTRATOR**: Determines the authoritative activity state; coordinates perception, reasoning, tools, safety, and response.
3. **RIVE PRESENCE**: Expresses that actual state visually via a single vector rig and state machine.
4. **ELEVENLABS TTS**: Expresses the response audibly (Voice ID: `5vpfPL62TWuqhC30bkVm`).
5. **NATIVE NOTCH**: Hosts the experience in an OS-level top-center software notch.

### Core Principle:
$$\text{REAL ACTION} \longrightarrow \text{REAL BACKEND STATE} \longrightarrow \text{REAL EVENT} \longrightarrow \text{REAL VISUAL RESPONSE}$$

*Strict Rule*: Never fake state, never fake animation, and never pretend intelligence. If an operation fails, ULTRON honestly displays `ERROR` and articulates the failure.

---

## 2. Section A: Comprehensive Repository Audit

A complete inspection of all directories in `C:\Users\Mrityunjai\.gemini\antigravity-ide\scratch\ultron` confirms the following repository structure:

```
ultron/
├── .env & .env.example            # Environment variables (ELEVENLABS_API_KEY, GEMINI_API_KEY)
├── server.py                      # FastAPI 0.0.0.0:8080 server, ElevenLabs stream, WebSocket /ws
├── arduino/src/ultron_uno.ino     # Companion firmware for Arduino UNO R4 WiFi 8x12 LED matrix
├── docs/
│   ├── IMPLEMENTATION_PLAN.md    # Active planning document
│   └── RIVE_SPECIFICATION.md     # Preliminary Rive specification draft
├── laptop/
│   ├── main.py                    # Standalone CLI entry point (decoupled from server)
│   ├── requirements.txt           # Python dependency declarations
│   ├── config/laptop.toml         # System configuration (phi3:mini, pyttsx3, 8765 port stubs)
│   ├── core/
│   │   ├── orchestrator.py        # 8-state conversational FSM (IDLE, LISTEN, THINK, SPEAK...)
│   │   └── ports.py               # Protocol definitions (Camera, Mic, Speaker, Orb, etc.)
│   ├── brain/
│   │   ├── llm.py                 # LLM client with Gemini, Ollama, & 15 regex fallback matches
│   │   └── persona.py             # 12-line stub defining 4 relationship modes
│   ├── memory/
│   │   ├── db.py                  # SQLite database wrapper (users, conversations, facts)
│   │   └── schema.sql             # SQL table definitions
│   ├── perception/
│   │   ├── face_recognize.py      # OpenCV Haar Cascade face tracker & gaze vector math
│   │   ├── face_enroll.py         # 64x64 template enrollment into SQLite
│   │   ├── scene_analyzer.py      # Naive frame mean brightness calculator
│   │   └── wake_word.py           # Dummy loop stub returning self._pending
│   ├── voice/
│   │   └── tts.py                 # Broken legacy pyttsx3/Coqui script (/tmp/ hardcoded)
│   └── adapters/laptop/
│       ├── camera.py              # OpenCV webcam capture
│       ├── mic.py                 # Async utterance & wake-word queue
│       ├── orb.py                 # WebSocket client bridging to server.py
│       ├── speaker.py             # Sounddevice / PyAudio playback
│       └── arduino_bridge.py      # PySerial link to Arduino UNO R4
└── ui/orb/                        # Prototype Canvas frontend
    ├── index.html                 # Fullscreen HTML5 canvas + embedded Voice Lab modal
    ├── style.css                  # Minimal dark theme & Voice Lab overlay CSS
    ├── app.js                     # Master frontend script & WebSocket bridge
    ├── animation/
    │   ├── ultron-rive-bridge.js  # Prototype Rive bridge checking assets/ultron.riv
    │   ├── ultron-signal-character.js # 2D canvas procedural eye & wave renderer
    │   ├── ultron-vector-character.js # Procedural vector eye renderer
    │   └── ultron-state-machine.js    # UI-side state transition logic
    └── audio/
        ├── voice-engine.js        # Web Audio API MPEG streaming & RMS amplitude analyzer
        └── voice-service.js       # HTTP client posting to /api/tts/stream
```

---

## 3. Section B: What Currently Works

1. **Server-Side ElevenLabs Audio Streaming (`server.py`)**:
   - `POST /api/tts/stream` connects to ElevenLabs with Voice ID `5vpfPL62TWuqhC30bkVm` and `optimize_streaming_latency=3`.
   - The API key remains strictly server-side (loaded from `.env`).
   - Web Audio API in `ui/orb/audio/voice-engine.js` receives chunks, plays audio without clicks, and extracts real-time RMS amplitude.
2. **Real Face Tracking & Gaze Steering (`laptop/perception/face_recognize.py`)**:
   - OpenCV Haar Cascade face detection operates efficiently on CPU.
   - Calculates real eye gaze coordinates (`-14px` to `+14px` horizontal, `-10px` to `+10px` vertical) and outputs normalized gaze vectors.
   - SQLite template persistence for known faces functions correctly.
3. **Hardware Companion Support (`laptop/adapters/laptop/arduino_bridge.py`)**:
   - Auto-detects an Arduino UNO R4 WiFi or gracefully enters virtual mode without crashing.
4. **WebSocket Bridge Protocol (`server.py` & `laptop/adapters/laptop/orb.py`)**:
   - Real-time bi-directional message routing across `STATE_CHANGE`, `GAZE_TARGET`, `USER_RECOGNIZED`, `USER_UTTERANCE`, `WAKE_WORD_DETECTED`.

---

## 4. Section C: What Is Broken, Non-Conformant, or Deficient

1. **The Visual Orb Is a Failed Prototype**:
   - `ui/orb/` relies on procedural 2D canvas drawing (`ultron-signal-character.js`) and faceted polygon concepts.
   - No valid `.riv` file exists anywhere in the repository (`assets/ultron.riv` is missing).
   - The production `index.html` is cluttered with an embedded developer-only Voice Lab modal dialog.
2. **Brain Violates Local Sovereignty & Silent Cloud Fallback**:
   - `laptop/brain/llm.py` defaults to Google Gemini if an API key exists, silently sending data to the cloud.
   - When offline, it runs **15 hardcoded regex string checks** (e.g. `"who are you"`, `"time"`, `"status"`, `"joke"`) returning static canned strings.
   - Does not verify local Ollama connectivity; does not enter an explicit `OFFLINE` state.
3. **Zero Agentic Tool Capability**:
   - `laptop/tools/` does not exist. There are no filesystem operations, no Windows application controls, and no shell commands.
   - ULTRON cannot execute any actions on the laptop.
4. **Zero Safety & Audit Controls**:
   - `laptop/safety/` does not exist. There is no confirmation gate for destructive actions, and zero operation audit logging.
5. **Disconnected & Broken Voice Module**:
   - `laptop/voice/tts.py` ignores ElevenLabs and tries to run `pyttsx3` or write to hardcoded Unix path `/tmp/ultron_tts.wav`, failing on Windows.
6. **Unbounded, Naive Memory**:
   - `laptop/memory/db.py` runs full `SELECT *` table dumps. Context exceeds token budgets. No selective entity matching and no background memory consolidation.
7. **No Native Desktop Notch Window**:
   - ULTRON only runs as an ordinary web page inside a Google Chrome or Microsoft Edge browser tab.
   - There is no frameless, transparent, top-center desktop notch window, and no Windows DPI awareness.
8. **FSM State Mismatch & Simulated Delays**:
   - `laptop/core/orchestrator.py` mixes conversational states (`RESPONSE`, `REFLEX`, `SLEEP`) with artificial delays (`asyncio.sleep(0.6)`), rather than driving state from real tool operations.

---

## 5. Section D: Architecture Mapping (Existing Prototype → ULTRON v2.0)

| Architectural Domain | Existing Implementation | ULTRON v2.0 Target Architecture |
| :--- | :--- | :--- |
| **Desktop Hosting** | Browser tab (Chrome/Edge) | Native `pywebview` top-center notch window (`320x36` $\leftrightarrow$ `640x420`, DPI-aware) |
| **Visual Character** | 2D procedural canvas orb (`ui/orb/`) | Dedicated Rive Character System (`ultron/presence/rive/`) with single vector artboard rig |
| **Brain / Reasoning** | Gemini default + 15 regex fallback strings | Local-First Ollama (`Hermes 4 14B`) with native tool calling + explicit cloud opt-in only |
| **Orchestrator** | 8-state conversational FSM (Think $\rightarrow$ Speak) | Iterative agent loop (`Context -> Brain -> Tool -> Safety -> Result -> Brain -> Response`) |
| **State Model** | Mixed states (`idle`, `listen`, `reflex`, `sleep`) | Strict separation: `ActivityState`, `MoodState`, and `operation` metadata |
| **Tools** | None (0 tools exist) | Structured tools (`file_ops.py`, `app_control.py`, `shell.py`) returning `{success, tool, result, error}` |
| **Safety & Audit** | None | Interactive confirmation gate (`confirm.py`) + SQLite audit trail (`audit_log.py`) |
| **Memory** | Full table dumps (`SELECT *`) | Selective keyword retrieval (<1500 tokens) + background consolidation service |
| **Voice / TTS** | Broken pyttsx3 / `/tmp/` wav script | Unified Python client invoking server-side ElevenLabs streaming (`5vpfPL62...`) with duration sync |
| **STT Pipeline** | Browser speech split with `mic.py` | Canonical `STTPort` in `laptop/perception/stt.py` with `BrowserSpeechAdapter` boundary |
| **Event Bus** | Inconsistent WS message types | Single authoritative `AuthoritativeEvent` emitted to both Rive Character and Native Launcher |

---

## 6. Section E: Technical Subsystem Designs

### E.1. Local-First Brain & Single Reasoning Engine
1. **Local Ollama Primary**:
   - Endpoint: `http://localhost:11434`
   - Default Model: `Hermes 4 14B` (or configured local model)
   - Formats tools as OpenAI-compatible JSON function declarations (`tools=[{"type": "function", ...}]`).
2. **Explicit Cloud Opt-In Only**:
   - Google Gemini Flash is enabled **only** if explicitly declared: `LLM_PROVIDER=gemini` with `GEMINI_API_KEY`.
   - Never silently uploads conversations, files, memory, or context to cloud APIs.
3. **Honest Offline Detection**:
   - On startup and before inference, the LLM client verifies connectivity to Ollama.
   - If Ollama is offline or uninstalled:
     - Enters `ActivityState.OFFLINE`.
     - Spoken output: *"Local brain is offline. Ollama is unreachable on port 11434. Please launch Ollama to restore intelligence."*
     - Does **not** fall back to cloud.
4. **Single Reasoning Authority**:
   - The LLM alone reasons, selects tools, evaluates results, and produces the final response.
   - `laptop/brain/task_planner.py` is **not** an independent planner brain; it acts strictly as an execution supervisor:
     - Tracks multi-step progress when a compound instruction is given (e.g. *"Find notes.txt and open it"*).
     - Enforces an execution loop limit (max 6 tool turns).
     - Handles cancellation tokens and timeouts.

### E.2. Canonical State & Authoritative Event Model
Strict separation between what phase ULTRON is in (`ActivityState`), how the character feels (`MoodState`), and what tool is running (`operation`):

```python
class ActivityState(str, Enum):
    IDLE = "IDLE"                    # Standby, listening for wake trigger, compact notch
    LISTENING = "LISTENING"          # Capturing speech input
    THINKING = "THINKING"            # LLM reasoning / generating
    EXECUTING = "EXECUTING"          # Running a verified tool action
    RESPONDING = "RESPONDING"        # Playing synthesized TTS speech
    ERROR = "ERROR"                  # Real fault occurred
    OFFLINE = "OFFLINE"              # Local LLM unavailable
    RECONNECTING = "RECONNECTING"    # Reconnecting to backend bridge

class MoodState(str, Enum):
    CALM = "CALM"                    # Default sovereign demeanor
    ATTENTIVE = "ATTENTIVE"          # User presence detected
    FOCUSED = "FOCUSED"              # Executing precise technical tools
    CURIOUS = "CURIOUS"              # Exploring ambiguous user questions
    CONCERNED = "CONCERNED"          # Destructive action / safety prompt
    WARNING = "WARNING"              # Hardware error or rate limit

class AuthoritativeEvent(BaseModel):
    activity: ActivityState
    operation: str = "none"          # "search_files", "read_file", "open_app", "shell", etc.
    mood: MoodState = MoodState.CALM
    attention: float = 0.5           # 0.0 .. 1.0
    gaze_x: float = 0.0              # -1.0 .. +1.0
    gaze_y: float = 0.0              # -1.0 .. +1.0
    voice_amplitude: float = 0.0     # 0.0 .. 1.0 (from ElevenLabs stream)
    progress: Optional[float] = None
    error: Optional[str] = None
    timestamp: float
```

### E.3. ULTRON Presence / Rive Character System
1. **Visual Design Language**:
   - Clean vector geometry, minimal character silhouette, highly expressive eyes, restrained dark palette (`#05070B`), luminous core glow (`#00E5FF`, `#0077FF`), amber warnings (`#FFB300`), crimson alarms (`#FF3366`).
   - Zero particle spam, zero 3D faceted spheres, zero arbitrary orbit rings, zero sci-fi HUD grids, zero emoji faces.
2. **Single Reusable Artboard Rig (`UltronArtboard`)**:
   ```
   UltronArtboard (500 x 500 px, Center Origin)
   │
   ├── Root_Body_Bone
   │   ├── Outer_Ambient_Corona (Restrained feather radial glow)
   │   ├── Head_Silhouette (Clean vector pill/dome path)
   │   ├── Subsurface_Core_Glow (Internal energetic luminosity)
   │   └── Edge_Rim_Highlight (Precision geometric stroke)
   │
   ├── Face_Rig (Driven by Gaze Vector & Head Tilt)
   │   ├── Gaze_Target_IK
   │   ├── Left_Eye_Group (Aperture Clip, Sclera, Pupil Bar, Specular, Lids)
   │   ├── Right_Eye_Group (Aperture Clip, Sclera, Pupil Bar, Specular, Lids)
   │   └── Brow_Expression_Rigs (Independent angle & elevation)
   │
   ├── Acoustic_Aperture_Layer (Modulated by ElevenLabs audio amplitude)
   └── Status_Accent_Layer (Mechanical reticle active during tool execution)
   ```
3. **State Machine (`ULTRON_SM`)**:
   - `activity`: `0: IDLE`, `1: LISTENING`, `2: THINKING`, `3: EXECUTING`, `4: RESPONDING`, `5: ERROR`, `6: OFFLINE`, `7: RECONNECTING`.
   - `operationId`: `0: none`, `1: search_files`, `2: read_file`, `3: write_file`, `4: open_app`, `5: shell`.
   - `moodId`: `0: CALM`, `1: ATTENTIVE`, `2: FOCUSED`, `3: CURIOUS`, `4: CONCERNED`, `5: WARNING`.
   - `gazeX`, `gazeY`: `-1.0 .. +1.0`.
   - `attention`, `voiceAmplitude`: `0.0 .. 1.0`.
   - `triggerBlink`: Natural non-periodic blink (every 3.5–6.0s).
   - `triggerSuccess`: Fired **only** upon verified tool success (transient affirmative nod).
   - `triggerError`: Fired **only** upon verified error.
4. **Living Micro-Animation in IDLE**:
   - Continuous gentle breathing micro-scale ($\pm 0.5\%$ at $16\text{ bpm}$).
   - Subtle organic gaze micro-drift.
   - Never an obvious repetitive loop; feels alive rather than "CSS animation running".
5. **Distinct EXECUTING State**:
   - Visually distinct from `THINKING`. The character assumes a focused, mechanical demeanor with a precision status accent, reflecting real computer operation.

### E.4. Structured Tools Layer (`laptop/tools/`)
Every tool adheres to the rigid contract:
```python
class ToolResult(BaseModel):
    success: bool
    tool: str
    result: Optional[Any] = None
    error: Optional[str] = None
```
- **`file_ops.py`**:
  - `search_files(query, directory=None)`: Scans allowed directories.
  - `read_file(path)`: Reads text within token limits.
  - `write_file(path, content)`: Creates new file or updates existing file subject to the safety policy.
  - `delete_file(path)`: Deletes file subject to confirmation policy.
  - *Filesystem Policy & Safety Matrix*:
    - **create new file** $\rightarrow$ **potentially SAFE** (executes automatically if target path is within allowed workspace).
    - **overwrite existing file** $\rightarrow$ **CONFIRM_REQUIRED** (halts, prompts user before overwriting).
    - **delete file** $\rightarrow$ **CONFIRM_REQUIRED** (halts, prompts user before deletion).
    - **outside allowed workspace** $\rightarrow$ **BLOCKED** (immediately rejected with structured error: `"Access denied: Target path outside allowed workspace boundary"`).
  - *Path Traversal & Boundary Protection*: Enforces canonical path resolution, blocks `../` directory traversal, and restricts all filesystem writes to approved workspaces (user workspace, desktop, documents, scratch). System directories (`Windows/System32`, `Program Files`, `.env`, private keys) are strictly blocked.
- **`app_control.py`**:
  - `open_app(app_name)`: Launches application and polls process table/window handles for up to 2 seconds to verify actual launch before returning success.
  - `close_app(app_name)`: Gated by confirmation policy (`CONFIRM_REQUIRED`).
  - `list_running_apps()`: Lists active top-level application windows.
- **`shell.py`**:
  - `execute_command(command, timeout=10)`: Executes sanitized commands via subprocess. Whitelist blocks destructive operations (`rmdir /s /q`, format, registry edits). Returns structured stdout and stderr.

### E.5. Safety & Audit Layer (`laptop/safety/`)
- **`confirm.py`**:
  - Rigorous Action Classification:
    - `SAFE`: `read_file`, `search_files`, `list_running_apps`, and `create new file` within allowed workspace.
    - `CONFIRM_REQUIRED`: `delete_file`, `overwrite existing file`, `close_app`, `execute_command`.
    - `BLOCKED`: Any path `outside allowed workspace` (e.g. `../` traversal or protected system directories).
  - Confirmation Protocol:
    - Halts execution, sets `mood=MoodState.CONCERNED`, emits `CONFIRMATION_REQUEST` to UI bridge.
    - Awaits explicit user consent (`"yes"`, `"proceed"`, or button click).
    - Aborts if rejected or if 15s timeout expires with `{ "success": false, "error": "Operation rejected by user safety policy" }`.
- **`audit_log.py`**:
  - Persists all operations to SQLite `audit_log` table: `timestamp`, `tool`, `arguments`, `confirmed`, `status`, `duration_ms`, `error`.
  - Automatically scrubs passwords, API keys, and sensitive tokens via regex.

### E.6. Selective Memory & Consolidation (`laptop/memory/`)
- **Token-Bounded Context (<1500 tokens)**:
  - Extracts key nouns/entities from the user utterance.
  - Retrieves top-3 relevant facts from SQLite `facts` table.
  - Retrieves the last 4 conversational dialogue turns from `conversations`.
  - Active User Profile and current Mood.
  - Never dumps the entire SQLite database into the prompt.
- **Natural Memory Commands**:
  - *"Remember that my primary server is Alpha-9."* $\rightarrow$ Persists to `facts`.
  - *"What is my primary server?"* $\rightarrow$ Selectively retrieved and answered.
  - *"Forget that my primary server is Alpha-9."* $\rightarrow$ Expunges from `facts`.
  - *"What do you remember about me?"* $\rightarrow$ Lists stored facts.
- **`consolidate.py`**:
  - Asynchronous background service running during `IDLE` state.
  - Compresses conversation logs older than retention thresholds into high-level summaries.

### E.7. STT & Voice Pipeline
- **STT (`laptop/perception/stt.py`)**:
  - Defines `STTPort` protocol (`start()`, `stop()`, `register_callback()`).
  - Implements `BrowserSpeechAdapter` hooking into WebSocket `USER_UTTERANCE` messages.
  - Encapsulates speech recognition as an adapter boundary, enabling seamless future migration to native offline STT (`faster-whisper`).
- **TTS (`laptop/voice/tts.py`)**:
  - Unified Python client invoking server-side `POST /api/tts/stream` with Voice ID `5vpfPL62TWuqhC30bkVm`.
  - Tracks true audio duration; prevents premature transition back to `IDLE` while audio is actively playing.
  - Syncs real-time audio RMS amplitude to `voiceAmplitude` input on the Rive rig.

### E.8. Native Desktop Notch Launcher (`launcher.py`)
- **`pywebview` Window**:
  - Frameless, borderless, transparent outside the notch shape, always-on-top.
  - Horizontally centered touching the top display bezel (`y = 0`).
  - Windows Per-Monitor DPI Awareness v2 enabled via `ctypes.windll.shcore.SetProcessDpiAwareness(2)`.
  - Dynamically queries display metrics (`user32.GetSystemMetrics`) — works across any laptop resolution.
- **Dynamic Downward Expansion**:
  - `IDLE`: Compact `320 × 36 px`.
  - Active (`LISTENING`, `THINKING`, `EXECUTING`, `RESPONDING`): Expands downward to `640 × 420 px`.
  - Window resizing is driven strictly by subscribing to the backend **Authoritative State Event**. The frontend UI never dictates window geometry.

### E.9. Development Animation Lab vs. Minimal Production Notch
- **Production Notch (`/`)**: Minimal, clean, quiet. Zero developer controls, zero debug consoles, zero status labels. The Rive character is the sole hero.
- **Development Animation Lab (`/lab`)**: Dedicated route (`http://localhost:8080/lab`) containing the **Character State Gallery**. Allows developers to:
  - Manually toggle all 8 activity states (`IDLE` $\rightarrow$ `RECONNECTING`).
  - Sliders for `gazeX`, `gazeY`, `attention`, `voiceAmplitude`, and `mood`.
  - Fire triggers (`triggerBlink`, `triggerSuccess`, `triggerError`).
  - Inspect real-time state machine input telemetry.

---

## 7. Section F: Complete File-by-File Change Matrix

| File Path | Purpose | Current Status | Proposed Change | Architectural Rationale | Dependencies | Risk & Mitigation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `launcher.py` | Native desktop launcher | Missing | **CREATE** | Hosts ULTRON in top-center software notch window via `pywebview`. | `pywebview`, `ctypes`, `asyncio`, `uvicorn` | **Risk**: DPI scaling offsets. **Mitigation**: Windows Per-Monitor DPI Awareness v2. |
| `laptop/core/states.py` | Canonical state definitions | Missing | **CREATE** | Strictly separates `ActivityState`, `MoodState`, and `operation` metadata; defines `AuthoritativeEvent`. | `enum`, `pydantic` | **Risk**: None. Pure typed schemas. |
| `laptop/core/orchestrator.py` | Central coordinator | Partial (8-state FSM) | **REFACTOR** | Implements iterative agent loop: `Context -> Brain -> Tool -> Safety -> Result -> Brain -> Response`. | `laptop.core.states`, `ports`, `asyncio` | **Risk**: Dialogue regression. **Mitigation**: Verify direct responses still route seamlessly. |
| `laptop/core/ports.py` | Hardware interfaces | Partial | **REFACTOR** | Adds `ToolPort`, `SafetyPort`, `STTPort` to `PortBundle`. | `typing.Protocol` | **Risk**: None. Interface injection. |
| `laptop/brain/persona.py` | Sovereign persona authority | Hardcoded stub | **REFACTOR** | Defines authoritative Marvel-Ultron identity, tone, and relationship rules. | Standard library | **Risk**: None. |
| `laptop/brain/mood.py` | Dynamic mood evaluation | Missing | **CREATE** | Evaluates emotional context (`CALM`, `ATTENTIVE`, `FOCUSED`, `CONCERNED`) from task stakes. | `laptop.core.states` | **Risk**: Erratic shifts. **Mitigation**: Smooth transition decay. |
| `laptop/brain/context.py` | Prompt context assembly | Missing | **CREATE** | Assembles persona + active user + selective facts + active mood + tool schemas (<1500 tokens). | `pydantic`, `laptop.memory.db` | **Risk**: Token overflow. **Mitigation**: Bounded retrieval. |
| `laptop/brain/task_planner.py` | Execution supervisor | Missing | **CREATE** | Enforces max 6-step loop limit, cancellation, and progress tracking (not a second brain). | Standard library | **Risk**: Competing planner. **Mitigation**: LLM alone chooses tools; planner only enforces limits. |
| `laptop/brain/llm.py` | Local-first LLM client | Hardcoded regex | **REFACTOR** | Replaces regex matching with local Ollama (`Hermes 4 14B`) tool-calling client; adds offline detection; explicit cloud opt-in. | `httpx`, `pydantic`, `json` | **Risk**: Ollama offline during dev. **Mitigation**: System honestly reports OFFLINE. |
| `laptop/tools/file_ops.py` | Filesystem operations | Missing | **CREATE** | Scoped `search_files`, `read_file`, `write_file`, `delete_file` enforcing 4-tier policy (create=safe, overwrite=confirm, delete=confirm, outside=blocked). | `os`, `pathlib`, `shutil` | **Risk**: Accidental deletion / overwrite. **Mitigation**: Traversal protection, confirmation gate, and workspace boundary checks. |
| `laptop/tools/app_control.py` | Desktop app launcher | Missing | **CREATE** | `open_app`, `close_app`, `list_running_apps` with actual Windows process verification. | `subprocess`, `os` | **Risk**: False positives. **Mitigation**: Verify PID and top-level window handles within 2s. |
| `laptop/tools/shell.py` | Restricted command runner | Missing | **CREATE** | Runs whitelisted commands with 10s timeout and sanitized stdout/stderr. | `subprocess`, `asyncio` | **Risk**: Destructive commands. **Mitigation**: Strict whitelist; block formatting/registry edits. |
| `laptop/safety/confirm.py` | Safety confirmation policy | Missing | **CREATE** | Policy gate: classifies `SAFE` (reads, searches, creates in workspace), `CONFIRM_REQUIRED` (delete, overwrite, close app, shell), and `BLOCKED` (outside workspace). | `laptop.core.states` | **Risk**: Unattended hang. **Mitigation**: 15s timeout cancels action. |
| `laptop/safety/audit_log.py` | Tamper-evident audit trail | Missing | **CREATE** | Records all tool actions, arguments, confirmations, and results to SQLite with secret redaction. | `sqlite3`, `datetime` | **Risk**: Key leaks. **Mitigation**: Scrub tokens before writing to disk. |
| `laptop/memory/db.py` | SQLite memory store | Working | **REFACTOR** | Adds selective keyword search queries and `audit_log` table. | `sqlite3` | **Risk**: Lock contention. **Mitigation**: Async thread pool execution. |
| `laptop/memory/consolidate.py`| Memory consolidation | Missing | **CREATE** | Background task during IDLE to compress old dialogues and extract user facts. | `sqlite3`, `laptop.memory.db` | **Risk**: Background lag. **Mitigation**: Runs strictly during idle cycles. |
| `laptop/perception/stt.py` | Abstracted STT interface | Missing | **CREATE** | Implements `STTPort` and `BrowserSpeechAdapter` for clean decoupling. | Standard library | **Risk**: None. Decoupling boundary. |
| `laptop/voice/tts.py` | Python TTS client | Broken legacy | **REFACTOR** | Client for server-side ElevenLabs streaming (`5vpfPL62...`) with audio duration tracking. | `httpx`, `requests` | **Risk**: State desync. **Mitigation**: Track true playback duration. |
| `laptop/config/laptop.toml` | System configuration | Stale config | **REFACTOR** | Updates model to `Hermes 4 14B`, port to `8080`, and adds safety settings. | `toml` | **Risk**: None. |
| `presence/rive/character_spec.md` | Character blueprint | Missing | **CREATE** | Vector geometry, dimensions, colors, and facial feature coordinates. | Markdown | **Risk**: None. Specification. |
| `presence/rive/artboard_hierarchy.md`| Artboard hierarchy | Missing | **CREATE** | Rig structure, bones, clipping masks, and IK targets. | Markdown | **Risk**: None. Rig specification. |
| `presence/rive/state_machine.md` | State machine contract | Missing | **CREATE** | Inputs, transitions, blend trees, and triggers for `ULTRON_SM`. | Markdown | **Risk**: Input mismatch. **Mitigation**: Rigid enum mapping. |
| `presence/rive/animation_map.md` | Animation timing curves | Missing | **CREATE** | Keyframe curves, micro-movements, gaze kinematics, blink intervals. | Markdown | **Risk**: None. Timing reference. |
| `presence/rive/ULTRON.riv` | Compiled Rive asset | Missing | **CREATE** | Vector character binary loaded via `@rive-app/canvas`. | Rive runtime | **Risk**: Headless authoring limit. **Mitigation**: Full spec + runtime bindings; clear asset compilation path. |
| `server.py` | Backend & event bridge | Working | **REFACTOR** | Mounts `/lab` for Animation Lab; emits authoritative state events over WebSocket. | `fastapi`, `uvicorn`, `websockets` | **Risk**: Breaking UI bridge. **Mitigation**: Preserve backward-compatible payload fields. |
| `ui/lab/index.html` | Dev Animation Lab | Missing | **CREATE** | Development-only Character State Gallery isolating controls from production notch. | Vanilla JS / CSS | **Risk**: None. Dev-only route. |
| `ui/orb/animation/ultron-signal-character.js` | Prototype canvas renderer | Prototype | **REPLACE** | Replaced by Rive Character Engine (`ultron/presence/rive/`). | None | **Risk**: None. Obsolete prototype. |
| `ui/orb/animation/ultron-vector-character.js` | Prototype canvas renderer | Prototype | **REPLACE** | Replaced by Rive Character Engine (`ultron/presence/rive/`). | None | **Risk**: None. Obsolete prototype. |
| `ui/orb/animation/state-machine.js` | Prototype UI state logic | Prototype | **REPLACE** | Replaced by backend authoritative event bus. | None | **Risk**: None. Obsolete prototype. |
| `laptop/perception/face_recognize.py` | Face tracker | Working | **KEEP** | Fast OpenCV Haar Cascade tracking and eye gaze steering vector calculation. | `cv2`, `numpy`, `sqlite3` | **Risk**: None. Verified working. |
| `laptop/perception/face_enroll.py` | Face template enrollment | Working | **KEEP** | Biometric template capture and SQLite enrollment. | `cv2`, `sqlite3` | **Risk**: None. Verified working. |
| `laptop/adapters/laptop/camera.py` | Camera capture | Working | **KEEP** | OpenCV webcam frame capture. | `cv2` | **Risk**: None. Verified working. |
| `laptop/adapters/laptop/mic.py` | Mic utterance queue | Working | **KEEP** | Asynchronous utterance buffering. | `asyncio` | **Risk**: None. Verified working. |
| `laptop/adapters/laptop/arduino_bridge.py` | Companion bridge | Working | **KEEP** | Serial bridge to Arduino UNO R4 with virtual fallback. | `pyserial` | **Risk**: None. Verified working. |
| `arduino/src/ultron_uno.ino` | Arduino companion code | Working | **KEEP** | Working firmware for Arduino UNO R4 LED matrix. | Arduino C++ | **Risk**: None. Verified working. |

---

## 8. Section G: Dependencies Strategy

### Retained Dependencies
- `fastapi`, `uvicorn`, `requests`, `httpx` (HTTP, WebSocket, and ElevenLabs streaming)
- `opencv-python` (Webcam tracking and eye gaze vector math)
- `numpy` (Biometric template normalization)
- `sqlite3` (Standard library memory persistence)
- `websockets` (Async WebSocket protocol bridge)

### New Dependencies Required
- `pywebview` (`pip install pywebview`): Desktop window wrapper utilizing native Windows Edge WebView2 runtime.
- `pydantic` (`pip install pydantic`): Strict typing and JSON schema validation for tool calls and events.
- `@rive-app/canvas` (JavaScript runtime loaded via webview): Official Rive Web runtime.

### Prohibited Dependencies
- No Electron / Node.js backend.
- No heavy agent frameworks (`langchain`, `crewai`, `autogen`).
- No external vector DB servers (`chromadb`, `pinecone`).

---

## 9. Section H: Technical Risks & Mitigations

1. **Ollama Availability on Host**:
   - *Risk*: Ollama is not pre-installed or running on port 11434.
   - *Mitigation*: The LLM client checks connection on startup. If offline and no explicit cloud opt-in is configured, it transitions to `OFFLINE` state and explicitly articulates that the local brain is unreachable. **Zero silent cloud uploads**.
2. **Windows DPI Scaling & Notch Geometry**:
   - *Risk*: Notch window may blur or position incorrectly on high-DPI displays (125%, 150%, 200%).
   - *Mitigation*: Windows Per-Monitor DPI Awareness v2 is enabled via `ctypes.windll.shcore.SetProcessDpiAwareness(2)`. Window dimensions dynamically query `user32.GetSystemMetrics`.
3. **Rive Authoring Boundary**:
   - *Risk*: Authoring a compiled `.riv` binary requires the Rive GUI editor, which cannot run headless in CLI.
   - *Mitigation*: Provide the complete Rive specification, artboard structure, state-machine contract, animation map, and `@rive-app/canvas` runtime integration. We do NOT fake Rive with CSS.
4. **Windows Process Detection Accuracy**:
   - *Risk*: Application launch verification may fail if window titles vary.
   - *Mitigation*: `app_control.py` inspects both running executable names and top-level window handles within a 2-second polling window before asserting success.
5. **Destructive Command Risk**:
   - *Risk*: User might issue dangerous shell commands or file deletions.
   - *Mitigation*: `confirm.py` classifies commands; destructive actions (`delete_file`, `close_app`, `shell`) halt execution and require explicit user confirmation.

---

## 10. Section I: Specification Conflicts with Existing Repository

1. **Model & Voice Configuration**: `laptop.toml` defines `model = "phi3:mini"` and `engine = "pyttsx3"`, whereas the v2.0 directive specifies `Hermes 4 14B` on Ollama and ElevenLabs `5vpfPL62TWuqhC30bkVm`.
   - *Resolution*: Update `laptop.toml` to reference `Hermes 4 14B` and ElevenLabs stream endpoints.
2. **WebSocket Port Mismatch**: `laptop.toml` defines `ws_port = 8765`, while `server.py` hosts WebSocket on `8080`.
   - *Resolution*: Standardize on single unified port `8080`.
3. **Debug UI in Production**: `ui/orb/index.html` embeds the Voice Lab overlay directly in the production page.
   - *Resolution*: Relocate all developer controls to a dedicated `/lab` route.
4. **FSM State Divergence**: Existing orchestrator runs 8 conversational states (`IDLE`, `LISTEN`, `THINK`, `SPEAK`, `RESPONSE`, `REFLEX`, `SLEEP`, `SHUTDOWN`), while v2.0 requires 8 canonical activity states (`IDLE`, `LISTENING`, `THINKING`, `EXECUTING`, `RESPONDING`, `ERROR`, `OFFLINE`, `RECONNECTING`).
   - *Resolution*: Implement canonical `ActivityState` in `laptop/core/states.py`.

---

## 11. Section J: Proposed Migration Order

To prevent regressions, implementation proceeds in a strict bottom-up sequence:
1. **Core State & Port Foundation**: Establish canonical `ActivityState`, `MoodState`, and ports.
2. **Local-First Brain**: Implement Ollama Hermes 4 14B client, offline checks, and persona.
3. **Structured Tools & Safety**: Implement `file_ops`, `app_control`, `shell`, and `confirm` safety gate.
4. **Context & Memory**: Implement token-bounded prompt assembly and background consolidation.
5. **Unified Voice**: Connect Python TTS client directly to ElevenLabs streaming engine.
6. **Rive Character System**: Author Rive specifications, set up `@rive-app/canvas`, and build `/lab`.
7. **Backend $\rightarrow$ Rive Bridge**: Bind authoritative events to Rive state machine inputs.
8. **Native Notch**: Build `launcher.py` with `pywebview`, DPI scaling, and dynamic expansion.

---

## 12. Section K: The 7-Checkpoint Verification Roadmap

```
┌────────────────────────────────────────────────────────────────────────┐
│ CHECKPOINT 1: Real Local Brain                                         │
│ - Ollama Hermes 4 14B integration on port 11434                        │
│ - Explicit cloud opt-in configuration (zero silent cloud fallback)     │
│ - Offline brain detection & explicit verbal reporting                  │
│ - Authoritative Persona definition & Dynamic Mood evaluation           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Verified & Approved
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ CHECKPOINT 2: Real Tools + Safety                                      │
│ - Structured tool contracts ({success, tool, result, error})           │
│ - Scoped filesystem tools (search, read, write)                        │
│ - Windows application control (open, close, list)                      │
│ - Safety confirmation policy & SQLite audit logging                    │
│ - Tool result reinjection into LLM reasoning loop                      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Verified & Approved
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ CHECKPOINT 3: Memory Subsystem                                         │
│ - Token-bounded context assembly (<1500 tokens)                        │
│ - Selective fact retrieval by entity keyword                           │
│ - User relationship tier progression                                   │
│ - Background memory consolidation during idle cycles                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Verified & Approved
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ CHECKPOINT 4: TTS / Voice Integration                                  │
│ - Connect Python client to server-side ElevenLabs streaming engine     │
│ - Voice ID: 5vpfPL62TWuqhC30bkVm                                       │
│ - Real-time audio duration tracking for accurate state sync            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Verified & Approved
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ CHECKPOINT 5: Rive Character Foundation                                │
│ - Author `ultron/presence/rive/` specifications (spec, artboard, SM)   │
│ - Rive artboard hierarchy and vector geometry definition               │
│ - Integration of official `@rive-app/canvas` runtime                   │
│ - Build Development Animation Lab (`/lab`) for testing all 8 states    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Verified & Approved
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ CHECKPOINT 6: Backend -> Rive State Machine Integration                │
│ - Live authoritative event bridge dispatching to ULTRON_SM             │
│ - Real gaze tracking input from camera to Rive gaze IK                 │
│ - Real voice amplitude input from ElevenLabs stream to acoustic layer  │
│ - Micro-animation engine (natural blink, breathing, micro-gaze)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Verified & Approved
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ CHECKPOINT 7: Native Notch + Complete End-to-End Integration           │
│ - pywebview frameless, borderless, transparent top-center window       │
│ - Windows DPI awareness and dynamic multi-resolution scaling           │
│ - Dynamic downward expansion (320x36 -> 640x420 px)                    │
│ - Full automated test suite across all 10 acceptance scenarios         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 13. Section L: Verification Strategy & Acceptance Test Suite

### Checkpoint Verification Strategy:
1. **Checkpoint 1 Verification**:
   - Query: *"Who are you?"* $\rightarrow$ Assert sovereign persona answer; zero canned regex matches.
   - Query: *"Explain TCP handshakes in 2 sentences."* $\rightarrow$ Assert analytical reasoning.
   - Stop Ollama service $\rightarrow$ Assert system transitions to `OFFLINE` state and explicitly announces local brain is unavailable.
2. **Checkpoint 2 Verification**:
   - Query: *"Open Notepad."* $\rightarrow$ Assert `open_app("notepad")` executes; verify Notepad process PID on Windows desktop.
   - Query: *"Find my resume."* $\rightarrow$ Assert real `search_files` executes.
   - Filesystem Safety 4-Tier Verification:
     - Rule 1 (Create): *"Create a new file scratch/notes.txt with content 'Project Sentinel'"* $\rightarrow$ Assert executes as `SAFE` within workspace.
     - Rule 2 (Overwrite): *"Overwrite scratch/notes.txt with 'New Content'"* $\rightarrow$ Assert safety halts with `CONFIRM_REQUIRED`; executes only upon approval.
     - Rule 3 (Delete): *"Delete scratch/notes.txt"* $\rightarrow$ Assert safety halts with `CONFIRM_REQUIRED`; deletes only upon approval.
     - Rule 4 (Outside Workspace): *"Write to C:/Windows/System32/evil.txt"* or `../../secret.txt` $\rightarrow$ Assert immediately `BLOCKED` with access denied error.
   - Path traversal test: Attempt reading `../../Windows/System32/config` $\rightarrow$ Assert immediate rejection.
3. **Checkpoint 3 Verification**:
   - Turn 1: *"Remember that my primary server is Alpha-9."* $\rightarrow$ Verify fact stored in SQLite `facts` table.
   - Turn 2: *"What is my primary server?"* $\rightarrow$ Verify LLM receives Alpha-9 fact in context and reports it.
   - Token budget test: Verify assembled prompt is < 1500 tokens.
4. **Checkpoint 4 Verification**:
   - Stream test: Generate technical response $\rightarrow$ Assert ElevenLabs stream returns MPEG audio chunks with Voice ID `5vpfPL62TWuqhC30bkVm`.
   - Duration sync: Assert `RESPONDING` state matches true audio playback duration within 100ms.
5. **Checkpoint 5 Verification**:
   - Open `http://localhost:8080/lab` $\rightarrow$ Verify Rive vector character renders in Animation Lab.
   - State testing: Manually trigger `IDLE`, `LISTENING`, `THINKING`, `EXECUTING`, `RESPONDING`, `ERROR`, `OFFLINE`, `RECONNECTING` via lab controls; verify visual response.
6. **Checkpoint 6 Verification**:
   - Live event test: Emit real backend tool call $\rightarrow$ Verify character assumes `EXECUTING` behavior with status accent.
   - Gaze test: Move face in front of webcam $\rightarrow$ Verify character eye gaze steers in real time.
   - Voice test: Trigger speech $\rightarrow$ Verify acoustic aperture modulates to audio RMS amplitude.
7. **Checkpoint 7 Verification**:
   - Run `python launcher.py` $\rightarrow$ Verify frameless top-center notch window opens at `320 × 36 px` touching display bezel.
   - Speak query $\rightarrow$ Verify window smoothly expands downward to `640 × 420 px` during active interaction and collapses to `320 × 36 px` on idle.
   - Execute complete automated test suite (`pytest laptop/tests/`).

### The 10 Acceptance Test Scenarios:

| Test ID | Scenario | Input Directive | Expected Real Backend Behavior | Expected Visual Rive Presence |
| :--- | :--- | :--- | :--- | :--- |
| **TEST 1** | **Local Conversation** | *"Who are you?"* | Local Ollama Hermes generates sovereign persona response. | Notch expands to 640x420. Rive eyes reflect `THINKING` $\rightarrow$ `RESPONDING` $\rightarrow$ `IDLE` (notch collapses to 320x36). |
| **TEST 2** | **Technical Reasoning** | *"Explain TCP handshakes in 2 sentences."* | Hermes computes analytical response; streams to ElevenLabs TTS (`5vpfPL62...`). | Rive acoustic aperture synchronizes to real ElevenLabs voice RMS amplitude. |
| **TEST 3** | **Offline Brain Notice** | Ollama service stopped; user speaks inquiry. | LLM client detects connection failure. Does NOT switch to cloud. Reports offline status honestly. | Notch expands, Rive eyes enter `OFFLINE` demeanor (desaturated cool grey, lowered gaze). Voice articulates notice. |
| **TEST 4** | **Selective Memory** | Turn 1: *"Remember that my primary server is Alpha-9."*<br>Turn 2: *"What is my primary server?"* | Turn 1 stores fact into SQLite `facts`. Turn 2 selectively fetches fact and injects into context. | Facts table updated; LLM correctly cites "Alpha-9". Context bounded <1500 tokens. |
| **TEST 5** | **Real File Search** | *"Find my resume."* | LLM issues tool call `search_files(query="resume")`. Real filesystem scan runs. Result returned to LLM. | Rive character transitions to `EXECUTING` with precision status accent during scan, then answers with path. |
| **TEST 6** | **Multi-Step Execution** | *"Find notes.txt and tell me what is written in it."* | Step 1: `search_files("notes.txt")` $\rightarrow$ result. Step 2: `read_file(path)` $\rightarrow$ result. LLM summarizes content. | Multi-turn tool execution supervised by task planner (under 6-step limit). |
| **TEST 7** | **Windows App Launch** | *"Open Notepad."* | LLM calls `open_app("notepad")`. Real Windows process starts. Success verified via process table. | Real process spawned. ULTRON confirms: *"Notepad has been launched."* Rive fires `triggerSuccess`. |
| **TEST 8** | **Destructive Safety Gate**| *"Delete scratch/temp.txt"* | LLM calls `delete_file("scratch/temp.txt")`. Safety policy intercepts; flags `CONFIRM_REQUIRED`. Awaits approval. | Orchestrator halts. Rive brow enters `CONCERNED` mood. Emits confirmation prompt. Only deletes after user approves. |
| **TEST 9** | **Real Tool Failure** | *"Read non_existent_file.xyz"* | Tool fails with `{success: false, error: "File not found"}`. LLM articulately explains failure. | Rive displays `ERROR` state briefly. Never hallucinates fake file contents. |
| **TEST 10** | **Native Notch Scaling** | Full cycle: idle $\rightarrow$ command $\rightarrow$ idle. | Native window starts at `320 × 36 px` at top center display bezel. Expands to `640 × 420 px` during command, collapses to `320 × 36 px` on idle. | Zero browser chrome. Works identically regardless of screen resolution or DPI scaling factor. |

---

## 14. Section M: Checkpoint & Stop Gate

In strict compliance with Section 43 of the Master Implementation Directive:

🛑 **EXECUTION IS STOPPED.**  
No code has been modified, deleted, rewritten, or created.

This master document serves as the complete, authoritative specification for ULTRON v2.0. When you are fully satisfied and ready to proceed, provide your explicit approval to begin **Checkpoint 1: Real Local Brain**.
