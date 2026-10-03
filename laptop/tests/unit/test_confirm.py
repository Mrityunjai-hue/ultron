"""
Unit Tests — Confirmation Manager
"""
import pytest
import asyncio
from laptop.safety.confirm import ConfirmationManager

def test_request_and_resolve_approved():
    async def _test():
        cm = ConfirmationManager()
        executed = []

        def my_action():
            executed.append("done")
            return "Action Result"

        req = cm.request_confirmation(
            tool_name="delete_file",
            description="Delete critical file",
            arguments={"path": "important.txt"},
            action_callback=my_action,
        )

        assert req.id is not None
        assert cm.get_pending(req.id) is not None

        # Resolve with approval
        result = await cm.resolve(req.id, approved=True)
        assert result["success"] is True
        assert result["approved"] is True
        assert result["result"] == "Action Result"
        assert executed == ["done"]
        # Pending request should now be removed
        assert cm.get_pending(req.id) is None

    asyncio.run(_test())

def test_request_and_resolve_denied():
    async def _test():
        cm = ConfirmationManager()
        executed = []

        def my_action():
            executed.append("should_not_run")

        req = cm.request_confirmation(
            tool_name="shell",
            description="Run dangerous script",
            arguments={"command": "rm script.py"},
            action_callback=my_action,
        )

        result = await cm.resolve(req.id, approved=False)
        assert result["success"] is False
        assert result["approved"] is False
        assert executed == []
        assert cm.get_pending(req.id) is None

    asyncio.run(_test())
