"""
ULTRON V3 — Interactive Desktop Presence Live Controller (Signature Redesign)
─────────────────────────────────────────────────────────────────────────────
Launches the live desktop overlay on your screen and lets you interactively
test state transitions, tool execution capsules, security vaults, and optical filaments.

Controls:
  [1] IDLE           (320x48 obsidian notch with living dual-filament signature)
  [2] HOVER          (328x50 subtle lift + filament parallax response)
  [3] LISTENING      (360x56 acoustic wave resonance + flanking sound brackets)
  [4] THINKING       (340x50 synaptic harmonic wave oscillations)
  [5] SPEAKING       (360x56 voice-driven fluid wave undulation)
  [6] INTERRUPTED    (Sub-40ms instant attentive snap)
  [7] TOOL EXECUTION (480x130 spacious Action Capsule: APP · OPEN Google Chrome)
  [8] TOOL COMPLETE  (480x130 Action Complete: ✓ Opened)
  [9] CONFIRMATION   (520x190 spacious Security Vault with amber perimeter highlight)
  [0] RETRACTED      (Invisible 2px hairline fullscreen mode)
  [Q] Exit

Hover with your mouse over the notch to see real-time filament parallax tracking!
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ultron.presence.animation import SpringChoreographer
from ultron.presence.audio_visualizer import AudioVisualizer
from ultron.presence.window import UltronOverlayWindow

def main():
    print("\n" + "=" * 65)
    print("       ULTRON V3 — CINEMATIC DESKTOP PRESENCE CONTROLLER       ")
    print("=" * 65)
    print(" Initializing native top-bezel overlay on your primary monitor...")

    ch = SpringChoreographer()
    viz = AudioVisualizer()

    def on_allow():
        print("\n [VAULT] >> User Clicked: ALLOW (Enter) <<")
        ch.set_state("IDLE")

    def on_dismiss():
        print("\n [VAULT] >> User Clicked: DISMISS (Esc) <<")
        ch.set_state("IDLE")

    def on_notch():
        print("\n [NOTCH] >> Notch Body Clicked <<")

    win = UltronOverlayWindow(
        choreographer=ch,
        audio_visualizer=viz,
        on_allow_click=on_allow,
        on_dismiss_click=on_dismiss,
        on_notch_click=on_notch,
    )
    win.start()

    print(" [OK] ULTRON is now live at the TOP-CENTER of your screen!")
    print("\n CONTROLS:")
    print("   [1] IDLE           - Dormant 300x46 obsidian notch")
    print("   [2] HOVER          - Lifted 312x48 notch with gaze tracking")
    print("   [3] LISTENING      - 340x52 active aperture resonance")
    print("   [4] THINKING       - 300x46 cognitive squint + synaptic spark")
    print("   [5] RESPONDING     - 340x52 acoustic vocal resonance")
    print("   [6] INTERRUPTED    - Instant barge-in snap reaction")
    print("   [7] TOOL EXEC      - 480x124 Action Capsule: APP · OPEN")
    print("   [8] TOOL COMPLETE  - 480x124 Action Complete: Opened")
    print("   [9] CONFIRMATION   - 500x180 Security Vault (Allow/Dismiss)")
    print("   [0] RETRACTED      - 2px hairline fullscreen mode")
    print("   [Q] Quit Controller")
    print("-" * 65)
    print(" Hover your mouse over the top notch to see ocular parallax tracking.\n")

    try:
        while True:
            cmd = input("Select state (1-9, 0, q to quit) > ").strip().lower()
            if cmd == "1":
                viz.reset()
                ch.set_state("IDLE")
                print(" -> State set to IDLE")
            elif cmd == "2":
                viz.reset()
                ch.set_state("HOVER")
                ch.set_gaze(3.5, 0.0)
                print(" -> State set to HOVER (Gaze shifted)")
            elif cmd == "3":
                viz.push_input_chunk(0.18)
                ch.set_state("LISTENING")
                print(" -> State set to LISTENING (Acoustic resonance)")
            elif cmd == "4":
                viz.reset()
                ch.set_state("THINKING")
                print(" -> State set to THINKING (Synaptic brow shimmer active)")
            elif cmd == "5":
                viz.push_input_chunk(0.24)
                ch.set_state("RESPONDING")
                print(" -> State set to RESPONDING (Acoustic vocal resonance)")
            elif cmd == "6":
                viz.reset()
                ch.snap_interruption()
                print(" -> Triggered INTERRUPTED snap reaction")
            elif cmd == "7":
                viz.reset()
                win.renderer.set_tool_context(
                    tool_name="APP:OPEN",
                    target="Google Chrome (chrome.exe)",
                    status="running",
                    progress=0.65,
                )
                ch.set_state("TOOL_EXEC")
                print(" -> State set to TOOL EXECUTION (Action Capsule)")
            elif cmd == "8":
                viz.reset()
                win.renderer.set_tool_context(
                    tool_name="APP:OPEN",
                    target="Google Chrome",
                    status="complete",
                    progress=1.0,
                )
                ch.set_state("TOOL_COMPLETE")
                print(" -> State set to TOOL COMPLETE (✓ Opened)")
            elif cmd == "9":
                viz.reset()
                win.renderer.set_vault_context(
                    action="DELETE_FILE",
                    target="build/artifacts/cache.db",
                    message="Permanent deletion requires authorization.",
                )
                ch.set_state("CONFIRMATION")
                print(" -> State set to CONFIRMATION VAULT (Click Allow/Dismiss on screen)")
            elif cmd == "0":
                viz.reset()
                ch.set_state("RETRACTED")
                print(" -> State set to RETRACTED (Fullscreen mode)")
            elif cmd in ("q", "quit", "exit"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        print("\nStopping desktop presence...")
        win.stop()
        print("Desktop presence stopped.")

if __name__ == "__main__":
    main()
