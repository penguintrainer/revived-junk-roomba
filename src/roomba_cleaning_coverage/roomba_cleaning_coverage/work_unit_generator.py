"""Work unit generator: decompose target mask into CoverageWorkUnits."""
from __future__ import annotations

from typing import List, Tuple

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    CoverageWorkUnit,
)


def generate_work_units(
    centroids: List[Tuple[float, float]],
    region_id: str = "default",
    cell_area_m2: float = 0.25,
) -> List[CoverageWorkUnit]:
    """Convert centroid coordinates into CoverageWorkUnit instances."""
    units: List[CoverageWorkUnit] = []
    for cx, cy in centroids:
        unit = CoverageWorkUnit(
            region_id=region_id,
            centroid_x=cx,
            centroid_y=cy,
            area_m2=cell_area_m2,
        )
        units.append(unit)
    return units
