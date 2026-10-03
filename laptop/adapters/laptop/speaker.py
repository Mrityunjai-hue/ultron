"""SoundDevice speaker adapter."""
import asyncio, logging
logger = logging.getLogger("ultron.adapters.laptop.speaker")

class SoundDeviceSpeaker:
    def __init__(self, config: dict): self.config = config
    async def play(self, audio_data):
        if isinstance(audio_data, bytes):
            import sounddevice as sd, soundfile as sf, io
            data, sr = sf.read(io.BytesIO(audio_data))
            await asyncio.to_thread(sd.play, data, sr)
            await asyncio.to_thread(sd.wait)
    async def release(self): pass

def create(config): return SoundDeviceSpeaker(config)
