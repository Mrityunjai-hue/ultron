# Contributing to ULTRON

Thank you for your interest in contributing to ULTRON! We welcome contributions from the community.

---

## Development Setup

### 1. Prerequisites
- **Operating System**: Windows 10 (Build 19041+) or Windows 11
- **Python**: Python 3.10, 3.11, 3.12, or 3.14
- **Git**: 2.30+

### 2. Setting Up Your Environment
```powershell
# 1. Clone the repository
git clone https://github.com/Mrityunjai-hue/ultron.git
cd ultron

# 2. Create isolated virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install development and build dependencies
pip install -r requirements.txt
pip install -r requirements-build.txt
```

---

## Quality & Security Invariants

All contributions must satisfy the following strict standards before being merged:

### 1. 100% Test Pass Rate
All existing tests across core runtime, audio streaming, tools, tasks, browser automation, adversarial security, onboarding, and release pipelines must pass without regression:
```powershell
python -m pytest tests -v
```

### 2. Zero Secret Scanner Findings
The automated secret scanner must report zero findings across all source files and assets:
```powershell
python scripts/secret_scanner.py . --fail-on-findings
```

### 3. Architecture & Safety Preservation
- **Never bypass the 3-tier security gateway**: Tool executions must route through `PolicyVerdict` checks (`SAFE`, `CONFIRM_REQUIRED`, `BLOCKED`).
- **Never allow arbitrary shell execution**: Direct invocation of `cmd.exe`, `powershell.exe`, or `bash.exe` is prohibited.
- **Never log plaintext credentials**: Use `ultron.core.logging_sanitizer` for all logging and diagnostic output.
- **Isolate user data**: All mutable state must reside under `%LOCALAPPDATA%\ULTRON\`, never in the repository root or `Program Files`.

---

## Code Style & Commit Conventions

- Use standard Python typing hints (`from __future__ import annotations`).
- Format commits using Conventional Commits:
  - `feat(component): add new capability`
  - `fix(security): resolve policy edge case`
  - `docs(readme): clarify installation steps`
  - `test(runtime): add regression test for audio underflow`

---

## Submitting Pull Requests

1. Fork the repository and create your feature branch: `git checkout -b feat/my-new-feature`.
2. Ensure your changes adhere to code style, safety invariants, and pass all tests.
3. Run `python scripts/secret_scanner.py .` to ensure no credentials or tokens are staged.
4. Submit a pull request against the `main` branch with a clear description of the problem solved and test evidence.
