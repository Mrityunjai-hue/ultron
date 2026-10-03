"""
Unit Tests — Desktop Notch Launcher
"""
import pytest
from unittest.mock import MagicMock
from launcher import (
    get_screen_dimensions,
    is_server_running,
    NotchApi,
    STANDBY_WIDTH,
    STANDBY_HEIGHT,
    EXPANDED_WIDTH,
    EXPANDED_HEIGHT,
)

def test_screen_dimensions_detection():
    w, h = get_screen_dimensions()
    assert isinstance(w, int) and w > 0
    assert isinstance(h, int) and h > 0

def test_is_server_running_on_active_server():
    # Tests port 8080 or returns bool without error
    status = is_server_running(8080)
    assert isinstance(status, bool)

def test_notch_api_expand_and_collapse():
    import launcher
    mock_window = MagicMock()
    launcher._active_window = mock_window
    api = NotchApi()

    api.expand()
    assert mock_window.resize.called
    assert mock_window.resize.call_args[0] == (EXPANDED_WIDTH, EXPANDED_HEIGHT)

    api.collapse()
    assert mock_window.resize.call_args[0] == (STANDBY_WIDTH, STANDBY_HEIGHT)

