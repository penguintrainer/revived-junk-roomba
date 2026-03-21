"""Contract tests for random cleaning published topic schemas."""
import pytest

from roomba_cleaning_nav.random_cleaning.adapters.telemetry_publisher import (
    TelemetryPublisher,
)
from roomba_cleaning_nav.random_cleaning.models import (
    EventSeverity,
    HandledAction,
    RobotMode,
    RobotRuntimeState,
    SafetyEvent,
    SafetyEventType,
)


ALLOWED_STATES = {"idle", "cleaning_forward", "cleaning_turn", "safety_stopped", "fault"}


class TestStateTopicContract:
    def test_all_robot_modes_produce_valid_state_strings(self):
        published = []
        pub = TelemetryPublisher(state_pub=published.append)
        for mode in RobotMode:
            state = RobotRuntimeState(mode=mode)
            pub.publish_state(state)
        for msg in published:
            assert msg in ALLOWED_STATES

    def test_state_string_is_exact_enum_value(self):
        published = []
        pub = TelemetryPublisher(state_pub=published.append)
        state = RobotRuntimeState(mode=RobotMode.CLEANING_FORWARD)
        pub.publish_state(state)
        assert published[0] == "cleaning_forward"


class TestSafetyEventTopicContract:
    def _collect_event(self, event_type=SafetyEventType.E_STOP):
        published = []
        pub = TelemetryPublisher(safety_event_pub=published.append)
        event = SafetyEvent(
            event_type=event_type,
            severity=EventSeverity.ERROR,
            handled_action=HandledAction.STOP,
        )
        pub.publish_safety_event(event)
        return published[0]

    def test_payload_has_four_pipe_segments(self):
        payload = self._collect_event()
        parts = payload.split("|")
        assert len(parts) == 4

    def test_first_segment_is_event_type(self):
        payload = self._collect_event(SafetyEventType.SENSOR_DROPOUT)
        parsed = TelemetryPublisher.parse_safety_event_payload(payload)
        assert parsed["event_type"] == "sensor_dropout"

    def test_second_segment_is_severity(self):
        payload = self._collect_event()
        parsed = TelemetryPublisher.parse_safety_event_payload(payload)
        assert parsed["severity"] == "error"

    def test_third_segment_is_timestamp(self):
        payload = self._collect_event()
        parsed = TelemetryPublisher.parse_safety_event_payload(payload)
        # Should be parseable ISO timestamp
        from datetime import datetime
        dt = datetime.fromisoformat(parsed["timestamp"])
        assert dt is not None

    def test_parse_invalid_raises(self):
        with pytest.raises(ValueError):
            TelemetryPublisher.parse_safety_event_payload("bad|payload")

    def test_all_event_types_produce_valid_payloads(self):
        for event_type in SafetyEventType:
            payload = self._collect_event(event_type)
            parsed = TelemetryPublisher.parse_safety_event_payload(payload)
            assert parsed["event_type"] == event_type.value
