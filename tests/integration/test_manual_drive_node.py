"""Integration tests for manual drive node (headless — no ROS2 required)."""
import pytest

from roomba_cleaning_nav.manual_drive.models import (
    CleaningState,
    DirectionInput,
    ManualDriveMode,
    ManualDriveState,
    SafetyFault,
)
from roomba_cleaning_nav.manual_drive.safety_watchdog import SafetyLatch
from roomba_cleaning_nav.manual_drive.command_mapper import (
    direction_to_velocity,
    resolve_direction,
)


class TestManualDriveIntegration:
    """Integration-level behavioral tests for manual drive state."""

    def _state(self) -> ManualDriveState:
        return ManualDriveState()

    def test_enter_and_exit_manual_mode(self):
        state = self._state()
        assert state.mode == ManualDriveMode.IDLE

        state.enter_manual_mode()
        assert state.mode == ManualDriveMode.MANUAL_ACTIVE

        state.exit_manual_mode()
        assert state.mode == ManualDriveMode.IDLE

    def test_cleaning_disabled_on_exit(self):
        state = self._state()
        state.enter_manual_mode()
        state.cleaning = CleaningState.ON
        state.exit_manual_mode()
        assert state.cleaning == CleaningState.OFF

    def test_forbidden_zone_override_on_enter(self):
        from roomba_cleaning_nav.manual_drive.models import ForbiddenZoneOverride
        state = self._state()
        state.enter_manual_mode()
        assert state.forbidden_zone_override == ForbiddenZoneOverride.BYPASSED

    def test_forbidden_zone_restored_on_exit(self):
        from roomba_cleaning_nav.manual_drive.models import ForbiddenZoneOverride
        state = self._state()
        state.enter_manual_mode()
        state.exit_manual_mode()
        assert state.forbidden_zone_override == ForbiddenZoneOverride.ENFORCED

    def test_safety_stop_exits_manual_mode(self):
        state = self._state()
        state.enter_manual_mode()
        state.apply_safety_stop(SafetyFault.CLIFF)
        assert state.mode == ManualDriveMode.SAFETY_STOPPED
        assert state.cleaning == CleaningState.OFF
        assert state.safety_latched

    def test_estop_via_latch(self):
        latch = SafetyLatch()
        latch.latch(SafetyFault.E_STOP)
        assert latch.latched

        latch.clear()
        assert not latch.latched

    def test_direction_to_velocity_forward(self):
        lin, ang = direction_to_velocity(DirectionInput.FORWARD)
        assert lin > 0
        assert ang == 0.0

    def test_direction_to_velocity_backward(self):
        lin, ang = direction_to_velocity(DirectionInput.BACKWARD)
        assert lin < 0
        assert ang == 0.0

    def test_conflict_resolution_forward_backward(self):
        result = resolve_direction([DirectionInput.FORWARD, DirectionInput.BACKWARD])
        assert result == DirectionInput.NONE

    def test_cleaning_toggle_when_active(self):
        state = self._state()
        state.enter_manual_mode()
        assert state.cleaning == CleaningState.OFF
        # toggle on
        if state.is_active():
            state.cleaning = CleaningState.ON
        assert state.cleaning == CleaningState.ON
        # toggle off
        if state.is_active():
            state.cleaning = CleaningState.OFF
        assert state.cleaning == CleaningState.OFF


class TestForbiddenZoneOverrideIntegration:
    def test_bypass_active_in_manual_mode(self):
        from roomba_cleaning_nav.manual_drive.models import ForbiddenZoneOverride
        state = ManualDriveState()
        state.enter_manual_mode()
        assert state.forbidden_zone_override == ForbiddenZoneOverride.BYPASSED

    def test_restore_on_mode_exit(self):
        from roomba_cleaning_nav.manual_drive.models import ForbiddenZoneOverride
        state = ManualDriveState()
        state.enter_manual_mode()
        state.exit_manual_mode()
        assert state.forbidden_zone_override == ForbiddenZoneOverride.ENFORCED
