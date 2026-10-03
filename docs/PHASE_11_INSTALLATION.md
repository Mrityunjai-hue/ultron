# ULTRON — PHASE 11: INSTALLATION & DEPLOYMENT GUIDE

## 1. Distribution Overview

ULTRON is distributed as a self-contained, standalone Windows desktop application. It requires **no Python installation**, **no Git**, **no development toolchain**, and **no repository checkout**.

Two official release formats are provided for each version on GitHub Releases:
1. **Self-Extracting Setup Installer (`Ultron-Setup-X.Y.Z.exe` / `.py`):** Recommended for all desktop users.
2. **Portable Standalone Bundle (`Ultron-vX.Y.Z-windows-x64.zip`):** Recommended for power users and enterprise environments.

---

## 2. Standard Installation Procedure

### 2.1 Using the Setup Installer
1. Download `Ultron-Setup-0.1.0.py` (or compiled `.exe`) from the official GitHub Release.
2. Run the setup installer:
   ```powershell
   python Ultron-Setup-0.1.0.py
   ```
   *(Or double-click `Ultron-Setup-0.1.0.exe`)*
3. The installer extracts all binaries to `%LOCALAPPDATA%\Programs\ULTRON` and creates:
   - Start Menu entry in `Programs\ULTRON.lnk`
   - Uninstaller `unins000.py` / `unins000.exe` in the application directory.

### 2.2 Using the Portable Archive
1. Download `Ultron-v0.1.0-windows-x64.zip` and extract to any local directory.
2. Run `ultron.exe` directly.

---

## 3. Post-Installation Verification

Open Windows Terminal or PowerShell and run:
```powershell
# Verify application version
ultron.exe --version

# Verify system health and readiness
ultron.exe --health

# Output machine-readable runtime diagnostics
ultron.exe --diagnostics
```

---

## 4. Upgrade & Migration

Upgrading to a newer version (e.g. `v0.1.0` -> `v0.1.1`):
1. Download the new release package.
2. Run the installer or overwrite application binaries in `%LOCALAPPDATA%\Programs\ULTRON`.
3. **User State Preservation:** All user memories (`memory/`), active tasks (`tasks/`), configurations (`config/`), and logs (`logs/`) reside in `%LOCALAPPDATA%\ULTRON\` and are untouched during binary upgrades.

---

## 5. Uninstallation

Run the uninstaller located in the application directory:
```powershell
python "%LOCALAPPDATA%\Programs\ULTRON\unins000.py"
```
To purge all user data, pass `--purge-data`:
```powershell
python "%LOCALAPPDATA%\Programs\ULTRON\unins000.py" --purge-data
```
The uninstaller cleanly removes:
- Application binaries
- Start Menu shortcuts
- Desktop shortcuts
- Windows startup registry entries
