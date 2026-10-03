"""
ULTRON Laptop Orb Adapter v2.0
Communicates state, gaze, and speech triggers to the Fullscreen Web UI via WebSocket / Bridge API.
"""
from __future__ import annotations
import asyncio
import logging
import json
from typing import Optional, Callable
import httpx

logger = logging.getLogger("ultron.adapters.laptop.orb")

STATE_MAP = {
    "idle": "idle",
    "listen": "listening",
    "think": "thinking",
    "speak": "speaking",
    "response": "listening",
    "reflex": "focused",
    "sleep": "sleep",
    "shutdown": "sleep",
}

class BrowserOrbAdapter:
    """
    Connects to the ULTRON WebSocket bridge at ws://localhost:8080/ws
    and falls back to HTTP /api/bridge endpoints if needed.
    """
    def __init__(self, config: dict):
        self.config = config
        self.port = config.get("server", {}).get("port", 8080)
        self.base_url = f"http://localhost:{self.port}"
        self.ws_url = f"ws://localhost:{self.port}/ws"
        self._ws = None
        self._running = False
        self._client = httpx.AsyncClient(timeout=3.0)
        self._on_utterance: Optional[Callable[[str], None]] = None
        self._on_wake: Optional[Callable[[], None]] = None

    def set_callbacks(self, on_utterance: Optional[Callable[[str], None]] = None, on_wake: Optional[Callable[[], None]] = None):
        self._on_utterance = on_utterance
        self._on_wake = on_wake

    async def start(self):
        """Start background connection to the WebSocket bridge."""
        self._running = True
        asyncio.create_task(self._connect_loop())

    async def _connect_loop(self):
        try:
            import websockets
        except ImportError:
            logger.warning("websockets library not found. Using HTTP bridge fallback.")
            return

        while self._running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self._ws = ws
                    logger.info(f"Connected to ULTRON WebSocket bridge at {self.ws_url}")
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            mtype = data.get("type", "")
                            if mtype == "USER_UTTERANCE" and self._on_utterance:
                                self._on_utterance(data.get("text", ""))
                            elif mtype == "WAKE_WORD_DETECTED" and self._on_wake:
                                self._on_wake()
                        except Exception:
                            pass
            except Exception as e:
                self._ws = None
                await asyncio.sleep(2.0)

    async def set_state(self, state_name: str):
        """Map and transmit orchestrator state to UI character."""
        mapped = STATE_MAP.get(state_name.lower(), state_name.lower())
        logger.debug(f"Orb state set: {state_name} -> {mapped}")

        # 1. Try active WebSocket connection
        if self._ws:
            try:
                await self._ws.send(json.dumps({"type": "SET_STATE", "state": mapped}))
                return
            except Exception:
                self._ws = None

        # 2. HTTP Fallback
        try:
            await self._client.post(f"{self.base_url}/api/bridge/state", json={"state": mapped})
        except Exception as e:
            logger.debug(f"Orb HTTP bridge note: {e}")

    async def emit_authoritative_event(self, event):
        """
        Emits AuthoritativeEvent directly to Rive character engine and legacy UI.
        """
        rive_inputs = event.to_rive_inputs() if hasattr(event, "to_rive_inputs") else {}
        legacy_state = event.to_legacy_ui_state() if hasattr(event, "to_legacy_ui_state") else str(getattr(event, "activity", "idle")).lower()
        payload = {
            "type": "AUTHORITATIVE_EVENT",
            **rive_inputs,
            "legacy_state": legacy_state,
            "activity_name": getattr(event.activity, "value", str(event.activity)),
            "operation": getattr(event, "operation", "none"),
            "mood": getattr(event.mood, "value", str(event.mood)),
            "gaze_x": getattr(event, "gaze_x", 0.0),
            "gaze_y": getattr(event, "gaze_y", 0.0),
            "attention": getattr(event, "attention", 0.5),
            "voice_amplitude": getattr(event, "voice_amplitude", 0.0),
        }

        # 1. Try WebSocket
        if self._ws:
            try:
                await self._ws.send(json.dumps(payload))
                return
            except Exception:
                self._ws = None

        # 2. HTTP Fallback
        try:
            await self._client.post(f"{self.base_url}/api/bridge/event", json=payload)
        except Exception:
            pass

    async def set_gaze(self, x: float, y: float):
        """Transmit eye gaze offset (-14 to +14 px) from face tracker."""
        if self._ws:
            try:
                await self._ws.send(json.dumps({"type": "GAZE_TARGET", "x": x, "y": y}))
                return
            except Exception:
                self._ws = None

        try:
            await self._client.post(f"{self.base_url}/api/bridge/gaze", json={"x": x, "y": y})
        except Exception:
            pass

    async def dispatch_tts(self, text: str):
        """Trigger UI voice engine to speak via ElevenLabs streaming."""
        if self._ws:
            try:
                await self._ws.send(json.dumps({"type": "TTS_DISPATCH", "text": text}))
                return
            except Exception:
                self._ws = None

        try:
            await self._client.post(f"{self.base_url}/api/bridge/speak", json={"text": text})
        except Exception:
            pass

    async def notify_user(self, name: str, confidence: float):
        """Transmit recognized user telemetry to UI."""
        if self._ws:
            try:
                await self._ws.send(json.dumps({
                    "type": "USER_RECOGNIZED",
                    "name": name,
                    "confidence": confidence
                }))
                return
            except Exception:
                self._ws = None

        try:
            await self._client.post(f"{self.base_url}/api/bridge/user", json={"name": name, "confidence": confidence})
        except Exception:
            pass

    async def release(self):
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        await self._client.aclose()

def create(config):
    adapter = BrowserOrbAdapter(config)
    return adapter
