"""
Unit Tests — Safety Policy and 4-Tier Filesystem Policy
"""
import pytest
from pathlib import Path
from laptop.safety.policy import (
    classify_file_operation,
    classify_shell_command,
    is_within_workspace,
    PolicyVerdict,
)

@pytest.fixture
def temp_workspace(tmp_path):
    ws = tmp_path / "sandbox"
    ws.mkdir()
    (ws / "existing.txt").write_text("initial content", encoding="utf-8")
    return ws

def test_within_workspace_boundary(temp_workspace):
    inside_file = temp_workspace / "sub" / "file.txt"
    outside_file = Path("C:/Windows/System32/cmd.exe")

    assert is_within_workspace(inside_file, temp_workspace) is True
    assert is_within_workspace(outside_file, temp_workspace) is False
    assert is_within_workspace(temp_workspace / ".." / "escaped.txt", temp_workspace) is False

def test_4_tier_policy_create_new_file(temp_workspace):
    new_file = temp_workspace / "new_file.txt"
    verdict, reason = classify_file_operation("create", new_file, temp_workspace)
    assert verdict == PolicyVerdict.SAFE

def test_4_tier_policy_overwrite_existing_file(temp_workspace):
    existing_file = temp_workspace / "existing.txt"
    verdict, reason = classify_file_operation("write", existing_file, temp_workspace)
    assert verdict == PolicyVerdict.CONFIRM_REQUIRED
    assert "Modifying existing file" in reason

def test_4_tier_policy_delete_file(temp_workspace):
    existing_file = temp_workspace / "existing.txt"
    verdict, reason = classify_file_operation("delete", existing_file, temp_workspace)
    assert verdict == PolicyVerdict.CONFIRM_REQUIRED
    assert "Permanent deletion" in reason

def test_4_tier_policy_outside_workspace_blocked(temp_workspace):
    forbidden = Path("C:/Windows/System32/drivers/etc/hosts")
    verdict, reason = classify_file_operation("read", forbidden, temp_workspace)
    assert verdict == PolicyVerdict.BLOCKED
    assert "outside the authorized workspace" in reason

def test_shell_command_whitelisted_safe():
    assert classify_shell_command("git status")[0] == PolicyVerdict.SAFE
    assert classify_shell_command("dir")[0] == PolicyVerdict.SAFE
    assert classify_shell_command("python --version")[0] == PolicyVerdict.SAFE
    assert classify_shell_command("echo hello")[0] == PolicyVerdict.SAFE

def test_shell_command_blocked_dangerous():
    assert classify_shell_command("format C:")[0] == PolicyVerdict.BLOCKED
    assert classify_shell_command("rmdir /s /q c:\\")[0] == PolicyVerdict.BLOCKED
    assert classify_shell_command("del /f /s /q c:\\")[0] == PolicyVerdict.BLOCKED
    assert classify_shell_command("shutdown /r")[0] == PolicyVerdict.BLOCKED

def test_shell_command_unlisted_requires_confirm():
    assert classify_shell_command("curl http://example.com")[0] == PolicyVerdict.CONFIRM_REQUIRED
