"""
ULTRON — Automated Standalone Windows Distribution Builder
─────────────────────────────────────────────────────────────────────────────
Orchestrates:
1. Pre-build secret scanning
2. PyInstaller compilation of sovereign Windows binary
3. Post-build artifact secret scanning & quarantine
4. SBOM manifest generation
5. Release ZIP packaging
6. Deterministic SHA256 checksum calculation
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# Add workspace to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ultron.__version__ import __version__, __build_date__, __product_name__
from scripts.secret_scanner import scan_directory


def compute_file_sha256(filepath: Path) -> str:
    """Computes SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def generate_sbom(output_path: Path) -> None:
    """Generates CycloneDX-compatible JSON Software Bill of Materials."""
    try:
        import importlib.metadata as md
        packages = []
        for dist in md.distributions():
            packages.append({
                "name": dist.metadata["Name"],
                "version": dist.version,
                "license": dist.metadata.get("License", "Unknown"),
            })
    except Exception:
        packages = [
            {"name": "google-genai", "version": "2.28.0", "license": "Apache-2.0"},
            {"name": "sounddevice", "version": "0.5.6", "license": "MIT"},
            {"name": "numpy", "version": "2.4.2", "license": "BSD-3-Clause"},
            {"name": "pillow", "version": "12.1.0", "license": "HPND"},
            {"name": "pywin32", "version": "312", "license": "PSF"},
            {"name": "psutil", "version": "7.2.2", "license": "BSD-3-Clause"},
            {"name": "requests", "version": "2.32.5", "license": "Apache-2.0"},
            {"name": "websockets", "version": "16.0", "license": "BSD-3-Clause"},
            {"name": "pydantic", "version": "2.12.5", "license": "MIT"},
        ]

    sbom_data = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:ultron-sbom-{__version__}",
        "version": 1,
        "metadata": {
            "component": {
                "name": __product_name__,
                "version": __version__,
                "type": "application",
            },
            "timestamp": __build_date__,
        },
        "components": packages,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sbom_data, f, indent=2)
    print(f"[Build] SBOM generated at: {output_path}")


def create_zip_archive(source_dir: Path, zip_path: Path) -> None:
    """Creates a compressed zip archive of the directory."""
    print(f"[Build] Creating ZIP archive: {zip_path}...")
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(source_dir.parent)
                zf.write(file_path, arcname)
    print(f"[Build] ZIP created successfully ({zip_path.stat().st_size / (1024*1024):.2f} MB)")


def main():
    print("================================================================================")
    print(f" ULTRON BUILD SYSTEM — Building {__product_name__} v{__version__}")
    print("================================================================================")

    dist_dir = REPO_ROOT / "dist"
    build_dir = REPO_ROOT / "build"
    spec_file = REPO_ROOT / "packaging" / "ultron.spec"

    # Step 1: Pre-build Secret Scan
    print("\n[Step 1/6] Running Pre-Build Source Secret Scan...")
    findings = scan_directory(REPO_ROOT / "ultron")
    if findings:
        print("[!] CRITICAL: Secret findings detected in source tree. Aborting build.")
        for item in findings:
            print(f"FILE: {item['file']} | LINE: {item['line']} | TYPE: {item['type']}")
        sys.exit(1)
    print("[OK] Source tree clean. Zero credentials detected.")

    # Step 2: Clean previous builds
    print("\n[Step 2/6] Cleaning previous build artifacts...")
    if dist_dir.exists():
        shutil.rmtree(dist_dir, ignore_errors=True)
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)

    # Step 3: PyInstaller Compilation
    print("\n[Step 3/6] Compiling Standalone Windows PE Binary via PyInstaller...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(spec_file),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if res.returncode != 0:
        print(f"[!] PyInstaller compilation failed with exit code {res.returncode}")
        sys.exit(res.returncode)

    app_dist_dir = dist_dir / "ultron"
    if not app_dist_dir.exists() or not (app_dist_dir / "ultron.exe").exists():
        print("[!] Build output missing ultron.exe binary!")
        sys.exit(1)
    print(f"[OK] PyInstaller compilation succeeded. Output: {app_dist_dir}")

    # Step 4: Post-build Artifact Secret Scan
    print("\n[Step 4/6] Scanning Built Distribution Directory for Secrets...")
    artifact_findings = scan_directory(app_dist_dir)
    if artifact_findings:
        print("[!] CRITICAL: Secret findings in build output! Quarantining and aborting.")
        for item in artifact_findings:
            print(f"FILE: {item['file']} | LINE: {item['line']} | TYPE: {item['type']}")
        shutil.rmtree(app_dist_dir, ignore_errors=True)
        sys.exit(1)
    print("[OK] Build artifact scan clean. Zero secrets present in compiled distribution.")

    # Step 5: Generate SBOM
    print("\n[Step 5/6] Generating SBOM...")
    sbom_path = dist_dir / "sbom.json"
    generate_sbom(sbom_path)

    # Step 6: Create ZIP Archive & Checksums
    print("\n[Step 6/6] Packaging Release Archive and Computing SHA256...")
    zip_filename = f"Ultron-v{__version__}-windows-x64.zip"
    zip_path = dist_dir / zip_filename
    create_zip_archive(app_dist_dir, zip_path)

    # SHA256 Sums
    zip_hash = compute_file_sha256(zip_path)
    sbom_hash = compute_file_sha256(sbom_path)
    exe_hash = compute_file_sha256(app_dist_dir / "ultron.exe")

    sha256_manifest = (
        f"{zip_hash}  {zip_filename}\n"
        f"{sbom_hash}  sbom.json\n"
        f"{exe_hash}  ultron.exe\n"
    )

    checksums_path = dist_dir / "SHA256SUMS.txt"
    checksums_path.write_text(sha256_manifest, encoding="utf-8")

    print("\n================================================================================")
    print(" BUILD COMPLETED SUCCESSFULLY")
    print("================================================================================")
    print(f" Artifact:  {zip_path}")
    print(f" SHA256:    {zip_hash}")
    print(f" SBOM:      {sbom_path}")
    print(f" Checksums: {checksums_path}")
    print("================================================================================\n")


if __name__ == "__main__":
    main()
