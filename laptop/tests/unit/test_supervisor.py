"""
Unit Tests — Task Execution Supervisor
"""
import pytest
from laptop.brain.task_planner import TaskSupervisor

def test_supervisor_initialization():
    supervisor = TaskSupervisor(max_steps=5)
    assert supervisor.max_steps == 5
    assert supervisor.current_step == 0
    assert supervisor.progress == 0.0
    assert supervisor.can_proceed() is True

def test_supervisor_step_recording_and_progress():
    supervisor = TaskSupervisor(max_steps=4)
    supervisor.start_task()

    supervisor.record_step(
        tool_name="search_files",
        arguments={"pattern": "*.py"},
        result=["main.py"],
        success=True,
    )
    assert supervisor.current_step == 1
    assert supervisor.progress == 0.25
    assert supervisor.can_proceed() is True

    # Fill to capacity
    supervisor.record_step("read_file", {"path": "main.py"}, success=True)
    supervisor.record_step("write_file", {"path": "out.txt"}, success=True)
    supervisor.record_step("open_app", {"app_name": "notepad"}, success=True)

    assert supervisor.current_step == 4
    assert supervisor.progress == 1.0
    # Should not proceed beyond max_steps
    assert supervisor.can_proceed() is False

def test_supervisor_cancellation():
    supervisor = TaskSupervisor(max_steps=6)
    supervisor.start_task()
    assert supervisor.can_proceed() is True

    supervisor.cancel()
    assert supervisor.is_cancelled is True
    assert supervisor.can_proceed() is False
