"""Conservative preprocessing of observed elevation, in metric units.

This is an input-quality filter, not a traversability classifier. It never
creates observations, averages a height discontinuity, or replaces a rejected
return with nearby ground. ``rejected_mask`` must also invalidate every HT
receptive field containing such a return; nearest-neighbour filling for the
network must not make these regions traversable.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import time

import numpy as np


@dataclass(frozen=True)
class ElevationQualityConfig:
    """Explicit bounds, intentionally independent of the sensor's variance.

    Range smoothing cannot grow with uncertainty: a large measurement variance
    must never allow smoothing a real step. The 3-by-3 default covers about
    12.3 cm at the HT input resolution, with a 2 cm height range scale.
    """

    radius_cells: int = 1
    spatial_sigma_m: float = 0.045
    height_sigma_m: float = 0.020
    preserve_height_jump_m: float = 0.075
    max_adjustment_m: float = 0.020
    max_measurement_std_m: float = 0.50
    confident_std_m: float = 0.005
    full_smoothing_std_m: float = 0.025
    isolated_jump_m: float = 0.12
    isolated_uncertain_std_m: float = 0.075
    isolated_background_spread_m: float = 0.040
    isolated_min_neighbors: int = 6

    def __post_init__(self):
        if not isinstance(self.radius_cells, int) or self.radius_cells not in (1, 2):
            raise ValueError("radius_cells must be 1 or 2")
        for name, value in vars(self).items():
            if name not in ("radius_cells", "isolated_min_neighbors"):
                if not math.isfinite(value) or value <= 0:
                    raise ValueError(f"{name} must be a positive finite metric value")
        if not 5 <= self.isolated_min_neighbors <= 8:
            raise ValueError("isolated_min_neighbors must be between 5 and 8")
        if self.full_smoothing_std_m <= self.confident_std_m:
            raise ValueError("full_smoothing_std_m must exceed confident_std_m")
        if self.isolated_jump_m <= self.preserve_height_jump_m:
            raise ValueError("isolated_jump_m must exceed preserve_height_jump_m")


@dataclass(frozen=True)
class ElevationQualityResult:
    height_m: np.ndarray
    observed_quality: np.ndarray
    rejected_mask: np.ndarray
    edge_mask: np.ndarray
    stats: dict


def _neighbor_view(padded, shape, padding, dx, dy):
    return padded[padding + dx:padding + dx + shape[0],
                  padding + dy:padding + dy + shape[1]]


def retain_recent_obstacle_edges(history_height, history_variance, current_height,
                                 current_variance, current_age, current_edges,
                                 max_age_s=2., innovation_m=.05):
    """Keep fresh measured upward edges from being averaged toward old ground.

    History remains the input away from directly observed height edges. This
    conservative input overlay cannot lower a retained obstacle or invent an
    observation in a hole; it does not alter the history's floor association.
    """
    z, v = np.asarray(history_height).copy(), np.asarray(history_variance).copy()
    current = np.asarray(current_height)
    age = np.asarray(current_age)
    use = (np.asarray(current_edges, bool) & np.isfinite(z) & np.isfinite(current)
           & np.isfinite(age) & (age >= -.001) & (age <= max_age_s)
           & (current-z >= innovation_m))
    z[use] = current[use]
    v[use] = np.asarray(current_variance)[use]
    return z, v, use


def preprocess_elevation(elevation_m, variance_m2, resolution_m,
                         config=None) -> ElevationQualityResult:
    """Denoise small texture while preserving measured steps and narrow posts.

    Uncertain *isolated* positive or negative height jumps become unknown only
    when at least six observed immediate neighbours agree on a compact
    background but disagree with the center, and none supports its height.
    A small object with consistent adjacent returns is kept;
    a confident single-cell object is also kept. An uncertain single-cell post
    cannot be distinguished from an outlier using this input and becomes
    unknown, never free ground.

    The bilateral filter uses only fully observed neighbourhoods and leaves all
    cells next to an observed >=7.5 cm discontinuity unchanged. NaN holes and
    their boundaries remain unchanged. Output variance is deliberately not
    reduced: overlapping height maps do not provide independent measurements.
    """
    started = time.perf_counter()
    cfg = config or ElevationQualityConfig()
    z = np.asarray(elevation_m, dtype=np.float32)
    variance = np.asarray(variance_m2, dtype=np.float32)
    if z.ndim != 2 or z.shape != variance.shape or min(z.shape) < 1:
        raise ValueError("elevation and variance must be equal nonempty 2D arrays")
    if not math.isfinite(resolution_m) or resolution_m <= 0:
        raise ValueError("resolution_m must be positive and finite")

    finite_height = np.isfinite(z)
    observed = (finite_height & np.isfinite(variance) & (variance >= 0)
                & (variance <= cfg.max_measurement_std_m ** 2))
    # Unknown and invalid variance are explicit quality rejections if a height
    # was present. Their values must not silently influence the network input.
    rejected = finite_height & ~observed
    height = np.where(observed, z, np.nan).astype(np.float32)

    one = np.pad(height, 1, constant_values=np.nan)
    observed_neighbors = np.zeros(z.shape, dtype=np.uint8)
    close_neighbors = np.zeros(z.shape, dtype=np.uint8)
    far_neighbors = np.zeros(z.shape, dtype=np.uint8)
    neighbor_min = np.full(z.shape, np.inf, dtype=np.float32)
    neighbor_max = np.full(z.shape, -np.inf, dtype=np.float32)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == dy == 0:
                continue
            neighbor = _neighbor_view(one, z.shape, 1, dx, dy)
            difference = np.abs(neighbor - height)
            known = np.isfinite(neighbor) & observed
            observed_neighbors += known
            close_neighbors += known & (difference < cfg.preserve_height_jump_m)
            far_neighbors += known & (difference >= cfg.isolated_jump_m)
            neighbor_min = np.minimum(neighbor_min, np.where(known, neighbor, np.inf))
            neighbor_max = np.maximum(neighbor_max, np.where(known, neighbor, -np.inf))
    isolated = (observed
                & (variance >= cfg.isolated_uncertain_std_m ** 2)
                & (observed_neighbors >= cfg.isolated_min_neighbors)
                & (far_neighbors == observed_neighbors)
                & (neighbor_max - neighbor_min <= cfg.isolated_background_spread_m)
                & (close_neighbors == 0))
    rejected |= isolated
    observed &= ~isolated
    height[~observed] = np.nan

    radius = cfg.radius_cells
    padded = np.pad(height, radius, constant_values=np.nan)
    edge = np.zeros(z.shape, dtype=bool)
    full_neighborhood = observed.copy()
    numerator = np.zeros(z.shape, dtype=np.float32)
    denominator = np.zeros(z.shape, dtype=np.float32)
    # At most 24 neighbours; no Python loop over grid cells and no wraparound.
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            neighbor = _neighbor_view(padded, z.shape, radius, dx, dy)
            difference = neighbor - height
            known = np.isfinite(neighbor) & observed
            full_neighborhood &= known
            edge |= known & (np.abs(difference) >= cfg.preserve_height_jump_m)
            eligible = known & (np.abs(difference) < cfg.preserve_height_jump_m)
            safe_difference = np.where(eligible, difference, 0.)
            spatial = ((dx * resolution_m) ** 2 + (dy * resolution_m) ** 2)
            exponent = (-0.5 * spatial / cfg.spatial_sigma_m ** 2
                        -0.5 * safe_difference ** 2 / cfg.height_sigma_m ** 2)
            weight = np.exp(exponent).astype(np.float32) * eligible
            numerator += weight * np.where(known, neighbor, 0.)
            denominator += weight

    smoothable = observed & full_neighborhood & ~edge
    candidate = np.divide(numerator, denominator, out=height.copy(),
                          where=denominator > 0)
    std_m = np.sqrt(np.maximum(variance, 0))
    blend = np.clip((std_m - cfg.confident_std_m)
                    / (cfg.full_smoothing_std_m - cfg.confident_std_m), 0., 1.)
    adjustment = np.clip(candidate - height,
                         -cfg.max_adjustment_m, cfg.max_adjustment_m)
    filtered = height.copy()
    filtered[smoothable] += (blend * adjustment)[smoothable]
    delta = filtered[observed] - z[observed]
    stats = {
        "input_height_cells": int(finite_height.sum()),
        "observed_quality_cells": int(observed.sum()),
        "rejected_cells": int(rejected.sum()),
        "isolated_rejected_cells": int(isolated.sum()),
        "preserved_edge_cells": int((edge & observed).sum()),
        "smoothed_cells": int(np.count_nonzero(delta)),
        "max_adjustment_m": float(np.max(np.abs(delta))) if delta.size else 0.,
        "rms_adjustment_m": float(np.sqrt(np.mean(delta ** 2))) if delta.size else 0.,
        "elapsed_ms": (time.perf_counter() - started) * 1000.,
    }
    return ElevationQualityResult(filtered, observed, rejected, edge & observed, stats)
