import os
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ultron.presence.animation import SpringChoreographer, STATE_TARGETS
from ultron.presence.audio_visualizer import AudioVisualizer
from ultron.presence.renderer import PresenceRenderer

def create_presentation_board():
    artifact_dir = _ROOT / "docs" / "assets" / "visual"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    out_path = artifact_dir / "ultron_all_9_stages.png"

    # Font setup
    def first_existing(*paths):
        for p in paths:
            if os.path.exists(p):
                return p
        return None

    sb = first_existing("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf") or "arialbd.ttf"
    sr = first_existing("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf") or "arial.ttf"

    font_title = ImageFont.truetype(sb, 22)
    font_sub   = ImageFont.truetype(sr, 18)

    # 9 Stages Specification
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
            {"tool": ("APP:OPEN", "Google Chrome (chrome.exe)", "running", 0.65)},
        ),
        (
            "07 · TOOL COMPLETE",
            "Clear success state with elegant feedback",
            "TOOL_COMPLETE",
            {"tool": ("APP:OPEN", "Google Chrome (chrome.exe)", "complete", 1.0)},
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

    cell_w, cell_h = 760, 310
    total_w = cell_w * 3
    total_h = cell_h * 3

    board = Image.new("RGBA", (total_w, total_h), (8, 10, 16, 255))
    draw_board = ImageDraw.Draw(board)

    for idx, (title, subtitle, st_name, extras) in enumerate(stages):
        row = idx // 3
        col = idx % 3
        cell_ox = col * cell_w
        cell_oy = row * cell_h

        # Cell background with subtle radial gradient tone
        cell_bg = Image.new("RGBA", (cell_w, cell_h), (7, 9, 15, 255))
        cdraw = ImageDraw.Draw(cell_bg)

        # Subtle dark ambient background vignette
        cdraw.rectangle([0, 0, cell_w, cell_h], fill=(8, 10, 16, 255))

        # Render stage UI
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

        frame = renderer.render_frame(ch, viz, 0.016)

        # Composite frame onto cell_bg
        cell_bg.alpha_composite(frame)

        # Draw Label & Description at bottom left of cell
        cdraw.text((28, cell_h - 68), title, fill=(235, 240, 252, 245), font=font_title)
        cdraw.text((28, cell_h - 38), subtitle, fill=(130, 145, 168, 200), font=font_sub)

        # Paste cell to board
        board.paste(cell_bg, (cell_ox, cell_oy))

    # Draw grid divider lines
    line_col = (255, 255, 255, 24)
    # Vertical grid lines
    draw_board.line([(cell_w, 0), (cell_w, total_h)], fill=line_col, width=1)
    draw_board.line([(cell_w * 2, 0), (cell_w * 2, total_h)], fill=line_col, width=1)
    # Horizontal grid lines
    draw_board.line([(0, cell_h), (total_w, cell_h)], fill=line_col, width=1)
    draw_board.line([(0, cell_h * 2), (total_w, cell_h * 2)], fill=line_col, width=1)

    board.save(out_path, format="PNG")
    print(f"Successfully generated presentation board at: {out_path}")

if __name__ == "__main__":
    create_presentation_board()
