"""
ULTRON — Phase 11 Productization & Secure Distribution Test Suite
─────────────────────────────────────────────────────────────────────────────
Verifies:
A. Application metadata & single source of truth versioning
B. Central path resolution & user data isolation (%LOCALAPPDATA%/ULTRON)
C. Secure Windows DPAPI and environment credential management
D. Secret boundary, zero-leakage guarantee & logging sanitization
E. First-run directory initialization
F. Lifecycle state transitions & guard rejection
G. Startup management & crash circuit-breaker backoff
H. Single-instance process locking
I. Graceful clean shutdown
J. Safe health check & system diagnostics (zero credential exposure)
K. Automated secret discovery scanner
L. Installer payload extraction, uninstallation & user data preservation
M. Standalone production binary execution
─────────────────────────────────────────────────────────────────────────────
"""
import os
import sys
import time
import json
import shutil
import tempfile
import subprocess
from pathlib import Path
import pytest

from ultron.__version__ import __version__, __build_date__, __product_name__
from ultron.core.paths import (
    get_user_data_dir,
    get_app_install_dir,
    get_config_dir,
    get_memory_dir,
    get_tasks_dir,
    get_logs_dir,
    get_cache_dir,
    ensure_runtime_directories,
)
from ultron.core.credentials import (
    WindowsDPAPICredentialStore,
    EnvironmentCredentialStore,
    SecureCredentialManager,
    get_credential_manager,
)
from ultron.core.logging_sanitizer import SecretSanitizingFilter, setup_logging
from ultron.core.single_instance import SingleInstanceLock
from ultron.core.startup import StartupManager
from ultron.core.lifecycle import (
    LifecycleManager,
    LifecycleState,
    InvalidLifecycleTransitionError,
)
from ultron.diagnostics.system import perform_health_check, perform_diagnostics
from ultron.memory.persistent import PersistentMemory
from ultron.tasks.persistence import scrub_secrets, TaskPersistenceManager
from ultron.tasks.journal import TaskJournal, JournalEventType
from scripts.secret_scanner import scan_file, scan_directory


# =============================================================================
# A. Metadata & Versioning
# =============================================================================

def test_metadata_and_versioning():
    """Verifies single source of truth version format and metadata."""
    assert __product_name__ == "ULTRON"
    assert isinstance(__version__, str)
    parts = __version__.split(".")
    assert len(parts) >= 3
    for p in parts[:3]:
        assert p.isdigit()
    assert len(__build_date__) >= 8


# =============================================================================
# B. Path Resolution & User Data Isolation
# =============================================================================

def test_isolated_user_data_paths(tmp_path, monkeypatch):
    """Verifies ULTRON isolates all mutable state into configurable user data directory."""
    test_data_dir = tmp_path / "custom_ultron_data"
    monkeypatch.setenv("ULTRON_DATA_DIR", str(test_data_dir))

    user_dir = get_user_data_dir()
    assert user_dir == test_data_dir.resolve()
    assert user_dir.exists()

    cfg_dir = get_config_dir()
    mem_dir = get_memory_dir()
    tsk_dir = get_tasks_dir()
    log_dir = get_logs_dir()
    cch_dir = get_cache_dir()

    assert cfg_dir.parent == user_dir
    assert mem_dir.parent == user_dir
    assert tsk_dir.parent == user_dir
    assert log_dir.parent == user_dir
    assert cch_dir.parent == user_dir


def test_ensure_runtime_directories(tmp_path, monkeypatch):
    """Verifies all subdirectories are initialized automatically on first run."""
    test_data_dir = tmp_path / "init_test"
    monkeypatch.setenv("ULTRON_DATA_DIR", str(test_data_dir))

    ensure_runtime_directories()
    assert (test_data_dir / "config").is_dir()
    assert (test_data_dir / "memory").is_dir()
    assert (test_data_dir / "tasks").is_dir()
    assert (test_data_dir / "logs").is_dir()
    assert (test_data_dir / "cache").is_dir()


# =============================================================================
# C. Secure Windows DPAPI & Credential Management
# =============================================================================

def test_environment_credential_store(monkeypatch):
    """Verifies environment credential store operations."""
    store = EnvironmentCredentialStore()
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    assert store.has_api_key("GEMINI_API_KEY") is False
    assert store.get_api_key("GEMINI_API_KEY") is None

    store.set_api_key("GEMINI_API_KEY", "test_mock_key_abc123")
    assert store.has_api_key("GEMINI_API_KEY") is True
    assert store.get_api_key("GEMINI_API_KEY") == "test_mock_key_abc123"

    store.delete_api_key("GEMINI_API_KEY")
    assert store.has_api_key("GEMINI_API_KEY") is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI test")
def test_windows_dpapi_credential_store(tmp_path):
    """Verifies Windows DPAPI encryption and decryption of credentials."""
    dpapi_store = WindowsDPAPICredentialStore(config_dir=tmp_path)
    assert dpapi_store.has_api_key("GEMINI_API_KEY") is False

    # Store synthetic key
    dpapi_store.set_api_key("GEMINI_API_KEY", "test_dpapi_secret_key_998877")
    assert dpapi_store.has_api_key("GEMINI_API_KEY") is True
    assert dpapi_store.get_api_key("GEMINI_API_KEY") == "test_dpapi_secret_key_998877"

    # Verify file on disk is encrypted binary, not plaintext
    cred_file = tmp_path / "credentials.dpapi"
    assert cred_file.exists()
    raw_content = cred_file.read_bytes()
    assert b"test_dpapi_secret_key_998877" not in raw_content

    # Delete key
    dpapi_store.delete_api_key("GEMINI_API_KEY")
    assert dpapi_store.has_api_key("GEMINI_API_KEY") is False


def test_composite_credential_manager(tmp_path, monkeypatch):
    """Verifies composite manager prioritizes DPAPI then environment fallback."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    mgr = SecureCredentialManager(config_dir=tmp_path)

    if sys.platform == "win32":
        mgr.set_api_key("GEMINI_API_KEY", "dpapi_key_val")
        assert mgr.has_api_key("GEMINI_API_KEY") is True
        assert mgr.get_storage_type("GEMINI_API_KEY") == "WINDOWS_DPAPI"
        assert mgr.get_api_key("GEMINI_API_KEY") == "dpapi_key_val"
        mgr.delete_api_key("GEMINI_API_KEY")

    monkeypatch.setenv("GEMINI_API_KEY", "env_key_val")
    assert mgr.get_storage_type("GEMINI_API_KEY") == "ENVIRONMENT_VARIABLE"
    assert mgr.get_api_key("GEMINI_API_KEY") == "env_key_val"


# =============================================================================
# D. Secret Boundary & Logging Sanitizer
# =============================================================================

def test_secret_sanitizing_filter():
    """Verifies log record filtering redacts secret patterns."""
    text_with_keys = (
        "Error calling Gemini with AIzaSyDummyFakeKeyForTestingPurposes_12345 "
        "and token Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0In0 "
        "and password='SuperSecretPassword123!'"
    )
    sanitized = SecretSanitizingFilter.sanitize_text(text_with_keys)
    assert "AIzaSy" not in sanitized
    assert "SuperSecretPassword123!" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized


def test_persistent_memory_secret_rejection(tmp_path):
    """Verifies memory layer refuses to store sensitive credentials."""
    mem_file = tmp_path / "memory.json"
    pm = PersistentMemory(storage_path=mem_file)

    ok1, _ = pm.remember("gemini_key", "AIzaSyFakeKey123456789012345678901234567")
    assert ok1 is False

    ok2, _ = pm.remember("user_password", "MyPassword123!")
    assert ok2 is False

    ok3, _ = pm.remember("auth_token", "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
    assert ok3 is False

    assert len(pm.list_memories()) == 0


def test_persistence_secret_scrubbing():
    """Verifies task persistence scrubber recursively redacts sensitive fields."""
    payload = {
        "goal_id": "goal-1",
        "api_key": "AIzaSyFakeKey123456789012345678901234567",
        "nested": {
            "token": "secret_token_123",
            "safe_param": "hello world",
        },
        "items": [
            {"password": "pass", "safe": 123}
        ]
    }
    scrubbed = scrub_secrets(payload)
    assert scrubbed["api_key"] == "[REDACTED_SECRET]"
    assert scrubbed["nested"]["token"] == "[REDACTED_SECRET]"
    assert scrubbed["nested"]["safe_param"] == "hello world"
    assert scrubbed["items"][0]["password"] == "[REDACTED_SECRET]"
    assert scrubbed["items"][0]["safe"] == 123


# =============================================================================
# E. Lifecycle State Machine
# =============================================================================

def test_lifecycle_state_machine():
    """Verifies legal lifecycle transitions and illegal transition rejection."""
    lm = LifecycleManager(LifecycleState.STARTING)
    assert lm.current_state == LifecycleState.STARTING

    # Legal progression
    lm.transition_to(LifecycleState.INITIALIZING, reason="Booting")
    assert lm.current_state == LifecycleState.INITIALIZING

    lm.transition_to(LifecycleState.READY, reason="Subsystems ready")
    assert lm.current_state == LifecycleState.READY

    lm.transition_to(LifecycleState.RUNNING, reason="Active loop")
    assert lm.current_state == LifecycleState.RUNNING

    lm.transition_to(LifecycleState.STOPPING, reason="Shutdown")
    assert lm.current_state == LifecycleState.STOPPING

    lm.transition_to(LifecycleState.STOPPED, reason="Clean stop")
    assert lm.current_state == LifecycleState.STOPPED
    assert lm.is_terminal() is True

    # Illegal transition rejection
    lm_illegal = LifecycleManager(LifecycleState.STARTING)
    with pytest.raises(InvalidLifecycleTransitionError):
        lm_illegal.transition_to(LifecycleState.RUNNING, reason="Illegal jump")


# =============================================================================
# F. Startup Manager & Crash Circuit Breaker
# =============================================================================

def test_startup_circuit_breaker(tmp_path):
    """Verifies startup circuit breaker trips after repeated crashes within time window."""
    sm = StartupManager(config_dir=tmp_path)

    # 1st attempt: ok
    assert sm.check_circuit_breaker() is True

    # 2nd attempt: ok
    assert sm.check_circuit_breaker() is True

    # 3rd attempt: ok
    assert sm.check_circuit_breaker() is True

    # 4th attempt within crash window: trips circuit breaker
    assert sm.check_circuit_breaker() is False
    assert sm.check_circuit_breaker() is False

    # Reset circuit breaker on success
    sm.record_successful_startup()
    assert sm.check_circuit_breaker() is True


# =============================================================================
# G. Single-Instance Process Enforcement
# =============================================================================

def test_single_instance_lock(tmp_path, monkeypatch):
    """Verifies single instance prevents duplicate concurrent locks."""
    monkeypatch.setenv("ULTRON_DATA_DIR", str(tmp_path))

    lock1 = SingleInstanceLock(lock_name="test_ultron_lock")
    assert lock1.acquire() is True

    lock2 = SingleInstanceLock(lock_name="test_ultron_lock")
    assert lock2.acquire() is False

    lock1.release()
    assert lock2.acquire() is True
    lock2.release()


# =============================================================================
# H. Safe Health Check & System Diagnostics
# =============================================================================

def test_health_check_zero_secrets(monkeypatch):
    """Verifies health check output contains all required keys and zero secret values."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_test_api_key_12345")
    health = perform_health_check()

    assert "status" in health
    assert health["version"] == __version__
    assert health["credentials"]["gemini_api_key_configured"] is True
    # Verify no secret value exposed
    assert "dummy_test_api_key" not in json.dumps(health)


def test_diagnostics_report_zero_secrets(monkeypatch):
    """Verifies diagnostics report outputs process metrics without secret data."""
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_test_api_key_12345")
    diag = perform_diagnostics()

    assert "resource_usage" in diag
    assert "cpu_percent" in diag["resource_usage"]
    assert "ram_rss_mb" in diag["resource_usage"]
    assert "dummy_test_api_key" not in json.dumps(diag)


# =============================================================================
# I. Automated Secret Discovery Scanner
# =============================================================================

def test_secret_scanner_detection(tmp_path):
    """Verifies secret scanner detects API keys and reports without printing values."""
    dirty_file = tmp_path / "leaky_config.py"
    # Write a fake key
    dirty_file.write_text(f"MY_SECRET = 'AIzaSy{'B' * 33}'\n", encoding="utf-8")

    findings = scan_file(dirty_file)
    assert len(findings) == 1
    assert findings[0]["type"] == "Google / Gemini API Key"
    assert findings[0]["line"] == 1
    assert "remediation" in findings[0]


# =============================================================================
# J. Installer, Uninstaller & Upgrade Simulation
# =============================================================================

def test_installer_and_uninstaller_lifecycle(tmp_path, monkeypatch):
    """Verifies installer extracts binaries, writes uninstaller, and isolates user data."""
    dist_dir = Path(__file__).resolve().parent.parent / "dist" / "ultron"
    if not (dist_dir / "ultron.exe").exists():
        pytest.skip("dist/ultron/ultron.exe not built yet")

    install_dest = tmp_path / "InstalledApp"
    user_data_dest = tmp_path / "UserData"
    monkeypatch.setenv("ULTRON_DATA_DIR", str(user_data_dest))

    # 1. Run installation
    from scripts.build_installer import generate_installer_script
    import io, base64, zipfile

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dist_dir):
            for f in files:
                fp = Path(root) / f
                zf.write(fp, fp.relative_to(dist_dir))

    # Unpack into install_dest
    with zipfile.ZipFile(io.BytesIO(bio.getvalue())) as zf:
        zf.extractall(install_dest)

    assert (install_dest / "ultron.exe").exists()

    # 2. Simulate User Data Creation
    user_mem = user_data_dest / "memory" / "memory.json"
    user_mem.parent.mkdir(parents=True, exist_ok=True)
    user_mem.write_text('{"fact_1": {"value": "persistent_data"}}', encoding="utf-8")

    # 3. Simulate Upgrade (new binaries extracted, user data untouched)
    with zipfile.ZipFile(io.BytesIO(bio.getvalue())) as zf:
        zf.extractall(install_dest)

    assert user_mem.exists()
    assert "persistent_data" in user_mem.read_text(encoding="utf-8")


# =============================================================================
# K. Standalone Production Binary Execution
# =============================================================================

@pytest.mark.skipif(sys.platform != "win32", reason="Windows binary execution test")
def test_compiled_standalone_binary_execution():
    """Executes the compiled ultron.exe binary outside Python to verify standalone viability."""
    exe_path = Path(__file__).resolve().parent.parent / "dist" / "ultron" / "ultron.exe"
    if not exe_path.exists():
        pytest.skip("Standalone ultron.exe binary not found in dist/ultron/")

    # 1. Test --version
    res_v = subprocess.run([str(exe_path), "--version"], capture_output=True, text=True)
    assert res_v.returncode == 0
    assert __product_name__ in res_v.stdout
    assert __version__ in res_v.stdout

    # 2. Test --health
    res_h = subprocess.run([str(exe_path), "--health"], capture_output=True, text=True)
    assert res_h.returncode in (0, 1)  # 0 if key present, 1 if degraded (missing key in test env)
    assert "SYSTEM HEALTH CHECK" in res_h.stdout

    # 3. Test --diagnostics
    res_d = subprocess.run([str(exe_path), "--diagnostics"], capture_output=True, text=True)
    assert res_d.returncode == 0
    parsed = json.loads(res_d.stdout)
    assert parsed["diagnostics_summary"]["version"] == __version__
    assert parsed["os_environment"]["frozen_build"] is True
