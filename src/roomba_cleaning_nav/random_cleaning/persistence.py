"""JSON Lines persistence helpers for sessions and safety events."""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from roomba_cleaning_nav.random_cleaning.models import (
    CleaningSession,
    SafetyEvent,
    MotionDecision,
)

_DEFAULT_LOG_DIR = Path(os.environ.get("ROOMBA_LOG_DIR", "/tmp/roomba_logs"))


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _serialize(obj: Any) -> Any:
    """Recursively serialize dataclass / datetime / enum fields."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "value"):  # Enum
        return obj.value
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialize(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def _write_jsonl(path: Path, record: Dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def persist_session(session: CleaningSession, log_dir: Optional[Path] = None) -> None:
    """Append a CleaningSession record to the sessions JSONL log."""
    d = log_dir or _DEFAULT_LOG_DIR
    _ensure_dir(d)
    record = _serialize(session)
    _write_jsonl(d / "sessions.jsonl", record)


def persist_safety_event(event: SafetyEvent, log_dir: Optional[Path] = None) -> None:
    """Append a SafetyEvent record to the safety_events JSONL log."""
    d = log_dir or _DEFAULT_LOG_DIR
    _ensure_dir(d)
    record = _serialize(event)
    _write_jsonl(d / "safety_events.jsonl", record)


def persist_motion_decision(
    decision: MotionDecision,
    log_dir: Optional[Path] = None,
) -> None:
    """Append a MotionDecision record to the motion_decisions JSONL log."""
    d = log_dir or _DEFAULT_LOG_DIR
    _ensure_dir(d)
    record = _serialize(decision)
    _write_jsonl(d / "motion_decisions.jsonl", record)


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read all records from a JSONL file."""
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
