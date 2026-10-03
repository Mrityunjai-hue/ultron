import os
import sys
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ultron.presence.animation import SpringChoreographer, STATE_TARGETS
from ultron.presence.audio_visualizer import AudioVisualizer
from ultron.presence.renderer import PresenceRenderer

def generate_clean_live_board():
    artifact_dir = Path(r"C:\Users\Mrityunjai\.gemini\antigravity-ide\brain\e33e180f-cea0-45db-9154-1db4b83009b7")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    out_path = artifact_dir / "ultron_live_all_9_stages.png"

    # Font setup
    def first_existing(*paths):
        for p in paths:
            if os.path.exists(p):
                return p
        return None

    sb = first_existing("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf") or "arialbd.ttf"
    sr = first_existing("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf") or "arial.ttf"
    sm = first_existing("C:/Windows/Fonts/CascadiaCode.ttf", "C:/Windows/Fonts/consola.ttf") or "consola.ttf"

    font_title = ImageFont.truetype(sb, 22)
    font_sub   = ImageFont.truetype(sr, 18)
    font_code  = ImageFont.truetype(sm, 12)

    # 9 Stages Specification matching user's exact reference
    stages = [
        (
            "01 · IDLE (Default)",
            "Larger, elegant presence with ambient awareness",
            "IDLE",
            {},
        ),
        (
            "02 · HOVER",
            "Slightly brighter with cursor awareness",
            "HOVER",
            {"gaze": (3.5, 0.0)},
        ),
        (
            "03 · LISTENING",
            "Clear state indicator with subtle audio response",
            "LISTENING",
            {"audio": 0.25},
        ),
        (
            "04 · THINKING",
            "Focused, sophisticated motion",
            "THINKING",
            {},
        ),
        (
            "05 · SPEAKING",
            "Clean indicator with audio-driven motion",
            "RESPONDING",
            {"audio": 0.38},
        ),
        (
            "06 · TOOL EXECUTION",
            "Spacious, clean action panel",
            "TOOL_EXEC",
            {"tool": ("APP:OPEN", "Google Chrome", "running", 0.65)},
        ),
        (
            "07 · TOOL COMPLETE",
            "Clear success state with elegant feedback",
            "TOOL_COMPLETE",
            {"tool": ("APP:OPEN", "Google Chrome", "complete", 1.0)},
        ),
        (
            "08 · CONFIRMATION",
            "Spacious, premium security dialog",
            "CONFIRMATION",
            {"vault": ("DELETE_FILE", "build/artifacts/cache.db", "Delete this file?")},
        ),
        (
            "09 · FULLSCREEN (Retracted)",
            "Minimal presence while fullscreen",
            "RETRACTED",
            {},
        ),
    ]

    cell_w, cell_h = 680, 280
    total_w = cell_w * 3
    total_h = cell_h * 3

    board = Image.new("RGBA", (total_w, total_h), (8, 10, 16, 255))
    draw_board = ImageDraw.Draw(board)

    # Sample code lines to draw blurred background editor
    code_lines = [
        "import torch",
        "from ultron.core.runtime import UltronEngine",
        "engine = UltronEngine(model='ultron-v3')",
        "with engine.activate_presence():",
        "    response = engine.listen_and_respond()",
        "    if response.requires_action:",
        "        engine.execute_action(response.tool)",
        "    print('Ultron state:', engine.state)",
    ]

    for idx, (title, subtitle, st_name, extras) in enumerate(stages):
        row = idx // 3
        col = idx % 3
        cell_ox = col * cell_w
        cell_oy = row * cell_h

        # Generate realistic desktop wallpaper/editor background
        cell_bg = Image.new("RGBA", (cell_w, cell_h), (11, 14, 22, 255))
        cdraw = ImageDraw.Draw(cell_bg)

        if idx == 8:
            # 09 FULLSCREEN: Rich purple city lights bokeh background
            for b in range(16):
                bx = (b * 45 + 20) % cell_w
                by = 120 + (b * 37) % 110
                br = 25 + (b * 13) % 45
                b_alpha = 18 + (b * 7) % 25
                cdraw.ellipse([bx - br, by - br, bx + br, by + br], fill=(130, 45, 230, b_alpha))
                cdraw.ellipse([bx + 15 - br, by - br, bx + 15 + br, by + br], fill=(60, 120, 240, b_alpha))
            cell_bg = cell_bg.filter(ImageFilter.GaussianBlur(radius=8.0))
            cdraw = ImageDraw.Draw(cell_bg)
        else:
            # 01-08: Realistic blurred VS Code editor background
            # Left gutter line numbers
            for li, ltext in enumerate(code_lines):
                ly = 45 + li * 22
                cdraw.text((18, ly), f"{li + 1:2d}", fill=(55, 68, 88, 160), font=font_code)
                # Syntax colored keywords
                words = ltext.split()
                wx = 45
                for w in words:
                    if w in ("import", "from", "with", "if", "print"):
                        wcol = (195, 120, 245, 140)
                    elif w.startswith("'"):
                        wcol = (220, 160, 90, 140)
                    elif "(" in w or ")" in w:
                        wcol = (90, 180, 245, 140)
                    else:
                        wcol = (180, 195, 215, 130)
                    cdraw.text((wx, ly), w + " ", fill=wcol, font=font_code)
                    try:
                        bb = font_code.getbbox(w + " ")
                        wx += bb[2] - bb[0]
                    except Exception:
                        wx += 50
            cell_bg = cell_bg.filter(ImageFilter.GaussianBlur(radius=3.5))
            cdraw = ImageDraw.Draw(cell_bg)

        # Bottom label bar background
        cdraw.rectangle([0, cell_h - 76, cell_w, cell_h], fill=(7, 9, 15, 245))

        # Render LIVE UI stage using Ultron's actual renderer
        ch = SpringChoreographer()
        viz = AudioVisualizer()
        renderer = PresenceRenderer(canvas_width=cell_w, canvas_height=cell_h)

        ch.set_state(st_name)
        for _ in range(60):
            ch.update(1.0 / 60.0)

        if "gaze" in extras:
            ch.set_gaze(extras["gaze"][0], extras["gaze"][1])
            for _ in range(30):
                ch.update(1.0 / 60.0)

        if "audio" in extras:
            ch._audio_resonance = extras["audio"]

        if "tool" in extras:
            t_name, target, status, prog = extras["tool"]
            renderer.set_tool_context(t_name, target, status, prog)

        if "vault" in extras:
            act, target, msg = extras["vault"]
            renderer.set_vault_context(act, target, msg)

        # Render the live frame from our real python code
        live_frame = renderer.render_frame(ch, viz, 0.016)

        # Composite live frame on top of realistic desktop
        cell_bg.alpha_composite(live_frame)

        # Draw Title & Subtitle at bottom of cell
        cdraw.text((24, cell_h - 66), title, fill=(235, 240, 252, 245), font=font_title)
        cdraw.text((24, cell_h - 36), subtitle, fill=(130, 145, 168, 200), font=font_sub)

        # Paste cell onto presentation board
        board.paste(cell_bg, (cell_ox, cell_oy))

    # Draw crisp 1px grid divider lines
    grid_line = (255, 255, 255, 28)
    draw_board.line([(cell_w, 0), (cell_w, total_h)], fill=grid_line, width=1)
    draw_board.line([(cell_w * 2, 0), (cell_w * 2, total_h)], fill=grid_line, width=1)
    draw_board.line([(0, cell_h), (total_w, cell_h)], fill=grid_line, width=1)
    draw_board.line([(0, cell_h * 2), (total_w, cell_h * 2)], fill=grid_line, width=1)

    board.save(out_path, format="PNG")
    print(f"Successfully generated clean live stage presentation board: {out_path}")

if __name__ == "__main__":
    generate_clean_live_board()
