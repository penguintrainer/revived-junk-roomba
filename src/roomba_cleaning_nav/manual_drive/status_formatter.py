"""Operator status formatting for manual drive diagnostics and topic publication.

Pure serialization helpers — no side effects.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

from roomba_cleaning_nav.manual_drive.models import (
    ManualDriveState,
    OperatorStatus,
)


def format_status(state: ManualDriveState) -> OperatorStatus:
    """Build an OperatorStatus snapshot from current ManualDriveState."""
    return OperatorStatus(
        mode=state.mode.value,
        cleaning=state.cleaning.value,
        fault=state.fault.value,
        estop_latched=state.estop_latched,
        link_ok=state.link_health_ok,
        low_battery=state.low_battery_warning,
        forbidden_zone_override=state.forbidden_zone_override.value,
        timestamp=datetime.utcnow().isoformat(),
    )


def status_to_json(status: OperatorStatus) -> str:
    """Serialize OperatorStatus to a JSON string."""
    return json.dumps({
        "mode": status.mode,
        "cleaning": status.cleaning,
        "fault": status.fault,
        "estop_latched": status.estop_latched,
        "link_ok": status.link_ok,
        "low_battery": status.low_battery,
        "forbidden_zone_override": status.forbidden_zone_override,
        "timestamp": status.timestamp,
    })


def status_to_dict(status: OperatorStatus) -> Dict[str, Any]:
    """Serialize OperatorStatus to a plain dict."""
    return {
        "mode": status.mode,
        "cleaning": status.cleaning,
        "fault": status.fault,
        "estop_latched": status.estop_latched,
        "link_ok": status.link_ok,
        "low_battery": status.low_battery,
        "forbidden_zone_override": status.forbidden_zone_override,
        "timestamp": status.timestamp,
    }


def format_diagnostics_keys(state: ManualDriveState, link_age_ms: float) -> Dict[str, str]:
    """Build the required diagnostics key-value pairs.

    Required keys: joycon_link_age_ms, manual_mode_active, cleaning_enabled,
    last_fault, rumble_available.
    """
    return {
        "joycon_link_age_ms": f"{link_age_ms:.0f}",
        "manual_mode_active": str(state.is_active()).lower(),
        "cleaning_enabled": str(state.cleaning.value == "on").lower(),
        "last_fault": state.fault.value,
        "rumble_available": "false",  # hardware-dependent; conservative default
    }
