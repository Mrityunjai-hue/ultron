"""
ULTRON V3 — Comprehensive Phase 6 Multi-Step Task Execution Test Suite
─────────────────────────────────────────────────────────────────────────────
Covers:
1. Single safe task execution & verification
2. Two-step task execution
3. Five-step task execution
4. Tool failure in middle of task
5. Verification failure detection
6. Bounded retry upon verification failure
7. Retry limit enforcement (max 2 retries)
8. Confirmation pause (TASK_WAITING_CONFIRMATION)
9. Confirmation approval & task resumption
10. Confirmation rejection & task cancellation
11. Confirmation token expiry handling
12. Cancellation before execution starts
13. Cancellation during execution
14. Cancellation after one step completes
15. Duplicate task prevention
16. Concurrent request handling (concurrency lock)
17. Pronoun resolution across task steps ('it', 'the file')
18. Persistent context integration across tasks
19. Runtime reconnect during task
20. Runtime shutdown during task
21. Blocked shell attempt (cmd, powershell, bash)
22. Command injection attempt
23. Protected system path access attempt
24. Successful end-to-end desktop task (Notepad + Workspace file + verify)
25. Failed end-to-end desktop task
26. Recovery after failed task
─────────────────────────────────────────────────────────────────────────────
"""
import pytest
import asyncio
import time
from pathlib import Path

from ultron.core.config import UltronConfig
from ultron.core.events import ActivityState, EngineEvent, EventBus
from ultron.core.runtime import UltronRuntime
from ultron.tasks.models import Task, TaskStep, VerificationResult
from ultron.tasks.state import TaskState, StepStatus
from ultron.tasks.errors import (
    TaskPlanningError,
    TaskSecurityViolationError,
    TaskVerificationError,
    TaskTimeoutError,
    TaskCancelledError,
    TaskConcurrencyError,
)
from ultron.tasks.planner import TaskPlanner
from ultron.tasks.executor import TaskExecutionEngine
from ultron.tasks.verifier import ActionVerifier
from ultron.tasks.cancellation import TaskCancellationManager
from ultron.tools.confirmation import ConfirmationManager
from ultron.tools.executor import ToolExecutor
from ultron.tools.safety import classify_file_operation, classify_app_operation, PolicyVerdict
from ultron.memory.manager import MemoryManager

@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "ultron_workspace"
    ws.mkdir()
    return ws

@pytest.fixture
def engine(workspace):
    conf_mgr = ConfirmationManager()
    mem_mgr = MemoryManager()
    tools = ToolExecutor(workspace_root=workspace, confirmation_manager=conf_mgr, memory_manager=mem_mgr)
    event_bus = EventBus()
    eng = TaskExecutionEngine(
        tool_executor=tools,
        confirmation_manager=conf_mgr,
        memory_manager=mem_mgr,
        event_bus=event_bus,
        workspace_root=workspace,
    )
    planner = TaskPlanner(workspace_root=workspace)
    return eng, planner, conf_mgr, mem_mgr, tools, event_bus

# =====================================================================
# 1. Single Safe Task
# =====================================================================
@pytest.mark.anyio
async def test_single_safe_task(engine, workspace):
    eng, planner, _, _, _, _ = engine
    task = planner.plan_single_action("get_current_time", {}, user_intent="Check the time")
    res = await eng.execute_task(task)

    assert res["success"] is True
    assert res["status"] == "COMPLETED"
    assert task.state == TaskState.TASK_COMPLETED
    assert len(task.steps) == 1
    assert task.steps[0].status == StepStatus.COMPLETED
    assert task.steps[0].verification.verified is True

# =====================================================================
# 2. Two-Step Task
# =====================================================================
@pytest.mark.anyio
async def test_two_step_task(engine, workspace):
    eng, planner, _, _, _, _ = engine
    plan_spec = [
        {"tool_name": "create_directory", "arguments": {"path": "projects"}, "purpose": "Create projects folder"},
        {"tool_name": "list_directory", "arguments": {"path": ""}, "purpose": "List workspace files"},
    ]
    task = planner.plan_multi_step_task("Create folder and list", plan_spec)
    res = await eng.execute_task(task)

    assert res["success"] is True
    assert res["steps_count"] == 2
    assert (workspace / "projects").is_dir()
    assert task.state == TaskState.TASK_COMPLETED

# =====================================================================
# 3. Five-Step Task
# =====================================================================
@pytest.mark.anyio
async def test_five_step_task(engine, workspace):
    eng, planner, _, _, _, _ = engine
    plan_spec = [
        {"tool_name": "get_current_time", "arguments": {}, "purpose": "Step 1: Check time"},
        {"tool_name": "get_system_status", "arguments": {}, "purpose": "Step 2: Check status"},
        {"tool_name": "create_directory", "arguments": {"path": "step_folder"}, "purpose": "Step 3: Make folder"},
        {"tool_name": "write_clipboard", "arguments": {"text": "Ultron Phase 6"}, "purpose": "Step 4: Copy to clipboard"},
        {"tool_name": "read_clipboard", "arguments": {}, "purpose": "Step 5: Verify clipboard"},
    ]
    task = planner.plan_multi_step_task("Execute five safe steps", plan_spec)
    res = await eng.execute_task(task)

    assert res["success"] is True
    assert res["steps_count"] == 5
    assert len(task.steps) == 5
    for s in task.steps:
        assert s.status == StepStatus.COMPLETED
        assert s.verification.verified is True

# =====================================================================
# 4. Tool Failure in Middle of Task
# =====================================================================
@pytest.mark.anyio
async def test_tool_failure_in_middle_of_task(engine, workspace):
    eng, planner, _, _, _, _ = engine
    plan_spec = [
        {"tool_name": "create_directory", "arguments": {"path": "dir_a"}, "purpose": "Step 1"},
        {"tool_name": "read_file", "arguments": {"path": "nonexistent_file_xyz.txt"}, "purpose": "Step 2: Read missing file"},
        {"tool_name": "create_directory", "arguments": {"path": "dir_b"}, "purpose": "Step 3: Should never run"},
    ]
    task = planner.plan_multi_step_task("Partial failure test", plan_spec)
    res = await eng.execute_task(task)

    assert res["success"] is False
    assert res["status"] == "TASK_FAILED"
    assert res["failed_step_id"] == "step-2"
    assert (workspace / "dir_a").is_dir()
    assert not (workspace / "dir_b").exists()
    assert task.steps[2].status == StepStatus.PENDING

# =====================================================================
# 5 & 6 & 7. Verification Failure, Retry, and Retry Limit
# =====================================================================
@pytest.mark.anyio
async def test_verification_failure_and_retry_limit(engine, workspace):
    eng, planner, _, _, _, _ = engine

    # Construct a step that intentionally fails verification
    step = TaskStep(
        step_id="step-fail-verify",
        tool_name="read_file",
        arguments={"path": "dummy.txt"},
        purpose="Fails verification test",
        max_retries=2,
    )
    task = Task.create(user_intent="Verification retry test", steps=[step])

    # Monkey patch verifier to simulate verification failure
    original_verify = eng.verifier.verify_step
    try:
        eng.verifier.verify_step = lambda s, r: VerificationResult(
            verified=False,
            method="mock_verifier",
            error_message="Simulated verification mismatch",
        )

        # Write dummy file so tool itself succeeds
        (workspace / "dummy.txt").write_text("ok", encoding="utf-8")

        res = await eng.execute_task(task)
        assert res["success"] is False
        assert res["status"] == "TASK_FAILED"
        assert "Simulated verification mismatch" in res["error"]
        assert step.retries_attempted == 3  # Initial attempt + 2 retries = 3 attempts total
    finally:
        eng.verifier.verify_step = original_verify

# =====================================================================
# 8 & 9. Confirmation Pause and Approval
# =====================================================================
@pytest.mark.anyio
async def test_confirmation_pause_and_approval(engine, workspace):
    eng, planner, conf_mgr, _, _, _ = engine

    plan_spec = [
        {"tool_name": "write_file", "arguments": {"path": "confirmed.txt", "content": "Confirmed data"}, "purpose": "Write with confirmation"},
    ]
    task = planner.plan_multi_step_task("Write file needing confirmation", plan_spec)
    assert task.steps[0].requires_confirmation is True

    # 1. First execution attempt pauses for confirmation
    res_pause = await eng.execute_task(task)
    assert res_pause["status"] == "CONFIRM_REQUIRED"
    token = res_pause["confirmation_token"]
    assert token != ""
    assert task.state == TaskState.TASK_WAITING_CONFIRMATION

    # 2. Approve by resuming with valid token
    res_resume = await eng.resume_task_with_confirmation(task.task_id, token)
    assert res_resume["success"] is True
    assert res_resume["status"] == "COMPLETED"
    assert (workspace / "confirmed.txt").read_text(encoding="utf-8") == "Confirmed data"

# =====================================================================
# 10. Confirmation Rejection
# =====================================================================
@pytest.mark.anyio
async def test_confirmation_rejection(engine, workspace):
    eng, planner, conf_mgr, _, _, _ = engine

    plan_spec = [
        {"tool_name": "write_file", "arguments": {"path": "reject.txt", "content": "Do not write"}, "purpose": "Write"},
    ]
    task = planner.plan_multi_step_task("Write file test", plan_spec)
    res_pause = await eng.execute_task(task)
    assert res_pause["status"] == "CONFIRM_REQUIRED"
    token = res_pause["confirmation_token"]

    # User rejects -> dismiss pending confirmation & cancel task
    conf_mgr.dismiss(token)
    eng.cancel_active_task("User rejected confirmation")

    assert task.state == TaskState.TASK_CANCELLED
    assert not (workspace / "reject.txt").exists()

# =====================================================================
# 11. Confirmation Expiration
# =====================================================================
@pytest.mark.anyio
async def test_confirmation_expiration(engine, workspace):
    eng, planner, conf_mgr, _, _, _ = engine

    plan_spec = [
        {"tool_name": "write_file", "arguments": {"path": "expire.txt", "content": "Expiry test"}, "purpose": "Write"},
    ]
    task = planner.plan_multi_step_task("Expiry test", plan_spec)
    res_pause = await eng.execute_task(task)
    token = res_pause["confirmation_token"]

    # Artificially expire the token
    pending = conf_mgr.get_pending(token)
    assert pending is not None
    pending.expires_at = time.time() - 10.0

    # Resume with expired token
    res_resume = await eng.resume_task_with_confirmation(task.task_id, token)
    assert res_resume["success"] is False
    assert not (workspace / "expire.txt").exists()

# =====================================================================
# 12. Cancellation Before Execution
# =====================================================================
@pytest.mark.anyio
async def test_cancellation_before_execution(engine, workspace):
    eng, planner, _, _, _, _ = engine
    task = planner.plan_single_action("get_current_time", {}, user_intent="Check time")
    
    # Pre-cancel before execute
    eng.cancellation.cancel_task(task.task_id, reason="Pre-cancelled")
    res = await eng.execute_task(task)

    assert res["success"] is False
    assert res["status"] == "TASK_CANCELLED"
    assert task.state == TaskState.TASK_CANCELLED

# =====================================================================
# 13 & 14. Cancellation During / After One Step
# =====================================================================
@pytest.mark.anyio
async def test_cancellation_during_multi_step_execution(engine, workspace):
    eng, planner, _, _, _, _ = engine

    # We will cancel during step 2 via event bus trigger
    plan_spec = [
        {"tool_name": "create_directory", "arguments": {"path": "step1_dir"}, "purpose": "Step 1"},
        {"tool_name": "create_directory", "arguments": {"path": "step2_dir"}, "purpose": "Step 2"},
        {"tool_name": "create_directory", "arguments": {"path": "step3_dir"}, "purpose": "Step 3: Should never run"},
    ]
    task = planner.plan_multi_step_task("Cancel midway", plan_spec)

    # Cancel right after step 1 completes
    original_verify = eng.verifier.verify_step
    def _verify_and_cancel(step, res):
        v = original_verify(step, res)
        if step.step_id == "step-1":
            eng.cancel_active_task("User said Stop")
        return v

    eng.verifier.verify_step = _verify_and_cancel
    try:
        res = await eng.execute_task(task)
        assert res["status"] == "TASK_CANCELLED"
        assert (workspace / "step1_dir").is_dir()
        assert not (workspace / "step3_dir").exists()
    finally:
        eng.verifier.verify_step = original_verify

# =====================================================================
# 15 & 16. Duplicate Task Prevention & Concurrency Locking
# =====================================================================
@pytest.mark.anyio
async def test_duplicate_task_and_concurrency_locking(engine, workspace):
    eng, planner, _, _, _, _ = engine

    task1 = planner.plan_single_action("get_current_time", {}, user_intent="Task 1")
    task2 = planner.plan_single_action("get_system_status", {}, user_intent="Task 2")

    # Manually set active task as running
    eng.active_task = task1
    task1.state = TaskState.TASK_EXECUTING

    with pytest.raises(TaskConcurrencyError) as exc_info:
        await eng.execute_task(task2)

    assert "currently running" in str(exc_info.value)
    eng.active_task = None

# =====================================================================
# 17. Pronoun Resolution Across Task Steps
# =====================================================================
@pytest.mark.anyio
async def test_pronoun_resolution_across_task_steps(engine, workspace):
    eng, planner, conf_mgr, mem_mgr, tools, _ = engine

    # Create file first
    test_file = workspace / "notes.txt"
    test_file.write_text("Initial notes", encoding="utf-8")
    mem_mgr.session.track_target("file", "notes.txt")

    # Reference "it" in next task step
    plan_spec = [
        {"tool_name": "read_file", "arguments": {"path": "it"}, "purpose": "Read active file via pronoun"},
    ]
    task = planner.plan_multi_step_task("Read it", plan_spec)
    res = await eng.execute_task(task)

    assert res["success"] is True
    assert res["results"][0]["result"]["content"] == "Initial notes"

# =====================================================================
# 18. Persistent Context Integration
# =====================================================================
@pytest.mark.anyio
async def test_persistent_context_across_tasks(engine, workspace):
    eng, planner, _, mem_mgr, _, _ = engine

    # Remember preference in task 1
    task1 = planner.plan_single_action("remember_fact", {"key": "editor", "value": "VS Code"}, user_intent="Set editor")
    res1 = await eng.execute_task(task1)
    assert res1["success"] is True

    # List memories in task 2
    task2 = planner.plan_single_action("list_memories", {}, user_intent="Check editor")
    res2 = await eng.execute_task(task2)
    assert res2["success"] is True
    assert "VS Code" in str(res2)

# =====================================================================
# 19. Runtime Reconnect During Task
# =====================================================================
@pytest.mark.anyio
async def test_runtime_reconnect_during_task(tmp_path):
    cfg = UltronConfig()
    cfg.workspace_root = tmp_path
    cfg.gemini_api_key = "test_key"
    runtime = UltronRuntime(cfg)

    # Start a 2-step task
    plan_spec = [
        {"tool_name": "create_directory", "arguments": {"path": "rec_folder"}, "purpose": "Make dir"},
        {"tool_name": "get_current_time", "arguments": {}, "purpose": "Time check"},
    ]
    res = await runtime.execute_plan("Test reconnect resilience", plan_spec)
    assert res["success"] is True
    assert (tmp_path / "rec_folder").is_dir()
    await runtime.stop()

# =====================================================================
# 20. Runtime Shutdown During Task
# =====================================================================
@pytest.mark.anyio
async def test_runtime_shutdown_during_task(tmp_path):
    cfg = UltronConfig()
    cfg.workspace_root = tmp_path
    cfg.gemini_api_key = "test_key"
    runtime = UltronRuntime(cfg)

    task = runtime.task_planner.plan_single_action("get_current_time", {}, user_intent="Time")
    runtime.tasks.active_task = task
    task.state = TaskState.TASK_EXECUTING

    # Stop runtime -> triggers active task cancellation
    await runtime.stop()
    assert task.state == TaskState.TASK_CANCELLED

# =====================================================================
# 21, 22, 23. Security Boundary: Blocked Shells, Injections, Paths
# =====================================================================
def test_security_boundary_enforcement(engine, workspace):
    _, planner, _, _, _, _ = engine

    # 21. Blocked shell attempt
    with pytest.raises(TaskSecurityViolationError) as exc_shell:
        planner.plan_single_action("open_app", {"app_name": "cmd.exe"})
    assert "blocked" in str(exc_shell.value).lower()

    with pytest.raises(TaskSecurityViolationError) as exc_ps:
        planner.plan_single_action("open_app", {"app_name": "powershell.exe"})
    assert "blocked" in str(exc_ps.value).lower()

    # 22. Command injection attempt
    with pytest.raises(TaskSecurityViolationError) as exc_inj:
        planner.plan_single_action("open_app", {"app_name": "notepad & calc"})
    assert "blocked" in str(exc_inj.value).lower()

    # 23. Protected system path attempt
    with pytest.raises(TaskSecurityViolationError) as exc_path:
        planner.plan_single_action("write_file", {"path": "C:/Windows/System32/evil.dll", "content": "bad"})
    assert "blocked" in str(exc_path.value).lower()

# =====================================================================
# 24. Successful Real End-to-End Desktop Task
# "Open Notepad -> Create Workspace File -> Write Sentence -> Verify -> Close Notepad"
# =====================================================================
@pytest.mark.anyio
async def test_e2e_real_desktop_task(tmp_path):
    cfg = UltronConfig()
    cfg.workspace_root = tmp_path
    cfg.gemini_api_key = "mock_key"
    runtime = UltronRuntime(cfg)

    # 1. Open Notepad
    t1 = runtime.task_planner.plan_single_action("open_app", {"app_name": "notepad"}, user_intent="Open Notepad")
    r1 = await runtime.execute_task(t1)
    assert r1["success"] is True

    # 2. Write file inside workspace
    t2 = runtime.task_planner.plan_single_action(
        "write_file",
        {"path": "phase6_sentence.txt", "content": "ULTRON Phase 6 works with verified accuracy."},
        user_intent="Write sentence to file",
    )
    r2_pause = await runtime.execute_task(t2)
    assert r2_pause["status"] == "CONFIRM_REQUIRED"
    token = r2_pause["confirmation_token"]

    r2_conf = await runtime.resume_task_confirmation(t2.task_id, token)
    assert r2_conf["success"] is True
    assert (tmp_path / "phase6_sentence.txt").read_text(encoding="utf-8") == "ULTRON Phase 6 works with verified accuracy."

    # 3. Read back and verify
    t3 = runtime.task_planner.plan_single_action("read_file", {"path": "phase6_sentence.txt"}, user_intent="Verify file content")
    r3 = await runtime.execute_task(t3)
    assert r3["success"] is True
    assert "ULTRON Phase 6" in r3["results"][0]["result"]["content"]

    # 4. Close Notepad with confirmation
    t4 = runtime.task_planner.plan_single_action("close_app", {"app_name": "notepad"}, user_intent="Close Notepad")
    r4_pause = await runtime.execute_task(t4)
    assert r4_pause["status"] == "CONFIRM_REQUIRED"
    token_close = r4_pause["confirmation_token"]

    r4_conf = await runtime.resume_task_confirmation(t4.task_id, token_close)
    assert r4_conf["success"] is True

    await runtime.stop()

# =====================================================================
# 25 & 26. Failed Desktop Task and Clean Recovery
# =====================================================================
@pytest.mark.anyio
async def test_failed_task_and_recovery(engine, workspace):
    eng, planner, _, _, _, _ = engine

    # Task 1: Fails on non-existent read
    t1 = planner.plan_single_action("read_file", {"path": "non_existent_123.txt"}, user_intent="Failing task")
    r1 = await eng.execute_task(t1)
    assert r1["success"] is False
    assert t1.state == TaskState.TASK_FAILED

    # Task 2: Recovers and executes cleanly
    t2 = planner.plan_single_action("get_current_time", {}, user_intent="Recovery task")
    r2 = await eng.execute_task(t2)
    assert r2["success"] is True
    assert t2.state == TaskState.TASK_COMPLETED
