"""
ULTRON V3 — Gemini Multimodal Live Realtime Provider
─────────────────────────────────────────────────────────────────────────────
Implements bidirectional streaming audio with Google Gemini Live API using
the official asynchronous google-genai SDK.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import asyncio
import logging
import time
from typing import AsyncGenerator, Dict, Any, Optional

from google import genai
from google.genai import types

from ultron.core.config import UltronConfig
from ultron.realtime.base import RealtimeProvider
from ultron.tools.registry import get_tool_declarations

logger = logging.getLogger("ultron.realtime.gemini")

class GeminiLiveProvider(RealtimeProvider):
    """Asynchronous Gemini Live streaming provider."""

    def __init__(self, config: UltronConfig):
        self.config = config
        self.api_key = config.gemini_api_key
        self.model = config.model.model
        self.voice_name = config.model.voice_name
        self.system_instruction = config.model.system_instruction

        self._client: Optional[genai.Client] = None
        self._session = None
        self._session_context = None
        self._is_connected = False
        self._reconnect_lock = asyncio.Lock()

        # Telemetry
        self.last_connect_time = 0.0
        self.connect_latency_ms = 0.0

    @property
    def is_connected(self) -> bool:
        return self._is_connected and self._session is not None

    async def connect(self) -> None:
        """Establishes streaming bidirectional connection to Gemini Live."""
        async with self._reconnect_lock:
            if self._is_connected and self._session is not None:
                return

            # Clean up previous session context if present
            if self._session_context:
                try:
                    await self._session_context.__aexit__(None, None, None)
                except Exception as ex:
                    logger.debug(f"[Gemini Live] Previous session context exit notice: {ex}")
                self._session_context = None
                self._session = None
                self._is_connected = False

            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not set. Set GEMINI_API_KEY environment variable.")

            t0 = time.perf_counter()
            logger.info(f"[Gemini Live] Connecting to {self.model} (Voice: {self.voice_name})...")

            self._client = genai.Client(api_key=self.api_key)

            speech_config = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice_name
                    )
                )
            )

            tool_declarations = get_tool_declarations()
            live_tools = [{"function_declarations": tool_declarations}] if tool_declarations else None

            connect_config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=speech_config,
                system_instruction=types.Content(
                    parts=[types.Part.from_text(text=self.system_instruction)]
                ),
                tools=live_tools,
            )

            try:
                self._session_context = self._client.aio.live.connect(
                    model=self.model,
                    config=connect_config,
                )
                self._session = await self._session_context.__aenter__()
                self._is_connected = True
                t_elapsed = (time.perf_counter() - t0) * 1000.0
                self.connect_latency_ms = round(t_elapsed, 2)
                self.last_connect_time = time.time()
                logger.info(f"[Gemini Live] Connected successfully in {self.connect_latency_ms}ms")

            except Exception as e:
                self._is_connected = False
                self._session = None
                if self._session_context:
                    try:
                        await self._session_context.__aexit__(None, None, None)
                    except Exception:
                        pass
                    self._session_context = None
                logger.error(f"[Gemini Live] Connection failed: {e}", exc_info=True)
                raise

    async def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        """Streams a chunk of 16kHz PCM16 audio to Gemini Live."""
        if not self.is_connected or not self._session:
            return

        try:
            await self._session.send_realtime_input(
                audio=types.Blob(
                    data=pcm_bytes,
                    mime_type="audio/pcm;rate=16000",
                )
            )
        except Exception as e:
            logger.warning(f"[Gemini Live] Send audio error: {e}")
            self._is_connected = False

    async def receive_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Continuously streams events from the Gemini Live server."""
        if not self._session:
            return

        try:
            async for response in self._session.receive():
                server_content = getattr(response, "server_content", None)
                if server_content:
                    # 1. Server-side Interruption Event
                    if getattr(server_content, "interrupted", False):
                        logger.info("[Gemini Live] Server indicated turn interrupted.")
                        yield {"type": "interrupted"}

                    # 2. Audio/Text Content in Model Turn
                    model_turn = getattr(server_content, "model_turn", None)
                    if model_turn and hasattr(model_turn, "parts"):
                        for part in model_turn.parts:
                            inline_data = getattr(part, "inline_data", None)
                            if inline_data and getattr(inline_data, "data", None):
                                yield {
                                    "type": "audio",
                                    "data": inline_data.data, # 24kHz PCM16 bytes
                                    "mime_type": getattr(inline_data, "mime_type", "audio/pcm;rate=24000"),
                                }

                            text = getattr(part, "text", None)
                            if text:
                                yield {"type": "text", "content": text}

                    # 3. Turn completion
                    if getattr(server_content, "turn_complete", False):
                        yield {"type": "turn_complete"}

                # 4. Function / Tool Call
                tool_call = getattr(response, "tool_call", None)
                if tool_call and hasattr(tool_call, "function_calls"):
                    for fc in tool_call.function_calls:
                        yield {
                            "type": "tool_call",
                            "name": fc.name,
                            "args": dict(fc.args) if fc.args else {},
                            "id": fc.id,
                        }

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[Gemini Live] Receive stream fault: {e}")
            self._is_connected = False

    async def send_tool_response(self, call_id: str, name: str, response: Dict[str, Any]) -> None:
        """Sends local tool execution result back to Gemini Live."""
        if not self.is_connected or not self._session:
            return

        logger.info(f"[Gemini Live] Returning tool response for '{name}' (ID: {call_id})")
        try:
            await self._session.send_tool_response(
                function_responses=[
                    types.FunctionResponse(
                        name=name,
                        id=call_id,
                        response={"result": response},
                    )
                ]
            )
        except Exception as e:
            logger.error(f"[Gemini Live] Failed sending tool response: {e}")

    async def interrupt(self) -> None:
        """Client-side interruption notification."""
        logger.info("[Gemini Live] Client barge-in interruption signaled.")

    async def disconnect(self) -> None:
        """Closes the active live session."""
        self._is_connected = False
        if self._session_context:
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._session_context = None
            self._session = None
        logger.info("[Gemini Live] Disconnected.")
