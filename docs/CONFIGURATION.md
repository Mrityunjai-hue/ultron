# ULTRON Configuration & Storage Boundaries

ULTRON strictly isolates mutable user data, credentials, task history, and logs from application binaries and repository code.

---

## Physical Storage Boundaries

All mutable user data is anchored strictly inside Windows `%LOCALAPPDATA%\ULTRON\`:

| Category | Canonical File / Directory Path | Purpose & Security Guarantee |
| :--- | :--- | :--- |
| **Application Binaries** | `C:\Program Files\ULTRON\` | Read-only application code; zero runtime disk writes |
| **User Configuration** | `%LOCALAPPDATA%\ULTRON\config\user_config.json` | Non-sensitive preferences, atomic file swap write |
| **Encrypted Credentials** | `%LOCALAPPDATA%\ULTRON\config\credentials.dpapi` | Windows DPAPI hardware-backed encryption |
| **Task Journal & Checkpoints** | `%LOCALAPPDATA%\ULTRON\tasks\` | Append-only execution journal & evidence chains |
| **Semantic Memory** | `%LOCALAPPDATA%\ULTRON\memory\` | Bounded facts store with automated secret redaction |
| **Sanitized Logs** | `%LOCALAPPDATA%\ULTRON\logs\` | 10MB rotating logs with real-time regex sanitization |
| **Runtime Cache** | `%LOCALAPPDATA%\ULTRON\cache\` | Temporary cache & CDP browser session profiles |

---

## Configuration Schema (`user_config.json`)

User preferences configured during the **First-Run Liquid Onboarding Experience** are persisted to `%LOCALAPPDATA%\ULTRON\config\user_config.json`:

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

### Self-Healing Guarantee
If `user_config.json` becomes corrupted, ULTRON automatically resets user configuration safely to defaults without crashing or corrupting DPAPI credential stores.

---

## Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API Key (Fallback if DPAPI store empty) | None |
| `GOOGLE_API_KEY` | Secondary alias for Gemini API key | None |
| `ULTRON_DATA_DIR` | Custom override root directory for user data (Testing / Portable) | `%LOCALAPPDATA%\ULTRON` |
