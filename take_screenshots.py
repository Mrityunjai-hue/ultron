"""
ULTRON v2.0 — PrintWindow-based screenshot capture.
Uses WinAPI PrintWindow with PW_RENDERFULLCONTENT to capture WebView2/DXGI windows.
All 8 states are driven via the backend AUTHORITATIVE_EVENT WebSocket.
"""
import sys
import ctypes
import ctypes.wintypes
import json
import time
import threading
import urllib.request
from pathlib import Path

OUT = Path("screenshots")
OUT.mkdir(exist_ok=True)

BASE = "http://localhost:8080"

# DPI awareness first
ctypes.windll.shcore.SetProcessDpiAwareness(2)

# Windows API bindings
user32   = ctypes.windll.user32
gdi32    = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
PW_RENDERFULLCONTENT = 0x00000002  # Capture layered/hardware-accelerated windows

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize",          ctypes.wintypes.DWORD),
        ("biWidth",         ctypes.wintypes.LONG),
        ("biHeight",        ctypes.wintypes.LONG),
        ("biPlanes",        ctypes.wintypes.WORD),
        ("biBitCount",      ctypes.wintypes.WORD),
        ("biCompression",   ctypes.wintypes.DWORD),
        ("biSizeImage",     ctypes.wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.wintypes.LONG),
        ("biYPelsPerMeter", ctypes.wintypes.LONG),
        ("biClrUsed",       ctypes.wintypes.DWORD),
        ("biClrImportant",  ctypes.wintypes.DWORD),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", ctypes.wintypes.DWORD * 3),
    ]

def hwnd_screenshot_png(hwnd, out_path: str) -> bool:
    """Capture a window using PrintWindow and save to PNG."""
    # Get window rect
    r = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w = r.right  - r.left
    h = r.bottom - r.top
    if w <= 0 or h <= 0:
        print(f"    Bad window size: {w}x{h}")
        return False

    # Create DC and compatible bitmap
    hwnd_dc  = user32.GetWindowDC(hwnd)
    mem_dc   = gdi32.CreateCompatibleDC(hwnd_dc)
    hbitmap  = gdi32.CreateCompatibleBitmap(hwnd_dc, w, h)
    old_bmp  = gdi32.SelectObject(mem_dc, hbitmap)

    # PrintWindow with PW_RENDERFULLCONTENT captures hardware-accelerated surfaces
    result = user32.PrintWindow(hwnd, mem_dc, PW_RENDERFULLCONTENT)
    
    if result:
        # Copy pixels out via GetDIBits
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize        = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth       = w
        bmi.bmiHeader.biHeight      = -h  # top-down
        bmi.bmiHeader.biPlanes      = 1
        bmi.bmiHeader.biBitCount    = 32
        bmi.bmiHeader.biCompression = 0   # BI_RGB

        buf_size = w * h * 4
        buf      = (ctypes.c_byte * buf_size)()
        ret = gdi32.GetDIBits(mem_dc, hbitmap, 0, h,
                              ctypes.byref(buf),
                              ctypes.byref(bmi), DIB_RGB_COLORS)
        if ret:
            # Write PNG using Pillow (BGRA → RGBA)
            try:
                from PIL import Image
                import numpy as np
                arr = np.frombuffer(buf, dtype=np.uint8).reshape((h, w, 4))
                # Windows BGRA → RGB
                rgb = arr[:, :, :3][:, :, ::-1]
                img = Image.fromarray(rgb, 'RGB')
                img.save(out_path)
            except ImportError:
                # Fallback: write raw BMP header + pixels
                _save_bmp(w, h, bytes(buf), out_path.replace('.png', '.bmp'))
                return True
    
    # Cleanup
    gdi32.SelectObject(mem_dc, old_bmp)
    gdi32.DeleteObject(hbitmap)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd, hwnd_dc)
    return bool(result)

def find_ultron_window():
    """Find the pywebview/ULTRON window by iterating top-level windows."""
    found = []
    def cb(hwnd, lp):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        title = buf.value
        if "ULTRON" in title or "State Capture" in title:
            found.append(hwnd)
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return found[0] if found else None

def post_event(activity, operation="none", mood="CALM"):
    payload = json.dumps({
        "activity_name": activity,
        "activity": activity,
        "mood": mood,
        "operation": operation,
        "attention": 0.9,
    }).encode()
    req = urllib.request.Request(
        f"{BASE}/api/bridge/event",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status
    except Exception as e:
        return f"ERR:{e}"

# Check deps
try:
    import numpy as np
    from PIL import Image
    print("PIL+numpy: OK")
except ImportError:
    print("Installing PIL+numpy...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "numpy", "-q"])
    import numpy as np
    from PIL import Image
    print("PIL+numpy: installed OK")

# Verify server
try:
    with urllib.request.urlopen(f"{BASE}/api/voice/status", timeout=2) as r:
        print(f"Server: {r.status}")
except Exception as e:
    print(f"Server NOT reachable: {e}"); sys.exit(1)

STATES = [
    ("IDLE",         "none",         "CALM"),
    ("LISTENING",    "none",         "CALM"),
    ("THINKING",     "none",         "CALM"),
    ("EXECUTING",    "search_files", "FOCUSED"),
    ("RESPONDING",   "none",         "CALM"),
    ("ERROR",        "none",         "WARNING"),
    ("OFFLINE",      "none",         "CALM"),
    ("RECONNECTING", "none",         "CALM"),
]
FILE_NAMES = ["01_idle","02_listening","03_thinking","04_executing",
              "05_responding","06_error","07_offline","08_reconnecting"]

import webview

user32_sys = ctypes.windll.user32
sw = user32_sys.GetSystemMetrics(0)
sh = user32_sys.GetSystemMetrics(1)
win_w, win_h = 640, 420
win_x = max(0, (sw - win_w) // 2)
win_y = max(0, (sh - win_h) // 2)

results = []

def capture_thread(window):
    time.sleep(3.0)  # Full page load

    hwnd = None
    for _ in range(10):
        hwnd = find_ultron_window()
        if hwnd: break
        time.sleep(0.5)
    
    if not hwnd:
        print("ERROR: Could not find ULTRON window handle!")
        window.destroy()
        return
    print(f"Found ULTRON window HWND: {hwnd}")

    for i, (act, op, mood) in enumerate(STATES):
        fname = FILE_NAMES[i]
        # Drive state via backend event AND JS evaluate
        post_event(act, op, mood)
        window.evaluate_js(f"""
            if(window.ultron) window.ultron.setState({{
                activity:'{act}', operation:'{op}', mood:'{mood}'
            }});
        """)
        time.sleep(1.5)

        out_path = str(OUT / f"{fname}.png")
        ok = hwnd_screenshot_png(hwnd, out_path)
        exists = Path(out_path).exists()
        size = Path(out_path).stat().st_size if exists else 0
        status = "OK" if (ok and exists and size > 100) else "FAIL"
        print(f"  {fname}.png: PrintWindow={ok}  exists={exists}  size={size}b  [{status}]")
        results.append((fname, act, status, size))

    # Production presence
    window.load_url(f"{BASE}/presence/")
    time.sleep(2.5)
    post_event("IDLE", "none", "CALM")
    time.sleep(1.0)
    out_path = str(OUT / "09_production_presence.png")
    ok = hwnd_screenshot_png(hwnd, out_path)
    exists = Path(out_path).exists()
    size   = Path(out_path).stat().st_size if exists else 0
    status = "OK" if (ok and exists and size > 100) else "FAIL"
    print(f"  09_production_presence.png: PrintWindow={ok}  exists={exists}  size={size}b  [{status}]")
    results.append(("09_production_presence", "IDLE", status, size))

    time.sleep(1)
    window.destroy()

win = webview.create_window(
    title="ULTRON State Capture",
    url=f"{BASE}/lab/",
    width=win_w,
    height=win_h,
    x=win_x,
    y=win_y,
    resizable=False,
    on_top=True,
)
t = threading.Thread(target=capture_thread, args=(win,), daemon=True)
t.start()
webview.start(debug=False)

print("\n=== SCREENSHOT SUMMARY ===")
for fname, act, status, size in results:
    print(f"  {fname}.png: [{status}] activity={act}  size={size}b")
print(f"\nSaved to: {OUT.resolve()}")
