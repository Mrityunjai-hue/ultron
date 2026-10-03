# ULTRON — SECURE GITHUB RELEASE SUPPLY CHAIN & DISTRIBUTION PROCESS

## 1. Overview & Architecture

ULTRON establishes an immutable, cryptographic release engineering supply chain connecting authoritative local source, GitHub Actions, and standalone Windows execution. The system guarantees zero sensitive credential or personal identity leakage at every transition point.

```
[ LOCAL SOURCE ] (Authoritative Repo, v0.1.0)
       ↓
[ PRE-COMMIT / GITHUB PUSH ]
       ↓
[ GITHUB ACTIONS CI ] (.github/workflows/ci.yml)
       │ • Pinned Action SHAs
       │ • Least-Privilege Permissions (contents: read)
       │ • Automated Secret Discovery Scan
       │ • Full 265-Test Regression Baseline
       │ • Standalone PyInstaller Compilation Test
       ↓
[ GIT VERSION TAG PUSH (v0.1.0) ]
       ↓
[ GITHUB ACTIONS RELEASE ] (.github/workflows/release.yml)
       │ • Tag Alignment Verification (v0.1.0 == __version__)
       │ • Source Secret Scan (Fail-Closed)
       │ • 265/265 Regression Suite
       │ • Windows Production PyInstaller Build
       │ • Distribution Artifact Secret Quarantine Scan
       │ • Inno Setup / Python Self-Contained Installer Generation
       │ • CycloneDX 1.4 SBOM Generation
       │ • Immutable SHA256 Digests (SHA256SUMS.txt)
       │ • Machine-Readable RELEASE_MANIFEST.json
       │ • GitHub Artifact Provenance Attestation
       ↓
[ GITHUB RELEASE PUBLICATION ] (ULTRON v0.1.0)
       │ • Ultron-v0.1.0-windows-x64.zip
       │ • Ultron-Setup-0.1.0.py
       │ • SHA256SUMS.txt
       │ • sbom.json
       │ • RELEASE_MANIFEST.json
       ↓
[ DOWNSTREAM CONSUMER / USER MACHINE ]
       │ • Download Release Assets
       │ • Verify SHA256 & Attestation Signature
       │ • Run Standalone Installer
       ↓
[ ISOLATED LOCAL RUNTIME ]
       │ • Physical First-Run Liquid Onboarding
       │ • User Configuration saved to %LOCALAPPDATA%\ULTRON\
       │ • Liquid Collapse to Compact Notch
       │ • Sovereign Autonomous Operation
```

---

## 2. GitHub Actions Security & Least-Privilege Model

All CI/CD workflows enforce strict principle-of-least-privilege permissions and immutable SHA-pinned actions:

### A. CI Workflow (`.github/workflows/ci.yml`)
- **Triggers:** Pull requests and pushes to `main`/`master`
- **Permissions:** `contents: read` (Default zero-write access)
- **Pinned Actions:**
  - `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683` (`v4.2.2`)
  - `actions/setup-python@42375524e23c412d93fb67b49958b491fce71c38` (`v5.4.0`)
- **Gates:**
  1. Secret discovery scan (`scripts/secret_scanner.py . --fail-on-findings`)
  2. Full 265-test regression suite
  3. Standalone build compilation verification
  4. SBOM and checksum validity checks

### B. Release Workflow (`.github/workflows/release.yml`)
- **Triggers:** Push of tags matching `v[0-9]+.[0-9]+.[0-9]+`
- **Scoped Permissions:**
  ```yaml
  permissions:
    contents: write
    id-token: write
    attestations: write
  ```
- **Pinned Actions:**
  - `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683` (`v4.2.2`)
  - `actions/setup-python@42375524e23c412d93fb67b49958b491fce71c38` (`v5.4.0`)
  - `actions/attest-build-provenance@c074443f1a5fb4aee83904b71241430048d93b62` (`v2.2.3`)
  - `softprops/action-gh-release@c95fe1489396fe8a9eb87c0abf8aa5b2ef267fda` (`v2.2.1`)
- **Fail-Closed Gates:**
  1. **Gate 0:** Verifies `${{ github.ref_name }}` strictly equals `v` + `__version__`
  2. **Gate 1:** Repository pre-build secret scan
  3. **Gate 2:** Complete 265-test regression run
  4. **Gate 3:** Standalone PE binary build & post-build artifact quarantine scan
  5. **Gate 4:** Windows setup package generation
  6. **Gate 5:** Cryptographic SHA256 & `RELEASE_MANIFEST.json` generation
  7. **Gate 6:** Artifact build provenance attestation
  8. **Gate 7:** GitHub Release publication

---

## 3. Cryptographic Provenance & Release Manifest

Every release artifact is accompanied by immutable digests and machine-readable metadata:

### `RELEASE_MANIFEST.json` Structure
```json
{
  "application": "ULTRON",
  "version": "0.1.0",
  "platform": "windows",
  "architecture": "x86_64",
  "git_commit": "<COMMIT_SHA>",
  "build_workflow": "ULTRON Release — Authoritative Windows Distribution",
  "artifact": "Ultron-v0.1.0-windows-x64.zip",
  "artifact_size_bytes": 62820000,
  "artifact_size_mb": "59.91 MB",
  "sha256": "9cde70382b0efc7b2f210cf3d2ad5a091bfd3d3164c92a4300ce08a5bdeb6c1e",
  "installer": {
    "name": "Ultron-Setup-0.1.0.py",
    "sha256": "<INSTALLER_SHA256>",
    "size_bytes": 10707
  },
  "sbom": {
    "name": "sbom.json",
    "format": "CycloneDX 1.4",
    "sha256": "<SBOM_SHA256>"
  },
  "build_timestamp": "2026-10-03",
  "test_status": "265/265 PASSED",
  "attestation_status": "PROVENANCE_READY"
}
```

---

## 4. Local Verification & Installation Procedure

### Step 1: Download Release Assets
Download `Ultron-v0.1.0-windows-x64.zip` and `SHA256SUMS.txt` from the authoritative GitHub Release.

### Step 2: Verify Checksum
In Windows PowerShell:
```powershell
Get-FileHash -Algorithm SHA256 Ultron-v0.1.0-windows-x64.zip
Get-Content SHA256SUMS.txt
```
Verify that the output hash strictly matches the entry in `SHA256SUMS.txt`.

### Step 3: Verify Attestation (Optional via GitHub CLI)
```bash
gh attestation verify Ultron-v0.1.0-windows-x64.zip --owner <ORG_OR_USER>
```

### Step 4: Installation
Run the installer or extract the portable archive:
```text
C:\Program Files\ULTRON\
├── ultron.exe
└── _internal\
```

---

## 5. Physical User Data Boundary & Upgrade Lifecycle

### A. Separation of Application Binaries vs. User State
- **Application Binaries:** `C:\Program Files\ULTRON\` (Read-only for standard users)
- **User Configuration & State:** `%LOCALAPPDATA%\ULTRON\`
  - `user_config.json` — Preferences and identity
  - `credentials.enc` — Hardware/user DPAPI encrypted credentials
  - `memory/` — Long-term semantic memory graph
  - `tasks/` — Task execution journal
  - `logs/` — Rotating application logs

### B. Upgrade Procedure (v0.1.0 → v0.1.1)
- Upgrading replaces binary files in `C:\Program Files\ULTRON\`.
- All user configurations, DPAPI credentials, task journals, and memory nodes in `%LOCALAPPDATA%\ULTRON\` remain untouched and 100% persistent.

### C. Clean Uninstallation Procedure
- Uninstaller removes `C:\Program Files\ULTRON\`, Start Menu shortcuts, and HKCU startup registry entries.
- User data in `%LOCALAPPDATA%\ULTRON\` is preserved unless the user explicitly requests complete data removal.

---

## 6. Privacy Guarantees & Secret Boundaries

1. **Zero Credential Transmission:** The GitHub build runner never receives user API keys or personal configuration.
2. **Sanitized Diagnostics & Logs:** Diagnostics outputs `configuration_present: true` without personal names (`OWNER_NAME = <REDACTED>`).
3. **Artifact Quarantine:** Distribution archives are scanned to ensure no `.env`, `.key`, `task_journal.jsonl`, or user configuration files are ever packaged into release builds.
