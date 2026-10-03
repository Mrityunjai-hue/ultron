"""
Unit Tests — Autonomous Orchestrator and Authoritative Event Dispatch
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from laptop.core.orchestrator import UltronOrchestrator, State
from laptop.core.states import ActivityState

@pytest.fixture
def mock_ports():
    ports = MagicMock()
    ports.camera = MagicMock()
    ports.camera.capture_frame = AsyncMock(return_value=None)
    ports.mic = MagicMock()
    ports.mic.wake_word_detected = AsyncMock(return_value=False)
    ports.mic.capture_utterance = AsyncMock(return_value="")
    ports.speaker = MagicMock()
    ports.orb = MagicMock()
    ports.orb.emit_authoritative_event = AsyncMock()
    ports.orb.set_state = AsyncMock()
    ports.orb.set_gaze = AsyncMock()
    ports.orb.dispatch_tts = AsyncMock()
    ports.perception = MagicMock()
    ports.perception.face_recognize = AsyncMock(return_value=None)
    ports.perception.analyze_scene = AsyncMock(return_value="")
    ports.memory = MagicMock()
    ports.memory.get_full_context = AsyncMock(return_value={
        "relationship_mode": "STRANGER",
        "interaction_count": 1,
        "trust_score": 0.0,
        "last_seen": "never",
        "recent_history": [],
        "facts": {},
    })
    ports.memory.log_interaction = AsyncMock()
    ports.brain = MagicMock()
    
    async def _mock_generate_response(*args, **kwargs):
        utterance = kwargs.get("utterance", "")
        tool_executor = kwargs.get("tool_executor")
        if "what time is it" in utterance.lower() and tool_executor:
            res = await tool_executor("get_current_time", {})
            return f"The time is {res.get('time', '12:00:00')}."
        if "search files" in utterance.lower() and tool_executor:
            res = await tool_executor("search_files", {"pattern": "*.txt"})
            matches = res.get("matches", [])
            return f"Found {len(matches)} matching files: {', '.join(m['path'] for m in matches)}"
        return "Calculated response."

    ports.brain.generate_response = AsyncMock(side_effect=_mock_generate_response)
    return ports

def test_orchestrator_transition_emits_authoritative_event(mock_ports):
    async def _test():
        orch = UltronOrchestrator(mock_ports, config={})
        await orch._transition(State.LISTEN)

        assert orch.state == State.LISTEN
        assert mock_ports.orb.emit_authoritative_event.called

        # Verify event content
        event = mock_ports.orb.emit_authoritative_event.call_args[0][0]
        assert event.activity == ActivityState.LISTENING

    asyncio.run(_test())

def test_orchestrator_search_files_execution(mock_ports, tmp_path):
    async def _test():
        orch = UltronOrchestrator(mock_ports, config={})
        orch.tools.file_ops.workspace = tmp_path
        (tmp_path / "scan.txt").write_text("sample", encoding="utf-8")

        orch.ctx.utterance = "search files *.txt"
        next_state = await orch._handle_think()

        assert next_state == State.SPEAK
        assert "scan.txt" in orch.ctx.response
        assert orch.ctx.operation == "search_files"

    asyncio.run(_test())

def test_orchestrator_pending_confirmation_resolution(mock_ports):
    async def _test():
        orch = UltronOrchestrator(mock_ports, config={})

        # Request confirmation
        req = orch.tools.confirm_manager.request_confirmation(
            tool_name="delete_file",
            description="Delete file",
            arguments={"path": "old.txt"},
        )

        orch.ctx.utterance = "yes, confirm"
        next_state = await orch._handle_think()

        assert next_state == State.SPEAK
        assert "confirmed" in orch.ctx.response.lower()
        # Pending request resolved
        assert orch.tools.confirm_manager.get_pending(req.id) is None

    asyncio.run(_test())

def test_orchestrator_get_current_time_execution(mock_ports):
    async def _test():
        orch = UltronOrchestrator(mock_ports, config={})
        orch.ctx.utterance = "what time is it"
        next_state = await orch._handle_think()

        assert next_state == State.SPEAK
        assert "The time is" in orch.ctx.response
        assert orch.ctx.operation == "get_current_time"

    asyncio.run(_test())

def test_orchestrator_memory_fact_recording(mock_ports):
    async def _test():
        orch = UltronOrchestrator(mock_ports, config={})
        orch.ports.memory.remember_fact = AsyncMock()
        orch.ctx.current_user = "Tony"
        orch.ctx.utterance = "remember that project is jarvis"
        next_state = await orch._handle_think()

        assert next_state == State.SPEAK
        assert "Catalogued" in orch.ctx.response
        orch.ports.memory.remember_fact.assert_called_with("Tony", "project", "jarvis")

    asyncio.run(_test())

