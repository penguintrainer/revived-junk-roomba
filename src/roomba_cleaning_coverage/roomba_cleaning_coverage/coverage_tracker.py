"""Coverage tracker: work-unit state, retry logic, and area metrics."""
from __future__ import annotations

from typing import List, Optional, Tuple

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.config import (
    RECOVERY_ATTEMPTS,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    CoverageSnapshot,
    CoverageWorkUnit,
    WorkUnitFailureReason,
    WorkUnitState,
)


def next_unvisited(units: List[CoverageWorkUnit]) -> Optional[CoverageWorkUnit]:
    """Return the first unvisited work unit, or None if all are processed."""
    for unit in units:
        if unit.state == WorkUnitState.UNVISITED:
            return unit
    return None


def mark_unit_covered(unit: CoverageWorkUnit) -> None:
    unit.state = WorkUnitState.COVERED
    unit.last_failure_reason = WorkUnitFailureReason.NONE


def mark_unit_failed(
    unit: CoverageWorkUnit,
    reason: WorkUnitFailureReason,
    max_retries: int = RECOVERY_ATTEMPTS,
) -> WorkUnitState:
    """Mark a unit failed and decide whether to retry or skip/block.

    Returns the new WorkUnitState.
    """
    unit.retry_count += 1
    unit.last_failure_reason = reason
    if unit.retry_count > max_retries:
        if reason == WorkUnitFailureReason.OBSTACLE_BLOCKED:
            unit.state = WorkUnitState.BLOCKED
        else:
            unit.state = WorkUnitState.SKIPPED
    # else leave as UNVISITED for retry
    return unit.state


def compute_snapshot(
    session_id: str,
    units: List[CoverageWorkUnit],
    active_unit_id: Optional[str] = None,
) -> CoverageSnapshot:
    """Compute a coverage snapshot from the current work unit list."""
    covered = sum(u.area_m2 for u in units if u.state == WorkUnitState.COVERED)
    blocked = sum(
        u.area_m2
        for u in units
        if u.state in (WorkUnitState.BLOCKED, WorkUnitState.SKIPPED)
    )
    remaining = sum(
        u.area_m2
        for u in units
        if u.state in (WorkUnitState.UNVISITED, WorkUnitState.RESERVED, WorkUnitState.NAVIGATING)
    )
    total = sum(u.area_m2 for u in units)
    reachable = total - blocked
    covered_ratio = covered / total if total > 0 else 0.0
    reachable_ratio = reachable / total if total > 0 else 0.0
    return CoverageSnapshot(
        session_id=session_id,
        covered_area_m2=covered,
        remaining_area_m2=remaining,
        blocked_area_m2=blocked,
        covered_ratio=covered_ratio,
        reachable_ratio=reachable_ratio,
        active_work_unit_id=active_unit_id,
    )


def all_reachable_done(units: List[CoverageWorkUnit]) -> bool:
    """Return True when all units are either covered, blocked, or skipped."""
    for u in units:
        if u.state in (WorkUnitState.UNVISITED, WorkUnitState.RESERVED,
                       WorkUnitState.NAVIGATING):
            return False
    return True
