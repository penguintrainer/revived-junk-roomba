"""Target mask builder for reachable floor area."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class MapCell:
    """Single grid cell in the occupancy map."""
    x: int
    y: int
    reachable: bool = True


def build_target_mask(
    occupancy_grid: List[List[int]],
    resolution_m: float = 0.5,
    free_threshold: int = 50,
) -> List[Tuple[float, float]]:
    """Return (x, y) centroids of reachable floor cells.

    occupancy_grid: 2D list of occupancy values (0=free, 100=occupied, -1=unknown).
    free_threshold: cells with value <= this are considered free.
    """
    centroids = []
    for row_idx, row in enumerate(occupancy_grid):
        for col_idx, cell_val in enumerate(row):
            if cell_val >= 0 and cell_val <= free_threshold:
                cx = (col_idx + 0.5) * resolution_m
                cy = (row_idx + 0.5) * resolution_m
                centroids.append((cx, cy))
    return centroids
