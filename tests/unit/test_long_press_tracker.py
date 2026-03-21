"""Unit tests for long_press_tracker: 1-second hold detection."""
import pytest

from roomba_cleaning_nav.manual_drive.long_press_tracker import (
    LongPressState,
    check_long_press,
    elapsed_since_press,
    release_press,
    start_press,
)
from roomba_cleaning_nav.manual_drive.config import MODE_LONG_PRESS_S


class TestLongPressTracker:
    def test_no_press_returns_none_elapsed(self):
        state = LongPressState()
        assert elapsed_since_press(state, now=100.0) is None

    def test_check_before_threshold_returns_false(self):
        state = LongPressState()
        start_press(state, "mode", now=0.0)
        result = check_long_press(state, now=MODE_LONG_PRESS_S - 0.01)
        assert result is False

    def test_check_at_threshold_returns_true(self):
        state = LongPressState()
        start_press(state, "mode", now=0.0)
        result = check_long_press(state, now=MODE_LONG_PRESS_S)
        assert result is True

    def test_check_after_threshold_returns_true(self):
        state = LongPressState()
        start_press(state, "mode", now=0.0)
        result = check_long_press(state, now=MODE_LONG_PRESS_S + 0.5)
        assert result is True

    def test_long_press_fires_only_once(self):
        state = LongPressState()
        start_press(state, "mode", now=0.0)
        first = check_long_press(state, now=MODE_LONG_PRESS_S)
        second = check_long_press(state, now=MODE_LONG_PRESS_S + 0.1)
        assert first is True
        assert second is False  # completed flag prevents double-fire

    def test_release_resets_state(self):
        state = LongPressState()
        start_press(state, "mode", now=0.0)
        release_press(state)
        assert state.press_start_time is None
        assert not state.completed

    def test_after_release_check_returns_false(self):
        state = LongPressState()
        start_press(state, "mode", now=0.0)
        release_press(state)
        result = check_long_press(state, now=MODE_LONG_PRESS_S + 1.0)
        assert result is False

    def test_elapsed_returns_correct_duration(self):
        state = LongPressState()
        start_press(state, "mode", now=10.0)
        elapsed = elapsed_since_press(state, now=10.5)
        assert abs(elapsed - 0.5) < 1e-9

    def test_new_button_resets_timer(self):
        state = LongPressState()
        start_press(state, "mode", now=0.0)
        start_press(state, "other_button", now=5.0)
        # elapsed should be relative to new press
        elapsed = elapsed_since_press(state, now=5.3)
        assert abs(elapsed - 0.3) < 1e-6

    def test_custom_required_duration(self):
        state = LongPressState()
        start_press(state, "btn", now=0.0)
        assert not check_long_press(state, now=0.4, required_s=0.5)
        assert check_long_press(state, now=0.5, required_s=0.5)
