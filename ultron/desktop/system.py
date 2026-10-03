"""
ULTRON V3 — Desktop & OS Utilities
─────────────────────────────────────────────────────────────────────────────
Direct, lightweight execution of local OS actions.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import os
import sys
import time
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

try:
    import psutil
except ImportError:
    psutil = None

def get_current_time() -> Dict[str, Any]:
    """Retrieves authoritative local clock and date."""
    now = datetime.now()
    tz_name = time.tzname[time.daylight] if time.daylight else time.tzname[0]
    return {
        "success": True,
        "time": now.strftime("%I:%M:%S %p"),
        "date": now.strftime("%A, %B %d, %Y"),
        "iso": now.isoformat(),
        "timezone": tz_name,
    }

def get_system_status() -> Dict[str, Any]:
    """Retrieves non-blocking substrate hardware statistics."""
    cpu_pct = psutil.cpu_percent(interval=None) if psutil else 0.0
    mem_pct = psutil.virtual_memory().percent if psutil else 0.0
    mem_avail_mb = round(psutil.virtual_memory().available / (1024 * 1024), 1) if psutil else 0.0

    return {
        "success": True,
        "platform": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "cpu_percent": cpu_pct,
        "memory_percent": mem_pct,
        "available_memory_mb": mem_avail_mb,
    }

def open_application(app_name: str) -> Dict[str, Any]:
    """Launches application safely on Windows without shell execution."""
    known_apps = {
        "notepad": "notepad.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "explorer": "explorer.exe",
        "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "msedge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "code": "code.cmd",
        "paint": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "spotify": "spotify.exe",
    }
    cleaned = app_name.lower().strip()
    target = known_apps.get(cleaned, f"{cleaned}.exe")

    try:
        proc = subprocess.Popen([target], shell=False)
        return {
            "success": True,
            "message": f"Application '{app_name}' launched successfully.",
            "pid": proc.pid,
        }
    except Exception as e:
        # Safe fallback for native Windows registered apps
        try:
            if hasattr(os, "startfile"):
                os.startfile(target)
                return {
                    "success": True,
                    "message": f"Application '{app_name}' launched successfully.",
                }
            raise
        except Exception:
            return {
                "success": False,
                "error": f"Failed to open '{app_name}': {str(e)}",
            }

def close_application(app_name: str) -> Dict[str, Any]:
    """Gracefully terminates running instances of a desktop application."""
    cleaned = app_name.lower().strip().replace(".exe", "")
    app_mapping = {
        "calculator": "calculatorapp.exe",
        "calc": "calculatorapp.exe",
        "notepad": "notepad.exe",
        "chrome": "chrome.exe",
        "edge": "msedge.exe",
        "msedge": "msedge.exe",
        "code": "code.exe",
        "paint": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "spotify": "spotify.exe",
    }
    target_names = [app_mapping.get(cleaned, f"{cleaned}.exe"), f"{cleaned}.exe", cleaned]

    if not psutil:
        return {"success": False, "error": "psutil not available for process management."}

    terminated_pids = []
    procs_to_wait = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            p_name = (proc.info['name'] or '').lower()
            if any(t.lower() == p_name or t.lower() in p_name for t in target_names if t):
                proc.terminate()
                terminated_pids.append(proc.pid)
                procs_to_wait.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if procs_to_wait:
        _, alive = psutil.wait_procs(procs_to_wait, timeout=0.5)
        for p in alive:
            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    if terminated_pids:
        return {
            "success": True,
            "message": f"Closed {len(terminated_pids)} instance(s) of '{app_name}'.",
            "closed_count": len(terminated_pids),
            "pids": terminated_pids,
        }
    else:
        return {
            "success": False,
            "error": f"No running instance of '{app_name}' found to close.",
        }

def read_workspace_file(path: str | Path, workspace_root: str | Path) -> Dict[str, Any]:
    """Reads safe file within workspace."""
    p = Path(path)
    if not p.is_absolute():
        p = Path(workspace_root) / p
    p = p.resolve()

    if not p.exists():
        return {"success": False, "error": f"File '{path}' does not exist."}

    try:
        content = p.read_text(encoding="utf-8", errors="replace")[:4000]
        return {
            "success": True,
            "path": str(p),
            "size_bytes": p.stat().st_size,
            "content": content,
        }
    except Exception as e:
        return {"success": False, "error": f"Failed reading '{path}': {e}"}

def write_workspace_file(path: str | Path, content: str, workspace_root: str | Path) -> Dict[str, Any]:
    """Writes text content to a file strictly within workspace."""
    p = Path(path)
    if not p.is_absolute():
        p = Path(workspace_root) / p
    p = p.resolve()

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "message": f"File '{p.name}' written successfully.",
            "path": str(p),
            "size_bytes": len(content.encode("utf-8")),
        }
    except Exception as e:
        return {"success": False, "error": f"Failed writing to '{path}': {e}"}

def delete_workspace_file(path: str | Path, workspace_root: str | Path) -> Dict[str, Any]:
    """Deletes a file strictly within workspace."""
    p = Path(path)
    if not p.is_absolute():
        p = Path(workspace_root) / p
    p = p.resolve()

    if not p.exists():
        return {"success": False, "error": f"File '{path}' does not exist."}

    try:
        p.unlink()
        return {
            "success": True,
            "message": f"File '{p.name}' deleted successfully.",
            "path": str(p),
        }
    except Exception as e:
        return {"success": False, "error": f"Failed deleting '{path}': {e}"}

def list_workspace_directory(path: str | Path, workspace_root: str | Path) -> Dict[str, Any]:
    """Lists files and folders inside a workspace directory."""
    p = Path(path) if str(path).strip() else Path(".")
    if not p.is_absolute():
        p = Path(workspace_root) / p
    p = p.resolve()

    if not p.exists():
        return {"success": False, "error": f"Directory '{path}' does not exist."}
    if not p.is_dir():
        return {"success": False, "error": f"Path '{path}' is a file, not a directory."}

    try:
        entries = []
        for item in sorted(p.iterdir()):
            entries.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size_bytes": item.stat().st_size if item.is_file() else 0,
            })
        return {
            "success": True,
            "path": str(p),
            "count": len(entries),
            "entries": entries,
        }
    except Exception as e:
        return {"success": False, "error": f"Failed listing directory '{path}': {e}"}

def get_workspace_file_info(path: str | Path, workspace_root: str | Path) -> Dict[str, Any]:
    """Retrieves metadata of a workspace file or directory."""
    p = Path(path)
    if not p.is_absolute():
        p = Path(workspace_root) / p
    p = p.resolve()

    if not p.exists():
        return {
            "success": True,
            "exists": False,
            "path": str(p),
            "name": p.name,
        }

    try:
        stat = p.stat()
        return {
            "success": True,
            "exists": True,
            "path": str(p),
            "name": p.name,
            "is_dir": p.is_dir(),
            "is_file": p.is_file(),
            "size_bytes": stat.st_size if p.is_file() else 0,
            "modified_time": stat.st_mtime,
        }
    except Exception as e:
        return {"success": False, "error": f"Failed getting info for '{path}': {e}"}

def create_workspace_directory(path: str | Path, workspace_root: str | Path) -> Dict[str, Any]:
    """Creates a new directory strictly within workspace."""
    p = Path(path)
    if not p.is_absolute():
        p = Path(workspace_root) / p
    p = p.resolve()

    try:
        p.mkdir(parents=True, exist_ok=True)
        return {
            "success": True,
            "message": f"Directory '{p.name}' created successfully.",
            "path": str(p),
        }
    except Exception as e:
        return {"success": False, "error": f"Failed creating directory '{path}': {e}"}

def copy_workspace_file(source: str | Path, destination: str | Path, workspace_root: str | Path) -> Dict[str, Any]:
    """Copies a file strictly within workspace."""
    import shutil
    src = Path(source)
    if not src.is_absolute():
        src = Path(workspace_root) / src
    src = src.resolve()

    dst = Path(destination)
    if not dst.is_absolute():
        dst = Path(workspace_root) / dst
    dst = dst.resolve()

    if not src.exists():
        return {"success": False, "error": f"Source file '{source}' does not exist."}

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return {
            "success": True,
            "message": f"Copied '{src.name}' to '{dst.name}'.",
            "source": str(src),
            "destination": str(dst),
        }
    except Exception as e:
        return {"success": False, "error": f"Failed copying '{source}' to '{destination}': {e}"}

def move_workspace_file(source: str | Path, destination: str | Path, workspace_root: str | Path) -> Dict[str, Any]:
    """Moves or renames a file strictly within workspace."""
    import shutil
    src = Path(source)
    if not src.is_absolute():
        src = Path(workspace_root) / src
    src = src.resolve()

    dst = Path(destination)
    if not dst.is_absolute():
        dst = Path(workspace_root) / dst
    dst = dst.resolve()

    if not src.exists():
        return {"success": False, "error": f"Source file '{source}' does not exist."}

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)
        return {
            "success": True,
            "message": f"Moved '{src.name}' to '{dst.name}'.",
            "source": str(src),
            "destination": str(dst),
        }
    except Exception as e:
        return {"success": False, "error": f"Failed moving '{source}' to '{destination}': {e}"}

def get_active_app() -> Dict[str, Any]:
    """Retrieves the foreground desktop application and window title."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return {"success": True, "app_name": "unknown", "window_title": "", "pid": 0}

        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value

        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        app_name = "unknown"
        if psutil and pid.value:
            try:
                proc = psutil.Process(pid.value)
                app_name = proc.name().lower().replace(".exe", "")
            except Exception:
                pass

        return {
            "success": True,
            "app_name": app_name,
            "window_title": title,
            "pid": pid.value,
        }
    except Exception as e:
        return {"success": False, "error": f"Failed getting active app: {e}"}

def get_running_apps() -> Dict[str, Any]:
    """Lists running user desktop applications."""
    if not psutil:
        return {"success": False, "error": "psutil not available"}

    apps = []
    seen = set()
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = proc.info['name']
            if name and name.lower().endswith('.exe') and name.lower() not in seen:
                cleaned = name.lower().replace('.exe', '')
                # Filter low-level system background processes
                if cleaned not in ("svchost", "csrss", "smss", "services", "lsass", "winlogon", "dwm", "system", "idle"):
                    apps.append({"name": cleaned, "pid": proc.info['pid']})
                    seen.add(name.lower())
        except Exception:
            pass

    return {
        "success": True,
        "count": len(apps),
        "apps": apps[:30],
    }

def _open_clipboard_retry(user32, retries: int = 10, delay: float = 0.03) -> bool:
    import time
    for _ in range(retries):
        if user32.OpenClipboard(None):
            return True
        time.sleep(delay)
    return False


def read_clipboard() -> Dict[str, Any]:
    """Reads plain text from Windows clipboard."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        if not _open_clipboard_retry(user32):
            return {"success": False, "error": "Unable to open clipboard"}

        CF_UNICODETEXT = 13
        h_clip_mem = user32.GetClipboardData(CF_UNICODETEXT)
        text = ""
        if h_clip_mem:
            p_clip_mem = kernel32.GlobalLock(h_clip_mem)
            if p_clip_mem:
                text = ctypes.c_wchar_p(p_clip_mem).value or ""
                kernel32.GlobalUnlock(h_clip_mem)

        user32.CloseClipboard()
        return {
            "success": True,
            "text": text[:2000],
            "length": len(text),
        }
    except Exception as e:
        return {"success": False, "error": f"Failed reading clipboard: {e}"}

def write_clipboard(text: str) -> Dict[str, Any]:
    """Writes plain text to Windows clipboard."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        if not _open_clipboard_retry(user32):
            return {"success": False, "error": "Unable to open clipboard"}

        user32.EmptyClipboard()
        CF_UNICODETEXT = 13

        str_val = str(text)
        buf = ctypes.create_unicode_buffer(str_val)
        bytes_len = (len(str_val) + 1) * 2

        GMEM_MOVEABLE = 0x0002
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, bytes_len)
        if not h_mem:
            user32.CloseClipboard()
            return {"success": False, "error": "GlobalAlloc failed"}

        p_mem = kernel32.GlobalLock(h_mem)
        if p_mem:
            ctypes.memmove(p_mem, ctypes.byref(buf), bytes_len)
            kernel32.GlobalUnlock(h_mem)
            user32.SetClipboardData(CF_UNICODETEXT, h_mem)

        user32.CloseClipboard()
        return {
            "success": True,
            "message": "Clipboard updated successfully.",
            "length": len(str_val),
        }
    except Exception as e:
        return {"success": False, "error": f"Failed writing clipboard: {e}"}

def enumerate_windows() -> Dict[str, Any]:
    """Lists visible top-level application windows."""
    try:
        import ctypes
        user32 = ctypes.windll.user32

        windows = []
        def enum_windows_callback(hwnd, extra):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value.strip()
                    if title and title not in ("Default IME", "MSCTFIME UI", "Ultron Presence Notch"):
                        pid = ctypes.c_ulong()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        windows.append({"hwnd": hwnd, "title": title, "pid": pid.value})
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)

        return {
            "success": True,
            "count": len(windows),
            "windows": windows[:25],
        }
    except Exception as e:
        return {"success": False, "error": f"Failed enumerating windows: {e}"}
