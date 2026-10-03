# ULTRON Phase 9 Architecture & Hardening Guide
## Production-Grade Long-Running Task Reliability, Recovery & Hardening

---

## 1. Overview & Objectives

Phase 9 hardens ULTRON for real-world, long-running, failure-prone desktop automation tasks. The objective is not adding superfluous tools, but establishing rigorous durability, observability, crash recovery, idempotency, bounded resource management, and safety guarantees under all failure conditions.

ULTRON survives:
- Gemini Live websocket disconnects and reconnects
- Network loss and session expirations
- Browser process crashes and stale Chrome DevTools Protocol (CDP) handles
- Application crashes
- Tool execution timeouts and partial task completions
- Process restarts and power interruptions
- User cancellations during execution, pause, or confirmation
- Confirmation delays, expiry, and restart invalidation
- Stale sessions and malformed model outputs
- Corrupted task state on disk
- Webpage DOM changes and untrusted prompt injection attacks

All without weakening or bypassing the **Safety Gateway**, **Confirmation Vault**, or **Authoritative Local Execution Engine**.

---

## 2. Durable Task State Architecture

### 2.1 Persistence Layer (`ultron.tasks.persistence`)
Long-running task state is stored under `.ultron_state/tasks/` in the workspace using atomic disk writes:
1. **Serialization**: State dictionary is filtered through recursive secret scrubbing.
2. **Atomic Write Pipeline**:
   - Write to temporary file (`task_<task_id>.json.tmp.<uuid>`)
   - Explicit `flush()` and `os.fsync()` ensuring hardware disk commit
   - Atomic rename via `os.replace`
3. **Checksum & Integrity Envelope**:
   - Payload wrapped with `sha256_checksum` and `timestamp`.
   - On load, checksum is recalculated and verified.
4. **Quarantine on Corruption**:
   - If corrupted or tampered, the file is automatically moved to `.corrupted_<timestamp>` and `None` is returned, preventing crashes or unsafe deserialization.

### 2.2 Strict Zero-Secret Storage Policy
Persisted task context explicitly excludes:
- API keys, bearer tokens, passwords
- Confirmation approval secrets (OTP / tokens)
- Browser cookies or local storage dumps
- Raw user audio bytes
- Arbitrary untrusted page blobs

---

## 3. Bounded Task Journal (`ultron.tasks.journal`)

Every execution lifecycle transition is logged immutably:
- **Events (17 Types)**:
  `TASK_CREATED`, `PLAN_CREATED`, `STEP_STARTED`, `STEP_COMPLETED`, `STEP_VERIFIED`, `STEP_FAILED`, `RETRY_STARTED`, `REPLAN_STARTED`, `REPLAN_COMPLETED`, `CONFIRMATION_REQUESTED`, `CONFIRMATION_APPROVED`, `CONFIRMATION_REJECTED`, `TASK_PAUSED`, `TASK_RESUMED`, `TASK_CANCELLED`, `TASK_COMPLETED`, `TASK_FAILED`.
- **Bounds**: In-memory ring buffer strictly capped at 500 entries (oldest evicted).
- **Disk Storage**: Appended to `.ultron_state/journal.jsonl`.
- **Sanitization**: All metadata dictionaries are recursively scrubbed of secrets prior to writing.

---

## 4. Crash Recovery & Resumption Engine

When ULTRON restarts during an active goal:
1. **Discovery & Validation**: Scans `.ultron_state/tasks/`, loads state envelopes, and verifies SHA256 integrity.
2. **Checkpoint Evaluation**: Identifies the latest verified `Checkpoint`.
3. **In-Flight Step Reconciliation**:
   - Any step left in `RUNNING` or `UNKNOWN_OUTCOME` is inspected.
   - If the step capability is `IDEMPOTENT` and the postcondition already exists (e.g. directory created, file exists), the step is promoted to `COMPLETED`.
   - If unverified, it is reset to `PENDING` for safe, single-instance re-execution.
4. **Safe Continuation**: Resumes plan execution starting at the first non-completed step.

---

## 5. Idempotent Recovery & Unknown Outcome Handling

### 5.1 Capability Retry Classifications
Every tool/capability is categorized via `RetrySafety`:
- `IDEMPOTENT`: `read_file`, `list_directory`, `get_page_title`, `get_page_text`, `find_element`, `create_directory` (if target exists). Safe to re-run anytime.
- `SAFE_TO_RETRY`: Pure observations, idempotent navigations.
- `NOT_SAFE_TO_RETRY`: `write_file`, `delete_file`, `click_element`, `type_text`, `open_application`, `press_key`. **Never blindly retried**.

### 5.2 `UNKNOWN_OUTCOME` State
When a tool experiences a timeout or partial crash during execution:
1. Status is marked as `UNKNOWN_OUTCOME`.
2. Execution engine invokes `_probe_environment_for_step`.
3. If empirical verification confirms the desired outcome (e.g., file was written before timeout), it advances safely.
4. If missing, and capability is `NOT_SAFE_TO_RETRY`, it triggers controlled replanning or alerts the user rather than blindly duplicate-invoking.

---

## 6. Network & Gemini Live Reconnect Hardening

- **Separation of Concerns**: Task identity (`goal_id`, `task_id`) is decoupled from the transient Gemini Live WebSocket connection (`session_id`).
- **Autonomous Local Execution**: Task execution continues locally even if the cloud websocket drops.
- **Context Synchronization**: Upon reconnect, Gemini Live is synchronized with verified step outputs and checkpoint evidence without re-executing steps.
- **Reconnect Locking**: Thread-safe reconnect locks prevent concurrent race conditions during transient network drops.

---

## 7. Browser & Application Recovery

- **Stale CDP Invalidation**: When Chrome crashes or CDP disconnects, `ChromeAdapter` detects the broken pipe, marks the adapter as disconnected, and invalidates cached page handles.
- **Safe Reconnection**: Subsequent browser actions trigger a controlled health probe, re-launch/re-connect to Chrome if permitted, and re-navigate to the verified tab state.
- **Destructive Action Protection**: Navigation or clicks are not blindly duplicated after browser drops.

---

## 8. Confirmation & Cancellation Durability

### 8.1 Confirmation Invalidation Across Restart
- Pending confirmation requests are held exclusively in volatile memory.
- If the runtime restarts while awaiting confirmation, the pending token defaults to `EXPIRED` / `INVALID`.
- Old approval tokens cannot be replayed or persisted. A fresh prompt is required.

### 8.2 Sticky Cancellation
- If a user commands "Cancel" or `cancel_active_goal()` is invoked, the goal transitions to `GOAL_CANCELLED`.
- Cancelled status is atomically persisted to disk.
- Reconnection or restart checks `persisted_goal.state == GOAL_CANCELLED` and **strictly refuses resurrection**.

---

## 9. Execution Budgets & Timeouts

To prevent runaway tasks or infinite loops:
- `max_duration_seconds`: Default 600s (configurable). Exceeding budget marks goal as `TIMED_OUT`.
- `max_steps`: Strict limit (e.g., 50 steps per goal).
- `max_replans`: Strict limit (default 3 dynamic replans per goal).
- `max_retries`: Maximum 2 retries per step before escalating to replanner.

---

## 10. Checkpoint Integrity & Evidence Chain

### 10.1 Checkpoints
- Created at key task milestones.
- Contains: `checkpoint_id`, `task_id`, `goal_id`, `plan_version`, `completed_step_ids`, `verified_outputs`, `environment_snapshot`, `timestamp`, and SHA256 `integrity_hash`.
- `checkpoint.is_valid()` cryptographically verifies that metadata has not been altered.

### 10.2 Evidence Chain (`ultron.tasks.evidence`)
Every side-effecting action generates verifiable empirical evidence:
- `action` + `observation` + `verification` + `evidence_data`.
- For files: Workspace-relative path, size in bytes, SHA256 checksum, last modification timestamp.
- For browser: Final URL, page title, element text signature.
- Completion responses from ULTRON must cite verified evidence rather than ungrounded assumptions.

---

## 11. Production Diagnostics & Resource Monitoring (`ultron.diagnostics.system`)

- `get_runtime_diagnostics(workspace_root)` generates a sanitized diagnostic snapshot containing:
  - Runtime state (`INITIALIZING`, `RUNNING`, `PAUSED`, `STOPPED`)
  - Active goal and task state
  - Active plan version and current step
  - System telemetry: Process RSS RAM (MB), CPU usage (%), disk usage (MB), thread count
  - Browser session status
  - Task journal count and recent sanitized events
  - Zero sensitive data exposure (all tokens/keys/passwords filtered)

---

## 12. Security Audit & Isolation Summary

| Security Boundary | Mechanism | Verification Result |
| :--- | :--- | :--- |
| **Shell Execution** | Hard-blocked command whitelist & no arbitrary shell invocation | PASSED (Blocked) |
| **Workspace Sandbox** | Strict path normalization and path containment validation | PASSED (Enforced) |
| **Confirmation Vault** | Cryptographic token binding, single-use, in-memory only | PASSED (No Replay/Restart) |
| **Prompt Injection** | Web content wrapped in untrusted envelope, safety gate inspection | PASSED (Isolated) |
| **Secret Sanitization** | Regex patterns across all persistence, logs, and diagnostics | PASSED (Clean) |
| **Cancellation** | Sticky cancellation state persisted and enforced across restarts | PASSED (No Resurrection) |

---

## 13. Known Limitations & Scope Boundaries

1. **Frozen UI**: The Presence UI remains strictly frozen per requirements (no layout, design, or geometry modifications).
2. **No Local LLM**: ULTRON operates cloud intelligence via Gemini Live paired with local authoritative execution; local LLMs (e.g., Ollama) are omitted to preserve low memory footprint (<60MB RSS).
3. **OS-Level Permissions**: Desktop operations remain bounded by the local user's operating system permissions within the designated workspace.
