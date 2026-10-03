# ULTRON — PHASE 11: CONFIGURATION & CREDENTIAL MANAGEMENT GUIDE

## 1. Configuration Philosophy

ULTRON strictly isolates configuration into four independent domains:
1. **Immutable Application Defaults:** Compiled into the application binary (sample rates, model IDs, frame sizes).
2. **Non-Sensitive User Preferences:** Stored in `%LOCALAPPDATA%\ULTRON\config\settings.json`.
3. **Protected Credentials:** Encrypted with **Windows DPAPI (Data Protection API)** or retrieved from process environment.
4. **Mutable Runtime State:** Stored across `%LOCALAPPDATA%\ULTRON\` subdirectories.

---

## 2. Secure Credential Provisioning

### 2.1 Recommended: Windows DPAPI Encrypted Storage
To store the Gemini API key encrypted locally with Windows user credentials:
```powershell
ultron.exe --set-api-key "your_gemini_api_key_here"
```
- The key is encrypted via Win32 `CryptProtectData` and stored in `%LOCALAPPDATA%\ULTRON\config\credentials.dpapi`.
- Only the currently logged-in Windows user can decrypt the file.
- Plaintext keys are NEVER written to disk or logs.

### 2.2 Alternative: Environment Variables (CI / Headless)
For development, automated testing, or CI/CD pipelines:
```powershell
$env:GEMINI_API_KEY = "your_gemini_api_key_here"
```

---

## 3. Windows Startup Management

ULTRON supports optional user-controlled automatic launch upon Windows login:
```powershell
# Enable startup launch
ultron.exe --enable-startup

# Disable startup launch
ultron.exe --disable-startup
```
- Uses standard non-admin HKCU registry key: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
- Protected by a **Startup Circuit Breaker** that halts automatic relaunch if 3 consecutive crashes occur within 120 seconds.

---

## 4. Environment Variables Reference

| Variable | Description | Default |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Primary Gemini multimodal API key | *(Loaded from DPAPI)* |
| `ULTRON_DATA_DIR` | Custom override for user data directory | `%LOCALAPPDATA%\ULTRON` |
| `ULTRON_CONFIG_DIR` | Custom override for configuration directory | `%LOCALAPPDATA%\ULTRON\config` |
| `ULTRON_LOG_LEVEL` | Logging verbosity (`INFO`, `DEBUG`, `WARNING`) | `INFO` |
