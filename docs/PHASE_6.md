# ULTRON Phase 6 Specification & Verification Report
## Advanced Desktop Agent & Multi-Step Task Execution

### 1. Architectural Map

```
USER VOICE
    │  (16 kHz PCM16 Streaming Microphone Stream)
    ▼
GEMINI LIVE
    │  (Bidirectional Realtime Cloud WebSocket)
    ▼
INTENT / MULTI-STEP TASK PROPOSAL
    │  (Structured JSON / execute_task_plan / single tool calls)
    ▼
LOCAL TASK PLANNER & VALIDATOR  [ultron/tasks/planner.py]
    │  (Validates registered capabilities, checks local safety policies)
    ▼
TASK EXECUTION ENGINE  [ultron/tasks/executor.py]
    │  (Authoritative singleton active task coordinator)
    ├── SAFETY GATEWAY & CONFIRMATION VAULT  [ultron/tools/safety.py, confirmation.py]
    │       (Authorizes SAFE or issues single-use token for CONFIRM_REQUIRED; BLOCKED stays BLOCKED)
    ├── LOCAL TOOL DISPATCH  [ultron/desktop/system.py, ultron/tools/executor.py]
    │       (Executes safe OS/filesystem APIs without arbitrary shell invocation)
    └── EMPIRICAL ACTION VERIFIER  [ultron/tasks/verifier.py]
            (Mandatory empirical verification: process scan, file hash/stat, clipboard readback)
    ▼
STRUCTURED RESULT & SESSION CONTEXT UPDATE  [ultron/memory/manager.py]
    ▼
GEMINI LIVE
    │  (Natural conversational speech generation)
    ▼
USER VOICE / AUDIO STREAM  (24 kHz PCM16 Output)
```

---

### 2. Task Lifecycle State Machine

The Task Engine manages the following lifecycle states:

```
[TASK_RECEIVED]
       │
       ▼
[TASK_PLANNING]  ──(Invalid Plan/Blocked Tool)──> [TASK_FAILED]
       │
       ▼
  [TASK_READY]
       │
       ▼
[TASK_EXECUTING] <─────────────┐
       │                       │
       ├──(Confirm Required)──> [TASK_WAITING_CONFIRMATION]
       │                              │ (User Approves)
       │                              └───────────┐
       │ (User Rejects/Cancels)                   │
       ▼                                          │
[TASK_CANCELLED] <────────────────────────────────┘
       │
       ▼
[TASK_VERIFYING] ──(Verify Failed & Retries Left)──> [TASK_EXECUTING] (Backoff)
       │
       ├──(Verify Failed & Retries Exhausted)──────> [TASK_FAILED]
       │
       ▼ (All Steps Verified)
[TASK_COMPLETED]
```

---

### 3. Safe Desktop Capabilities

All desktop actions are executed through strictly controlled local Python APIs rather than unrestricted OS shells (`cmd.exe`, `powershell.exe`, `bash`):

| Category | Capability | Safety Tier | Confirmation Required | Verification Method |
| :--- | :--- | :--- | :--- | :--- |
| **Time & Substrate** | `get_current_time` | `SAFE` | No | Authoritative timestamp |
| | `get_system_status` | `SAFE` | No | Substrate telemetry metrics |
| **Application Awareness** | `get_active_app` | `SAFE` | No | Active window / process inspection |
| | `get_running_apps` | `SAFE` | No | Process enumeration |
| | `open_app` | `SAFE` | No | Process table verification |
| | `close_app` | `CONFIRM_REQUIRED` | **Yes** | Process termination verification |
| **File Awareness** | `list_directory` | `SAFE` | No | Directory listing inspect |
| *(Workspace-Sandboxed)* | `get_file_info` | `SAFE` | No | File stat verification |
| | `read_file` | `SAFE` | No | File read / content validation |
| | `create_directory` | `SAFE` | No | Directory existence verification |
| | `write_file` | `CONFIRM_REQUIRED` | **Yes** | File existence + SHA256 content verification |
| | `copy_file` | `CONFIRM_REQUIRED` | **Yes** | Destination existence & size verification |
| | `move_file` | `CONFIRM_REQUIRED` | **Yes** | Source removal + destination existence verification |
| | `delete_file` | `CONFIRM_REQUIRED` | **Yes** | Absolute absence verification |
| **Clipboard** | `read_clipboard` | `SAFE` | No | Direct clipboard buffer read |
| | `write_clipboard` | `SAFE` | No | Readback verification |
| **Window Awareness** | `get_active_window` | `SAFE` | No | Window handle check |
| | `enumerate_windows` | `SAFE` | No | Visible window enumeration |
| **Memory** | `remember_fact` | `SAFE` | No | Persistent store lookup |
| | `forget_fact` | `SAFE` | No | Store key absence check |
| | `list_memories` | `SAFE` | No | Fact count verification |

---

### 4. Mandatory Verification & Bounded Retries

ULTRON never marks an action complete on faith. Every side effect is empirically checked:
- **`open_app`**: Polled via process table inspection to ensure the target executable has an active PID.
- **`write_file`**: Read back from disk, validating file existence, non-zero size, and text content equivalence.
- **`delete_file`**: Validated that `os.path.exists` returns `False`.
- **`create_directory`**: Validated that `os.path.isdir` returns `True`.
- **`write_clipboard`**: Immediate readback of clipboard buffer.

If verification fails, the step is automatically retried up to `max_retries = 2` with incremental backoff. If all retries fail, execution halts and returns a structured failure detailing the failed step and reason.

---

### 5. Independent Voice Cancellation vs. Barge-In

- **Barge-In**: Triggered by user speech detection while ULTRON is speaking. Flushes speaker playback buffer (<50ms) and resumes listening without terminating background multi-step execution.
- **Task Cancellation**: Triggered by explicit user cancellation commands ("Cancel that", "Stop task", "Abort"). Signals `TaskCancellationManager`, transitions the active task to `TASK_CANCELLED`, and prevents any subsequent steps from running.

---

### 6. Security Boundary Enforcement

The local runtime remains authoritative. The cloud intelligence layer cannot override local security rules:
- **Blocked Executables**: `cmd`, `powershell`, `pwsh`, `bash`, `sh`, `wsl`, `regedit`, `rundll32`, `cscript`, `wscript`, `mshta` are strictly rejected.
- **Command Injection Characters**: Any arguments containing `&`, `|`, `;`, `>`, `<`, `` ` ``, `$`, or `\n` are blocked with `TaskSecurityViolationError`.
- **Workspace Sandboxing**: File operations outside the configured workspace root (e.g. `C:\Windows\System32`) return `PolicyVerdict.BLOCKED` and cannot be authorized by confirmation tokens.

---

### 7. Performance & Substrate Resource Usage

- **Task Creation Overhead**: < 0.2ms
- **Plan Safety Validation**: < 0.5ms
- **Action Dispatch & Verification Overhead**: < 5ms per step
- **Cancellation Latency**: < 1ms
- **Memory Subsystem Lookup**: < 0.1ms
- **Local LLM Footprint**: 0 MB (Cloud-only Gemini Live intelligence layer)

---

### 8. Verification & Test Suite Summary

- **Phase 5 Regression Suite**: 43/43 PASSED
- **Phase 6 Task Engine Suite**: 18/18 PASSED
- **Total Automated Test Suite**: **61/61 PASSED** (0 failures, 0 regressions)

---

### 9. Intentionally Unsupported Capabilities

The following capabilities are deliberately excluded in Phase 6 to protect system integrity:
1. Arbitrary OS command execution via system shell.
2. Low-level global mouse/keyboard injection without window sandboxing.
3. Modification of Windows registry keys or system files.
4. Continuous background computer vision screen capture.
