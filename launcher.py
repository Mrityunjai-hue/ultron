"""
ULTRON v2.0 — Native Desktop Notch Launcher & Presence Supervisor
─────────────────────────────────────────────────────────────────────────────
Top-Center Desktop Notch Window:
- Frameless, floating on top, transparent-ready
- Primary monitor top-center: y=0, x=(screen_w - width) // 2
- Dynamic sizing: Standby (320x36 px) <-> Active/Expanded (640x420 px)
- DPI-aware (Per-Monitor DPI v2 via Windows API)
- Healthcheck watchdog with auto-boot for server.py
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import os
import sys
import time
import shutil
import argparse
import subprocess
import urllib.request
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ultron.launcher")

STANDBY_WIDTH = 320
STANDBY_HEIGHT = 48
EXPANDED_WIDTH = 640
EXPANDED_HEIGHT = 420

def set_windows_dpi_awareness():
    """Configures high-DPI awareness on Windows to prevent blurry rendering."""
    if sys.platform == "win32":
        try:
            import ctypes
            # PROCESS_PER_MONITOR_DPI_AWARE = 2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            logger.info("Windows Per-Monitor DPI awareness configured (level 2).")
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                logger.info("Windows system DPI awareness configured.")
            except Exception as e:
                logger.debug(f"DPI awareness note: {e}")

def get_screen_dimensions():
    """Returns primary monitor (width, height) in pixels."""
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except Exception:
            pass
    return 1920, 1080

def is_server_running(port: int = 8080) -> bool:
    """Checks whether the ULTRON bridge server is active and responding."""
    url = f"http://localhost:{port}/api/voice/status"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "UltronLauncher"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False

def ensure_server_running(port: int = 8080, with_orchestrator: bool = True):
    """Spawns server.py in background if not already active."""
    if is_server_running(port):
        logger.info(f"ULTRON Bridge Server is already active on port {port}.")
        return None

    root_dir = Path(__file__).resolve().parent
    server_py = root_dir / "server.py"

    cmd = [sys.executable, str(server_py), "--port", str(port)]
    if with_orchestrator:
        cmd.append("--with-orchestrator")

    logger.info(f"Starting server in background: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=str(root_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait up to 6 seconds for server readiness
    start_wait = time.time()
    while time.time() - start_wait < 6.0:
        if is_server_running(port):
            logger.info(f"ULTRON Bridge Server verified ready on port {port}.")
            return proc
        time.sleep(0.3)

    logger.warning("Bridge server did not confirm healthcheck within 6s; proceeding anyway.")
    return proc

_active_window = None

class NotchApi:
    """JS-to-Python Bridge API exposed to the webview."""

    def expand(self):
        """Expands notch window to active size."""
        global _active_window
        if _active_window:
            try:
                screen_w, _ = get_screen_dimensions()
                new_x = (screen_w - EXPANDED_WIDTH) // 2
                _active_window.resize(EXPANDED_WIDTH, EXPANDED_HEIGHT)
                _active_window.move(new_x, 0)
                logger.info("Notch window expanded to 640x420.")
            except Exception as e:
                logger.error(f"Error expanding notch window: {e}")

    def collapse(self):
        """Collapses notch window to compact standby size."""
        global _active_window
        if _active_window:
            try:
                screen_w, _ = get_screen_dimensions()
                new_x = (screen_w - STANDBY_WIDTH) // 2
                _active_window.resize(STANDBY_WIDTH, STANDBY_HEIGHT)
                _active_window.move(new_x, 0)
                logger.info("Notch window collapsed to standby.")
            except Exception as e:
                logger.error(f"Error collapsing notch window: {e}")

def launch_pywebview(target_url: str, is_lab: bool = False):
    """Launches native floating notch window via pywebview."""
    global _active_window
    import webview

    set_windows_dpi_awareness()
    try:
        if webview.screens and len(webview.screens) > 0:
            screen_w = webview.screens[0].width
            screen_h = webview.screens[0].height
        else:
            screen_w, screen_h = get_screen_dimensions()
    except Exception:
        screen_w, screen_h = get_screen_dimensions()

    if is_lab:
        lab_w = 1140
        lab_h = 720
        lab_x = max(0, (screen_w - lab_w) // 2)
        lab_y = max(0, (screen_h - lab_h) // 2)
        window = webview.create_window(
            title="ULTRON v2.0 — Animation Lab & Character Gallery",
            url=target_url,
            width=lab_w,
            height=lab_h,
            x=lab_x,
            y=lab_y,
            resizable=True,
            on_top=False,
        )
        _active_window = window
        logger.info(f"Opening Animation Lab window at ({lab_x}, {lab_y}) [{lab_w}x{lab_h}]")
    else:
        notch_x = (screen_w - STANDBY_WIDTH) // 2
        notch_y = 0

        api = NotchApi()
        window = webview.create_window(
            title="ULTRON Presence",
            url=target_url,
            width=STANDBY_WIDTH,
            height=STANDBY_HEIGHT,
            x=notch_x,
            y=notch_y,
            frameless=True,
            on_top=True,
            transparent=True,
            resizable=False,
            js_api=api,
        )
        _active_window = window
        logger.info(f"Opening PyWebview top-center notch window at ({notch_x}, {notch_y}) [Size: {STANDBY_WIDTH}x{STANDBY_HEIGHT}]")

    webview.start(debug=False)

def launch_browser_app_mode(target_url: str):
    """Fallback: Launches dedicated frameless application window using Edge or Chrome."""
    screen_w, _ = get_screen_dimensions()
    notch_x = (screen_w - STANDBY_WIDTH) // 2

    # Check for Edge or Chrome
    edge_exe = shutil.which("msedge") or shutil.which("msedge.exe") or r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    chrome_exe = shutil.which("chrome") or shutil.which("chrome.exe") or r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    target_exe = None
    if os.path.exists(str(edge_exe)):
        target_exe = str(edge_exe)
    elif os.path.exists(str(chrome_exe)):
        target_exe = str(chrome_exe)

    if target_exe:
        app_flags = [
            target_exe,
            f"--app={target_url}",
            f"--window-size={STANDBY_WIDTH},{STANDBY_HEIGHT + 30}",
            f"--window-position={notch_x},0",
            "--disable-extensions",
            "--disable-features=Translate",
        ]
        logger.info(f"Launching desktop application mode notch: {target_exe}")
        subprocess.Popen(app_flags)
    else:
        import webbrowser
        logger.info(f"Opening system web browser to {target_url}")
        webbrowser.open(target_url)

def main():
    parser = argparse.ArgumentParser(description="ULTRON v2.0 Desktop Notch Launcher")
    parser.add_argument("--port", type=int, default=8080, help="Bridge server port")
    parser.add_argument("--lab", action="store_true", help="Launch Developer Animation Lab instead of notch")
    parser.add_argument("--server-only", action="store_true", help="Only start bridge server")
    parser.add_argument("--notch-only", action="store_true", help="Only launch UI window without starting server")
    parser.add_argument("--diagnostics", action="store_true", help="Run comprehensive live system diagnostics")
    parser.add_argument("--brain-test", action="store_true", help="Run local AI Brain diagnostic & verification test")
    args = parser.parse_args()

    if args.diagnostics:
        from laptop.diagnostics import run_all_diagnostics
        run_all_diagnostics()
        sys.exit(0)

    if args.brain_test:
        from laptop.brain_test import run_brain_test
        run_brain_test()
        sys.exit(0)

    if not args.notch_only:
        ensure_server_running(port=args.port, with_orchestrator=True)

    if args.server_only:
        logger.info("Server-only mode active. Running continuously.")
        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            sys.exit(0)

    # Determine URL
    target_path = "/lab/" if args.lab else "/presence/"
    target_url = f"http://localhost:{args.port}{target_path}"

    try:
        import webview
        launch_pywebview(target_url, is_lab=args.lab)
    except ImportError:
        logger.info("pywebview not detected. Attempting automatic installation...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview"])
            import webview
            launch_pywebview(target_url, is_lab=args.lab)
        except Exception as e:
            logger.error(f"Failed to auto-install pywebview: {e}")
            logger.info("Utilizing application mode launcher fallback.")
            launch_browser_app_mode(target_url)

if __name__ == "__main__":
    main()
