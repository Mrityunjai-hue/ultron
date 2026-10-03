"""
ULTRON V3 — Presence Redesign Visual Capture & 3x3 Master Contact Sheet
─────────────────────────────────────────────────────────────────────────────
Generates high-resolution PNG renders for all 9 authoritative states
of the ULTRON desktop presence matching the reference art direction:
01 IDLE (Default)
02 HOVER
03 LISTENING
04 THINKING
05 SPEAKING
06 TOOL EXECUTION
07 TOOL COMPLETE
08 CONFIRMATION
09 FULLSCREEN (Retracted)
─────────────────────────────────────────────────────────────────────────────
"""
import math
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from ultron.presence.animation import SpringChoreographer
from ultron.presence.audio_visualizer import AudioVisualizer
from ultron.presence.renderer import PresenceRenderer

_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = _ROOT / "docs" / "assets" / "screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def composite_on_desktop_backdrop(presence_img: Image.Image) -> Image.Image:
    """Composites the presence layer over a dark atmospheric wallpaper."""
    w, h = 1000, 420
    bg = Image.new("RGBA", (w, h), (10, 12, 16, 255))
    draw = ImageDraw.Draw(bg)

    # Gradient mountain / dark tech atmosphere
    for y in range(h):
        r = int(12 + (y / h) * 16)
        g = int(14 + (y / h) * 18)
        b = int(22 + (y / h) * 26)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

    # Mountain silhouette curves in background
    mountain_pts_1 = [(0, h)]
    for x in range(0, w + 20, 20):
        my = h - 140 - int(45.0 * math.sin(x * 0.008) + 25.0 * math.cos(x * 0.015))
        mountain_pts_1.append((x, my))
    mountain_pts_1.append((w, h))
    draw.polygon(mountain_pts_1, fill=(16, 18, 26, 255))

    mountain_pts_2 = [(0, h)]
    for x in range(0, w + 20, 20):
        my = h - 80 - int(30.0 * math.sin((x + 100) * 0.009))
        mountain_pts_2.append((x, my))
    mountain_pts_2.append((w, h))
    draw.polygon(mountain_pts_2, fill=(8, 10, 15, 255))

    # Windows Taskbar at bottom
    draw.rectangle([0, h - 36, w, h], fill=(12, 14, 18, 240))
    for icon_idx in range(6):
        ix = w // 2 - 90 + icon_idx * 30
        draw.rounded_rectangle([ix, h - 28, ix + 20, h - 8], radius=4, fill=(40, 45, 60, 200))

    # Composite presence layer centered at top
    dest_x = (w - presence_img.width) // 2
    bg.alpha_composite(presence_img, dest=(dest_x, 0))
    return bg

def run_capture():
    ch = SpringChoreographer()
    viz = AudioVisualizer()
    renderer = PresenceRenderer(canvas_width=600, canvas_height=220)

    states_to_capture = [
        ("01_idle", "IDLE", 0.0, 0.0, False, "01  IDLE (Default)", "Calm, minimal presence"),
        ("02_hover", "HOVER", 0.0, 2.5, True, "02  HOVER", "Subtle response to cursor"),
        ("03_listening", "LISTENING", 0.18, 0.0, False, "03  LISTENING", "Responsive acoustic state"),
        ("04_thinking", "THINKING", 0.0, 0.0, False, "04  THINKING", "Focused, intelligent motion"),
        ("05_speaking", "RESPONDING", 0.22, 0.0, False, "05  SPEAKING", "Voice-driven fluid motion"),
        ("06_tool_execution", "TOOL_EXEC", 0.0, 0.0, False, "06  TOOL EXECUTION", "Spacious, clean action surface"),
        ("07_tool_complete", "TOOL_COMPLETE", 0.0, 0.0, False, "07  TOOL COMPLETE", "Clear success state"),
        ("08_confirmation", "CONFIRMATION", 0.0, 0.0, False, "08  CONFIRMATION", "Premium security dialog"),
        ("09_fullscreen_retracted", "RETRACTED", 0.0, 0.0, False, "09  FULLSCREEN (Retracted)", "Minimal presence while fullscreen"),
    ]

    print("Generating ULTRON Signature Presence Visual Captures...")
    rendered_panels = []

    for fname, state, audio_amp, gaze_x, hover, title, subtitle in states_to_capture:
        ch.set_state(state)
        ch.set_gaze(gaze_x, 0.0)
        ch.set_hover(hover)

        if state == "TOOL_EXEC":
            renderer.set_tool_context(tool_name="APP:OPEN", target="Google Chrome", status="running", progress=0.5)
        elif state == "TOOL_COMPLETE":
            renderer.set_tool_context(tool_name="APP:OPEN", target="Google Chrome", status="complete", progress=1.0)
        elif state == "CONFIRMATION":
            renderer.set_vault_context(action="DELETE_FILE", target="build/artifacts/cache.db", message="Permanent deletion requires authorization.")

        if audio_amp > 0.0:
            viz.push_input_chunk(audio_amp)
        else:
            viz.reset()

        # Settle physics into target state
        for _ in range(50):
            amp = viz.update(0.016)
            ch.update(0.016, amp)

        img = renderer.render_frame(ch, viz, 0.016)

        # 1. Save transparent cropped PNG
        img.save(str(OUTPUT_DIR / f"{fname}_transparent.png"))
        shutil.copy(str(OUTPUT_DIR / f"{fname}_transparent.png"), str(BRAIN_DIR / f"{fname}_transparent.png"))

        # 2. Save full desktop context composite
        comp = composite_on_desktop_backdrop(img)
        comp.save(str(OUTPUT_DIR / f"{fname}_desktop.png"))
        # 3. Add caption block for contact sheet
        card = Image.new("RGBA", (1000, 500), (8, 10, 14, 255))
        card.paste(comp, (0, 0))
        cdraw = ImageDraw.Draw(card)
        cdraw.text((40, 435), title, fill=(240, 240, 245, 240), font=ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 20))
        cdraw.text((40, 465), subtitle, fill=(140, 150, 170, 200), font=ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 15))
        rendered_panels.append(card)

        print(f"  [OK] Captured: {fname}")

    # Build 3x3 Master Contact Sheet
    grid_w = 3000
    grid_h = 1500
    sheet = Image.new("RGBA", (grid_w, grid_h), (5, 6, 8, 255))
    sdraw = ImageDraw.Draw(sheet)

    for idx, panel in enumerate(rendered_panels):
        row = idx // 3
        col = idx % 3
        sheet.paste(panel, (col * 1000, row * 500))

    # Grid dividing hairlines
    for c in range(1, 3):
        sdraw.line([(c * 1000, 0), (c * 1000, grid_h)], fill=(40, 45, 60, 200), width=1)
    for r in range(1, 3):
        sdraw.line([(0, r * 500), (grid_w, r * 500)], fill=(40, 45, 60, 200), width=1)

    sheet_path = OUTPUT_DIR / "00_master_presence_contact_sheet.png"
    sheet.save(str(sheet_path))
    print(f"\n[SUCCESS] 3x3 Master Contact Sheet saved to: {sheet_path}")

if __name__ == "__main__":
    run_capture()
