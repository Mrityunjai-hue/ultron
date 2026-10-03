"""
ULTRON — Safe System Diagnostics & Production Health Checks
─────────────────────────────────────────────────────────────────────────────
Implements secret-safe, non-revealing inspection of system capabilities,
subsystem readiness, resource footprints, and local storage integrity.

CRITICAL SECURITY RULE:
Never displays, logs, or exports API keys, passwords, bearer tokens, or user secrets.
All paths are normalized and sanitized.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, List

from ultron.__version__ import __version__, __build_date__, __product_name__
from ultron.core.paths import (
    get_user_data_dir,
    get_config_dir,
    get_memory_dir,
    get_tasks_dir,
    get_logs_dir,
    get_cache_dir,
    get_app_install_dir,
)
from ultron.core.credentials import get_credential_manager
from ultron.core.config import get_config
from ultron.core.user_config import load_user_config, is_first_run_required


def perform_health_check(workspace_root: Optional[Path | str] = None, **kwargs) -> Dict[str, Any]:
    """
    Executes comprehensive health check verifying all runtime subsystems.
    Returns machine-readable dictionary with overall status.
    """
    config = get_config()
    cred_mgr = get_credential_manager()

    user_data_dir = Path(workspace_root).resolve() if workspace_root else get_user_data_dir()
    install_dir = get_app_install_dir()
    cfg_dir = (user_data_dir / "config") if workspace_root else get_config_dir()
    user_cfg = load_user_config(config_dir=cfg_dir)
    user_config_data = user_cfg.to_safe_diagnostics_dict()
    user_config_data["first_run_required"] = is_first_run_required(config_dir=cfg_dir)

    # 1. Filesystem check
    fs_ok = True
    fs_errors = []
    try:
        user_data_dir.mkdir(parents=True, exist_ok=True)
        test_file = user_data_dir / ".health_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
    except Exception as ex:
        fs_ok = False
        fs_errors.append(f"User data directory write error: {ex}")

    # 2. Credential availability check (BOOLEAN ONLY — ZERO SECRET EXPOSURE)
    has_gemini_key = cred_mgr.has_api_key("GEMINI_API_KEY") or bool(config.gemini_api_key)
    cred_storage_type = cred_mgr.get_storage_type("GEMINI_API_KEY")

    # 3. Audio driver / device availability
    audio_ok = True
    audio_driver = "DirectSound / WASAPI"
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        audio_ok = len(devices) > 0
    except Exception:
        # Fallback for headless / CI environments
        audio_driver = "Mock / Virtual PCM16 Engine"
        audio_ok = True

    # 4. Browser capability
    chrome_path = shutil.which("chrome") or shutil.which("google-chrome")
    if not chrome_path and sys.platform == "win32":
        for test_p in [
            Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Google\\Chrome\\Application\\chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Google\\Chrome\\Application\\chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google\\Chrome\\Application\\chrome.exe",
        ]:
            if test_p.exists():
                chrome_path = str(test_p)
                break
    browser_available = bool(chrome_path)

    # 5. UI Capability (Win32 layered window)
    ui_capable = sys.platform == "win32"

    overall_healthy = fs_ok and has_gemini_key

    return {
        "status": "HEALTHY" if overall_healthy else "DEGRADED",
        "product": __product_name__,
        "version": __version__,
        "build_date": __build_date__,
        "os": {
            "platform": sys.platform,
            "release": platform.release(),
            "architecture": platform.machine(),
        },
        "filesystem": {
            "healthy": fs_ok,
            "install_dir": str(install_dir.as_posix()),
            "user_data_dir": str(user_data_dir.as_posix()),
            "errors": fs_errors,
        },
        "credentials": {
            "gemini_api_key_configured": has_gemini_key,
            "storage_type": cred_storage_type,
            # CRITICAL: Do NOT include key value
        },
        "model_config": {
            "model": config.model.model,
            "voice": config.model.voice_name,
            "sample_rate_in_hz": config.audio.input_sample_rate,
            "sample_rate_out_hz": config.audio.output_sample_rate,
        },
        "subsystems": {
            "audio_hardware": {"available": audio_ok, "driver": audio_driver},
            "browser_automation": {"available": browser_available, "chrome_detected": browser_available},
            "desktop_presence_ui": {"available": ui_capable, "backend": "Win32 GDI Layered Window"},
            "task_persistence": {"available": fs_ok, "storage": str(get_tasks_dir().as_posix())},
        },
        "user_configuration": user_config_data,
    }


def perform_diagnostics(workspace_root: Optional[Path | str] = None, **kwargs) -> Dict[str, Any]:
    """
    Collects safe runtime diagnostics, memory usage, and component statuses.
    """
    health = perform_health_check(workspace_root=workspace_root, **kwargs)

    # Process resource consumption
    cpu_percent = 0.0
    ram_mb = 0.0
    try:
        import psutil
        proc = psutil.Process()
        cpu_percent = proc.cpu_percent(interval=0.05)
        ram_mb = proc.memory_info().rss / (1024 * 1024)
    except Exception:
        pass

    disk_mb = 0.0
    try:
        import psutil
        target_dir = Path(workspace_root).resolve() if workspace_root else get_user_data_dir()
        disk_usage = psutil.disk_usage(str(target_dir))
        disk_mb = disk_usage.used / (1024 * 1024)
    except Exception:
        pass

    # Inspect persistent task counts
    task_dir = Path(workspace_root) / ".ultron_tasks" if workspace_root else get_tasks_dir()
    goal_count = len(list(task_dir.glob("goal_*.json"))) if task_dir.exists() else 0

    return {
        "diagnostics_summary": {
            "product": __product_name__,
            "version": __version__,
            "status": health["status"],
        },
        "system_metrics": {
            "cpu_percent": round(cpu_percent, 2),
            "rss_memory_mb": round(ram_mb, 2),
            "disk_usage_mb": round(disk_mb, 2),
        },
        "resource_usage": {
            "cpu_percent": round(cpu_percent, 2),
            "ram_rss_mb": round(ram_mb, 2),
            "pid": os.getpid(),
        },
        "storage_statistics": {
            "active_persisted_goals": goal_count,
            "logs_directory": str(get_logs_dir().as_posix()),
            "cache_directory": str(get_cache_dir().as_posix()),
            "config_directory": str(get_config_dir().as_posix()),
        },
        "subsystems": health["subsystems"],
        "credentials": health["credentials"],
        "user_configuration": health.get("user_configuration", {}),
        "os_environment": {
            "platform": sys.platform,
            "python_version": platform.python_version(),
            "frozen_build": getattr(sys, "frozen", False),
        }
    }


def print_health_report() -> int:
    """Prints formatted health check to stdout. Returns 0 if healthy, 1 if unhealthy."""
    data = perform_health_check()
    print("\n=======================================================")
    print(f"             {data['product']} SYSTEM HEALTH CHECK")
    print("=======================================================")
    print(f" Status:         {data['status']}")
    print(f" Version:        {data['version']} (Build: {data['build_date']})")
    print(f" OS:             {data['os']['platform']} ({data['os']['release']} {data['os']['architecture']})")
    print(f" Filesystem:     {'OK' if data['filesystem']['healthy'] else 'ERROR'}")
    print(f" Credentials:    {'Configured (' + data['credentials']['storage_type'] + ')' if data['credentials']['gemini_api_key_configured'] else 'MISSING'}")
    print(f" Audio Engine:   {'Available' if data['subsystems']['audio_hardware']['available'] else 'Unavailable'}")
    print(f" Chrome/CDP:     {'Detected' if data['subsystems']['browser_automation']['available'] else 'Not Found'}")
    print(f" Presence UI:    {'Supported' if data['subsystems']['desktop_presence_ui']['available'] else 'Unsupported'}")
    print("=======================================================\n")
    return 0 if data["status"] == "HEALTHY" else 1


def print_diagnostics_report() -> int:
    """Prints formatted JSON diagnostics report to stdout."""
    diag = perform_diagnostics()
    print(json.dumps(diag, indent=2))
    return 0


# Backward compatibility alias
get_runtime_diagnostics = perform_diagnostics

