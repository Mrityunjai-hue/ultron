"""
Unit Tests — MoodEngine
"""
import pytest
from laptop.core.states import ActivityState, MoodState
from laptop.brain.mood import MoodEngine

def test_mood_engine_default_calm():
    engine = MoodEngine()
    mood = engine.evaluate(activity=ActivityState.IDLE)
    assert mood == MoodState.CALM

def test_mood_engine_error_yields_warning():
    engine = MoodEngine()
    assert engine.evaluate(activity=ActivityState.ERROR) == MoodState.WARNING
    assert engine.evaluate(activity=ActivityState.OFFLINE) == MoodState.WARNING
    assert engine.evaluate(activity=ActivityState.IDLE, has_error=True) == MoodState.WARNING

def test_mood_engine_requires_confirm_yields_concerned():
    engine = MoodEngine()
    mood = engine.evaluate(activity=ActivityState.EXECUTING, requires_confirm=True)
    assert mood == MoodState.CONCERNED

def test_mood_engine_activity_mapping():
    engine = MoodEngine()
    assert engine.evaluate(activity=ActivityState.EXECUTING) == MoodState.FOCUSED
    assert engine.evaluate(activity=ActivityState.LISTENING) == MoodState.ATTENTIVE

def test_mood_engine_semantic_keywords():
    engine = MoodEngine()
    # Destructive -> CONCERNED
    assert engine.evaluate(activity=ActivityState.IDLE, utterance="Please delete the old files") == MoodState.CONCERNED
    # Inquisitive -> CURIOUS
    assert engine.evaluate(activity=ActivityState.IDLE, utterance="Why does the cosmos expand?") == MoodState.CURIOUS
    # Analytical -> FOCUSED
    assert engine.evaluate(activity=ActivityState.IDLE, utterance="Compute the trajectory matrix") == MoodState.FOCUSED
