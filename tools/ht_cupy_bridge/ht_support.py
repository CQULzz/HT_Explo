"""Build HT context without turning measured obstacles into unknown halos."""
import numpy as np
from scipy.ndimage import distance_transform_edt, uniform_filter, maximum_filter


def preserve_rejected_obstacles(obstacle_elevation, raw_height, rejected):
    """Keep finite post-filter rejects as unsafe occupied context, never ground.

    Source-level quality rejects already use this rule in HistoricalElevation.
    A second quality filter on the fused crop must not lose the rejected height.
    Unmeasured/nonfinite rejects remain unknown and retain the context veto.
    """
    obstacle = np.asarray(obstacle_elevation, np.float32)
    raw = np.asarray(raw_height, np.float32)
    mask = np.asarray(rejected, bool)
    if obstacle.ndim != 2 or raw.shape != obstacle.shape or mask.shape != obstacle.shape:
        raise ValueError('Rejected obstacle arrays must be equal two-dimensional shapes')
    return np.where(np.isfinite(obstacle), obstacle,
                    np.where(mask & np.isfinite(raw), raw, np.nan)).astype(np.float32)


def prepare_ht_context(elevation, observed, rejected, obstacle_elevation, resolution):
    height = np.asarray(elevation, np.float32).copy()
    occupied = np.isfinite(obstacle_elevation)
    height[occupied] = np.asarray(obstacle_elevation)[occupied]
    known = np.asarray(observed, bool) | occupied
    uncertain = np.asarray(rejected, bool) & ~occupied
    distance, nearest = distance_transform_edt(~known, return_indices=True)
    network_height = height[tuple(nearest)].astype(np.float32)
    near = distance*resolution <= .25
    support = uniform_filter(near.astype(np.float32), size=51, mode='constant')[25:-25,25:-25] >= .9
    support &= ~maximum_filter(uncertain, size=51, mode='constant')[25:-25,25:-25]
    # Context validity describes a neural receptive field. Physical support
    # describes observed terrain at each XY cell; footprint inflation belongs
    # to the consumer and must not inflate the neural context a second time.
    physical = near & ~uncertain
    return network_height, support, occupied[25:-25,25:-25], physical[25:-25,25:-25]
