"""
Unit Tests — ElevenLabs TTS Voice Pipeline
"""
import pytest
import asyncio
from laptop.voice.tts import TTS, DEFAULT_VOICE_ID

def test_tts_initialization():
    config = {
        "voice": {
            "engine": "elevenlabs",
            "voice_id": "5vpfPL62TWuqhC30bkVm",
            "server_url": "http://127.0.0.1:19998",  # dummy port
        }
    }
    tts = TTS(speaker=None, config=config)
    assert tts.voice_id == DEFAULT_VOICE_ID
    assert tts.is_speaking is False
    assert tts.current_amplitude == 0.0

def test_tts_amplitude_calculation():
    tts = TTS(speaker=None, config={})

    # Empty chunk -> 0.0
    assert tts._calculate_chunk_amplitude(b"") == 0.0

    # Silent PCM (128 centered)
    silent_chunk = bytes([128] * 64)
    assert tts._calculate_chunk_amplitude(silent_chunk) == 0.0

    # Active audio wave
    active_chunk = bytes([0, 255, 0, 255] * 16)
    amp = tts._calculate_chunk_amplitude(active_chunk)
    assert 0.0 < amp <= 1.0

def test_tts_graceful_stream_handling_on_offline_server():
    async def _test():
        config = {
            "voice": {
                "server_url": "http://127.0.0.1:19998",  # guaranteed offline
            }
        }
        tts = TTS(speaker=None, config=config)
        # Should not raise exception; falls back gracefully
        result = await tts.synthesize_stream("Testing synthesis stream.")
        assert result is None
        assert tts.is_speaking is False
        assert tts.current_amplitude == 0.0
        await tts.close()

    asyncio.run(_test())
