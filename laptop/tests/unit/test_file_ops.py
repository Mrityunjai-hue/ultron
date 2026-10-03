"""
Unit Tests — FileOpsTool with 4-Tier Policy Enforcement
"""
import pytest
from pathlib import Path
from laptop.tools.file_ops import FileOpsTool

@pytest.fixture
def workspace_with_files(tmp_path):
    ws = tmp_path / "sandbox"
    ws.mkdir()
    (ws / "hello.txt").write_text("Hello Ultron", encoding="utf-8")
    sub = ws / "sub"
    sub.mkdir()
    (sub / "nested.py").write_text("print(42)", encoding="utf-8")
    return ws

def test_search_files(workspace_with_files):
    tool = FileOpsTool(workspace=workspace_with_files)
    res = tool.search_files("*.txt")
    assert res["success"] is True
    assert res["count"] >= 1
    assert any("hello.txt" in m["path"] for m in res["matches"])

def test_read_file(workspace_with_files):
    tool = FileOpsTool(workspace=workspace_with_files)
    res = tool.read_file("hello.txt")
    assert res["success"] is True
    assert res["content"] == "Hello Ultron"

def test_write_new_file_safe(workspace_with_files):
    tool = FileOpsTool(workspace=workspace_with_files)
    res = tool.write_file("new.txt", "Fresh Content")
    assert res["success"] is True
    assert res["status"] == "SUCCESS"
    assert (workspace_with_files / "new.txt").read_text(encoding="utf-8") == "Fresh Content"

def test_overwrite_existing_file_requires_confirm(workspace_with_files):
    tool = FileOpsTool(workspace=workspace_with_files)
    # Attempt overwrite without flag
    res = tool.write_file("hello.txt", "Overwritten", overwrite=False)
    assert res["success"] is False
    assert res["status"] == "CONFIRM_REQUIRED"
    assert "already exists" in res["message"]

    # Provide overwrite=True
    res2 = tool.write_file("hello.txt", "Overwritten", overwrite=True)
    assert res2["success"] is True
    assert (workspace_with_files / "hello.txt").read_text(encoding="utf-8") == "Overwritten"

def test_delete_file_requires_confirm(workspace_with_files):
    tool = FileOpsTool(workspace=workspace_with_files)
    # Without confirmation
    res = tool.delete_file("hello.txt", confirmed=False)
    assert res["success"] is False
    assert res["status"] == "CONFIRM_REQUIRED"
    assert (workspace_with_files / "hello.txt").exists()

    # With confirmation
    res2 = tool.delete_file("hello.txt", confirmed=True)
    assert res2["success"] is True
    assert not (workspace_with_files / "hello.txt").exists()

def test_file_ops_outside_workspace_blocked(workspace_with_files):
    tool = FileOpsTool(workspace=workspace_with_files)
    res = tool.read_file("../../outside.txt")
    assert res["success"] is False
    assert res["status"] == "BLOCKED"
