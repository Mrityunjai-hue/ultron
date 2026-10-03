"""
ULTRON — Automated Secret & Credential Scanner
─────────────────────────────────────────────────────────────────────────────
Scans repository source files, configuration files, test fixtures, documentation,
and release packaging trees for potential credential leaks.

CRITICAL SECURITY RULE:
Never outputs, prints, logs, or transforms secret values.
Outputs ONLY:
  FILE: <path> | LINE: <line_number> | TYPE: <classification> | REMEDIATION: <advice>
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Any

# Pattern definitions for sensitive data types
SECRET_PATTERNS = {
    "Google / Gemini API Key": re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    "GitHub Personal Access Token": re.compile(r"gh[pousr]_[0-9a-zA-Z]{36,255}"),
    "Generic High-Entropy API Key": re.compile(r"(?i)(api[_-]?key|secret[_-]?key|auth[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_\-\.]{20,}['\"]"),
    "Private Key Header": re.compile(r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP)?\s*PRIVATE\s+KEY"),
    "Hardcoded Password": re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{6,}['\"]"),
    "OAuth Bearer Header": re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{30,}"),
    "Database Connection String with Credentials": re.compile(r"(?i)(postgres|mysql|mongodb|redis|mssql):\/\/[^\s:]+:[^\s@]+@"),
    "AWS Access Key ID": re.compile(r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"),
    "Slack Token": re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"),
    "JWT Token": re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"),
}

# Allowlist for false positives in test cases or docs (e.g. synthetic regex definitions or scrubbed strings)
IGNORED_PATTERNS = [
    re.compile(r"AIza\[0-9A-Za-z"),  # Regex pattern definition
    re.compile(r"ghp_\[0-9a-zA-Z"),  # Regex pattern definition
    re.compile(r"AIzaSyDummyFakeKeyForTestingPurposes_"), # Synthetic test fixture
    re.compile(r"AIzaSyFakeKey"),
    re.compile(r"\[REDACTED_SECRET\]"),
    re.compile(r"FAKE_GEMINI_KEY"),
    re.compile(r"FAKE_PASSWORD"),
    re.compile(r"FAKE_TOKEN"),
    re.compile(r"your_api_key_here"),
    re.compile(r"\<YOUR_GEMINI_API_KEY\>"),
    re.compile(r"your_gemini_api_key_here"),
    re.compile(r"example_api_key"),
    re.compile(r"secret_api_token_"),
    re.compile(r"SuperSecret"),
    re.compile(r"MyPassword123!"),
    re.compile(r"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"),
    re.compile(r"dummy_test_api_key"),
    re.compile(r"test_dpapi_secret_key"),
]

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    ".pytest_cache",
    "__pycache__",
    "dist",
    "build",
    "node_modules",
    ".chrome_profile",
}

BINARY_EXTENSIONS = {
    ".pyc", ".pyd", ".exe", ".dll", ".so", ".dylib",
    ".png", ".jpg", ".jpeg", ".webp", ".ico", ".gif",
    ".tar", ".gz", ".zip", ".whl", ".bin"
}


def is_allowed_example(line: str) -> bool:
    """Checks if a match is an explicitly allowed documentation example or test pattern."""
    for allow_pat in IGNORED_PATTERNS:
        if allow_pat.search(line):
            return True
    return False


def scan_file(file_path: Path) -> List[Dict[str, Any]]:
    """Scans a single file for secret patterns."""
    findings = []
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return findings

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, 1):
                if is_allowed_example(line):
                    continue
                for secret_type, pattern in SECRET_PATTERNS.items():
                    if pattern.search(line):
                        findings.append({
                            "file": str(file_path.as_posix()),
                            "line": line_no,
                            "type": secret_type,
                            "remediation": "Remove secret, move to secure credential manager / environment, add to .gitignore"
                        })
    except Exception as e:
        pass
    return findings


def scan_directory(target_dir: Path) -> List[Dict[str, Any]]:
    """Recursively scans directory tree for credentials."""
    all_findings = []
    for root, dirs, files in os.walk(target_dir):
        # Filter ignored directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".venv")]
        for file in files:
            fp = Path(root) / file
            findings = scan_file(fp)
            all_findings.extend(findings)
    return all_findings


def main():
    parser = argparse.ArgumentParser(description="ULTRON Secret Discovery & Release Scanner")
    parser.add_argument("path", nargs="?", default=".", help="Root directory or file to scan")
    parser.add_argument("--fail-on-findings", action="store_true", help="Exit with non-zero code if secrets found")
    args = parser.parse_args()

    target = Path(args.path).resolve()
    print(f"[ULTRON Secret Scanner] Scanning '{target}'...")

    findings = []
    if target.is_file():
        findings = scan_file(target)
    else:
        findings = scan_directory(target)

    print("================================================================================")
    print(f" SCAN COMPLETED — Total Findings: {len(findings)}")
    print("================================================================================")

    for item in findings:
        # ABSOLUTE RULE: Never print or reveal the secret value!
        print(f"FILE: {item['file']} | LINE: {item['line']} | TYPE: {item['type']} | REMEDIATION: {item['remediation']}")

    print("================================================================================")

    if findings and args.fail_on_findings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
