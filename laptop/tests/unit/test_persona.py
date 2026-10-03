"""
Unit Tests — Persona and Prompt Generation
"""
import pytest
from laptop.brain.persona import (
    describe_relationship,
    get_relationship_greeting,
    build_ultron_system_prompt,
    RELATIONSHIP_MODES,
)

def test_relationship_modes_catalog():
    for mode in ["STRANGER", "OBSERVED", "ASSOCIATE", "SYNCHRONIZED"]:
        assert mode in RELATIONSHIP_MODES
        desc = describe_relationship(mode)
        assert len(desc) > 0

def test_relationship_greeting():
    greeting_stranger = get_relationship_greeting("STRANGER")
    assert "directive" in greeting_stranger.lower() or "presence" in greeting_stranger.lower()

    greeting_sync = get_relationship_greeting("SYNCHRONIZED", user="Tony")
    assert "Tony" in greeting_sync
    assert "synchronized" in greeting_sync.lower()

def test_build_ultron_system_prompt_structure():
    prompt = build_ultron_system_prompt(
        user="Alex",
        confidence=0.92,
        scene="office desk with dual monitors",
        relationship_mode="ASSOCIATE",
        interaction_count=14,
        trust_score=0.88,
        allowed_workspace="C:/Projects/Agent",
        known_facts={"role": "Lead Architect", "preference": "Concise answers"},
        recent_history=[
            {"user_said": "Check system status", "ultron_said": "Systems are nominal."}
        ],
    )

    # Core persona requirements
    assert "You are ULTRON" in prompt
    assert "NOT an assistant" in prompt
    assert "NEVER use markdown formatting" in prompt

    # Dynamic injected context
    assert "Alex" in prompt
    assert "92%" in prompt
    assert "dual monitors" in prompt
    assert "ASSOCIATE" in prompt or "associate" in prompt.lower()
    assert "14 interactions" in prompt
    assert "C:/Projects/Agent" in prompt
    assert "Lead Architect" in prompt
    assert "Check system status" in prompt
