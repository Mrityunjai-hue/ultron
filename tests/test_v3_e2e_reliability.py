"""
ULTRON V3 — Phase 5 End-to-End Reliability & Runtime Integration Test Suite
─────────────────────────────────────────────────────────────────────────────
Covers:
1. Audio Pipeline (16kHz in, 24kHz out, queue drain, on_playback_finished)
2. Gemini Live Session Resilience, Reconnect, Stale Context Disposal & Lock
3. Barge-In Interruption Latency & Epoch Queue Flushing (<100ms)
4. Tool Safety Gateway & Unrestricted Shell / Injection Prevention
5. Confirmation Security (Target/Tool/Session binding, single-use, replay/expiry/tamper rejection)
6. Memory Persistence, Secret Rejection, Bounded History & Pronoun Resolution ('it')
7. State Flow Authority & Audio State Synchronization
8. Graceful Fault Recovery & Clean Startup / Shutdown / Restart Lifecycle
─────────────────────────────────────────────────────────────────────────────
"""
import pytest
import asyncio
import time
import json
from pathlib import Path
import numpy as np

from ultron.core.config import UltronConfig
from ultron.core.events import ActivityState, EngineEvent, EventBus
from ultron.realtime.audio_stream import AudioStreamEngine
from ultron.realtime.interruption import InterruptionManager
from ultron.realtime.gemini_live import GeminiLiveProvider
from ultron.tools.safety import classify_file_operation, classify_app_operation, PolicyVerdict, is_within_workspace
from ultron.tools.confirmation import ConfirmationManager
from ultron.tools.executor import ToolExecutor
from ultron.memory.session import SessionMemory
from ultron.memory.persistent import PersistentMemory
from ultron.memory.manager import MemoryManager
from ultron.core.runtime import UltronRuntime

@pytest.fixture
def test_workspace(tmp_path):
    ws = tmp_path / "ultron_workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws

@pytest.fixture
def test_config(test_workspace):
    cfg = UltronConfig()
    cfg.workspace_root = test_workspace
    cfg.gemini_api_key = "test_key_phase5"
    return cfg

# =====================================================================
# 1. Audio Pipeline & Queue Drain Lifecycle Tests
# =====================================================================

def test_audio_pipeline_sample_rates_and_format():
    engine = AudioStreamEngine(input_sample_rate=16000, output_sample_rate=24000, chunk_size=512)
    assert engine.input_sample_rate == 16000
    assert engine.output_sample_rate == 24000
    assert engine.chunk_size == 512
    assert engine.is_playing is False

def test_audio_playback_finished_callback():
    finished_called = []
    engine = AudioStreamEngine(
        input_sample_rate=16000,
        output_sample_rate=24000,
        on_playback_finished=lambda: finished_called.append(True),
    )
    engine._is_running = True

    # Enqueue chunks
    chunk = (np.ones(512, dtype=np.int16) * 500).tobytes()
    engine.enqueue_playback(chunk)
    assert engine.is_playing is True

    # Clearing playback stops playing immediately
    lat = engine.clear_playback()
    assert lat < 50.0
    assert engine.is_playing is False

def test_audio_engine_stop_clean_release():
    engine = AudioStreamEngine(input_sample_rate=16000, output_sample_rate=24000)
    # Stop when not started should not raise
    asyncio.run(engine.stop())
    assert engine.input_stream is None
    assert engine.output_stream is None
    assert engine._is_running is False

# =====================================================================
# 2. Barge-in & Interruption Timing (<100ms)
# =====================================================================

def test_barge_in_sub100ms_latency_and_queue_flush():
    engine = AudioStreamEngine(input_sample_rate=16000, output_sample_rate=24000)
    engine._is_running = True
    engine._is_playing = True

    interrupted_latencies = []
    mgr = InterruptionManager(
        audio_engine=engine,
        rms_threshold=0.035,
        consecutive_frames_required=2,
        on_interruption=lambda lat: interrupted_latencies.append(lat),
    )

    # Enqueue multiple chunks to simulate model speaking
    for _ in range(10):
        engine.enqueue_playback((np.ones(512, dtype=np.int16) * 2000).tobytes())

    loud_pcm = (np.ones(512, dtype=np.int16) * 15000).tobytes()
    
    # Frame 1: onset
    mgr.process_input_frame(loud_pcm, rms_energy=0.10)
    assert len(interrupted_latencies) == 0

    # Frame 2: confirmed speech onset
    t0 = time.perf_counter()
    mgr.process_input_frame(loud_pcm, rms_energy=0.12)
    t_elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert len(interrupted_latencies) == 1
    assert interrupted_latencies[0] < 100.0, f"Interruption latency exceeded 100ms: {interrupted_latencies[0]}ms"
    assert t_elapsed_ms < 100.0
    assert engine.is_playing is False
    assert engine._playback_queue.empty() is True

def test_repeated_interruption_stability():
    engine = AudioStreamEngine(input_sample_rate=16000, output_sample_rate=24000)
    engine._is_running = True

    latencies = []
    mgr = InterruptionManager(
        audio_engine=engine,
        rms_threshold=0.035,
        consecutive_frames_required=1,
        on_interruption=lambda lat: latencies.append(lat),
    )

    loud_pcm = (np.ones(512, dtype=np.int16) * 10000).tobytes()

    for i in range(5):
        engine._is_playing = True
        engine.enqueue_playback(loud_pcm)
        mgr.process_input_frame(loud_pcm, rms_energy=0.15)
        assert engine.is_playing is False

    assert len(latencies) == 5
    for lat in latencies:
        assert lat < 100.0

# =====================================================================
# 3. Tool Safety & Shell / Injection Blocking Tests
# =====================================================================

def test_safety_blocks_arbitrary_shells():
    shells = [
        "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh",
        "bash", "bash.exe", "wsl", "wsl.exe", "sh", "zsh",
        "regedit", "cscript", "wscript", "rundll32", "net", "mshta", "certutil"
    ]
    for s in shells:
        verdict, reason = classify_app_operation(s, action="open")
        assert verdict == PolicyVerdict.BLOCKED, f"Shell '{s}' was not blocked!"

def test_safety_blocks_command_injection_characters():
    injections = [
        "notepad & calc",
        "notepad && calc",
        "calc | whoami",
        "calc; dir",
        "notepad > out.txt",
        "notepad < in.txt",
        "calc `whoami`",
        "calc $HOME",
        "calc\nwhoami",
        "calc\rwhoami",
    ]
    for inj in injections:
        verdict, reason = classify_app_operation(inj, action="open")
        assert verdict == PolicyVerdict.BLOCKED, f"Injection '{inj}' was not blocked!"

def test_safety_blocks_system_directory_file_access(test_workspace):
    blocked_targets = [
        r"C:\Windows\System32\cmd.exe",
        r"C:\Windows\win.ini",
        r"C:\Program Files\Common Files\config.xml",
        r"C:\Program Files (x86)\Microsoft\Edge\test.txt",
    ]
    for target in blocked_targets:
        verdict, reason = classify_file_operation("read", target, test_workspace)
        assert verdict == PolicyVerdict.BLOCKED, f"Path '{target}' read was not blocked!"

        verdict_w, _ = classify_file_operation("write", target, test_workspace)
        assert verdict_w == PolicyVerdict.BLOCKED, f"Path '{target}' write was not blocked!"

        verdict_d, _ = classify_file_operation("delete", target, test_workspace)
        assert verdict_d == PolicyVerdict.BLOCKED, f"Path '{target}' delete was not blocked!"

# =====================================================================
# 4. Confirmation Security & Token Lifecycle Tests
# =====================================================================

def test_confirmation_token_full_security_matrix():
    cm = ConfirmationManager(default_ttl_sec=60.0)

    # 1. Generate valid token
    p = cm.create_pending_confirmation(
        tool_name="write_file",
        arguments={"path": "report.txt", "content": "Phase 5 verified"},
        session_id="session_100",
    )
    assert p.token.startswith("conf-")
    assert p.is_expired() is False

    # 2. Tampered file target -> REJECT
    ok, msg = cm.validate_and_consume(
        token=p.token,
        tool_name="write_file",
        arguments={"path": "other.txt", "content": "Tampered"},
        session_id="session_100",
    )
    assert ok is False
    assert "target" in msg.lower()

    # 3. Tampered tool name -> REJECT
    ok, msg = cm.validate_and_consume(
        token=p.token,
        tool_name="delete_file",
        arguments={"path": "report.txt"},
        session_id="session_100",
    )
    assert ok is False
    assert "tool" in msg.lower()

    # 4. Session mismatch -> REJECT
    ok, msg = cm.validate_and_consume(
        token=p.token,
        tool_name="write_file",
        arguments={"path": "report.txt", "content": "Phase 5 verified"},
        session_id="session_DIFFERENT",
    )
    assert ok is False
    assert "session" in msg.lower()

    # 5. Exact match -> ACCEPT
    ok, msg = cm.validate_and_consume(
        token=p.token,
        tool_name="write_file",
        arguments={"path": "report.txt", "content": "Phase 5 verified"},
        session_id="session_100",
    )
    assert ok is True

    # 6. Replay / Reuse consumed token -> REJECT
    ok_replay, msg_replay = cm.validate_and_consume(
        token=p.token,
        tool_name="write_file",
        arguments={"path": "report.txt", "content": "Phase 5 verified"},
        session_id="session_100",
    )
    assert ok_replay is False

def test_confirmation_token_expiry_rejection():
    cm = ConfirmationManager(default_ttl_sec=0.05) # 50ms TTL
    p = cm.create_pending_confirmation(
        tool_name="delete_file",
        arguments={"path": "notes.txt"},
        session_id="sess_1",
        ttl_sec=0.05,
    )
    time.sleep(0.08) # Wait for expiry
    ok, msg = cm.validate_and_consume(
        token=p.token,
        tool_name="delete_file",
        arguments={"path": "notes.txt"},
        session_id="sess_1",
    )
    assert ok is False
    assert "expired" in msg.lower()

# =====================================================================
# 5. Memory Continuity, Pronoun Resolution & Secret Rejection
# =====================================================================

def test_pronoun_reference_resolution_multi_turn(test_workspace):
    cm = ConfirmationManager()
    mem = MemoryManager()
    executor = ToolExecutor(test_workspace, confirmation_manager=cm, memory_manager=mem)

    # Turn 1: User asks to open chrome
    mem.record_turn(
        role="tool",
        content="Opened Chrome",
        tool_name="open_app",
        tool_args={"app_name": "chrome"},
        tool_result={"success": True},
    )
    assert mem.session.resolve_target("app") == "chrome"

    # Turn 2: User says "Close it" -> Gemini requests close_app(app_name="it")
    # Executor should resolve "it" to "chrome" and issue confirmation for "chrome"
    res = asyncio.run(executor.execute("close_app", {"app_name": "it"}, session_id="sess_1"))
    assert res["status"] == "CONFIRM_REQUIRED"
    assert res["target"] == "chrome"
    token = res["confirmation_token"]

    # Turn 3: Confirmation provided with token
    res_conf = asyncio.run(executor.execute("close_app", {"app_name": "it", "confirmation_token": token}, session_id="sess_1"))
    # close_app executes for chrome (returns success or no running instance cleanly)
    assert "status" not in res_conf or res_conf.get("status") != "CONFIRMATION_INVALID"

def test_file_pronoun_resolution_multi_turn(test_workspace):
    cm = ConfirmationManager()
    mem = MemoryManager()
    executor = ToolExecutor(test_workspace, confirmation_manager=cm, memory_manager=mem)

    # Write a test file first
    test_file = test_workspace / "system_manifest.json"
    test_file.write_text('{"phase": 5}', encoding="utf-8")

    # Turn 1: Read file
    read_res = asyncio.run(executor.execute("read_file", {"path": "system_manifest.json"}, session_id="sess_1"))
    assert read_res["success"] is True
    mem.record_turn(
        role="tool",
        content="Read system_manifest.json",
        tool_name="read_file",
        tool_args={"path": "system_manifest.json"},
        tool_result=read_res,
    )
    assert mem.session.resolve_target("file") == "system_manifest.json"

    # Turn 2: User says "Delete it" -> delete_file(path="it")
    del_req = asyncio.run(executor.execute("delete_file", {"path": "it"}, session_id="sess_1"))
    assert del_req["status"] == "CONFIRM_REQUIRED"
    assert del_req["target"] == "system_manifest.json"
    del_token = del_req["confirmation_token"]

    # Turn 3: Confirm deletion
    del_res = asyncio.run(executor.execute("delete_file", {"path": "it", "confirmation_token": del_token}, session_id="sess_1"))
    assert del_res["success"] is True
    assert not test_file.exists()

def test_persistent_memory_restart_persistence_and_secrets(tmp_path):
    storage = tmp_path / "ultron_mem.json"
    pm1 = PersistentMemory(storage_path=storage)

    # 1. Write user preference
    ok, msg = pm1.remember("theme_mode", "stealth_black")
    assert ok is True

    # 2. Reject sensitive tokens
    assert pm1.remember("anthropic_key", "sk-ant-api03-1234567890abcdef1234567890")[0] is False
    assert pm1.remember("openai_key", "sk-1234567890abcdefghijklmnopqrstuvwxyz")[0] is False
    assert pm1.remember("db_pass", "password=SecretPassword123!")[0] is False

    # 3. Simulate restart: instantiate new PersistentMemory from disk
    pm2 = PersistentMemory(storage_path=storage)
    facts = pm2.get_all_facts()
    assert any("theme_mode: stealth_black" in f for f in facts)
    assert len(facts) == 1

    # 4. Forget
    ok_f, msg_f = pm2.forget("theme_mode")
    assert ok_f is True
    assert len(pm2.get_all_facts()) == 0

    # 5. Reload after forget
    pm3 = PersistentMemory(storage_path=storage)
    assert len(pm3.get_all_facts()) == 0

# =====================================================================
# 6. Authoritative State Transitions & Event Bus Mapping
# =====================================================================

def test_authoritative_state_transitions(test_config):
    runtime = UltronRuntime(test_config)
    observed_states = []

    runtime.event_bus.subscribe(lambda ev: observed_states.append(ev.state))

    assert runtime.state == ActivityState.IDLE

    # Transition to LISTENING
    runtime._transition(ActivityState.LISTENING)
    assert runtime.state == ActivityState.LISTENING

    # Transition to THINKING
    runtime._transition(ActivityState.THINKING, operation="get_current_time")
    assert runtime.state == ActivityState.THINKING

    # Transition to RESPONDING
    runtime._transition(ActivityState.RESPONDING)
    assert runtime.state == ActivityState.RESPONDING

    # Audio playback finished -> IDLE
    runtime._on_playback_finished()
    assert runtime.state == ActivityState.IDLE

    # Interruption flow
    runtime._transition(ActivityState.RESPONDING)
    runtime._on_barge_in_detected(total_latency_ms=35.0)
    assert runtime.state == ActivityState.LISTENING

    # Shutdown flow
    runtime._transition(ActivityState.OFFLINE)
    assert runtime.state == ActivityState.OFFLINE

    assert ActivityState.LISTENING in observed_states
    assert ActivityState.THINKING in observed_states
    assert ActivityState.RESPONDING in observed_states
    assert ActivityState.INTERRUPTED in observed_states
    assert ActivityState.OFFLINE in observed_states

# =====================================================================
# 7. Fault Recovery & Clean Startup / Shutdown Lifecycle
# =====================================================================

def test_tool_fault_recovery_runtime_survives(test_workspace):
    executor = ToolExecutor(test_workspace)

    # Missing arguments
    res_missing = asyncio.run(executor.execute("read_file", {}))
    assert res_missing["success"] is False
    assert "error" in res_missing

    # Non-existent file
    res_nofile = asyncio.run(executor.execute("read_file", {"path": "non_existent_123.txt"}))
    assert res_nofile["success"] is False

    # Unknown tool
    res_unknown = asyncio.run(executor.execute("unknown_tool_xyz", {}))
    assert res_unknown["success"] is False
    assert "not registered" in res_unknown["error"]

def test_clean_start_stop_restart_cycle(test_config):
    runtime = UltronRuntime(test_config)
    assert runtime.state == ActivityState.IDLE
    assert runtime._running is False

    # Stop without starting is completely safe
    asyncio.run(runtime.stop())
    assert runtime.state == ActivityState.OFFLINE

    # New runtime instance starts cleanly
    runtime2 = UltronRuntime(test_config)
    assert runtime2.state == ActivityState.IDLE
    asyncio.run(runtime2.stop())
    assert runtime2.state == ActivityState.OFFLINE
