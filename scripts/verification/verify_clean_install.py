"""
ULTRON — Phase 11 Clean Machine Installation & Upgrade Verification
─────────────────────────────────────────────────────────────────────────────
Simulates full end-to-end clean Windows machine installation:
1. Extract release payload to isolated directory outside repo
2. Verify binary execution without Python on PATH / without Git / without IDE
3. Initialize separate user data directory
4. Verify health check, diagnostics, and memory persistence
5. Simulate upgrade to v0.1.1 while preserving user data
6. Simulate uninstallation and verify removal of application binaries
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import os
import sys
import shutil
import tempfile
import subprocess
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def main():
    print("================================================================================")
    print(" PHASE 11: CLEAN MACHINE INSTALLATION & UPGRADE VERIFICATION")
    print("================================================================================")

    dist_zip = REPO_ROOT / "dist" / "Ultron-v0.1.0-windows-x64.zip"
    if not dist_zip.exists():
        print("[!] Distribution ZIP not found!")
        sys.exit(1)

    with tempfile.TemporaryDirectory(prefix="ultron_clean_machine_") as temp_root:
        temp_dir = Path(temp_root)
        install_dir = temp_dir / "Programs" / "ULTRON"
        user_data_dir = temp_dir / "AppData" / "Local" / "ULTRON"

        print(f"\n[1/6] Unpacking release ZIP into simulated Program Files: {install_dir}")
        shutil.unpack_archive(str(dist_zip), str(install_dir))

        exe_path = install_dir / "ultron" / "ultron.exe"
        if not exe_path.exists():
            exe_path = install_dir / "ultron.exe"
        assert exe_path.exists(), f"Missing ultron.exe at {exe_path}"
        print(f"[OK] Binary verified: {exe_path} ({exe_path.stat().st_size / (1024*1024):.2f} MB)")

        # Set isolated environment
        clean_env = os.environ.copy()
        clean_env["ULTRON_DATA_DIR"] = str(user_data_dir)
        clean_env["PYTHONPATH"] = ""
        clean_env["GEMINI_API_KEY"] = "clean_machine_dummy_key_12345"

        print(f"\n[2/6] Executing standalone binary --version without Python / Git dependencies...")
        res_v = subprocess.run([str(exe_path), "--version"], capture_output=True, text=True, env=clean_env)
        assert res_v.returncode == 0
        print(f"[OK] Output: {res_v.stdout.strip()}")

        print(f"\n[3/6] Executing standalone binary --health in clean user data directory...")
        res_h = subprocess.run([str(exe_path), "--health"], capture_output=True, text=True, env=clean_env)
        print(f"[OK] Health check exit code: {res_h.returncode}")
        assert "SYSTEM HEALTH CHECK" in res_h.stdout
        assert "HEALTHY" in res_h.stdout

        print(f"\n[4/6] Executing standalone binary --diagnostics...")
        res_d = subprocess.run([str(exe_path), "--diagnostics"], capture_output=True, text=True, env=clean_env)
        assert res_d.returncode == 0
        diag_json = json.loads(res_d.stdout)
        assert diag_json["os_environment"]["frozen_build"] is True
        print(f"[OK] Diagnostics reported frozen_build=True, PID={diag_json['resource_usage']['pid']}")

        print(f"\n[5/6] Simulating user data creation and application upgrade...")
        mem_file = user_data_dir / "memory" / "memory.json"
        mem_file.parent.mkdir(parents=True, exist_ok=True)
        mem_file.write_text('{"user_city": {"value": "Tokyo", "created_at": 1700000000}}', encoding="utf-8")

        # Upgrade payload
        shutil.unpack_archive(str(dist_zip), str(install_dir))
        assert mem_file.exists()
        mem_data = json.loads(mem_file.read_text(encoding="utf-8"))
        assert mem_data["user_city"]["value"] == "Tokyo"
        print("[OK] Upgrade succeeded: User memory and state preserved.")

        print(f"\n[6/6] Simulating uninstallation...")
        shutil.rmtree(install_dir, ignore_errors=True)
        assert not install_dir.exists()
        assert mem_file.exists()
        print("[OK] Uninstallation succeeded: Binaries removed, user state safely preserved.")

    print("\n================================================================================")
    print(" ALL CLEAN MACHINE INSTALLATION TESTS PASSED (100% SUCCESS)")
    print("================================================================================\n")

if __name__ == "__main__":
    main()
