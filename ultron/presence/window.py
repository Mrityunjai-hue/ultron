"""
ULTRON V3 — Native Windows Transparent Overlay Window
─────────────────────────────────────────────────────────────────────────────
High-performance borderless transparent layered overlay using Win32 API:
- WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW
- True 32-bit per-pixel alpha transparency (UpdateLayeredWindow)
- Non-rectangular click-through hit testing via WM_NCHITTEST
- Adaptive frame pacing: event-driven sleeping at idle (<0.2% CPU), locked 60 FPS when active
- Integrated fullscreen application retraction
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import logging
import sys
import threading
import time
from typing import Optional, Callable

if sys.platform == "win32":
    import win32gui
    import win32con
    import win32api
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
else:
    win32gui = None
    win32con = None
    win32api = None
    user32 = None
    gdi32 = None

from ultron.presence.animation import SpringChoreographer
from ultron.presence.audio_visualizer import AudioVisualizer
from ultron.presence.hit_testing import HitTester, FullscreenDetector, HTCLIENT, HTTRANSPARENT, ClickTarget
from ultron.presence.renderer import PresenceRenderer

logger = logging.getLogger("ultron.presence.window")

# Win32 GDI Structures for UpdateLayeredWindow
class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_byte),
        ("BlendFlags", ctypes.c_byte),
        ("SourceConstantAlpha", ctypes.c_byte),
        ("AlphaFormat", ctypes.c_byte),
    ]

AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]

BI_RGB = 0

class UltronOverlayWindow:
    """Manages the native Windows desktop top-bezel overlay window."""

    def __init__(
        self,
        choreographer: Optional[SpringChoreographer] = None,
        audio_visualizer: Optional[AudioVisualizer] = None,
        on_allow_click: Optional[Callable[[], None]] = None,
        on_dismiss_click: Optional[Callable[[], None]] = None,
        on_notch_click: Optional[Callable[[], None]] = None,
    ):
        self.choreographer = choreographer or SpringChoreographer()
        self.audio_viz = audio_visualizer or AudioVisualizer()
        self.on_allow_click = on_allow_click
        self.on_dismiss_click = on_dismiss_click
        self.on_notch_click = on_notch_click
        self.onboarding_controller = None

        self.screen_width = 1920
        self.screen_height = 1080
        self.window_width = 640
        self.window_height = 540
        self.window_left = (self.screen_width - self.window_width) // 2

        self.hwnd: Optional[int] = None
        self.hit_tester = HitTester(self.window_width, self.window_height)
        self.fullscreen_detector = FullscreenDetector()
        self.renderer: Optional[PresenceRenderer] = None

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._render_thread: Optional[threading.Thread] = None
        self._wake_event = threading.Event()

        # Telemetry metrics
        self.metrics = {
            "fps": 0.0,
            "frame_time_ms": 0.0,
            "render_cpu_percent": 0.0,
        }

        self._init_screen_metrics()

    def set_onboarding_controller(self, controller):
        """Sets the onboarding controller for step handling and rendering."""
        self.onboarding_controller = controller
        if self.renderer:
            self.renderer.set_onboarding_controller(controller)

    def _init_screen_metrics(self):
        """Sets Per-Monitor DPI awareness and queries primary monitor dimensions."""
        if sys.platform == "win32" and user32:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per-monitor DPI v2
            except Exception:
                try:
                    user32.SetProcessDPIAware()
                except Exception:
                    pass
            self.screen_width = user32.GetSystemMetrics(0)
            self.screen_height = user32.GetSystemMetrics(1)
        self.window_left = (self.screen_width - self.window_width) // 2
        self.hit_tester.set_screen_size(self.screen_width, self.screen_height, self.window_width, self.window_height)
        self.renderer = PresenceRenderer(canvas_width=self.window_width, canvas_height=self.window_height)
        if self.onboarding_controller:
            self.renderer.set_onboarding_controller(self.onboarding_controller)

    def get_window_styles(self) -> Dict[str, int]:
        """Returns the current Win32 style and ex_style of the window."""
        if not self.hwnd or not win32gui:
            return {"style": 0, "ex_style": 0}
        try:
            return {
                "style": win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE),
                "ex_style": win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE),
            }
        except Exception:
            return {"style": 0, "ex_style": 0}

    def start(self):

        """Spawns native window and render loop threads."""
        if self._running or sys.platform != "win32":
            return
        self._running = True
        self._thread = threading.Thread(target=self._window_message_loop, daemon=True, name="UltronWindowThread")
        self._thread.start()

        # Wait up to 1.5s for window HWND creation
        t0 = time.time()
        while not self.hwnd and (time.time() - t0 < 1.5):
            time.sleep(0.02)

        self._render_thread = threading.Thread(target=self._render_loop, daemon=True, name="UltronRenderThread")
        self._render_thread.start()
        logger.info(f"[Presence Window] Initialized native overlay HWND: {self.hwnd} on {self.screen_width}x{self.screen_height}")

    def wake(self):
        """Signals render loop to wake immediately from idle sleep."""
        self._wake_event.set()

    def _window_proc(self, hwnd: int, msg: int, wparam: int, lparam: int):
        """Win32 window message handler."""
        if msg == win32con.WM_NCHITTEST:
            # Extract screen cursor coordinates
            x = win32api.LOWORD(lparam)
            y = win32api.HIWORD(lparam)
            if x > 32767: x -= 65536
            if y > 32767: y -= 65536

            nw = self.choreographer.size.x + self.choreographer.hover_lift.current
            nh = self.choreographer.size.y
            state = self.choreographer.current_state_name
            onb_step = self.onboarding_controller.current_step if self.onboarding_controller else 1

            ht, target = self.hit_tester.test_point(x, y, nw, nh, state, onboarding_step=onb_step)
            if ht == HTCLIENT:
                # Calculate gaze parallax offset (normalized -4.0 to +4.0 px)
                cx = self.screen_width // 2
                offset_x = (x - cx) / (nw * 0.5 + 1e-5) * 4.0
                self.choreographer.set_gaze(offset_x, 0.0)
                self.choreographer.set_hover(True)
                self.wake()
                return win32con.HTCLIENT
            else:
                self.choreographer.set_hover(False)
                self.choreographer.set_gaze(0.0, 0.0)
                return win32con.HTTRANSPARENT

        elif msg == win32con.WM_LBUTTONDOWN:
            if user32:
                try:
                    user32.SetFocus(hwnd)
                except Exception:
                    pass

            x = win32api.LOWORD(lparam)
            y = win32api.HIWORD(lparam)
            nw = self.choreographer.size.x + self.choreographer.hover_lift.current
            nh = self.choreographer.size.y
            state = self.choreographer.current_state_name
            onb_step = self.onboarding_controller.current_step if self.onboarding_controller else 1
            ht, target = self.hit_tester.test_point(x, y, nw, nh, state, onboarding_step=onb_step)

            if state == "ONBOARDING" and self.onboarding_controller:
                ctrl = self.onboarding_controller
                if target.target_type == "ONBOARDING_FIELD_OWNER":
                    ctrl.set_active_field("owner_name")
                elif target.target_type == "ONBOARDING_FIELD_HINT":
                    ctrl.set_active_field("pronunciation_hint")
                elif target.target_type == "ONBOARDING_OPT_ADDR_PREF":
                    ctrl.addressing_mode = "preferred"
                    ctrl.active_field = ""
                    ctrl.wake()
                elif target.target_type == "ONBOARDING_OPT_ADDR_CUSTOM":
                    ctrl.addressing_mode = "custom"
                    ctrl.set_active_field("custom_address")
                elif target.target_type == "ONBOARDING_FIELD_ADDRESS":
                    ctrl.set_active_field("custom_address")
                elif target.target_type == "ONBOARDING_OPT_ID_ULTRON":
                    ctrl.identity_mode = "ultron"
                    ctrl.active_field = ""
                    ctrl.wake()
                elif target.target_type == "ONBOARDING_OPT_ID_CUSTOM":
                    ctrl.identity_mode = "custom"
                    ctrl.set_active_field("custom_assistant_name")
                elif target.target_type == "ONBOARDING_FIELD_ASSISTANT":
                    ctrl.set_active_field("custom_assistant_name")
                elif target.target_type == "ONBOARDING_VOICE" and target.data:
                    ctrl.voice_name = target.data
                    ctrl.wake()
                elif target.target_type == "ONBOARDING_STYLE" and target.data:
                    ctrl.response_style = target.data
                    ctrl.wake()
                elif target.target_type == "ONBOARDING_TOGGLE_MEMORY":
                    ctrl.allow_memory = not ctrl.allow_memory
                    ctrl.wake()
                elif target.target_type == "ONBOARDING_TOGGLE_STARTUP":
                    ctrl.start_with_windows = not ctrl.start_with_windows
                    ctrl.wake()
            return 0

        elif msg == win32con.WM_LBUTTONUP:
            x = win32api.LOWORD(lparam)
            y = win32api.HIWORD(lparam)
            nw = self.choreographer.size.x + self.choreographer.hover_lift.current
            nh = self.choreographer.size.y
            state = self.choreographer.current_state_name
            onb_step = self.onboarding_controller.current_step if self.onboarding_controller else 1
            ht, target = self.hit_tester.test_point(x, y, nw, nh, state, onboarding_step=onb_step)

            if state == "ONBOARDING" and self.onboarding_controller:
                if target.target_type == "ONBOARDING_NEXT":
                    self.onboarding_controller.go_next()
                    self.wake()
                elif target.target_type == "ONBOARDING_BACK":
                    self.onboarding_controller.go_back()
                    self.wake()
            elif target.target_type == "ALLOW_BUTTON":
                logger.info("[Presence Window] Clicked 'Allow' button")
                if self.on_allow_click:
                    self.on_allow_click()
            elif target.target_type == "DISMISS_BUTTON":
                logger.info("[Presence Window] Clicked 'Dismiss' button")
                if self.on_dismiss_click:
                    self.on_dismiss_click()
            elif target.target_type == "NOTCH":
                logger.info("[Presence Window] Clicked Notch body")
                if self.on_notch_click:
                    self.on_notch_click()
            return 0

        elif msg == win32con.WM_KEYDOWN:
            state = self.choreographer.current_state_name
            if state == "ONBOARDING" and self.onboarding_controller:
                ctrl = self.onboarding_controller
                if wparam == 0x0D:  # VK_RETURN (Enter)
                    ctrl.go_next()
                elif wparam == 0x1B:  # VK_ESCAPE (Esc)
                    ctrl.go_back()
                elif wparam == 0x08:  # VK_BACK (Backspace)
                    ctrl.handle_backspace()
                elif wparam == 0x25:  # VK_LEFT
                    ctrl.handle_key_left()
                elif wparam == 0x27:  # VK_RIGHT
                    ctrl.handle_key_right()
                elif wparam == 0x09:  # VK_TAB
                    shift = bool(win32api.GetAsyncKeyState(0x10) & 0x8000) if win32api else False
                    ctrl.handle_tab(shift=shift)
                elif wparam == 0x20:  # VK_SPACE
                    if ctrl.current_step == 5:
                        ctrl.allow_memory = not ctrl.allow_memory
                        ctrl.wake()
                    elif ctrl.current_step == 6:
                        ctrl.start_with_windows = not ctrl.start_with_windows
                        ctrl.wake()
                elif wparam == ord('V') or wparam == ord('v'):
                    if win32api and (win32api.GetAsyncKeyState(0x11) & 0x8000):  # Ctrl+V
                        try:
                            import tkinter as tk
                            root = tk.Tk()
                            root.withdraw()
                            clip = root.clipboard_get()
                            root.destroy()
                            ctrl.handle_paste(clip)
                        except Exception:
                            pass
                self.wake()
                return 0
            elif state == "CONFIRMATION":
                if wparam == 0x0D:  # Enter -> Allow
                    if self.on_allow_click:
                        self.on_allow_click()
                elif wparam == 0x1B:  # Esc -> Dismiss
                    if self.on_dismiss_click:
                        self.on_dismiss_click()
                return 0

        elif msg == win32con.WM_CHAR:
            state = self.choreographer.current_state_name
            if state == "ONBOARDING" and self.onboarding_controller:
                if wparam >= 32:
                    self.onboarding_controller.handle_char(chr(wparam))
                    self.wake()
                return 0

        elif msg == win32con.WM_DESTROY:
            self._running = False
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _window_message_loop(self):
        """Registers and creates the layered window, pumps Win32 messages."""
        wndclass = win32gui.WNDCLASS()
        wndclass.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        wndclass.lpfnWndProc = self._window_proc
        wndclass.hInstance = win32gui.GetModuleHandle(None)
        wndclass.lpszClassName = "UltronCinematicPresence"
        wndclass.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)

        try:
            atom = win32gui.RegisterClass(wndclass)
        except Exception:
            atom = None

        # Window Styles: Borderless, Topmost, Layered, Toolwindow (no taskbar button)
        ex_style = (
            win32con.WS_EX_LAYERED
            | win32con.WS_EX_TOPMOST
            | win32con.WS_EX_TOOLWINDOW
            | win32con.WS_EX_NOACTIVATE
        )
        style = win32con.WS_POPUP | win32con.WS_VISIBLE

        self.hwnd = win32gui.CreateWindowEx(
            ex_style,
            "UltronCinematicPresence",
            "ULTRON Presence",
            style,
            self.window_left,
            0,
            self.window_width,
            self.window_height,
            0,
            0,
            wndclass.hInstance,
            None,
        )

        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNOACTIVATE)
        win32gui.UpdateWindow(self.hwnd)

        # Message pump
        while self._running:
            try:
                win32gui.PumpWaitingMessages()
                time.sleep(0.02)
            except Exception:
                break

    def _render_loop(self):
        """Adaptive 60 FPS frame-paced render loop with idle sleep gating."""
        last_frame_time = time.perf_counter()
        target_frame_dt = 1.0 / 60.0 # 60 FPS cap
        fps_counter = 0
        fps_start = time.perf_counter()

        while self._running:
            t0 = time.perf_counter()
            dt = t0 - last_frame_time
            last_frame_time = t0

            # 1. Check Fullscreen Retraction
            is_fs = self.fullscreen_detector.is_fullscreen_active(self.screen_width, self.screen_height)
            if is_fs:
                if self.choreographer.current_state_name != "RETRACTED":
                    self.choreographer.set_state("RETRACTED")
            else:
                if self.choreographer.current_state_name == "RETRACTED":
                    self.choreographer.set_state("IDLE")

            # 2. Advance Choreographer Physics & Audio Smoother
            amp = self.audio_viz.update(dt)
            self.choreographer.update(dt, amp)

            # 3. Render and Blit Frame via UpdateLayeredWindow
            if self.hwnd and self.renderer:
                try:
                    img = self.renderer.render_frame(self.choreographer, self.audio_viz, dt)
                    self._update_layered_window(img)
                except Exception as e:
                    logger.debug(f"[Render Loop] Blit exception: {e}")

            # 4. Measure Frame Telemetry
            t_elapsed = time.perf_counter() - t0
            self.metrics["frame_time_ms"] = round(t_elapsed * 1000.0, 2)
            fps_counter += 1
            if time.perf_counter() - fps_start >= 1.0:
                self.metrics["fps"] = fps_counter / (time.perf_counter() - fps_start)
                fps_counter = 0
                fps_start = time.perf_counter()

            # 5. Adaptive Sleep Gating (Idle Sleep Policy)
            if self.choreographer.is_all_settled() and self.choreographer.current_state_name == "IDLE" and not self.audio_viz.is_active:
                # Sleep up to 50ms between ticks for slow respiration (~20 Hz wake), waking immediately on event
                self._wake_event.wait(timeout=0.05)
                self._wake_event.clear()
            else:
                # Active 60 FPS pacing
                sleep_rem = target_frame_dt - t_elapsed
                if sleep_rem > 0.0005:
                    time.sleep(sleep_rem)

    def _update_layered_window(self, img):
        """Passes 32-bit Premultiplied BGRA image to Windows UpdateLayeredWindow."""
        bgra_bytes = self.renderer.to_premultiplied_bgra(img)
        if not bgra_bytes:
            return

        w, h = img.size
        hdc_screen = user32.GetDC(0)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h  # Top-down DIB
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = BI_RGB

        bits_ptr = ctypes.c_void_p()
        hbmp = gdi32.CreateDIBSection(
            hdc_screen,
            ctypes.byref(bmi),
            0,
            ctypes.byref(bits_ptr),
            0,
            0,
        )

        ctypes.memmove(bits_ptr, bgra_bytes, len(bgra_bytes))
        old_bmp = gdi32.SelectObject(hdc_mem, hbmp)

        pt_src = wintypes.POINT(0, 0)
        pt_dst = wintypes.POINT(self.window_left, 0)
        sz = wintypes.SIZE(w, h)

        blend = BLENDFUNCTION(
            BlendOp=AC_SRC_OVER,
            BlendFlags=0,
            SourceConstantAlpha=255,
            AlphaFormat=AC_SRC_ALPHA,
        )

        user32.UpdateLayeredWindow(
            self.hwnd,
            hdc_screen,
            ctypes.byref(pt_dst),
            ctypes.byref(sz),
            hdc_mem,
            ctypes.byref(pt_src),
            0,
            ctypes.byref(blend),
            2,  # ULW_ALPHA
        )

        # Cleanup GDI handles
        gdi32.SelectObject(hdc_mem, old_bmp)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)

    def stop(self):
        """Closes window and terminates rendering thread."""
        self._running = False
        self.wake()
        if self.hwnd and win32gui:
            try:
                win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception:
                pass
        if self._render_thread:
            self._render_thread.join(timeout=1.0)
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("[Presence Window] Stopped.")
