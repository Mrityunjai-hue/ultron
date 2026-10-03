"""
ULTRON — Single-Instance Process Enforcement
─────────────────────────────────────────────────────────────────────────────
Guarantees that only one active ULTRON runtime can execute concurrently per user
session. Uses a Win32 Named Mutex on Windows and an atomic advisory lockfile as
a cross-platform and process-safe boundary.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from ultron.core.paths import get_cache_dir

logger = logging.getLogger("ultron.core.single_instance")

ERROR_ALREADY_EXISTS = 183


class SingleInstanceLock:
    """Manages single-instance mutex and lockfile acquisition."""

    def __init__(self, lock_name: str = "ULTRON_SingleInstance_Mutex"):
        self.lock_name = lock_name
        self._mutex_handle = None
        self._lock_file_fd = None
        self._acquired = False
        self._lock_file_path = get_cache_dir() / f"{lock_name}.lock"

    def acquire(self) -> bool:
        """Attempts to acquire the single-instance lock. Returns True if successful, False if another instance is running."""
        if self._acquired:
            return True

        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes
                kernel32 = ctypes.windll.kernel32
                mutex_name = f"Local\\{self.lock_name}"

                handle = kernel32.CreateMutexW(None, False, mutex_name)
                last_error = kernel32.GetLastError()
                if last_error == ERROR_ALREADY_EXISTS:
                    logger.warning("[Single Instance] Another instance of ULTRON is already running (Win32 Mutex).")
                    if handle:
                        kernel32.CloseHandle(handle)
                    return False
                self._mutex_handle = handle
            except Exception as e:
                logger.debug(f"[Single Instance] Win32 mutex creation fallback: {e}")

        # Secondary / cross-platform file locking
        try:
            self._lock_file_path.parent.mkdir(parents=True, exist_ok=True)
            self._lock_file_fd = open(self._lock_file_path, "w")
            if sys.platform == "win32":
                import msvcrt
                try:
                    msvcrt.locking(self._lock_file_fd.fileno(), msvcrt.LK_NBLCK, 1)
                except (IOError, OSError):
                    logger.warning("[Single Instance] Another instance is holding the process lockfile.")
                    self._lock_file_fd.close()
                    self._lock_file_fd = None
                    if self._mutex_handle:
                        import ctypes
                        ctypes.windll.kernel32.CloseHandle(self._mutex_handle)
                        self._mutex_handle = None
                    return False
            else:
                import fcntl
                try:
                    fcntl.flock(self._lock_file_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except (IOError, OSError):
                    logger.warning("[Single Instance] Another instance is holding the POSIX lockfile.")
                    self._lock_file_fd.close()
                    self._lock_file_fd = None
                    return False

            self._lock_file_fd.write(str(os.getpid()))
            self._lock_file_fd.flush()
            self._acquired = True
            return True
        except Exception as ex:
            logger.error(f"[Single Instance] Error establishing process lockfile: {ex}")
            return False

    def release(self) -> None:
        """Releases all held mutex handles and lockfile descriptors."""
        if not self._acquired and not self._mutex_handle and not self._lock_file_fd:
            return

        if self._lock_file_fd:
            try:
                if sys.platform == "win32":
                    import msvcrt
                    try:
                        self._lock_file_fd.seek(0)
                        msvcrt.locking(self._lock_file_fd.fileno(), msvcrt.LK_UNLCK, 1)
                    except Exception:
                        pass
                else:
                    import fcntl
                    try:
                        fcntl.flock(self._lock_file_fd, fcntl.LOCK_UN)
                    except Exception:
                        pass
                self._lock_file_fd.close()
            except Exception:
                pass
            self._lock_file_fd = None

        try:
            if self._lock_file_path.exists():
                self._lock_file_path.unlink()
        except Exception:
            pass

        if self._mutex_handle:
            try:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(self._mutex_handle)
            except Exception:
                pass
            self._mutex_handle = None

        self._acquired = False

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("Another instance of ULTRON is currently active.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
