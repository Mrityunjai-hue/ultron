# ULTRON — PHASE 11: SECRET BOUNDARY & CREDENTIAL LIFECYCLE

## 1. Absolute Security Mandate

ULTRON operates under a strict **Zero Credential Leakage Boundary**. At no point may API keys, bearer tokens, OAuth credentials, passwords, cookies, or private tokens be exposed across logs, UI, memory, journal, evidence chains, crash reports, GitHub Actions, installers, or release artifacts.

---

## 2. Credential Flow & Lifecycle

The lifecycle of the Gemini API Key adheres to the following unidirectional, tightly scoped flow:

```
┌─────────────────────────────────────────────────────────┐
│                   USER PROVISIONING                     │
│  - Windows DPAPI Store (%LOCALAPPDATA%/ULTRON/config)   │
│  - Or Process Environment Variable (GEMINI_API_KEY)     │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│             SecureCredentialManager                     │
│  - In-memory decrypt on demand                          │
│  - Non-revealing boolean presence checks                │
└────────────────────────────┬────────────────────────────┘
                             │ (Passed ONLY to genai.Client)
                             ▼
┌─────────────────────────────────────────────────────────┐
│            GeminiLiveProvider.__init__()                │
│  - genai.Client(api_key=...)                            │
│  - Transient client object for WebSocket TLS handshake │
└────────────────────────────┬────────────────────────────┘
                             │ (TLS Encrypted Traffic)
                             ▼
┌─────────────────────────────────────────────────────────┐
│             Google Gemini Live Backend                  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Explicit Prohibition Matrix

| Subsystem / Surface | Policy | Enforcement Mechanism |
| :--- | :--- | :--- |
| **Gemini Model Prompts & Context** | **STRICTLY PROHIBITED** | Prompts contain only high-level task instructions and sanitized tool schemas. |
| **Goal Planner & Task Context** | **STRICTLY PROHIBITED** | `TaskContext` and `GoalPlanner` run all inputs/outputs through `scrub_secrets()`. |
| **Persistent Memory** | **STRICTLY PROHIBITED** | `PersistentMemory.remember()` validates all keys and values against `FORBIDDEN_KEY_PATTERNS` and `SECRET_PATTERNS`. |
| **Task Checkpoints & State** | **STRICTLY PROHIBITED** | `TaskPersistenceManager.persist_goal_state()` scrubs all state dictionaries prior to JSON serialization and SHA256 checksumming. |
| **Execution Journal** | **STRICTLY PROHIBITED** | `TaskJournal.record()` redacts all metadata keys matching auth, token, password, or bearer patterns. |
| **Evidence Chains** | **STRICTLY PROHIBITED** | `EvidenceRecorder.record()` scrubs file paths and payload metadata. |
| **System Diagnostics** | **STRICTLY PROHIBITED** | `ultron --diagnostics` reports only boolean presence (`has_gemini_api_key: true`), storage type (`WINDOWS_DPAPI`), and version strings. |
| **Health Check** | **STRICTLY PROHIBITED** | `ultron --health` outputs structured status without returning or displaying API key values. |
| **Application & Crash Logs** | **STRICTLY PROHIBITED** | `SecretSanitizingFilter` intercepts all Python `logging.LogRecord` instances and masks regex-matched credentials before writing to disk or stdout. |
| **Presence UI** | **STRICTLY PROHIBITED** | Pure Win32 GDI overlay receives only audio visualizer waveforms, state machine states, and task titles. |
| **GitHub Actions Workflows** | **STRICTLY PROHIBITED** | Workflows run secret-free for CI. Release jobs pass minimum tokens strictly via GitHub secret context without echoing or CLI argument interpolation. |
| **Release Artifacts & Installers** | **STRICTLY PROHIBITED** | Pre-release and post-build secret scanners inspect the entire distribution bundle. Any match fails the release immediately. |

---

## 4. Remediation & Gating

If any credential or high-entropy key is detected by the automated scanner in any artifact or log:
1. The build or release workflow **FAILS CLOSED**.
2. The scanner outputs ONLY `FILE`, `LINE`, `TYPE`, and `REMEDIATION`.
3. Secret values are **NEVER** echoed, transformed, or printed.
