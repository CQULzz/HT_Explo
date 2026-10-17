"""Build HT context without turning measured obstacles into unknown halos."""
import numpy as np
from scipy.ndimage import distance_transform_edt, uniform_filter, maximum_filter


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
