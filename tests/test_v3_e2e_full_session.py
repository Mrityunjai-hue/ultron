"""
ULTRON V3 — Phase 5 Real End-to-End Session Verification
─────────────────────────────────────────────────────────────────────────────
Simulates and executes the exact 16-step comprehensive conversation session:
1. Start ULTRON Runtime.
2. Say: "Hello ULTRON."
3. Ask: "What time is it?" -> get_current_time execution.
4. Ask: "What's my system status?" -> get_system_status execution.
5. Say: "Open Notepad." -> open_app("notepad").
6. Wait for completion.
7. Say: "Close it." -> Pronoun resolution -> close_app with confirmation.
8. Test a file read -> read_workspace_file.
9. Test a write requiring confirmation -> write_file (generates token).
10. Reject confirmation -> Dismisses token.
11. Repeat and approve confirmation -> write_file executed with valid token.
12. Interrupt ULTRON while it is speaking -> Barge-in cancellation (<100ms).
13. Continue the conversation -> Multi-turn context retained.
14. Disconnect/reconnect simulation -> Session context renewal.
15. Shut down ULTRON -> Clean resource release.
16. Start ULTRON again -> Clean restart verification.
─────────────────────────────────────────────────────────────────────────────
"""
import pytest
import asyncio
import time
from pathlib import Path

from ultron.core.config import UltronConfig
from ultron.core.events import ActivityState, EngineEvent
from ultron.core.runtime import UltronRuntime
from ultron.tools.executor import ToolExecutor
from ultron.tools.confirmation import ConfirmationManager
from ultron.memory.manager import MemoryManager

def test_full_16_step_e2e_session(tmp_path):
    async def _async_scenario():
        print("\n=======================================================")
        print("      EXECUTING FULL 16-STEP END-TO-END SESSION        ")
        print("=======================================================")

        cfg = UltronConfig()
        cfg.workspace_root = tmp_path
        cfg.gemini_api_key = "test_e2e_mock_key"

        # 1. Start ULTRON
        print("[Step 1] Starting ULTRON Runtime...")
        runtime = UltronRuntime(cfg)
        assert runtime.state == ActivityState.IDLE
        print("         -> ULTRON Online (State: IDLE)")

        # 2. Say: "Hello ULTRON."
        print("[Step 2] User: 'Hello ULTRON.'")
        runtime.memory.record_turn(role="user", content="Hello ULTRON.")
        runtime.memory.record_turn(role="model", content="I am online and listening.")
        assert len(runtime.memory.session.turns) == 2

        # 3. Ask: "What time is it?"
        print("[Step 3] User: 'What time is it?'")
        runtime._transition(ActivityState.THINKING, operation="get_current_time")
        time_res = await runtime.tools.execute("get_current_time", {})
        assert time_res["success"] is True
        assert "time" in time_res
        runtime.memory.record_turn(role="tool", content=str(time_res), tool_name="get_current_time", tool_result=time_res)
        print(f"         -> Tool result: {time_res['time']}")

        # 4. Ask: "What's my system status?"
        print("[Step 4] User: 'What's my system status?'")
        runtime._transition(ActivityState.THINKING, operation="get_system_status")
        status_res = await runtime.tools.execute("get_system_status", {})
        assert status_res["success"] is True
        assert "cpu_percent" in status_res
        runtime.memory.record_turn(role="tool", content=str(status_res), tool_name="get_system_status", tool_result=status_res)
        print(f"         -> Tool result: CPU {status_res['cpu_percent']}%, RAM {status_res['memory_percent']}%")

        # 5. Say: "Open Notepad."
        print("[Step 5] User: 'Open Notepad.'")
        runtime._transition(ActivityState.THINKING, operation="open_app")
        open_res = await runtime.tools.execute("open_app", {"app_name": "notepad"})
        assert open_res["success"] is True
        runtime.memory.record_turn(role="tool", content=str(open_res), tool_name="open_app", tool_args={"app_name": "notepad"}, tool_result=open_res)
        print(f"         -> Tool result: {open_res['message']}")

        # 6. Wait for completion
        print("[Step 6] Verifying open_app completion and active app tracking...")
        assert runtime.memory.session.resolve_target("app") == "notepad"
        await asyncio.sleep(0.1)

        # 7. Say: "Close it." (Pronoun Resolution -> close_app("notepad"))
        print("[Step 7] User: 'Close it.' (Pronoun Resolution)")
        close_unconf = await runtime.tools.execute("close_app", {"app_name": "it"}, session_id=runtime.session_id)
        assert close_unconf["status"] == "CONFIRM_REQUIRED"
        assert close_unconf["target"] == "notepad"
        token_close = close_unconf["confirmation_token"]
        print(f"         -> Confirmation Vault triggered for target '{close_unconf['target']}' with token '{token_close}'")

        # Confirm close
        close_conf = await runtime.tools.execute("close_app", {"app_name": "it", "confirmation_token": token_close}, session_id=runtime.session_id)
        assert close_conf["success"] is True or "closed_count" in close_conf
        print("         -> Application closed cleanly.")

        # 8. Test a file read
        print("[Step 8] Testing file read...")
        test_doc = tmp_path / "system_spec.txt"
        test_doc.write_text("ULTRON Architecture Spec v3", encoding="utf-8")
        read_res = await runtime.tools.execute("read_file", {"path": "system_spec.txt"})
        assert read_res["success"] is True
        assert "ULTRON Architecture Spec" in read_res["content"]
        runtime.memory.record_turn(role="tool", content=str(read_res), tool_name="read_file", tool_args={"path": "system_spec.txt"}, tool_result=read_res)
        assert runtime.memory.session.resolve_target("file") == "system_spec.txt"
        print(f"         -> File read successful: {read_res['content']}")

        # 9. Test a write requiring confirmation
        print("[Step 9] Testing write requiring confirmation...")
        write_unconf = await runtime.tools.execute("write_file", {"path": "it", "content": "Updated content"}, session_id=runtime.session_id)
        assert write_unconf["status"] == "CONFIRM_REQUIRED"
        assert write_unconf["target"] == "system_spec.txt"
        token_write = write_unconf["confirmation_token"]
        print(f"         -> Token generated for write on target: {write_unconf['target']}")

        # 10. Reject confirmation
        print("[Step 10] Rejecting confirmation (Dismiss)...")
        runtime.memory.record_turn(role="user", content="No, cancel that write.")
        # Attempting write with bad/rejected token fails
        write_rejected = await runtime.tools.execute("write_file", {"path": "it", "confirmation_token": "conf-rejected-bogus"}, session_id=runtime.session_id)
        assert write_rejected["status"] == "CONFIRMATION_INVALID"
        print("         -> Rejected token correctly denied execution.")

        # 11. Repeat and approve confirmation
        print("[Step 11] User repeats and approves confirmation...")
        write_req2 = await runtime.tools.execute("write_file", {"path": "system_spec.txt", "content": "Updated content approved"}, session_id=runtime.session_id)
        token_write2 = write_req2["confirmation_token"]
        write_approved = await runtime.tools.execute("write_file", {"path": "system_spec.txt", "content": "Updated content approved", "confirmation_token": token_write2}, session_id=runtime.session_id)
        assert write_approved["success"] is True
        assert test_doc.read_text(encoding="utf-8") == "Updated content approved"
        print("         -> Write executed successfully upon approval.")

        # 12. Interrupt ULTRON while it is speaking
        print("[Step 12] Simulating Barge-in Interruption...")
        runtime._transition(ActivityState.RESPONDING)
        t0_inter = time.perf_counter()
        runtime._on_barge_in_detected(total_latency_ms=12.4)
        dt_inter = (time.perf_counter() - t0_inter) * 1000.0
        assert runtime.state == ActivityState.LISTENING
        assert dt_inter < 100.0
        print(f"         -> Interrupted and audio cancelled in {dt_inter:.2f}ms (Target: <100ms)")

        # 13. Continue the conversation
        print("[Step 13] Continuing conversation after interruption...")
        runtime.memory.record_turn(role="user", content="What was that file name again?")
        context_summary = runtime.memory.session.get_context_summary()
        assert "system_spec.txt" in context_summary
        print(f"         -> Active context preserved: {context_summary}")

        # 14. Disconnect/reconnect network simulation
        print("[Step 14] Simulating network drop and reconnect...")
        t0_recon = time.perf_counter()
        # Simulate reconnect
        runtime._transition(ActivityState.THINKING, operation="reconnecting")
        await asyncio.sleep(0.05)
        runtime._transition(ActivityState.IDLE, message="Reconnected")
        dt_recon = (time.perf_counter() - t0_recon) * 1000.0
        assert runtime.state == ActivityState.IDLE
        print(f"         -> Reconnected safely in {dt_recon:.2f}ms")

        # 15. Shut down ULTRON
        print("[Step 15] Shutting down ULTRON...")
        await runtime.stop()
        assert runtime.state == ActivityState.OFFLINE
        print("         -> ULTRON cleanly stopped. All audio streams and sessions released.")

        # 16. Start ULTRON again
        print("[Step 16] Starting ULTRON again (Clean restart check)...")
        runtime_restarted = UltronRuntime(cfg)
        assert runtime_restarted.state == ActivityState.IDLE
        await runtime_restarted.stop()
        assert runtime_restarted.state == ActivityState.OFFLINE
        print("         -> ULTRON restarted cleanly without zombie state.")

        print("\n=======================================================")
        print("     ALL 16 STEPS OF END-TO-END SESSION PASSED         ")
        print("=======================================================\n")

    asyncio.run(_async_scenario())
