"""
ULTRON Filesystem Tools v2.0
─────────────────────────────────────────────────────────────────────────────
Real filesystem tools strictly governed by the 4-Tier Safety Policy:
1. create new file        -> SAFE
2. overwrite existing     -> CONFIRM_REQUIRED
3. delete file            -> CONFIRM_REQUIRED
4. outside workspace      -> BLOCKED
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import os
import glob
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from laptop.safety.policy import (
        classify_file_operation,
        is_within_workspace,
        get_workspace_root,
        PolicyVerdict,
    )
except ImportError:
    from safety.policy import (
        classify_file_operation,
        is_within_workspace,
        get_workspace_root,
        PolicyVerdict,
    )

EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode"}

class FileOpsTool:
    """Secure filesystem operations tool."""

    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = (workspace or get_workspace_root()).resolve()

    def _resolve(self, path: str | Path) -> Path:
        """Resolves path relative to workspace if not absolute."""
        p = Path(path)
        if not p.is_absolute():
            return (self.workspace / p).resolve()
        return p.resolve()

    def search_files(self, pattern: str, dir_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Searches files matching a glob pattern within the workspace.
        """
        search_dir = self._resolve(dir_path) if dir_path else self.workspace
        verdict, reason = classify_file_operation("search", search_dir, self.workspace)
        if verdict == PolicyVerdict.BLOCKED:
            return {"success": False, "status": verdict.value, "error": reason}

        if not search_dir.exists() or not search_dir.is_dir():
            return {"success": False, "error": f"Search directory '{search_dir}' does not exist."}

        matches: List[Dict[str, Any]] = []
        try:
            for root, dirs, files in os.walk(search_dir):
                # Filter out excluded directories in-place
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                for file in files:
                    if glob.fnmatch.fnmatch(file, pattern) or pattern in file:
                        full_path = Path(root) / file
                        rel_path = full_path.relative_to(self.workspace).as_posix()
                        matches.append({
                            "path": rel_path,
                            "size_bytes": full_path.stat().st_size,
                        })
                        if len(matches) >= 50:
                            break
                if len(matches) >= 50:
                    break

            return {
                "success": True,
                "status": "SUCCESS",
                "count": len(matches),
                "pattern": pattern,
                "matches": matches,
            }
        except Exception as e:
            return {"success": False, "error": f"Search failed: {e}"}

    def read_file(self, path: str, max_bytes: int = 8000) -> Dict[str, Any]:
        """
        Reads content from a text file within the workspace.
        """
        target = self._resolve(path)
        verdict, reason = classify_file_operation("read", target, self.workspace)
        if verdict == PolicyVerdict.BLOCKED:
            return {"success": False, "status": verdict.value, "error": reason}

        if not target.exists():
            return {"success": False, "error": f"File '{target.name}' not found."}

        if not target.is_file():
            return {"success": False, "error": f"Path '{target.name}' is a directory, not a file."}

        try:
            file_size = target.stat().st_size
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_bytes)

            truncated = file_size > max_bytes
            return {
                "success": True,
                "status": "SUCCESS",
                "path": target.relative_to(self.workspace).as_posix(),
                "content": content,
                "size_bytes": file_size,
                "truncated": truncated,
            }
        except Exception as e:
            return {"success": False, "error": f"Read failed: {e}"}

    def write_file(self, path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
        """
        Writes content to a file.
        Enforces 4-tier policy:
        - If file already exists and overwrite is False -> returns CONFIRM_REQUIRED
        - If file is new or overwrite is True -> writes file
        """
        target = self._resolve(path)
        exists = target.exists()

        verdict, reason = classify_file_operation("write" if exists else "create", target, self.workspace)
        if verdict == PolicyVerdict.BLOCKED:
            return {"success": False, "status": verdict.value, "error": reason}

        if exists and not overwrite:
            return {
                "success": False,
                "status": PolicyVerdict.CONFIRM_REQUIRED.value,
                "message": f"File '{target.name}' already exists. Overwriting requires explicit user confirmation.",
                "path": target.relative_to(self.workspace).as_posix(),
            }

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "status": "SUCCESS",
                "path": target.relative_to(self.workspace).as_posix(),
                "bytes_written": len(content.encode("utf-8")),
                "action": "overwritten" if exists else "created",
            }
        except Exception as e:
            return {"success": False, "error": f"Write failed: {e}"}

    def delete_file(self, path: str, confirmed: bool = False) -> Dict[str, Any]:
        """
        Permanently deletes a file within the workspace.
        Enforces CONFIRM_REQUIRED unless confirmed=True.
        """
        target = self._resolve(path)
        verdict, reason = classify_file_operation("delete", target, self.workspace)
        if verdict == PolicyVerdict.BLOCKED:
            return {"success": False, "status": verdict.value, "error": reason}

        if not target.exists():
            return {"success": False, "error": f"File '{target.name}' does not exist."}

        if not confirmed:
            return {
                "success": False,
                "status": PolicyVerdict.CONFIRM_REQUIRED.value,
                "message": f"Permanent deletion of '{target.name}' requires explicit user confirmation.",
                "path": target.relative_to(self.workspace).as_posix(),
            }

        try:
            target.unlink()
            return {
                "success": True,
                "status": "SUCCESS",
                "path": target.relative_to(self.workspace).as_posix(),
                "action": "deleted",
            }
        except Exception as e:
            return {"success": False, "error": f"Delete failed: {e}"}
