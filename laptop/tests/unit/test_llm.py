"""
Unit Tests — Local-First LLM Engine and Offline Handling
"""
import pytest
import os
from laptop.brain.llm import LLM, OFFLINE_NOTICE
from laptop.core.states import ActivityState

@pytest.fixture
def base_config():
    return {
        "brain": {
            "provider": "ollama",
            "model": "hermes4:14b",
            "ollama_url": "http://127.0.0.1:19999",  # Non-existent port to guarantee offline
            "max_tokens": 128,
            "temperature": 0.7,
        }
    }

def test_llm_defaults_to_local_first(base_config):
    llm = LLM(base_config)
    assert llm.provider == "ollama"
    assert llm.model == "hermes4:14b"
    assert llm.base_url == "http://127.0.0.1:19999"

def test_llm_offline_detection(base_config):
    import asyncio

    async def _run():
        llm = LLM(base_config)

        # Availability check returns False on offline port
        available = await llm.check_availability()
        assert available is False
        assert llm.is_offline is True

        # Generation triggers honest OFFLINE state and returns OFFLINE_NOTICE
        dispatched_sentences = []
        def on_sentence(clause: str):
            dispatched_sentences.append(clause)

        resp = await llm.generate_response(
            utterance="Explain quantum computing.",
            on_sentence=on_sentence,
        )

        assert resp == OFFLINE_NOTICE
        assert llm.last_state == ActivityState.OFFLINE
        assert OFFLINE_NOTICE in dispatched_sentences
        await llm.close()

    asyncio.run(_run())

def test_clean_speech_clause_removes_markdown():
    llm = LLM({"brain": {}})
    raw = "**Warning:** `system` status is *nominal*. # Note\n- item 1\n- item 2"
    cleaned = llm._clean_speech_clause(raw)
    assert "*" not in cleaned
    assert "`" not in cleaned
    assert "#" not in cleaned
    assert "Warning: system status is nominal. Note item 1 item 2" in cleaned

def test_explicit_cloud_provider_opt_in():
    config = {
        "brain": {
            "provider": "gemini",
            "model": "gemini-1.5-flash",
        }
    }
    llm = LLM(config)
    assert llm.provider == "gemini"
