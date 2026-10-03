"""
ULTRON V3 — Comprehensive Phase 1, 2 & 3 Test Suite
Covers:
1. Session context tracking & bounds
2. Context across multiple turns & reference resolution
3. Tool execution results entering context
4. Persistent memory write, retrieve, and explicit forget
5. Sensitive-secret rejection from persistent store
6. Memory size & item bounds
7. Confirmation token generation, expiration, and exact-target binding
8. Confirmation cannot be fabricated or spoofed
9. 4-Tier safety policy & workspace sandbox
10. Sub-50ms playback cancellation & barge-in protection
"""
import pytest
import asyncio
import time
import numpy as np
from pathlib import Path

from ultron.core.config import UltronConfig
from ultron.core.identity import build_system_instruction
from ultron.core.events import ActivityState, EngineEvent, EventBus
from ultron.realtime.audio_stream import AudioStreamEngine
from ultron.realtime.interruption import InterruptionManager
from ultron.tools.safety import classify_file_operation, classify_app_operation, PolicyVerdict, is_within_workspace
from ultron.tools.confirmation import ConfirmationManager
from ultron.tools.executor import ToolExecutor
from ultron.tools.registry import get_tool_declarations
from ultron.memory.session import SessionMemory
from ultron.memory.persistent import PersistentMemory
from ultron.memory.manager import MemoryManager

@pytest.fixture
def test_config(tmp_path):
    cfg = UltronConfig()
    cfg.workspace_root = tmp_path
    cfg.gemini_api_key = "test_key_mock"
    return cfg

# =====================================================================
# 1. 4-Tier Safety Gateway & Sandboxing Tests
# =====================================================================

def test_workspace_boundary_check(tmp_path):
    inside_file = tmp_path / "test.txt"
    inside_file.write_text("hello", encoding="utf-8")
    assert is_within_workspace(inside_file, tmp_path) is True

    outside_file = Path("C:/Windows/System32/drivers/etc/hosts")
    assert is_within_workspace(outside_file, tmp_path) is False

def test_safety_file_operations(tmp_path):
    safe_file = tmp_path / "data.txt"
    safe_file.write_text("content", encoding="utf-8")

    # Read safe file inside workspace -> SAFE
    verdict, reason = classify_file_operation("read", safe_file, tmp_path)
    assert verdict == PolicyVerdict.SAFE

    # Read blocked outside file -> BLOCKED
    verdict, reason = classify_file_operation("read", "C:/Windows/win.ini", tmp_path)
    assert verdict == PolicyVerdict.BLOCKED

    # Write existing file inside workspace -> CONFIRM_REQUIRED
    verdict, reason = classify_file_operation("write", safe_file, tmp_path)
    assert verdict == PolicyVerdict.CONFIRM_REQUIRED

    # Write new file inside workspace -> CONFIRM_REQUIRED
    new_file = tmp_path / "new.txt"
    verdict, reason = classify_file_operation("write", new_file, tmp_path)
    assert verdict == PolicyVerdict.CONFIRM_REQUIRED

    # Delete existing file inside workspace -> CONFIRM_REQUIRED
    verdict, reason = classify_file_operation("delete", safe_file, tmp_path)
    assert verdict == PolicyVerdict.CONFIRM_REQUIRED

    # Delete file outside workspace -> BLOCKED
    verdict, reason = classify_file_operation("delete", "C:/Windows/notepad.exe", tmp_path)
    assert verdict == PolicyVerdict.BLOCKED

def test_safety_app_launch_and_close():
    # Safe apps open
    verdict, reason = classify_app_operation("notepad", action="open")
    assert verdict == PolicyVerdict.SAFE

    verdict, reason = classify_app_operation("calc", action="open")
    assert verdict == PolicyVerdict.SAFE

    # Close user apps -> CONFIRM_REQUIRED
    verdict, reason = classify_app_operation("notepad", action="close")
    assert verdict == PolicyVerdict.CONFIRM_REQUIRED

    # Close protected OS process -> BLOCKED
    verdict, reason = classify_app_operation("explorer", action="close")
    assert verdict == PolicyVerdict.BLOCKED

    verdict, reason = classify_app_operation("svchost", action="close")
    assert verdict == PolicyVerdict.BLOCKED

    # Dangerous executables -> BLOCKED
    verdict, reason = classify_app_operation("cmd.exe /c del *")
    assert verdict == PolicyVerdict.BLOCKED

    verdict, reason = classify_app_operation("powershell.exe -Command Remove-Item")
    assert verdict == PolicyVerdict.BLOCKED

# =====================================================================
# 2. Confirmation Security Hardening Tests
# =====================================================================

def test_confirmation_token_generation_and_consumption():
    cm = ConfirmationManager(default_ttl_sec=60.0)

    # Generate token for close_app("notepad")
    req = cm.create_pending_confirmation(
        tool_name="close_app",
        arguments={"app_name": "notepad"},
        session_id="session_1",
    )
    assert req.token.startswith("conf-")
    assert req.is_expired() is False

    # Validate and consume
    valid, msg = cm.validate_and_consume(
        token=req.token,
        tool_name="close_app",
        arguments={"app_name": "notepad"},
        session_id="session_1",
    )
    assert valid is True

    # Token cannot be re-used (single-use guarantee)
    valid2, msg2 = cm.validate_and_consume(
        token=req.token,
        tool_name="close_app",
        arguments={"app_name": "notepad"},
        session_id="session_1",
    )
    assert valid2 is False

def test_confirmation_token_tied_to_exact_action():
    cm = ConfirmationManager()

    # Issue token for deleting A.txt
    req = cm.create_pending_confirmation(
        tool_name="delete_file",
        arguments={"path": "A.txt"},
        session_id="session_1",
    )

    # Attempting to use token for B.txt must FAIL
    valid_b, msg_b = cm.validate_and_consume(
        token=req.token,
        tool_name="delete_file",
        arguments={"path": "B.txt"},
        session_id="session_1",
    )
    assert valid_b is False
    assert "target" in msg_b.lower()

    # Attempting to use token for write_file("A.txt") must FAIL
    valid_w, msg_w = cm.validate_and_consume(
        token=req.token,
        tool_name="write_file",
        arguments={"path": "A.txt"},
        session_id="session_1",
    )
    assert valid_w is False
    assert "tool" in msg_w.lower()

def test_confirmation_token_expiration():
    cm = ConfirmationManager(default_ttl_sec=0.1)  # 100ms TTL

    req = cm.create_pending_confirmation(
        tool_name="delete_file",
        arguments={"path": "temp.txt"},
        session_id="session_1",
        ttl_sec=0.1,
    )
    time.sleep(0.15)  # Wait for expiration

    valid, msg = cm.validate_and_consume(
        token=req.token,
        tool_name="delete_file",
        arguments={"path": "temp.txt"},
        session_id="session_1",
    )
    assert valid is False
    assert "expired" in msg.lower()

def test_confirmation_cannot_be_fabricated():
    cm = ConfirmationManager()

    # Arbitrary fabricated token by model
    valid, msg = cm.validate_and_consume(
        token="conf-fabricated-fake-12345",
        tool_name="delete_file",
        arguments={"path": "secret.txt"},
        session_id="session_1",
    )
    assert valid is False
    assert "invalid" in msg.lower() or "unauthorized" in msg.lower()

# =====================================================================
# 3. Local Tool Gateway & Lifecycle Tests
# =====================================================================

def test_tool_executor_time_and_status(test_config):
    executor = ToolExecutor(test_config.workspace_root)

    # get_current_time
    time_res = asyncio.run(executor.execute("get_current_time", {}))
    assert time_res["success"] is True
    assert "time" in time_res

    # get_system_status
    sys_res = asyncio.run(executor.execute("get_system_status", {}))
    assert sys_res["success"] is True
    assert "cpu_percent" in sys_res

def test_tool_executor_file_lifecycle_with_tokens(tmp_path):
    cm = ConfirmationManager()
    executor = ToolExecutor(tmp_path, confirmation_manager=cm)

    # 1. Write file without token -> CONFIRM_REQUIRED
    unconf_res = asyncio.run(executor.execute("write_file", {"path": "test_note.txt", "content": "Ultron Test"}))
    assert unconf_res["success"] is False
    assert unconf_res["status"] == "CONFIRM_REQUIRED"
    token = unconf_res["confirmation_token"]

    # 2. Write file with token -> SUCCESS
    conf_res = asyncio.run(executor.execute("write_file", {
        "path": "test_note.txt",
        "content": "Ultron Test",
        "confirmation_token": token,
    }))
    assert conf_res["success"] is True

    # 3. Read file -> SUCCESS
    read_res = asyncio.run(executor.execute("read_file", {"path": "test_note.txt"}))
    assert read_res["success"] is True
    assert "Ultron Test" in read_res["content"]

    # 4. Delete file without token -> CONFIRM_REQUIRED
    del_unconf = asyncio.run(executor.execute("delete_file", {"path": "test_note.txt"}))
    assert del_unconf["success"] is False
    assert del_unconf["status"] == "CONFIRM_REQUIRED"
    del_token = del_unconf["confirmation_token"]

    # 5. Delete file with token -> SUCCESS
    del_conf = asyncio.run(executor.execute("delete_file", {
        "path": "test_note.txt",
        "confirmation_token": del_token,
    }))
    assert del_conf["success"] is True

# =====================================================================
# 4. Session Memory & Context Resolution Tests
# =====================================================================

def test_session_memory_turns_and_bounds():
    mem = SessionMemory(max_turns=5)
    for i in range(10):
        mem.record_turn(role="user", content=f"Message {i}")

    assert len(mem.turns) == 5
    assert mem.turns[0].content == "Message 5"
    assert mem.turns[-1].content == "Message 9"

def test_session_memory_target_tracking_and_reference_resolution():
    mem = SessionMemory()

    # Record open_app turn
    mem.record_turn(
        role="tool",
        content="Opened Chrome",
        tool_name="open_app",
        tool_args={"app_name": "chrome"},
        tool_result={"success": True},
    )
    assert mem.resolve_target("app") == "chrome"
    assert "chrome" in mem.get_context_summary().lower()

    # Record read_file turn
    mem.record_turn(
        role="tool",
        content="Read config",
        tool_name="read_file",
        tool_args={"path": "ultron/core/config.py"},
        tool_result={"success": True},
    )
    assert mem.resolve_target("file") == "ultron/core/config.py"
    assert "config.py" in mem.get_context_summary()

# =====================================================================
# 5. Persistent Memory & Security Secret Rejection Tests
# =====================================================================

def test_persistent_memory_write_and_retrieval(tmp_path):
    mem_file = tmp_path / "memory.json"
    pm = PersistentMemory(storage_path=mem_file)

    # Write preference
    ok, msg = pm.remember("preferred_name", "Mrityunjai")
    assert ok is True

    # Retrieve facts
    facts = pm.get_all_facts()
    assert any("preferred_name: Mrityunjai" in f for f in facts)

    # Reload from disk (persistence check)
    pm2 = PersistentMemory(storage_path=mem_file)
    assert any("preferred_name: Mrityunjai" in f for f in pm2.get_all_facts())

def test_persistent_memory_explicit_forget(tmp_path):
    mem_file = tmp_path / "memory.json"
    pm = PersistentMemory(storage_path=mem_file)

    pm.remember("editor", "VS Code")
    assert len(pm.get_all_facts()) == 1

    ok, msg = pm.forget("editor")
    assert ok is True
    assert len(pm.get_all_facts()) == 0

def test_persistent_memory_sensitive_secret_rejection(tmp_path):
    mem_file = tmp_path / "memory.json"
    pm = PersistentMemory(storage_path=mem_file)

    # API Keys & Tokens
    ok1, msg1 = pm.remember("my_api_key", "AIzaSyD-example12345678901234567890")
    assert ok1 is False
    assert "forbidden" in msg1.lower()

    # Passwords
    ok2, msg2 = pm.remember("admin_password", "SuperSecretPass123!")
    assert ok2 is False
    assert "forbidden" in msg2.lower()

    # Bearer tokens
    ok3, msg3 = pm.remember("auth", "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
    assert ok3 is False

    assert len(pm.get_all_facts()) == 0

def test_persistent_memory_capacity_bounds(tmp_path):
    mem_file = tmp_path / "memory.json"
    pm = PersistentMemory(storage_path=mem_file, max_items=5)

    for i in range(10):
        pm.remember(f"fact_{i}", f"Value {i}")

    assert len(pm.list_memories()) == 5
    facts = pm.get_all_facts()
    assert "fact_9: Value 9" in facts[-1]

# =====================================================================
# 6. Centralized Identity & System Prompt Builder Tests
# =====================================================================

def test_identity_system_prompt_builder():
    prompt = build_system_instruction(
        persistent_facts=["preferred_name: Mrityunjai", "style: concise"],
        recent_context_summary="Last active application: chrome",
    )
    assert "ULTRON" in prompt
    assert "preferred_name: Mrityunjai" in prompt
    assert "Last active application: chrome" in prompt
    assert "Never use filler pleasantries" in prompt

# =====================================================================
# 7. Audio Streaming Engine & Barge-In Tests
# =====================================================================

def test_audio_engine_playback_cancellation():
    audio = AudioStreamEngine(input_sample_rate=16000, output_sample_rate=24000, chunk_size=512)
    dummy_chunk = (np.ones(512, dtype=np.int16) * 1000).tobytes()
    audio._is_running = True
    audio.enqueue_playback(dummy_chunk)
    audio.enqueue_playback(dummy_chunk)

    assert audio.is_playing is True
    latency_ms = audio.clear_playback()
    assert latency_ms < 50.0
    assert audio.is_playing is False

def test_interruption_manager_barge_in():
    audio = AudioStreamEngine(input_sample_rate=16000, output_sample_rate=24000)
    audio._is_running = True
    audio._is_playing = True

    interrupted_latencies = []
    interruption_mgr = InterruptionManager(
        audio_engine=audio,
        rms_threshold=0.035,
        consecutive_frames_required=2,
        on_interruption=lambda lat: interrupted_latencies.append(lat),
    )

    loud_frame = (np.ones(512, dtype=np.int16) * 10000).tobytes()
    interruption_mgr.process_input_frame(loud_frame, rms_energy=0.10)
    assert len(interrupted_latencies) == 0

    interruption_mgr.process_input_frame(loud_frame, rms_energy=0.12)
    assert len(interrupted_latencies) == 1
    assert interrupted_latencies[0] < 50.0
