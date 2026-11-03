"""Separate model context from physical evidence on observed terrain.

Discarding a stale/ambiguous height is never an observation of free ground.
The returned physical-unknown mask must be applied by the context publisher.
"""
from dataclasses import dataclass
import math
import numpy as np


def _selected_times(z, times, selected, obstacle, rejected_at, rejected_z):
    shape=selected.shape
    chosen=np.full(shape,-np.inf,np.float64)
    blocked=np.full(shape,-np.inf,np.float64)
    for i in range(shape[0]):
        for j in range(shape[1]):
            for k in range(z.shape[0]):
                if np.isfinite(z[k,i,j]):
                    if z[k,i,j]==selected[i,j]:
                        chosen[i,j]=max(chosen[i,j],times[k,i,j])
                    if z[k,i,j]==obstacle[i,j]:
                        blocked[i,j]=max(blocked[i,j],times[k,i,j])
            if np.isfinite(obstacle[i,j]) and rejected_z[i,j]==obstacle[i,j]:
                blocked[i,j]=max(blocked[i,j],rejected_at[i,j])
    return chosen,blocked


_compiled_times=None


def overlay_observation_times(selected_times, current_age, retained_edges, stamp_s):
    """Carry timestamps with a measured edge overlay; no time refresh elsewhere."""
    out=np.asarray(selected_times,np.float64).copy()
    mask=np.asarray(retained_edges,bool)
    if out.shape!=np.shape(current_age) or out.shape!=mask.shape:
        raise ValueError('Edge time geometry mismatch')
    out[mask]=(float(stamp_s)-np.asarray(current_age,np.float64))[mask]
    return out


def warmup_evidence_times(backend):
    """Resolve/warm the metadata reducer before receiving real-time inputs."""
    global _compiled_times
    if backend!='numba':
        def numpy_times(z,times,selected,obstacle,rejected_at,rejected_z):
            chosen=np.max(np.where(np.isfinite(z)&(z==selected[None]),times,-np.inf),axis=0)
            blocked=np.max(np.where(np.isfinite(z)&(z==obstacle[None]),times,-np.inf),axis=0)
            return chosen,np.maximum(blocked,np.where(
                np.isfinite(obstacle)&(rejected_z==obstacle),rejected_at,-np.inf))
        return numpy_times
    if _compiled_times is None:
        from numba import njit
        _compiled_times=njit(cache=True)(_selected_times)
        z=np.zeros((4,3,3),np.float32)[:,::-1,::-1]
        times=np.zeros((4,3,3),np.float64)[:,::-1,::-1]
        _compiled_times(z,times,np.zeros((3,3),np.float32),np.full((3,3),np.nan,np.float32),
                        np.full((3,3),-np.inf,np.float64),np.full((3,3),np.nan,np.float32))
    return _compiled_times


@dataclass(frozen=True)
class QualifiedEvidence:
    height: np.ndarray
    observed: np.ndarray
    obstacle: np.ndarray
    physical_unknown: np.ndarray
    stats: dict
    stale_surface: np.ndarray
    quarantined_candidate: np.ndarray


def qualify_height_evidence(height, observed, rejected, obstacle, height_time,
                            obstacle_time, reference, stamp_s, *,
                            stale_surface_s=5., surface_margin_m=.15):
    """Keep fresh obstacle evidence; quarantine unconfirmed/old height values.

    A fresh accepted surface is still passed to the learned model unchanged.
    Only *already rejected* obstacle candidates are classified by the margin.
    Old accepted off-surface heights become unknown, never replacement ground.
    """
    z = np.asarray(height, np.float32)
    arrays = [np.asarray(a) for a in
              (observed, rejected, obstacle, height_time, obstacle_time, reference)]
    if z.ndim != 2 or any(a.shape != z.shape for a in arrays):
        raise ValueError('Height evidence arrays must share a 2D shape')
    if (not math.isfinite(stamp_s) or not math.isfinite(stale_surface_s)
            or stale_surface_s <= 0 or not math.isfinite(surface_margin_m)
            or surface_margin_m <= 0):
        raise ValueError('Invalid height evidence age/margin')
    obs, reject, candidate, measured_at, candidate_at, ref = arrays
    reject = reject.astype(bool)
    accepted = obs.astype(bool) & np.isfinite(z) & ~reject

    def fresh(times):
        # Compute in float64: float32 epoch seconds lose observation ordering.
        age = float(stamp_s)-np.asarray(times, np.float64)
        return np.isfinite(age) & (age >= -.001) & (age <= stale_surface_s)

    off_surface = ~np.isfinite(ref) | (np.abs(z-ref) > surface_margin_m)
    stale_surface = accepted & off_surface & ~fresh(measured_at)
    accepted &= ~stale_surface
    keep_obstacle = (np.isfinite(candidate) & np.isfinite(ref)
                     & (np.abs(candidate-ref) > surface_margin_m)
                     & fresh(candidate_at))
    unknown = (reject | stale_surface
               | (np.isfinite(candidate) & ~keep_obstacle)) & ~keep_obstacle
    accepted &= ~unknown
    return QualifiedEvidence(
        np.where(accepted, z, np.nan).astype(np.float32), accepted,
        np.where(keep_obstacle, candidate, np.nan).astype(np.float32), unknown,
        {'stale_surface_cells': int(stale_surface.sum()),
         'fresh_obstacle_cells': int(keep_obstacle.sum()),
         'quarantined_obstacle_candidates': int((np.isfinite(candidate) & ~keep_obstacle).sum()),
         'physical_unknown_cells': int(unknown.sum()),
         'stale_surface_s': float(stale_surface_s),
         'surface_margin_m': float(surface_margin_m)},
        stale_surface, np.isfinite(candidate) & ~keep_obstacle)
