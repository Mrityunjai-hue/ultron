"""
Unit Tests — Safety Audit Logger
"""
import pytest
from laptop.safety.audit_log import AuditLogger

def test_audit_log_append_and_retrieve(tmp_path):
    log_file = tmp_path / "audit.log"
    logger = AuditLogger(log_path=log_file)

    logger.log(
        tool_name="search_files",
        arguments={"pattern": "*.py"},
        verdict="SAFE",
        user="Alex",
        success=True,
        duration_ms=12.4,
    )

    logger.log(
        tool_name="delete_file",
        arguments={"path": "bad.py"},
        verdict="CONFIRM_REQUIRED",
        user="Alex",
        success=False,
        error="User confirmation required",
    )

    entries = logger.get_recent(limit=10)
    assert len(entries) == 2
    # Reverse chronological
    assert entries[0]["tool_name"] == "delete_file"
    assert entries[0]["verdict"] == "CONFIRM_REQUIRED"
    assert entries[1]["tool_name"] == "search_files"
    assert entries[1]["user"] == "Alex"
