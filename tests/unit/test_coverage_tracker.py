"""Unit tests for coverage tracker."""
import pytest

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    CoverageWorkUnit,
    WorkUnitFailureReason,
    WorkUnitState,
)
from roomba_cleaning_coverage.roomba_cleaning_coverage.coverage_tracker import (
    all_reachable_done,
    compute_snapshot,
    mark_unit_covered,
    mark_unit_failed,
    next_unvisited,
)


def make_units(n: int, area: float = 1.0) -> list:
    return [CoverageWorkUnit(area_m2=area) for _ in range(n)]


class TestNextUnvisited:
    def test_returns_first_unvisited(self):
        units = make_units(3)
        units[0].state = WorkUnitState.COVERED
        result = next_unvisited(units)
        assert result is units[1]

    def test_all_done_returns_none(self):
        units = make_units(2)
        for u in units:
            u.state = WorkUnitState.COVERED
        assert next_unvisited(units) is None

    def test_empty_list_returns_none(self):
        assert next_unvisited([]) is None


class TestMarkUnitCovered:
    def test_marks_as_covered(self):
        unit = CoverageWorkUnit()
        mark_unit_covered(unit)
        assert unit.state == WorkUnitState.COVERED
        assert unit.last_failure_reason == WorkUnitFailureReason.NONE


class TestMarkUnitFailed:
    def test_first_failure_leaves_unvisited_for_retry(self):
        unit = CoverageWorkUnit()
        state = mark_unit_failed(unit, WorkUnitFailureReason.NAV_TIMEOUT, max_retries=1)
        assert unit.retry_count == 1
        assert state == WorkUnitState.UNVISITED  # still retryable

    def test_second_failure_skips(self):
        unit = CoverageWorkUnit()
        mark_unit_failed(unit, WorkUnitFailureReason.NAV_TIMEOUT, max_retries=1)
        state = mark_unit_failed(unit, WorkUnitFailureReason.NAV_TIMEOUT, max_retries=1)
        assert state == WorkUnitState.SKIPPED

    def test_obstacle_block_marks_as_blocked(self):
        unit = CoverageWorkUnit()
        mark_unit_failed(unit, WorkUnitFailureReason.OBSTACLE_BLOCKED, max_retries=0)
        assert unit.state == WorkUnitState.BLOCKED


class TestComputeSnapshot:
    def test_all_unvisited(self):
        units = make_units(4, area=1.0)
        snap = compute_snapshot("sess", units)
        assert snap.covered_area_m2 == 0.0
        assert snap.remaining_area_m2 == 4.0
        assert snap.covered_ratio == 0.0

    def test_all_covered(self):
        units = make_units(4, area=1.0)
        for u in units:
            u.state = WorkUnitState.COVERED
        snap = compute_snapshot("sess", units)
        assert snap.covered_area_m2 == 4.0
        assert snap.remaining_area_m2 == 0.0
        assert snap.covered_ratio == 1.0

    def test_partial_coverage(self):
        units = make_units(4, area=1.0)
        units[0].state = WorkUnitState.COVERED
        units[1].state = WorkUnitState.COVERED
        snap = compute_snapshot("sess", units)
        assert snap.covered_area_m2 == 2.0
        assert snap.remaining_area_m2 == 2.0
        assert snap.covered_ratio == 0.5

    def test_blocked_counted_separately(self):
        units = make_units(2, area=1.0)
        units[0].state = WorkUnitState.BLOCKED
        snap = compute_snapshot("sess", units)
        assert snap.blocked_area_m2 == 1.0
        assert snap.covered_area_m2 == 0.0


class TestAllReachableDone:
    def test_all_covered_is_done(self):
        units = make_units(3)
        for u in units:
            u.state = WorkUnitState.COVERED
        assert all_reachable_done(units)

    def test_mix_covered_blocked_is_done(self):
        units = make_units(3)
        units[0].state = WorkUnitState.COVERED
        units[1].state = WorkUnitState.BLOCKED
        units[2].state = WorkUnitState.SKIPPED
        assert all_reachable_done(units)

    def test_unvisited_not_done(self):
        units = make_units(3)
        units[0].state = WorkUnitState.COVERED
        assert not all_reachable_done(units)

    def test_empty_is_done(self):
        assert all_reachable_done([])
