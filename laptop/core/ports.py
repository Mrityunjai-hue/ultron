"""
Port Bundle — hardware abstraction layer v2.0
All IO goes through these interfaces; seamlessly integrates Web UI Orb and Arduino UNO R4 hardware companion.
"""
from __future__ import annotations
import importlib
import logging
from dataclasses import dataclass
from typing import Protocol, Optional, Any

logger = logging.getLogger("ultron.core.ports")

class CameraPort(Protocol):
    async def capture_frame(self): ...
    async def release(self): ...

class MicPort(Protocol):
    async def wake_word_detected(self) -> bool: ...
    async def capture_utterance(self, timeout: float) -> Optional[str]: ...
    async def has_pending_audio(self) -> bool: ...
    def trigger_wake_word(self): ...
    async def release(self): ...

class SpeakerPort(Protocol):
    async def play(self, audio_data): ...
    async def release(self): ...

class OrbPort(Protocol):
    async def set_state(self, state_name: str): ...
    async def set_gaze(self, x: float, y: float): ...
    async def dispatch_tts(self, text: str): ...
    async def release(self): ...

class ArduinoPort(Protocol):
    async def send_state(self, state: str): ...
    def set_wake_callback(self, callback): ...
    async def close(self): ...

class PerceptionPort(Protocol):
    async def face_recognize(self, frame) -> Optional[dict]: ...
    async def face_enroll(self, frame, name: str) -> bool: ...
    async def analyze_scene(self, frame) -> str: ...

class MemoryPort(Protocol):
    async def log_interaction(self, **kwargs): ...
    async def forget_user(self, name: str): ...
    async def get_relationship(self, name: str) -> dict: ...
    async def get_full_context(self, name: Optional[str]) -> dict: ...

class BrainPort(Protocol):
    async def generate_response(self, utterance: str, **ctx) -> str: ...

class VoicePort(Protocol):
    async def synthesize(self, text: str): ...
    async def play(self, audio): ...

@dataclass
class PortBundle:
    camera:     CameraPort
    mic:        MicPort
    speaker:    SpeakerPort
    orb:        OrbPort
    perception: PerceptionPort
    memory:     MemoryPort
    brain:      BrainPort
    voice:      VoicePort
    arduino:    Optional[ArduinoPort] = None

    @classmethod
    async def create(cls, config: dict) -> "PortBundle":
        profile = config.get("profile", "laptop")
        adapter_pkg = f"adapters.{profile}"

        cam = _load(adapter_pkg, "camera",  config)
        mic = _load(adapter_pkg, "mic",     config)
        spk = _load(adapter_pkg, "speaker", config)
        orb = _load(adapter_pkg, "orb",     config)

        # Start browser orb adapter websocket if supported
        if hasattr(orb, "start"):
            await orb.start()

        # Load optional Arduino UNO R4 hardware companion
        arduino = None
        try:
            arduino = _load(adapter_pkg, "arduino_bridge", config)
            if hasattr(arduino, "start"):
                await arduino.start()
            if hasattr(arduino, "set_wake_callback") and hasattr(mic, "trigger_wake_word"):
                arduino.set_wake_callback(mic.trigger_wake_word)
        except Exception as e:
            logger.debug(f"Arduino adapter optional load note: {e}")

        from perception.face_recognize import FaceRecognizer
        from perception.face_enroll    import FaceEnroller
        from perception.scene_analyzer import SceneAnalyzer
        from memory.db                 import MemoryDB
        from brain.llm                 import LLM
        from voice.tts                 import TTS

        perception = _PerceptionBundle(FaceRecognizer(config), FaceEnroller(config), SceneAnalyzer(config))
        memory     = MemoryDB(config)
        brain      = LLM(config)
        voice      = TTS(spk, config)

        return cls(
            camera=cam,
            mic=mic,
            speaker=spk,
            orb=orb,
            perception=perception,
            memory=memory,
            brain=brain,
            voice=voice,
            arduino=arduino,
        )

    async def shutdown(self):
        for port in [self.camera, self.mic, self.speaker, self.orb]:
            try:
                await port.release()
            except Exception:
                pass
        if self.arduino and hasattr(self.arduino, "close"):
            try:
                await self.arduino.close()
            except Exception:
                pass

def _load(pkg: str, module: str, config: dict):
    mod = importlib.import_module(f"{pkg}.{module}")
    return mod.create(config)

class _PerceptionBundle:
    def __init__(self, recognizer, enroller, analyzer):
        self._rec = recognizer
        self._enr = enroller
        self._ana = analyzer
    async def face_recognize(self, frame): return await self._rec.recognize(frame)
    async def face_enroll(self, frame, name): return await self._enr.enroll(frame, name)
    async def analyze_scene(self, frame): return await self._ana.analyze(frame)
