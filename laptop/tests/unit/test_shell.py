"""
Unit Tests — Safe Shell Tool
"""
import pytest
from laptop.tools.shell import ShellTool

def test_shell_safe_command_execution(tmp_path):
    tool = ShellTool(workspace=tmp_path)
    res = tool.execute("python --version")
    assert res["success"] is True
    assert res["status"] == "SUCCESS"
    assert "Python" in res["stdout"] or "Python" in res["stderr"]

def test_shell_blocked_destructive_command(tmp_path):
    tool = ShellTool(workspace=tmp_path)
    res = tool.execute("format C:")
    assert res["success"] is False
    assert res["status"] == "BLOCKED"

def test_shell_unlisted_command_requires_confirmation(tmp_path):
    tool = ShellTool(workspace=tmp_path)
    res = tool.execute("powershell -Command Get-Process", confirmed=False)
    assert res["success"] is False
    assert res["status"] == "CONFIRM_REQUIRED"

    # With confirmed=True
    res2 = tool.execute("powershell -Command Get-Process", confirmed=True)
    assert res2["status"] in ("SUCCESS", "COMMAND_ERROR")
