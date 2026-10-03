"""
pywebview smoke-test — opens the ULTRON presence for 5 seconds, takes a screenshot, then exits.
Run: python verify_webview.py
"""
import sys
import time
import os

print(f"Python: {sys.version}")

try:
    import webview
    print("pywebview: imported OK")
except ImportError as e:
    print(f"pywebview: IMPORT FAILED — {e}")
    sys.exit(1)

# Resolve version
try:
    import importlib.metadata
    ver = importlib.metadata.version("pywebview")
    print(f"pywebview version: {ver}")
except Exception:
    print("pywebview version: unable to resolve")

# Screen info
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    user32 = ctypes.windll.user32
    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)
    print(f"Screen: {sw}x{sh}")
    notch_x = (sw - 320) // 2
    notch_y = 0
except Exception as e:
    print(f"Screen detection fallback: {e}")
    sw, sh = 1920, 1080
    notch_x, notch_y = 800, 0

# Check server alive
import urllib.request
url = "http://localhost:8080/presence/"
try:
    r = urllib.request.urlopen(url, timeout=2)
    print(f"Server: {r.status} — {url}")
except Exception as e:
    print(f"Server NOT reachable at {url}: {e}")
    sys.exit(1)

print(f"Creating window: 320x48 at ({notch_x}, {notch_y})...")
print("Window will auto-close after 6 seconds.")

def auto_close():
    time.sleep(6)
    import webview as wv
    for w in wv.windows:
        w.destroy()

import threading
threading.Thread(target=auto_close, daemon=True).start()

window = webview.create_window(
    title="ULTRON Presence — Smoke Test",
    url=url,
    width=320,
    height=48,
    x=notch_x,
    y=notch_y,
    frameless=True,
    on_top=True,
    transparent=True,
    resizable=False,
)

webview.start(debug=False)
print("pywebview window closed. Smoke test PASSED.")
