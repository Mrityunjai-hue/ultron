"""
Unit Tests — Canonical States and Authoritative Event Model
"""
import pytest
from pydantic import ValidationError
from laptop.core.states import ActivityState, MoodState, AuthoritativeEvent

def test_canonical_activity_states():
    expected_states = {
        "IDLE", "LISTENING", "THINKING", "EXECUTING",
        "RESPONDING", "ERROR", "OFFLINE", "RECONNECTING"
    }
    actual_states = {s.value for s in ActivityState}
    assert actual_states == expected_states

def test_canonical_mood_states():
    expected_moods = {"CALM", "ATTENTIVE", "FOCUSED", "CURIOUS", "CONCERNED", "WARNING"}
    actual_moods = {m.value for m in MoodState}
    assert actual_moods == expected_moods

def test_authoritative_event_defaults():
    event = AuthoritativeEvent(activity=ActivityState.IDLE)
    assert event.activity == ActivityState.IDLE
    assert event.mood == MoodState.CALM
    assert event.operation == "none"
    assert event.attention == 0.5
    assert event.gaze_x == 0.0
    assert event.gaze_y == 0.0
    assert event.voice_amplitude == 0.0
    assert event.progress is None
    assert event.error is None

def test_authoritative_event_validation_bounds():
    # Valid bounds
    event = AuthoritativeEvent(
        activity=ActivityState.EXECUTING,
        attention=1.0,
        gaze_x=-1.0,
        gaze_y=1.0,
        voice_amplitude=0.8,
    )
    assert event.attention == 1.0

    # Out of bounds attention (>1.0)
    with pytest.raises(ValidationError):
        AuthoritativeEvent(activity=ActivityState.IDLE, attention=1.5)

    # Out of bounds gaze_x (< -1.0)
    with pytest.raises(ValidationError):
        AuthoritativeEvent(activity=ActivityState.IDLE, gaze_x=-1.5)

def test_to_legacy_ui_state_mapping():
    # Idle
    assert AuthoritativeEvent(activity=ActivityState.IDLE).to_legacy_ui_state() == "idle"
    # Listening
    assert AuthoritativeEvent(activity=ActivityState.LISTENING).to_legacy_ui_state() == "listening"
    # Thinking
    assert AuthoritativeEvent(activity=ActivityState.THINKING).to_legacy_ui_state() == "thinking"
    # Executing search vs generic tool
    search_event = AuthoritativeEvent(activity=ActivityState.EXECUTING, operation="search_files")
    assert search_event.to_legacy_ui_state() == "searching"
    shell_event = AuthoritativeEvent(activity=ActivityState.EXECUTING, operation="shell")
    assert shell_event.to_legacy_ui_state() == "processing"
    # Responding
    assert AuthoritativeEvent(activity=ActivityState.RESPONDING).to_legacy_ui_state() == "speaking"
    # Error & Offline
    assert AuthoritativeEvent(activity=ActivityState.ERROR).to_legacy_ui_state() == "error"
    assert AuthoritativeEvent(activity=ActivityState.OFFLINE).to_legacy_ui_state() == "warning"

def test_to_rive_inputs_mapping():
    event = AuthoritativeEvent(
        activity=ActivityState.EXECUTING,
        operation="search_files",
        mood=MoodState.FOCUSED,
        gaze_x=0.45,
        gaze_y=-0.2,
        attention=0.9,
        voice_amplitude=0.3,
    )
    rive_inputs = event.to_rive_inputs()
    assert rive_inputs["activity"] == 3       # EXECUTING = 3
    assert rive_inputs["operationId"] == 1    # search_files = 1
    assert rive_inputs["moodId"] == 2         # FOCUSED = 2
    assert rive_inputs["gazeX"] == 0.45
    assert rive_inputs["gazeY"] == -0.2
    assert rive_inputs["attention"] == 0.9
    assert rive_inputs["voiceAmplitude"] == 0.3
