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

def render_all_states():
    out_dir = _ROOT / "docs" / "assets" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    states_to_test = [
        ("01_IDLE", "IDLE", {}),
        ("02_HOVER", "HOVER", {"gaze": (3.5, 0.0)}),
        ("03_LISTENING", "LISTENING", {"audio": 0.22}),
        ("04_THINKING", "THINKING", {}),
        ("05_SPEAKING", "RESPONDING", {"audio": 0.35}),
        ("06_TOOL_EXEC", "TOOL_EXEC", {"tool": ("APP:OPEN", "Google Chrome (chrome.exe)", "running", 0.65)}),
        ("07_TOOL_COMPLETE", "TOOL_COMPLETE", {"tool": ("APP:OPEN", "Google Chrome", "complete", 1.0)}),
        ("08_CONFIRMATION", "CONFIRMATION", {"vault": ("DELETE_FILE", "build/artifacts/cache.db", "Delete this file?")}),
        ("09_RETRACTED", "RETRACTED", {}),
    ]

    rendered_images = []

    # Dark background color similar to desktop wallpaper in reference image
    bg_color = (12, 14, 22)

    for prefix, st_name, extras in states_to_test:
        ch = SpringChoreographer()
        viz = AudioVisualizer()
        renderer = PresenceRenderer(canvas_width=640, canvas_height=240)

        # Snap choreographer to target state
        ch.set_state(st_name)
        # Advance springs to settle instantly
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

        # Render frame
        img = renderer.render_frame(ch, viz, 0.016)

        # Composite on dark background for preview
        comp = Image.new("RGBA", (640, 240), (*bg_color, 255))
        comp.alpha_composite(img)

        # Add label
        draw = ImageDraw.Draw(comp)
        draw.text((16, 210), f"{prefix} ({st_name})", fill=(200, 210, 230, 255))

        out_path = out_dir / f"{prefix}.png"
        comp.save(out_path)
        rendered_images.append((prefix, comp))
        print(f"Saved {out_path}")

    # Create 3x3 grid comparison
    cell_w, cell_h = 640, 240
    grid = Image.new("RGBA", (cell_w * 3, cell_h * 3), (*bg_color, 255))
    for idx, (prefix, comp) in enumerate(rendered_images):
        row = idx // 3
        col = idx % 3
        grid.paste(comp, (col * cell_w, row * cell_h))

    grid_path = out_dir / "grid_9states_preview.png"
    grid.save(grid_path)
    print(f"\nSaved composite 3x3 grid to: {grid_path}")

if __name__ == "__main__":
    render_all_states()
