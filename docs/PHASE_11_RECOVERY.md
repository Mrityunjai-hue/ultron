# ULTRON — PHASE 11: CRASH RECOVERY, RESILIENCE & INTEGRITY SPECIFICATION

## 1. Resilience Architecture

ULTRON implements deterministic, crash-safe execution recovery across all task planning, browser automation, and audio session operations.

```
┌─────────────────────────────────────────────────────────┐
│               UNEXPECTED CRASH OCCURS                   │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│             NEW PROCESS BOOT / INITIALIZING             │
│  - Acquires SingleInstanceLock                          │
│  - Startup circuit breaker verifies crash history       │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│              TASK RECOVERY & INTEGRITY AUDIT            │
│  - Inspects %LOCALAPPDATA%/ULTRON/tasks/goal_*.json     │
│  - Verifies SHA256 payload checksums                    │
│  - Quarantines corrupted files to *.corrupted           │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│             NON-RESURRECTION POLICY CHECK               │
│  - Expired confirmations -> DISCARDED                   │
│  - Cancelled tasks -> MARKED CANCELLED                  │
│  - Non-idempotent side-effects -> NO BLIND RETRY        │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Integrity Guarantees

1. **Atomic Checkpoint Writes:** All goal states and plans are saved via temporary write and atomic rename (`tmp_*.json` -> `goal_*.json`). Half-written states are impossible.
2. **Corrupted State Quarantine:** If a persisted state file has a mismatched SHA256 checksum, the engine isolates it with `.corrupted` and emits an alert without crashing the runtime.
3. **Journal Audit Trail:** Append-only JSONL journal (`journal.jsonl`) records each step transition, verification, and dynamic replan.
4. **Startup Circuit Breaker:** If 3 consecutive crashes occur within 120 seconds, the automatic startup launch is tripped and disabled, preventing boot loops.

---

## 3. Manual Recovery Procedures

### Resetting Single-Instance Lock
If a hard crash leaves a stale lockfile:
```powershell
Remove-Item "$env:LOCALAPPDATA\ULTRON\cache\*.lock" -Force
```

### Resetting Startup Circuit Breaker
```powershell
python -c "from ultron.core.startup import StartupManager; StartupManager().reset_circuit_breaker()"
```
