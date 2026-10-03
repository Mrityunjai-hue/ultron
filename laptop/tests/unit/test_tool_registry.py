"""
Unit Tests — Tool Registry and Execution Dispatch
"""
import pytest
import asyncio
from laptop.tools.registry import ToolRegistry, TOOL_SCHEMAS

def test_tool_schemas_validity():
    registry = ToolRegistry()
    schemas = registry.get_schemas()
    assert len(schemas) >= 5
    tool_names = [s["function"]["name"] for s in schemas]
    assert "search_files" in tool_names
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "delete_file" in tool_names
    assert "open_app" in tool_names
    assert "close_app" in tool_names
    assert "shell" in tool_names

def test_registry_dispatch_search_files(tmp_path):
    async def _test():
        registry = ToolRegistry()
        registry.file_ops.workspace = tmp_path
        (tmp_path / "data.csv").write_text("a,b,c", encoding="utf-8")

        res = await registry.execute(
            tool_name="search_files",
            arguments={"pattern": "*.csv"},
            user="Tester",
        )
        assert res["success"] is True
        assert res["count"] == 1

    asyncio.run(_test())

def test_registry_dispatch_write_file_confirm_gating(tmp_path):
    async def _test():
        registry = ToolRegistry()
        registry.file_ops.workspace = tmp_path
        target = tmp_path / "exist.txt"
        target.write_text("old", encoding="utf-8")

        # Overwrite attempt without overwrite=True
        res = await registry.execute(
            tool_name="write_file",
            arguments={"path": "exist.txt", "content": "new"},
            user="Tester",
        )
        assert res["success"] is False
        assert res["status"] == "CONFIRM_REQUIRED"

        # Check pending confirmation was created
        pending = registry.confirm_manager.get_latest_pending()
        assert pending is not None
        assert pending.tool_name == "write_file"

    asyncio.run(_test())

def test_registry_dispatch_get_current_time():
    async def _test():
        registry = ToolRegistry()
        res = await registry.execute(tool_name="get_current_time", arguments={})
        assert res["success"] is True
        assert "time" in res
        assert "date" in res
        assert "timezone" in res

    asyncio.run(_test())

def test_registry_dispatch_get_system_status():
    async def _test():
        registry = ToolRegistry()
        res = await registry.execute(tool_name="get_system_status", arguments={})
        assert res["success"] is True
        assert "platform" in res
        assert "machine" in res

    asyncio.run(_test())

