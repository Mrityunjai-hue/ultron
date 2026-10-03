"""
ULTRON V3 — Presence Hit-Testing & Fullscreen Environmental Detector
─────────────────────────────────────────────────────────────────────────────
Calculates non-rectangular hit regions for click-through transparency and
monitors OS state for fullscreen applications (games/video/presentations)
to gracefully retract the notch into an unobtrusive 2px hairline.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import sys
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Literal

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
else:
    user32 = None

# Win32 Constants
HTTRANSPARENT = -1
HTCLIENT = 1

@dataclass
class ClickTarget:
    target_type: str = "NONE"
    data: Optional[str] = None

class HitTester:
    """Calculates whether a screen coordinate falls within the active notch or action buttons."""

    def __init__(self, window_width: int = 640, window_height: int = 540):
        self.screen_width = 1920
        self.screen_height = 1080
        self.window_width = window_width
        self.window_height = window_height

    def set_screen_size(self, width: int, height: int, win_w: int = 640, win_h: int = 540):
        self.screen_width = width
        self.screen_height = height
        self.window_width = win_w
        self.window_height = win_h

    def test_point(
        self,
        screen_x: int,
        screen_y: int,
        notch_width: float,
        notch_height: float,
        state_name: str,
        onboarding_step: int = 1,
    ) -> Tuple[int, ClickTarget]:
        """
        Determines Win32 hit-test response (HTCLIENT vs HTTRANSPARENT)
        and semantic click target for centered overlay window.
        """
        notch_w = int(notch_width)
        notch_h = int(notch_height)
        win_left = (self.screen_width - self.window_width) // 2
        
        # Cursor relative to window center
        rel_x = screen_x - win_left
        rel_y = screen_y

        # Center inside window is (window_width // 2)
        win_cx = self.window_width // 2
        notch_left = win_cx - notch_w // 2
        notch_right = notch_left + notch_w

        # 1. Outside active notch area -> transparent click-through
        if rel_x < notch_left - 12 or rel_x > notch_right + 12 or rel_y < 0 or rel_y > notch_h + 8:
            return HTTRANSPARENT, ClickTarget("NONE")

        # 2. Confirmation Vault State Hit-Testing
        if state_name == "CONFIRMATION" and 130 <= rel_y <= 180:
            btn_w = 154
            gap = 18
            if (win_cx - btn_w - gap // 2 - 4) <= rel_x <= (win_cx - gap // 2 + 4):
                return HTCLIENT, ClickTarget("ALLOW_BUTTON")
            elif (win_cx + gap // 2 - 4) <= rel_x <= (win_cx + btn_w + gap // 2 + 4):
                return HTCLIENT, ClickTarget("DISMISS_BUTTON")

        # 3. Onboarding Experience State Hit-Testing
        if state_name == "ONBOARDING":
            lx = notch_left
            rx = notch_right

            # Bottom navigation buttons (Back & Continue/Finish)
            if 410 <= rel_y <= 462:
                if (lx + 35) <= rel_x <= (lx + 165):
                    return HTCLIENT, ClickTarget("ONBOARDING_BACK")
                elif (rx - 215) <= rel_x <= (rx - 35):
                    return HTCLIENT, ClickTarget("ONBOARDING_NEXT")

            # Step-specific interactive controls
            if onboarding_step == 1:
                if 175 <= rel_y <= 232 and (lx + 35) <= rel_x <= (rx - 35):
                    return HTCLIENT, ClickTarget("ONBOARDING_FIELD_OWNER")
                elif 265 <= rel_y <= 322 and (lx + 35) <= rel_x <= (rx - 35):
                    return HTCLIENT, ClickTarget("ONBOARDING_FIELD_HINT")

            elif onboarding_step == 2:
                if 170 <= rel_y <= 235 and (lx + 35) <= rel_x <= (rx - 35):
                    return HTCLIENT, ClickTarget("ONBOARDING_OPT_ADDR_PREF")
                elif 245 <= rel_y <= 310 and (lx + 35) <= rel_x <= (rx - 35):
                    return HTCLIENT, ClickTarget("ONBOARDING_OPT_ADDR_CUSTOM")
                elif 320 <= rel_y <= 375 and (lx + 35) <= rel_x <= (rx - 35):
                    return HTCLIENT, ClickTarget("ONBOARDING_FIELD_ADDRESS")

            elif onboarding_step == 3:
                if 170 <= rel_y <= 235 and (lx + 35) <= rel_x <= (rx - 35):
                    return HTCLIENT, ClickTarget("ONBOARDING_OPT_ID_ULTRON")
                elif 245 <= rel_y <= 310 and (lx + 35) <= rel_x <= (rx - 35):
                    return HTCLIENT, ClickTarget("ONBOARDING_OPT_ID_CUSTOM")
                elif 320 <= rel_y <= 375 and (lx + 35) <= rel_x <= (rx - 35):
                    return HTCLIENT, ClickTarget("ONBOARDING_FIELD_ASSISTANT")

            elif onboarding_step == 4:
                if 175 <= rel_y <= 225:
                    if (lx + 35) <= rel_x <= (lx + 195):
                        return HTCLIENT, ClickTarget("ONBOARDING_VOICE", "Puck")
                    elif (lx + 205) <= rel_x <= (lx + 365):
                        return HTCLIENT, ClickTarget("ONBOARDING_VOICE", "Charon")
                    elif (lx + 375) <= rel_x <= (rx - 35):
                        return HTCLIENT, ClickTarget("ONBOARDING_VOICE", "Aoede")
                elif 235 <= rel_y <= 285:
                    if (lx + 35) <= rel_x <= (lx + 280):
                        return HTCLIENT, ClickTarget("ONBOARDING_VOICE", "Fenrir")
                    elif (lx + 295) <= rel_x <= (rx - 35):
                        return HTCLIENT, ClickTarget("ONBOARDING_VOICE", "Kore")
                elif 305 <= rel_y <= 345 and (lx + 35) <= rel_x <= (rx - 35):
                    return HTCLIENT, ClickTarget("ONBOARDING_STYLE", "Concise & Authoritative")
                elif 350 <= rel_y <= 390 and (lx + 35) <= rel_x <= (rx - 35):
                    return HTCLIENT, ClickTarget("ONBOARDING_STYLE", "Analytical & Detailed")

            elif onboarding_step == 5:
                if 305 <= rel_y <= 375 and (lx + 35) <= rel_x <= (rx - 35):
                    return HTCLIENT, ClickTarget("ONBOARDING_TOGGLE_MEMORY")

            elif onboarding_step == 6:
                if 215 <= rel_y <= 290 and (lx + 35) <= rel_x <= (rx - 35):
                    return HTCLIENT, ClickTarget("ONBOARDING_TOGGLE_STARTUP")

            if 0 <= rel_y <= notch_h:
                return HTCLIENT, ClickTarget("NOTCH")

        # 4. Standard client hit on active notch body
        if 0 <= rel_y <= notch_h:
            return HTCLIENT, ClickTarget("NOTCH")

        return HTTRANSPARENT, ClickTarget("NONE")

class FullscreenDetector:
    """Monitors foreground window to detect active fullscreen games, videos, or presentations."""

    def __init__(self):
        self._last_check = 0.0
        self._check_interval = 0.5  # Check twice per second to minimize CPU (<0.01%)
        self._is_fullscreen = False

    def is_fullscreen_active(self, screen_w: int, screen_h: int) -> bool:
        if not user32 or sys.platform != "win32":
            return False

        now = time.time()
        if now - self._last_check < self._check_interval:
            return self._is_fullscreen

        self._last_check = now
        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return self._is_fullscreen

            # Ignore Desktop, Taskbar, and Shell
            class_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_buf, 256)
            cname = class_buf.value
            if cname in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
                self._is_fullscreen = False
                return False

            # Check window bounding rect
            rect = wintypes.RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                # Fullscreen matches or exceeds primary display size
                if rect.left <= 0 and rect.top <= 0 and w >= screen_w and h >= screen_h:
                    self._is_fullscreen = True
                    return True

            self._is_fullscreen = False
            return False
        except Exception:
            return self._is_fullscreen
