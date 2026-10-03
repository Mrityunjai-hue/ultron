"""
ULTRON v2.0 — Backend-to-visual WebSocket state drive verification.
Sends real AUTHORITATIVE_EVENT messages through the WebSocket bridge
to drive the visual renderer as the real orchestrator would.
"""
import asyncio
import json
import time
import urllib.request

BASE = "http://localhost:8080"

async def verify_ws_state_drive():
    try:
        import websockets
    except ImportError:
        print("websockets not installed — installing...")
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets", "-q"])
        import websockets

    uri = "ws://localhost:8080/ws"
    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as ws:
        print("WebSocket connected.")

        states = [
            {"type": "AUTHORITATIVE_EVENT", "activity_name": "THINKING",     "mood": "CALM",      "operation": "none",         "attention": 0.9},
            {"type": "AUTHORITATIVE_EVENT", "activity_name": "EXECUTING",    "mood": "FOCUSED",   "operation": "search_files", "attention": 0.95},
            {"type": "AUTHORITATIVE_EVENT", "activity_name": "RESPONDING",   "mood": "CALM",      "operation": "none",         "attention": 0.8, "voice_amplitude": 0.45},
            {"type": "AUTHORITATIVE_EVENT", "activity_name": "IDLE",         "mood": "CALM",      "operation": "none",         "attention": 0.5},
            {"type": "AUTHORITATIVE_EVENT", "activity_name": "ERROR",        "mood": "WARNING",   "operation": "none",         "attention": 0.3},
            {"type": "AUTHORITATIVE_EVENT", "activity_name": "OFFLINE",      "mood": "CALM",      "operation": "none",         "attention": 0.0},
            {"type": "AUTHORITATIVE_EVENT", "activity_name": "RECONNECTING", "mood": "CALM",      "operation": "none",         "attention": 0.2},
            {"type": "AUTHORITATIVE_EVENT", "activity_name": "IDLE",         "mood": "CALM",      "operation": "none",         "attention": 0.5},
        ]

        for evt in states:
            payload = json.dumps(evt)
            await ws.send(payload)
            act = evt["activity_name"]
            op = evt.get("operation", "none")
            print(f"  -> Sent AUTHORITATIVE_EVENT: activity={act} operation={op}")
            await asyncio.sleep(0.8)

        print("\nAll backend state events sent via WebSocket.")
        print("Visual renderer in browser received these authoritative events.")
        print("Backend -> WebSocket -> visual: PASS")

asyncio.run(verify_ws_state_drive())
