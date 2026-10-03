"""
ULTRON v2.0 — SECURE SERVER-SIDE VOICE BACKEND, WEBSOCKET BRIDGE & UNIFIED RUNNER
─────────────────────────────────────────────────────────────────────────────
Server-Side ElevenLabs Integration & Real-Time Bi-Directional Bridge:
- Selected Voice ID: 5vpfPL62TWuqhC30bkVm
- Audio Streaming with optimize_streaming_latency=3
- 100% Server-Side API Key Security (Never exposed to client)
- Bi-Directional WebSocket Bridge (/ws):
    • STATE_CHANGE: Syncs Orchestrator FSM states to Living Canvas UI
    • TTS_DISPATCH: Pushes LLM responses directly to ElevenLabs stream
    • GAZE_TARGET: Steers eyes to user face coordinates from camera
    • USER_RECOGNIZED: Displays user identification telemetry
    • USER_UTTERANCE / WAKE_WORD_DETECTED: Real-time speech input from UI
    • USER_SPEECH_START / USER_SPEECH_END / INTERRUPT: Real-time UI events
- Static UI Serving & Voice Telemetry Status
- Unified Orchestrator Mode (--with-orchestrator or RUN_ORCHESTRATOR=1)
─────────────────────────────────────────────────────────────────────────────
"""
import os
import sys
import json
import logging
import asyncio
import argparse
from pathlib import Path
from typing import Optional, List, Set

import requests
from fastapi import FastAPI, Request, Response, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ultron.voice.server")

# Default Voice Configuration
DEFAULT_VOICE_ID = "5vpfPL62TWuqhC30bkVm"
ROOT_DIR = Path(__file__).resolve().parent
ENV_FILE = ROOT_DIR / ".env"
PRESENCE_DIR = ROOT_DIR / "ultron" / "presence" / "visual"
LAB_DIR = ROOT_DIR / "ui" / "lab"

# Load .env if present
def load_env():
    key = os.environ.get("ELEVENLABS_API_KEY", "") or os.environ.get("XI_API_KEY", "")
    if not key and ENV_FILE.exists():
        try:
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ELEVENLABS_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
                    elif line.startswith("XI_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except Exception as e:
            logger.warning(f"Error reading .env: {e}")
    return key

SERVER_API_KEY = load_env()
RUN_ORCHESTRATOR = os.environ.get("RUN_ORCHESTRATOR", "0") in ["1", "true", "True"]

# ── WebSocket Connection Manager ─────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.current_state: str = "idle"
        self.current_user: Optional[str] = None
        self.current_confidence: float = 0.0

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total active: {len(self.active_connections)}")

        # Send initial handshake state
        await websocket.send_json({
            "type": "HANDSHAKE",
            "status": "connected",
            "voice_id": DEFAULT_VOICE_ID,
            "state": self.current_state,
            "has_api_key": bool(SERVER_API_KEY),
            "user": self.current_user,
            "confidence": self.current_confidence,
        })

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total active: {len(self.active_connections)}")

    async def broadcast(self, message: dict, sender: Optional[WebSocket] = None):
        if not self.active_connections:
            return
        dead = set()
        for connection in self.active_connections:
            if connection == sender:
                continue
            try:
                await connection.send_json(message)
            except Exception:
                dead.add(connection)
        for d in dead:
            self.active_connections.discard(d)

ws_manager = ConnectionManager()

def broadcast_sync(message: dict):
    """Synchronous helper to broadcast into asyncio loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(ws_manager.broadcast(message))
    except Exception as e:
        logger.debug(f"Broadcast sync note: {e}")

# ── FastAPI Application Setup ────────────────────────────────────────────────
app = FastAPI(title="ULTRON Voice & Orchestration Server", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Optional Integrated Orchestrator Task ────────────────────────────────────
orch_instance = None
ports_instance = None

@app.on_event("startup")
async def on_startup():
    global orch_instance, ports_instance
    if RUN_ORCHESTRATOR:
        logger.info("[Server] Booting integrated ULTRON Orchestrator background loop...")
        try:
            sys.path.insert(0, str(ROOT_DIR / "laptop"))
            from laptop.main import load_config
            from laptop.core.ports import PortBundle
            from laptop.core.orchestrator import UltronOrchestrator

            config = load_config("laptop")
            ports_instance = await PortBundle.create(config)
            orch_instance = UltronOrchestrator(ports_instance, config)
            asyncio.create_task(orch_instance.run())
            logger.info("[Server] Integrated ULTRON Orchestrator running.")
        except Exception as e:
            logger.error(f"[Server] Failed to boot orchestrator: {e}", exc_info=True)

@app.on_event("shutdown")
async def on_shutdown():
    global ports_instance, orch_instance
    if orch_instance:
        orch_instance.stop()
    if ports_instance:
        await ports_instance.shutdown()

# ── WebSocket Endpoint ───────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "CLIENT_READY":
                logger.info("UI Client signaled ready.")

            elif msg_type == "USER_SPEECH_START":
                logger.info("User speech start detected by client.")
                ws_manager.current_state = "listening"
                await ws_manager.broadcast({"type": "STATE_CHANGE", "state": "listening"}, sender=websocket)

            elif msg_type == "USER_SPEECH_END":
                logger.info("User speech end detected by client.")
                await ws_manager.broadcast({"type": "USER_SPEECH_END"}, sender=websocket)

            elif msg_type == "INTERRUPT_TRIGGERED":
                logger.info("Speech interruption triggered by client.")
                ws_manager.current_state = "interrupted"
                await ws_manager.broadcast({"type": "STATE_CHANGE", "state": "interrupted"}, sender=websocket)

            elif msg_type == "SET_STATE":
                new_state = data.get("state", "idle")
                ws_manager.current_state = new_state
                await ws_manager.broadcast({"type": "STATE_CHANGE", "state": new_state}, sender=websocket)

            elif msg_type == "USER_UTTERANCE":
                text = data.get("text", "")
                logger.info(f"User utterance received via WebSocket: {text!r}")
                if orch_instance:
                    orch_instance._on_ui_utterance(text)
                await ws_manager.broadcast({"type": "USER_UTTERANCE", "text": text}, sender=websocket)

            elif msg_type == "WAKE_WORD_DETECTED":
                logger.info("Wake word detected via WebSocket!")
                ws_manager.current_state = "listening"
                if orch_instance:
                    orch_instance._on_ui_wake()
                await ws_manager.broadcast({"type": "WAKE_WORD_DETECTED"}, sender=websocket)
                await ws_manager.broadcast({"type": "STATE_CHANGE", "state": "listening"}, sender=websocket)

            elif msg_type == "GAZE_TARGET":
                await ws_manager.broadcast(data, sender=websocket)

            elif msg_type == "TTS_DISPATCH":
                await ws_manager.broadcast(data, sender=websocket)

            elif msg_type == "USER_RECOGNIZED":
                ws_manager.current_user = data.get("name")
                ws_manager.current_confidence = data.get("confidence", 0.9)
                await ws_manager.broadcast(data, sender=websocket)

            elif msg_type == "PING":
                await websocket.send_json({"type": "PONG"})

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)

# ── REST API Endpoints ───────────────────────────────────────────────────────
@app.get("/api/voice/status")
async def voice_status():
    global SERVER_API_KEY
    SERVER_API_KEY = SERVER_API_KEY or load_env()
    return {
        "status": "online",
        "voice_id": DEFAULT_VOICE_ID,
        "has_api_key": bool(SERVER_API_KEY and len(SERVER_API_KEY) > 5),
        "model": "eleven_multilingual_v2",
        "streaming": True,
        "clients_connected": len(ws_manager.active_connections),
        "voice_character": "Deep, mature, resonant, calm, controlled, authoritative"
    }

@app.post("/api/voice/config")
async def voice_config(req: Request):
    global SERVER_API_KEY
    data = await req.json()
    new_key = data.get("api_key", "").strip()
    if new_key:
        SERVER_API_KEY = new_key
        try:
            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.write(f"ELEVENLABS_API_KEY={new_key}\n")
            logger.info("Saved new ElevenLabs API key server-side.")
        except Exception as e:
            logger.error(f"Failed to persist .env: {e}")
        return {"status": "ok", "message": "API key updated on server", "has_api_key": True}
    return JSONResponse({"error": "Empty API key provided"}, status_code=400)

@app.post("/api/bridge/event")
async def bridge_set_authoritative_event(req: Request):
    """Allows backend orchestrator to post AuthoritativeEvent directly to Rive."""
    data = await req.json()
    await ws_manager.broadcast({"type": "AUTHORITATIVE_EVENT", **data})
    return {"status": "ok"}

@app.post("/api/bridge/state")
async def bridge_set_state(req: Request):
    """Allows backend orchestrator to post state changes directly."""
    data = await req.json()
    state = data.get("state", "idle")
    ws_manager.current_state = state
    await ws_manager.broadcast({"type": "STATE_CHANGE", "state": state})
    return {"status": "ok", "state": state}

@app.post("/api/bridge/gaze")
async def bridge_set_gaze(req: Request):
    """Allows camera face detection to steer eye gaze."""
    data = await req.json()
    x = data.get("x", 0.0)
    y = data.get("y", 0.0)
    await ws_manager.broadcast({"type": "GAZE_TARGET", "x": x, "y": y})
    return {"status": "ok"}

@app.post("/api/bridge/user")
async def bridge_set_user(req: Request):
    """Allows face recognition to broadcast user identification."""
    data = await req.json()
    name = data.get("name", "UNKNOWN")
    confidence = data.get("confidence", 0.9)
    ws_manager.current_user = name
    ws_manager.current_confidence = confidence
    await ws_manager.broadcast({"type": "USER_RECOGNIZED", "name": name, "confidence": confidence})
    return {"status": "ok", "user": name}

@app.post("/api/bridge/speak")
async def bridge_speak(req: Request):
    """Allows orchestrator to trigger speech playback on UI."""
    data = await req.json()
    text = data.get("text", "")
    if text:
        await ws_manager.broadcast({"type": "TTS_DISPATCH", "text": text})
        return {"status": "dispatched", "text": text}
    return JSONResponse({"error": "No text provided"}, status_code=400)

@app.post("/api/bridge/utterance")
async def bridge_utterance(req: Request):
    """Allows submitting an utterance to the system."""
    data = await req.json()
    text = data.get("text", "")
    if text:
        if orch_instance:
            orch_instance._on_ui_utterance(text)
        await ws_manager.broadcast({"type": "USER_UTTERANCE", "text": text})
        return {"status": "dispatched", "text": text}
    return JSONResponse({"error": "No text provided"}, status_code=400)

@app.post("/api/tts/stream")
async def stream_tts(req: Request):
    global SERVER_API_KEY
    SERVER_API_KEY = SERVER_API_KEY or load_env()

    data = await req.json()
    text = data.get("text", "").strip()
    voice_id = data.get("voice_id", DEFAULT_VOICE_ID) or DEFAULT_VOICE_ID

    if not text:
        return JSONResponse({"error": "Text is required for TTS synthesis"}, status_code=400)

    if not SERVER_API_KEY:
        logger.warning("TTS request received but ELEVENLABS_API_KEY is not set on server.")
        return JSONResponse(
            {
                "error": "ELEVENLABS_API_KEY is not configured on the server",
                "voice_id": voice_id,
                "hint": "Set ELEVENLABS_API_KEY in .env or via Developer Voice Lab."
            },
            status_code=401
        )

    # ElevenLabs Streaming Endpoint with low latency optimization
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?optimize_streaming_latency=3"
    headers = {
        "xi-api-key": SERVER_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.65,
            "similarity_boost": 0.85,
            "style": 0.10,
            "use_speaker_boost": True
        }
    }

    try:
        logger.info(f"Initiating ElevenLabs stream: Voice={voice_id}, text='{text[:36]}...'")
        resp = requests.post(url, json=payload, headers=headers, stream=True, timeout=15)

        if resp.status_code != 200:
            err_msg = resp.text
            logger.error(f"ElevenLabs error ({resp.status_code}): {err_msg}")
            return JSONResponse(
                {
                    "error": f"ElevenLabs API Error ({resp.status_code})",
                    "details": err_msg
                },
                status_code=resp.status_code
            )

        def iter_chunks():
            try:
                for chunk in resp.iter_content(chunk_size=4096):
                    if chunk:
                        yield chunk
            except Exception as e:
                logger.error(f"Error streaming chunks: {e}")

        return StreamingResponse(
            iter_chunks(),
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "no-cache",
                "X-Voice-ID": voice_id,
                "X-Ultron-Status": "speaking"
            }
        )
    except Exception as e:
        logger.error(f"TTS Stream exception: {e}")
        return JSONResponse({"error": f"Server exception during TTS stream: {str(e)}"}, status_code=500)

# Serve Web UI static files
@app.get("/presence")
def redirect_presence():
    return RedirectResponse(url="/presence/")

@app.get("/lab")
def redirect_lab():
    return RedirectResponse(url="/lab/")

if PRESENCE_DIR.exists():
    app.mount("/presence", StaticFiles(directory=str(PRESENCE_DIR), html=True), name="presence")
    logger.info(f"Mounted production visual presence at /presence: {PRESENCE_DIR}")

if LAB_DIR.exists():
    app.mount("/lab", StaticFiles(directory=str(LAB_DIR), html=True), name="lab")
    logger.info(f"Mounted Animation Lab at /lab: {LAB_DIR}")

if PRESENCE_DIR.exists():
    app.mount("/", StaticFiles(directory=str(PRESENCE_DIR), html=True), name="root")
    logger.info(f"Mounted production visual presence at /: {PRESENCE_DIR}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ULTRON Server & Bridge")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)))
    parser.add_argument("--with-orchestrator", action="store_true", help="Launch integrated orchestrator loop")
    args = parser.parse_args()

    if args.with_orchestrator:
        RUN_ORCHESTRATOR = True

    logger.info(f"Starting ULTRON Voice & Bridge Server on port {args.port} (Orchestrator={RUN_ORCHESTRATOR})...")
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")
