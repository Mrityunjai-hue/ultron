# Security Policy

## Reporting Security Issues

We take the security of ULTRON seriously. If you discover a security vulnerability or potential exposure in ULTRON, please disclose it responsibly.

### Reporting Process
1. **Do not open public GitHub issues for security vulnerabilities.**
2. Send an email with vulnerability details, reproduction steps, and potential impact to:
   **security@ultron-ai.local** (or submit a Private Vulnerability Report via GitHub Security Advisories).
3. We will acknowledge receipt of your vulnerability report within 48 hours and provide an estimated timeline for a patch.

---

## Security Invariants & Policy

ULTRON operates under a strict **Zero-Trust Local Execution Model**:

### 1. 3-Tier Execution Policy
- **`SAFE` (Tier 1)**: Read-only system telemetry (`get_current_time`, `get_system_status`), workspace-sandboxed file reading (`read_file`, `list_directory`), and safe application launching (`open_app`). Executed automatically without user intervention.
- **`CONFIRM_REQUIRED` (Tier 2)**: File modification (`write_file`), deletion (`delete_file`), file movements (`move_file`), application termination (`close_app`), and browser file downloads (`chrome_download_file`). Requires explicit user confirmation via a single-use cryptographic token.
- **`BLOCKED` (Tier 3)**: Execution of arbitrary shell interpreters (`cmd.exe`, `powershell.exe`, `pwsh.exe`, `bash.exe`, `wsl.exe`), command injection sequences (`&`, `|`, `;`, `>`, `<`, `` ` ``, `$`, `\n`), system directory escapes (`C:\Windows`, `C:\Program Files`), and critical operating system process terminations (`csrss`, `lsass`, `services`, `explorer`). Permanently rejected before execution.

### 2. Single-Use Cryptographic Confirmation Tokens
Destructive actions generate a unique token:
$$\text{Token} = \text{HMAC-SHA256}(\text{Tool} \parallel \text{Target} \parallel \text{SessionID} \parallel \text{Salt})$$
- Valid for exactly 60 seconds (TTL expiration).
- Single-use only (burned upon evaluation).
- Replay and parameter tampering immune.

### 3. Credential Protection
- API keys are encrypted at rest using user-bound **Windows DPAPI** (`CryptProtectData`) stored in `%LOCALAPPDATA%\ULTRON\config\credentials.dpapi`.
- Decrypted keys exist only in volatile memory during active API client initialization and are never logged, printed, or exported in diagnostics.

### 4. Continuous Secret Discovery Scanning
- Automated secret scanning is enforced on every commit and pull request via `scripts/secret_scanner.py`.
- Releases fail closed if any credential pattern is discovered in source or build artifacts.

---

## Supported Versions

| Version | Supported | Security Updates |
| :--- | :---: | :--- |
| `0.1.x` | ✅ | Active Support & Security Patches |
| `< 0.1.0` | ❌ | End of Life |
