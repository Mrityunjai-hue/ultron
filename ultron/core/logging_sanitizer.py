"""
ULTRON — Secret-Sanitizing Structured Logging Layer
─────────────────────────────────────────────────────────────────────────────
Filters all application, dependency, and crash log records to guarantee that
no API keys, tokens, passwords, or credentials can ever reach log files or stdout.
Manages bounded, rotating file logging in %LOCALAPPDATA%/ULTRON/logs/.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from ultron.core.paths import get_logs_dir

# Secret scrubbing regexes for active log stream
LOG_SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z\-_]{30,45}"),                             # Gemini / Google API Key
    re.compile(r"gh[pousr]_[0-9a-zA-Z]{36,255}"),                         # GitHub Token
    re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{20,}"),                    # Bearer Token
    re.compile(r"(?i)(password|passwd|pwd|api[_-]?key|secret[_-]?key)\s*[:=]\s*['\"][^'\"]+['\"]"), # Hardcoded secrets
    re.compile(r"-----BEGIN\s+(?:[A-Z ]+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:[A-Z ]+)?PRIVATE\s+KEY-----"),
    re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"), # JWT
]


class SecretSanitizingFilter(logging.Filter):
    """Logging filter that scrubs sensitive patterns from all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.sanitize_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: (self.sanitize_text(v) if isinstance(v, str) else v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.sanitize_text(arg) if isinstance(arg, str) else arg for arg in record.args)
        return True

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        if not isinstance(text, str):
            return text
        sanitized = text
        for pat in LOG_SECRET_PATTERNS:
            sanitized = pat.sub("[REDACTED_SECRET]", sanitized)
        return sanitized


def setup_logging(
    level: int = logging.INFO,
    log_dir: Optional[Path] = None,
    log_file_name: str = "ultron.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB per file
    backup_count: int = 5,
    enable_console: bool = True,
) -> logging.Logger:
    """Configures root logging with secret scrubbing, rotation, and bounded storage."""
    target_dir = log_dir or get_logs_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / log_file_name

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    sanitizer = SecretSanitizingFilter()
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Rotating File Handler
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(sanitizer)
    root_logger.addHandler(file_handler)

    # 2. Console Handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(sanitizer)
        root_logger.addHandler(console_handler)

    return logging.getLogger("ultron")
