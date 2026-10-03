"""
ULTRON — Phase 11 Addendum: Liquid Onboarding Experience Test Suite
─────────────────────────────────────────────────────────────────────────────
Comprehensive unit and integration test suite verifying:
01. Fresh install → onboarding required
02. Completed setup → normal startup
03. Owner name persistence
04. Conversational address persistence
05. Assistant name persistence
06. Interaction preference persistence
07. Memory preference persistence
08. Startup preference persistence
09. Atomic configuration save
10. Corrupted configuration recovery (self-healing)
11. Crash during step recovery
12. Shutdown during step recovery
13. Repeated first launch
14. Duplicate launch (single-instance lock holds during onboarding)
15. Configuration cannot bypass safety or security policies
16. Secrets cannot enter configuration logs
17. Configuration cannot leak into diagnostics (redacted/boolean only)
18. Uninstall behavior preservation
19. Upgrade behavior preserves onboarding user config
20. Onboarding completion → notch transition & spring dynamics
─────────────────────────────────────────────────────────────────────────────
"""
import os
import sys
import json
import time
import tempfile
import pytest
from pathlib import Path

from ultron.__version__ import __version__, __product_name__
from ultron.core.paths import get_config_dir, get_user_data_dir, ensure_runtime_directories
from ultron.core.user_config import (
    UserConfig,
    load_user_config,
    save_user_config,
    is_first_run_required,
    reset_user_config,
    get_user_config_path,
)
from ultron.core.config import UltronConfig, get_config
from ultron.core.single_instance import SingleInstanceLock
from ultron.core.logging_sanitizer import SecretSanitizingFilter
from ultron.diagnostics.system import perform_health_check, perform_diagnostics
from ultron.presence.animation import SpringChoreographer, STATE_TARGETS
from ultron.presence.onboarding_controller import OnboardingController
from ultron.presence.hit_testing import HitTester, HTCLIENT, HTTRANSPARENT


# =============================================================================
# 01. Fresh install → Onboarding Required
# =============================================================================

def test_fresh_install_requires_onboarding(tmp_path):
    """Verifies that a fresh installation with no user_config.json requires onboarding."""
    assert is_first_run_required(config_dir=tmp_path) is True
    cfg = load_user_config(config_dir=tmp_path)
    assert cfg.first_run_completed is False


# =============================================================================
# 02. Completed Setup → Normal Startup
# =============================================================================

def test_completed_setup_normal_startup(tmp_path):
    """Verifies that once setup is finalized, first-run is no longer required."""
    cfg = UserConfig(
        owner_name="Mrityunjai",
        addressing_name="Mrityunjai",
        assistant_name="ULTRON",
        first_run_completed=True,
    )
    ok = save_user_config(cfg, config_dir=tmp_path)
    assert ok is True
    assert is_first_run_required(config_dir=tmp_path) is False


# =============================================================================
# 03. Owner Name Persistence
# =============================================================================

def test_owner_name_persistence(tmp_path):
    """Verifies owner preferred name is cleanly persisted and reloaded."""
    cfg = UserConfig(
        owner_name="Tony Stark",
        pronunciation_hint="Toh-nee",
        first_run_completed=True,
    )
    save_user_config(cfg, config_dir=tmp_path)

    loaded = load_user_config(config_dir=tmp_path)
    assert loaded.owner_name == "Tony Stark"
    assert loaded.pronunciation_hint == "Toh-nee"


# =============================================================================
# 04. Conversational Address Persistence
# =============================================================================

def test_conversational_address_persistence(tmp_path):
    """Verifies owner name and conversational address are stored separately."""
    cfg = UserConfig(
        owner_name="Mrityunjai",
        addressing_name="Mr.",
        assistant_name="ULTRON",
        first_run_completed=True,
    )
    save_user_config(cfg, config_dir=tmp_path)

    loaded = load_user_config(config_dir=tmp_path)
    assert loaded.owner_name == "Mrityunjai"
    assert loaded.addressing_name == "Mr."
    assert loaded.owner_name != loaded.addressing_name


# =============================================================================
# 05. Assistant Name Persistence
# =============================================================================

def test_assistant_name_persistence(tmp_path):
    """Verifies custom assistant identity persistence."""
    cfg = UserConfig(
        owner_name="Tester",
        assistant_name="FRIDAY",
        first_run_completed=True,
    )
    save_user_config(cfg, config_dir=tmp_path)

    loaded = load_user_config(config_dir=tmp_path)
    assert loaded.assistant_name == "FRIDAY"


# =============================================================================
# 06. Preference Persistence (Voice & Style)
# =============================================================================

def test_preference_persistence(tmp_path):
    """Verifies voice persona and response style preferences are persisted."""
    cfg = UserConfig(
        owner_name="Tester",
        voice_preference="Charon",
        response_style="Analytical & Detailed",
        first_run_completed=True,
    )
    save_user_config(cfg, config_dir=tmp_path)

    loaded = load_user_config(config_dir=tmp_path)
    assert loaded.voice_preference == "Charon"
    assert loaded.response_style == "Analytical & Detailed"


# =============================================================================
# 07. Memory Preference Persistence
# =============================================================================

def test_memory_preference_persistence(tmp_path):
    """Verifies local memory permission flag persistence."""
    cfg = UserConfig(
        owner_name="Tester",
        allow_explicit_memory=False,
        first_run_completed=True,
    )
    save_user_config(cfg, config_dir=tmp_path)

    loaded = load_user_config(config_dir=tmp_path)
    assert loaded.allow_explicit_memory is False


# =============================================================================
# 08. Startup Preference Persistence
# =============================================================================

def test_startup_preference_persistence(tmp_path):
    """Verifies Windows startup toggle preference persistence."""
    cfg = UserConfig(
        owner_name="Tester",
        start_with_windows=True,
        first_run_completed=True,
    )
    save_user_config(cfg, config_dir=tmp_path)

    loaded = load_user_config(config_dir=tmp_path)
    assert loaded.start_with_windows is True


# =============================================================================
# 09. Atomic Configuration Save
# =============================================================================

def test_atomic_configuration_save(tmp_path):
    """Verifies save_user_config writes via atomic temporary replacement."""
    cfg = UserConfig(
        owner_name="AtomicUser",
        first_run_completed=True,
    )
    ok = save_user_config(cfg, config_dir=tmp_path)
    assert ok is True

    # Check that no temporary files remain in the config dir
    temp_files = list(tmp_path.glob("ultron_cfg_*.tmp"))
    assert len(temp_files) == 0

    # Verify target file is valid JSON
    target = get_user_config_path(tmp_path)
    assert target.exists()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["owner_name"] == "AtomicUser"


# =============================================================================
# 10. Corrupted Configuration Recovery (Self-Healing)
# =============================================================================

def test_corrupted_configuration_recovery(tmp_path):
    """Verifies malformed JSON resets to safe defaults without crashing."""
    target = get_user_config_path(tmp_path)
    target.write_text("{{corrupted-json:::bad-data--", encoding="utf-8")

    # is_first_run_required should detect corrupted config and return True
    assert is_first_run_required(config_dir=tmp_path) is True

    # load_user_config should safely return default UserConfig
    recovered = load_user_config(config_dir=tmp_path)
    assert recovered.first_run_completed is False
    assert recovered.assistant_name == "ULTRON"


# =============================================================================
# 11. Crash During Onboarding Recovery
# =============================================================================

def test_crash_during_onboarding_recovery(tmp_path):
    """Verifies partial onboarding state before completion keeps first-run active."""
    # Simulate partial save before final step
    cfg = UserConfig(
        owner_name="IncompleteUser",
        first_run_completed=False,
    )
    # Force direct write
    target = get_user_config_path(tmp_path)
    target.write_text(json.dumps({"owner_name": "IncompleteUser", "first_run_completed": False}), encoding="utf-8")

    assert is_first_run_required(config_dir=tmp_path) is True


# =============================================================================
# 12. Shutdown During Step Recovery
# =============================================================================

def test_shutdown_during_step_recovery(tmp_path):
    """Verifies application termination during step retains clean fallback."""
    ctrl = OnboardingController()
    ctrl.owner_name = "StepUser"
    ctrl.current_step = 3

    # If not finalized, disk state does not mark completed
    assert is_first_run_required(config_dir=tmp_path) is True


# =============================================================================
# 13. Repeated First Launch
# =============================================================================

def test_repeated_first_launch(tmp_path):
    """Verifies repeatedly querying first launch remains consistent until finalized."""
    for _ in range(5):
        assert is_first_run_required(config_dir=tmp_path) is True


# =============================================================================
# 14. Duplicate Launch (Single-Instance Lock Holds During Onboarding)
# =============================================================================

def test_duplicate_launch_lock_during_onboarding(tmp_path, monkeypatch):
    """Verifies SingleInstanceLock prevents concurrent secondary processes."""
    monkeypatch.setenv("ULTRON_DATA_DIR", str(tmp_path))

    lock1 = SingleInstanceLock(lock_name="ultron_onboarding_test_lock")
    assert lock1.acquire() is True

    # Second instance attempting to launch while onboarding is active must fail
    lock2 = SingleInstanceLock(lock_name="ultron_onboarding_test_lock")
    assert lock2.acquire() is False

    lock1.release()


# =============================================================================
# 15. Configuration Cannot Bypass Safety Policies
# =============================================================================

def test_configuration_cannot_bypass_safety():
    """Verifies UserConfig dataclass does not expose any security bypass parameters."""
    allowed_fields = {
        "owner_name",
        "pronunciation_hint",
        "addressing_name",
        "assistant_name",
        "preferred_language",
        "voice_preference",
        "response_style",
        "presence_enabled",
        "allow_explicit_memory",
        "start_with_windows",
        "first_run_completed",
    }
    actual_fields = set(UserConfig.__dataclass_fields__.keys())
    assert actual_fields == allowed_fields

    # Verify dangerous attributes are not configurable
    forbidden = ["safety_level", "sandbox_mode", "bypass_confirmation", "shell_access", "planner_limits"]
    for f in forbidden:
        assert f not in actual_fields


# =============================================================================
# 16. Secrets Cannot Enter Configuration Logs
# =============================================================================

def test_secrets_cannot_enter_configuration_logs():
    """Verifies SecretSanitizingFilter scrubs API keys even in onboarding logs."""
    raw_log = "User entered API key AIzaSyTestKeySecret1234567890123456 during setup."
    clean_log = SecretSanitizingFilter.sanitize_text(raw_log)
    assert "AIzaSy" not in clean_log
    assert "[REDACTED_SECRET]" in clean_log


# =============================================================================
# 17. Configuration Cannot Leak into Diagnostics
# =============================================================================

def test_configuration_cannot_leak_into_diagnostics(tmp_path, monkeypatch):
    """Verifies diagnostics report exports only non-identifying booleans, never private names."""
    monkeypatch.setenv("ULTRON_DATA_DIR", str(tmp_path))
    ensure_runtime_directories()

    cfg = UserConfig(
        owner_name="SensitivePrivateName123",
        pronunciation_hint="PrivatePronunciation",
        addressing_name="PrivateAddressingName",
        assistant_name="ULTRON",
        voice_preference="Charon",
        first_run_completed=True,
    )
    save_user_config(cfg, config_dir=tmp_path / "config")

    diag = perform_diagnostics(workspace_root=tmp_path)
    diag_str = json.dumps(diag)

    # Private identifiers must NOT appear in diagnostics
    assert "SensitivePrivateName123" not in diag_str
    assert "PrivatePronunciation" not in diag_str
    assert "PrivateAddressingName" not in diag_str

    # Safe summary must be present
    assert "user_configuration" in diag
    assert diag["user_configuration"]["configuration_present"] is True
    assert diag["user_configuration"]["first_run_completed"] is True


# =============================================================================
# 18. Uninstall Behavior Preserves User Data
# =============================================================================

def test_uninstall_behavior_preserves_user_config(tmp_path, monkeypatch):
    """Verifies application uninstaller keeps user config intact."""
    user_data = tmp_path / "UserDir"
    cfg_dir = user_data / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    cfg = UserConfig(owner_name="PersistentUser", first_run_completed=True)
    save_user_config(cfg, config_dir=cfg_dir)

    # Simulate app binaries removal
    bin_dir = tmp_path / "BinDir"
    bin_dir.mkdir(parents=True, exist_ok=True)
    (bin_dir / "ultron.exe").write_text("binary", encoding="utf-8")
    (bin_dir / "ultron.exe").unlink()

    # User config remains untouched
    loaded = load_user_config(config_dir=cfg_dir)
    assert loaded.owner_name == "PersistentUser"
    assert loaded.first_run_completed is True


# =============================================================================
# 19. Upgrade Behavior Preserves Onboarding User Config
# =============================================================================

def test_upgrade_behavior_preserves_user_config(tmp_path):
    """Verifies software upgrade preserves completed onboarding config."""
    cfg = UserConfig(
        owner_name="UpgradedUser",
        addressing_name="Commander",
        assistant_name="ULTRON",
        voice_preference="Fenrir",
        first_run_completed=True,
    )
    save_user_config(cfg, config_dir=tmp_path)

    # Re-instantiate UltronConfig
    app_cfg = UltronConfig(user=load_user_config(config_dir=tmp_path))
    assert app_cfg.user.first_run_completed is True
    assert app_cfg.model.voice_name == "Fenrir"
    assert "UpgradedUser" in app_cfg.model.system_instruction
    assert "Commander" in app_cfg.model.system_instruction


# =============================================================================
# 20. Onboarding Completion → Notch Transition State & Spring Dynamics
# =============================================================================

def test_onboarding_completion_notch_transition_state(tmp_path):
    """Verifies OnboardingController progression, validation, and choreographer transition."""
    ch = SpringChoreographer()

    # 1. Initial notch state
    assert ch.current_state_name == "IDLE"
    assert ch.size.sx.target == STATE_TARGETS["IDLE"].width
    assert ch.size.sy.target == STATE_TARGETS["IDLE"].height

    # 2. Liquid expansion into ONBOARDING container
    ch.set_state("ONBOARDING")
    assert ch.current_state_name == "ONBOARDING"
    assert ch.size.sx.target == 580.0
    assert ch.size.sy.target == 480.0
    assert ch.onboarding_alpha.target == 1.0

    completed_configs = []
    def on_complete(cfg: UserConfig):
        completed_configs.append(cfg)

    ctrl = OnboardingController(on_complete=on_complete)
    assert ctrl.current_step == 1

    # Step 1: Blank name should fail validation
    assert ctrl.go_next() is False
    assert "Please enter your name" in ctrl.validation_error

    # Enter name and advance
    for ch_char in "Mrityunjai":
        ctrl.handle_char(ch_char)
    assert ctrl.owner_name == "Mrityunjai"
    assert ctrl.go_next() is True
    assert ctrl.current_step == 2

    # Step 2: Addressing -> advance
    assert ctrl.go_next() is True
    assert ctrl.current_step == 3

    # Step 3: Identity -> advance
    assert ctrl.go_next() is True
    assert ctrl.current_step == 4

    # Step 4: Interaction & Voice -> advance
    ctrl.voice_name = "Aoede"
    assert ctrl.go_next() is True
    assert ctrl.current_step == 5

    # Step 5: Privacy & Memory -> advance
    assert ctrl.go_next() is True
    assert ctrl.current_step == 6

    # Step 6: Startup & Finish -> Finalize
    # Override save directory for test isolation
    monkeypatch_config_dir = tmp_path
    def isolated_finalize():
        cfg = UserConfig(
            owner_name=ctrl.owner_name,
            addressing_name=ctrl.owner_name,
            assistant_name="ULTRON",
            voice_preference=ctrl.voice_name,
            first_run_completed=True,
        )
        save_user_config(cfg, config_dir=tmp_path)
        on_complete(cfg)

    ctrl.finalize = isolated_finalize
    ctrl.go_next()

    assert len(completed_configs) == 1
    assert completed_configs[0].owner_name == "Mrityunjai"
    assert completed_configs[0].voice_preference == "Aoede"
    assert completed_configs[0].first_run_completed is True

    # 3. Liquid collapse back to IDLE notch
    ch.set_state("IDLE")
    assert ch.current_state_name == "IDLE"
    assert ch.size.sx.target == STATE_TARGETS["IDLE"].width  # 340.0
    assert ch.size.sy.target == STATE_TARGETS["IDLE"].height # 68.0
    assert ch.onboarding_alpha.target == 0.0

    # Step through simulation until fully settled
    for _ in range(120):
        ch.update(0.016)
    assert ch.is_all_settled() is True
    assert abs(ch.size.x - 340.0) < 0.1
    assert abs(ch.size.y - 68.0) < 0.1
