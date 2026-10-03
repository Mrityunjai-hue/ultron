import os
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ultron.presence.animation import SpringChoreographer, STATE_TARGETS
from ultron.presence.audio_visualizer import AudioVisualizer
from ultron.presence.renderer import PresenceRenderer

def generate_live_stage_board():
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

    font_title = ImageFont.truetype(sb, 22)
    font_sub   = ImageFont.truetype(sr, 18)

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

    # Load reference image to use its realistic desktop wallpaper textures
    ref_path = artifact_dir / ".user_uploaded" / "media_1791013958029.png"
    ref_img = None
    if ref_path.exists():
        ref_img = Image.open(ref_path).convert("RGBA")

    board = Image.new("RGBA", (total_w, total_h), (8, 10, 16, 255))
    draw_board = ImageDraw.Draw(board)

    for idx, (title, subtitle, st_name, extras) in enumerate(stages):
        row = idx // 3
        col = idx % 3
        cell_ox = col * cell_w
        cell_oy = row * cell_h

        # Extract realistic background from reference or generate synthetic dark IDE background
        if ref_img is not None:
            rw, rh = ref_img.size
            rcw, rch = rw // 3, rh // 3
            ref_crop = ref_img.crop((col * rcw, row * rch, (col + 1) * rcw, (row + 1) * rch))
            # Blur the background crop slightly to let our live rendered overlay shine
            bg_base = ref_crop.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
            bg_base = bg_base.filter(ImageFilter.GaussianBlur(radius=1.2))
            # Darken slightly for high contrast
            darkener = Image.new("RGBA", (cell_w, cell_h), (0, 0, 0, 75))
            bg_base.alpha_composite(darkener)
        else:
            bg_base = Image.new("RGBA", (cell_w, cell_h), (8, 10, 16, 255))

        # Bottom label bar
        draw_cell = ImageDraw.Draw(bg_base)
        draw_cell.rectangle([0, cell_h - 76, cell_w, cell_h], fill=(8, 10, 16, 230))

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

        # Render the live frame
        live_frame = renderer.render_frame(ch, viz, 0.016)

        # Composite live frame on top of realistic desktop
        bg_base.alpha_composite(live_frame)

        # Draw Title & Subtitle at bottom of cell
        draw_cell.text((24, cell_h - 66), title, fill=(235, 240, 252, 245), font=font_title)
        draw_cell.text((24, cell_h - 36), subtitle, fill=(130, 145, 168, 200), font=font_sub)

        # Paste cell onto presentation board
        board.paste(bg_base, (cell_ox, cell_oy))

    # Draw crisp 1px grid divider lines
    grid_line = (255, 255, 255, 28)
    draw_board.line([(cell_w, 0), (cell_w, total_h)], fill=grid_line, width=1)
    draw_board.line([(cell_w * 2, 0), (cell_w * 2, total_h)], fill=grid_line, width=1)
    draw_board.line([(0, cell_h), (total_w, cell_h)], fill=grid_line, width=1)
    draw_board.line([(0, cell_h * 2), (total_w, cell_h * 2)], fill=grid_line, width=1)

    board.save(out_path, format="PNG")
    print(f"Successfully generated live stage presentation board: {out_path}")

if __name__ == "__main__":
    generate_live_stage_board()
