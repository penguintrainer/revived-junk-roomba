"""Unit tests for persistence: JSON Lines helpers."""
import json
import tempfile
from pathlib import Path

import pytest

from roomba_cleaning_nav.random_cleaning.persistence import (
    load_jsonl,
    persist_motion_decision,
    persist_safety_event,
    persist_session,
)
from roomba_cleaning_nav.random_cleaning.models import (
    CleaningSession,
    EndReason,
    EventSeverity,
    HandledAction,
    MotionDecision,
    MotionPhase,
    MotionTrigger,
    RobotMode,
    SafetyEvent,
    SafetyEventType,
)


@pytest.fixture()
def tmp_log_dir(tmp_path: Path) -> Path:
    return tmp_path


class TestPersistSession:
    def test_session_persisted_as_jsonl(self, tmp_log_dir: Path):
        session = CleaningSession()
        persist_session(session, log_dir=tmp_log_dir)
        records = load_jsonl(tmp_log_dir / "sessions.jsonl")
        assert len(records) == 1
        assert records[0]["session_id"] == session.session_id

    def test_multiple_sessions_appended(self, tmp_log_dir: Path):
        for _ in range(3):
            persist_session(CleaningSession(), log_dir=tmp_log_dir)
        records = load_jsonl(tmp_log_dir / "sessions.jsonl")
        assert len(records) == 3

    def test_ended_session_has_end_reason(self, tmp_log_dir: Path):
        session = CleaningSession()
        session.end(EndReason.USER_STOP, RobotMode.IDLE)
        persist_session(session, log_dir=tmp_log_dir)
        records = load_jsonl(tmp_log_dir / "sessions.jsonl")
        assert records[0]["end_reason"] == "user_stop"
        assert records[0]["ended_at"] is not None


class TestPersistSafetyEvent:
    def test_event_persisted(self, tmp_log_dir: Path):
        event = SafetyEvent(
            event_type=SafetyEventType.E_STOP,
            severity=EventSeverity.ERROR,
            handled_action=HandledAction.STOP,
        )
        persist_safety_event(event, log_dir=tmp_log_dir)
        records = load_jsonl(tmp_log_dir / "safety_events.jsonl")
        assert len(records) == 1
        assert records[0]["event_type"] == "e_stop"
        assert records[0]["severity"] == "error"

    def test_resolved_event_has_resolved_at(self, tmp_log_dir: Path):
        event = SafetyEvent(event_type=SafetyEventType.SENSOR_DROPOUT)
        event.resolve()
        persist_safety_event(event, log_dir=tmp_log_dir)
        records = load_jsonl(tmp_log_dir / "safety_events.jsonl")
        assert records[0]["resolved"] is True
        assert records[0]["resolved_at"] is not None


class TestPersistMotionDecision:
    def test_decision_persisted(self, tmp_log_dir: Path):
        d = MotionDecision(
            phase=MotionPhase.FORWARD,
            duration_ms=2000,
            linear_velocity=0.15,
            trigger=MotionTrigger.PERIODIC,
        )
        persist_motion_decision(d, log_dir=tmp_log_dir)
        records = load_jsonl(tmp_log_dir / "motion_decisions.jsonl")
        assert len(records) == 1
        assert records[0]["phase"] == "forward"
        assert records[0]["duration_ms"] == 2000


class TestLoadJsonl:
    def test_empty_returns_empty_list(self, tmp_log_dir: Path):
        result = load_jsonl(tmp_log_dir / "nonexistent.jsonl")
        assert result == []

    def test_parses_multiple_lines(self, tmp_log_dir: Path):
        path = tmp_log_dir / "test.jsonl"
        with open(path, "w") as f:
            f.write('{"a": 1}\n{"b": 2}\n')
        records = load_jsonl(path)
        assert len(records) == 2
        assert records[0]["a"] == 1
        assert records[1]["b"] == 2
