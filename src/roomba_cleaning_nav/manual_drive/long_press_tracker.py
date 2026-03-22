"""1-second long-press button timing tracker.

Pure functions — no side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from roomba_cleaning_nav.manual_drive.config import MODE_LONG_PRESS_S


@dataclass
class LongPressState:
    """Tracks a button-press start time and completion."""
    button_id: str = ""
    press_start_time: Optional[float] = None  # monotonic seconds
    completed: bool = False  # True once the required duration is met


def start_press(state: LongPressState, button_id: str, now: float) -> None:
    """Record the start of a button press."""
    if state.press_start_time is None or state.button_id != button_id:
        state.button_id = button_id
        state.press_start_time = now
        state.completed = False


def release_press(state: LongPressState) -> None:
    """Record a button release — resets tracking."""
    state.press_start_time = None
    state.completed = False


def check_long_press(
    state: LongPressState,
    now: float,
    required_s: float = MODE_LONG_PRESS_S,
) -> bool:
    """Return True if the button has been held for at least required_s.

    Marks state.completed=True on first trigger to avoid double-fires.
    """
    if state.press_start_time is None:
        return False
    if state.completed:
        return False
    elapsed = now - state.press_start_time
    if elapsed >= required_s:
        state.completed = True
        return True
    return False


def elapsed_since_press(state: LongPressState, now: float) -> Optional[float]:
    """Return elapsed seconds since press started, or None if not pressed."""
    if state.press_start_time is None:
        return None
    return now - state.press_start_time
