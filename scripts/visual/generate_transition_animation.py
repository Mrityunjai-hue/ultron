import os
import sys
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ultron.presence.animation import SpringChoreographer
from ultron.presence.audio_visualizer import AudioVisualizer
from ultron.presence.renderer import PresenceRenderer

def generate_transition_visuals():
    artifact_dir = _ROOT / "docs" / "assets" / "visual"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    out_gif = artifact_dir / "ultron_bouncy_spring_demo.gif"
    out_sheet = artifact_dir / "ultron_transition_frames.png"

    ch = SpringChoreographer()
    viz = AudioVisualizer()
    rnd = PresenceRenderer(canvas_width=600, canvas_height=220)

    # 1. Warm-up IDLE
    ch.set_state("IDLE")
    for _ in range(30):
        ch.update(1/60.0)

    frames = []
    sampled_frames = []

    # Sequence of states to record
    timeline = [
        ("IDLE", 20, {}),
        ("LISTENING", 25, {"audio": 0.35}),
        ("THINKING", 25, {}),
        ("CONFIRMATION", 45, {"vault": ("DELETE_FILE", "build/artifacts/cache.db", "Delete this file?")}),
        ("TOOL_EXEC", 45, {"tool": ("APP:OPEN", "Google Chrome", "running", 0.65)}),
        ("TOOL_COMPLETE", 35, {"tool": ("APP:OPEN", "Google Chrome", "complete", 1.0)}),
        ("IDLE", 30, {}),
    ]

    total_ticks = sum(count for _, count, _ in timeline)
    sample_indices = [int(i * (total_ticks - 1) / 11) for i in range(12)]

    tick = 0
    for state_name, count, extras in timeline:
        if "vault" in extras:
            action, target, msg = extras["vault"]
            rnd.set_vault_context(action, target, msg)
        if "tool" in extras:
            tool_name, target, status, prog = extras["tool"]
            rnd.set_tool_context(tool_name, target, status, prog)

        ch.set_state(state_name)

        for _ in range(count):
            audio_amp = extras.get("audio", 0.0)
            if audio_amp > 0:
                viz.push_input_chunk(audio_amp)
            amp = viz.update(1/60.0)
            ch.update(1/60.0, amp)
            frame_img = rnd.render_frame(ch, viz, 1/60.0)

            # Composite over sleek dark background
            bg = Image.new("RGBA", (600, 220), (12, 14, 22, 255))
            bdraw = ImageDraw.Draw(bg)
            bdraw.line([(0, 0), (600, 0)], fill=(40, 48, 65, 255), width=1)
            bg.alpha_composite(frame_img)

            frames.append(bg.convert("P", palette=Image.ADAPTIVE))

            if tick in sample_indices:
                sampled_frames.append((f"{state_name} (t={tick/60:.2f}s)", bg.copy()))

            tick += 1

    # Save animated GIF (40ms per frame = 25 fps playback)
    if frames:
        frames[0].save(
            out_gif,
            save_all=True,
            append_images=frames[1:],
            optimize=True,
            duration=40,
            loop=0,
        )
        print(f"Generated animated demo GIF: {out_gif}")

    # Generate 4x3 progression filmstrip
    if sampled_frames:
        sw, sh = 600, 220
        sheet_w = sw * 3
        sheet_h = sh * 4
        sheet = Image.new("RGBA", (sheet_w, sheet_h), (8, 10, 16, 255))
        sdraw = ImageDraw.Draw(sheet)

        def first_existing(*paths):
            for p in paths:
                if os.path.exists(p):
                    return p
            return None
        sb = first_existing("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf") or "arialbd.ttf"
        f_label = ImageFont.truetype(sb, 14)

        for i, (label, fimg) in enumerate(sampled_frames[:12]):
            r = i // 3
            c = i % 3
            ox = c * sw
            oy = r * sh
            sheet.paste(fimg, (ox, oy))
            sdraw.rectangle([ox, oy, ox + sw, oy + sh], outline=(30, 36, 52, 255), width=1)
            sdraw.text((ox + 16, oy + sh - 28), label, fill=(160, 180, 215, 255), font=f_label)

        sheet.save(out_sheet)
        print(f"Generated transition progression filmstrip: {out_sheet}")

if __name__ == "__main__":
    generate_transition_visuals()
