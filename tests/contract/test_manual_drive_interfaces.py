"""Contract tests for manual drive published topic schemas."""
import json
import pytest

from roomba_cleaning_nav.manual_drive.adapters.feedback_adapter import FeedbackAdapter
from roomba_cleaning_nav.manual_drive.models import ManualDriveState, SafetyFault
from roomba_cleaning_nav.manual_drive.status_formatter import (
    format_diagnostics_keys,
    format_status,
)


REQUIRED_DIAGNOSTICS_KEYS = {
    "joycon_link_age_ms",
    "manual_mode_active",
    "cleaning_enabled",
    "last_fault",
    "rumble_available",
}

ALLOWED_MODES = {"idle", "manual_active", "safety_stopped", "fault"}
ALLOWED_CLEANING = {"on", "off"}
ALLOWED_FAULTS = {"none", "link_loss", "cliff", "e_stop", "serial_fault"}


class TestStatusTopicContract:
    def test_status_json_has_required_fields(self):
        published = []
        adapter = FeedbackAdapter(status_pub=published.append)
        state = ManualDriveState()
        adapter.publish_status(state)
        data = json.loads(published[0])
        for field in ("mode", "cleaning", "fault", "estop_latched", "link_ok", "timestamp"):
            assert field in data

    def test_mode_values_are_valid(self):
        for fault in SafetyFault:
            state = ManualDriveState()
            status = format_status(state)
            assert status.mode in ALLOWED_MODES

    def test_cleaning_values_are_valid(self):
        state = ManualDriveState()
        status = format_status(state)
        assert status.cleaning in ALLOWED_CLEANING

    def test_fault_values_are_valid(self):
        for fault in SafetyFault:
            state = ManualDriveState()
            state.fault = fault
            status = format_status(state)
            assert status.fault in ALLOWED_FAULTS


class TestDiagnosticsContract:
    def test_all_required_keys_present(self):
        state = ManualDriveState()
        keys = format_diagnostics_keys(state, link_age_ms=100.0)
        assert REQUIRED_DIAGNOSTICS_KEYS.issubset(set(keys.keys()))

    def test_link_age_is_numeric_string(self):
        state = ManualDriveState()
        keys = format_diagnostics_keys(state, link_age_ms=123.45)
        float(keys["joycon_link_age_ms"])  # should not raise

    def test_bool_fields_are_lowercase_string(self):
        state = ManualDriveState()
        keys = format_diagnostics_keys(state, link_age_ms=0.0)
        assert keys["manual_mode_active"] in ("true", "false")
        assert keys["cleaning_enabled"] in ("true", "false")
        assert keys["rumble_available"] in ("true", "false")
