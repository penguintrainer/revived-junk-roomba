"""Unit tests for status_formatter: payload serialization."""
import json
import pytest

from roomba_cleaning_nav.manual_drive.status_formatter import (
    format_diagnostics_keys,
    format_status,
    status_to_dict,
    status_to_json,
)
from roomba_cleaning_nav.manual_drive.models import (
    CleaningState,
    ForbiddenZoneOverride,
    ManualDriveMode,
    ManualDriveState,
    SafetyFault,
)


class TestFormatStatus:
    def test_idle_state_fields(self):
        state = ManualDriveState()
        status = format_status(state)
        assert status.mode == "idle"
        assert status.cleaning == "off"
        assert status.fault == "none"
        assert not status.estop_latched
        assert status.link_ok is True

    def test_active_manual_mode(self):
        state = ManualDriveState()
        state.enter_manual_mode()
        status = format_status(state)
        assert status.mode == "manual_active"
        assert status.forbidden_zone_override == "bypassed"

    def test_cleaning_on_reflected(self):
        state = ManualDriveState()
        state.enter_manual_mode()
        state.cleaning = CleaningState.ON
        status = format_status(state)
        assert status.cleaning == "on"

    def test_fault_reflected(self):
        state = ManualDriveState()
        state.apply_safety_stop(SafetyFault.CLIFF)
        status = format_status(state)
        assert status.fault == "cliff"


class TestStatusToJson:
    def test_serializes_to_valid_json(self):
        state = ManualDriveState()
        status = format_status(state)
        payload = status_to_json(status)
        data = json.loads(payload)
        assert "mode" in data
        assert "cleaning" in data
        assert "fault" in data
        assert "estop_latched" in data
        assert "timestamp" in data

    def test_active_mode_in_json(self):
        state = ManualDriveState()
        state.enter_manual_mode()
        status = format_status(state)
        data = json.loads(status_to_json(status))
        assert data["mode"] == "manual_active"


class TestFormatDiagnosticsKeys:
    def test_required_keys_present(self):
        state = ManualDriveState()
        keys = format_diagnostics_keys(state, link_age_ms=150.0)
        assert "joycon_link_age_ms" in keys
        assert "manual_mode_active" in keys
        assert "cleaning_enabled" in keys
        assert "last_fault" in keys
        assert "rumble_available" in keys

    def test_link_age_formatted(self):
        state = ManualDriveState()
        keys = format_diagnostics_keys(state, link_age_ms=250.7)
        assert keys["joycon_link_age_ms"] == "251"

    def test_manual_mode_active_when_active(self):
        state = ManualDriveState()
        state.enter_manual_mode()
        keys = format_diagnostics_keys(state, link_age_ms=0.0)
        assert keys["manual_mode_active"] == "true"

    def test_cleaning_enabled_when_on(self):
        state = ManualDriveState()
        state.enter_manual_mode()
        state.cleaning = CleaningState.ON
        keys = format_diagnostics_keys(state, link_age_ms=0.0)
        assert keys["cleaning_enabled"] == "true"
