"""
ULTRON System & Informational Tools v2.0
─────────────────────────────────────────────────────────────────────────────
Real informational tools providing:
1. Current date, time, timezone, and day of week
2. System resource telemetry (platform, CPU, memory, uptime)
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import datetime
import time
import platform
import os
from typing import Dict, Any

class SystemInfoTool:
    """Provides system time and machine status telemetry."""

    def get_current_time(self) -> Dict[str, Any]:
        """Returns the current local time, date, day of week, and timezone."""
        now = datetime.datetime.now()
        tz_name = time.tzname[time.daylight] if time.daylight else time.tzname[0]
        formatted_time = now.strftime("%I:%M %p").lstrip("0")
        formatted_date = now.strftime("%A, %B %d, %Y")
        
        return {
            "success": True,
            "status": "SUCCESS",
            "time": formatted_time,
            "date": formatted_date,
            "day_of_week": now.strftime("%A"),
            "iso_timestamp": now.isoformat(),
            "timezone": tz_name,
            "summary": f"{formatted_time}, {formatted_date} ({tz_name})",
        }

    def get_system_status(self) -> Dict[str, Any]:
        """Returns hardware and OS platform telemetry."""
        try:
            import psutil
            cpu_pct = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            mem_pct = mem.percent
            mem_avail_gb = round(mem.available / (1024 ** 3), 2)
        except ImportError:
            cpu_pct = 0.0
            mem_pct = 0.0
            mem_avail_gb = 0.0

        return {
            "success": True,
            "status": "SUCCESS",
            "platform": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_percent": cpu_pct,
            "memory_percent": mem_pct,
            "memory_available_gb": mem_avail_gb,
            "python_version": platform.python_version(),
        }
