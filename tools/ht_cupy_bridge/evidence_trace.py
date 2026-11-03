"""Per-cell provenance of actual evidence; flags overlap and grant no support.

Times are subtracted in float64 before publishing relative ages as float32.
No finite timestamp means no record in retained history, not proof that the
sensor has never observed this cell over its entire lifetime.
"""
import numpy as np

EVIDENCE_FLAGS = {
    'source_height_missing': 1, 'source_quality_rejected': 2,
    'history_selection_missing': 4, 'history_incompatible': 8,
    'final_quality_rejected': 16, 'stale_off_surface': 32,
    'quarantined_candidate': 64, 'physical_unsupported': 128,
    'context_unsupported': 256, 'measured_occupied': 512,
    'source_variance_rejected': 1024,
}


def relative_age(stamp_s, times):
    times = np.asarray(times, np.float64)
    return np.where(np.isfinite(times), float(stamp_s)-times, np.nan).astype(np.float32)


def trace_evidence(*, source_height, source_variance, source_age, source_rejected,
                   history_height, history_incompatible, final_rejected,
                   stale_surface, quarantined_candidate, physical, context,
                   occupied, selected_time, last_accepted_time, last_rejected_time,
                   stamp_s, max_measurement_std_m=.5):
    source = np.asarray(source_height)
    finite = np.isfinite(source)
    variance = np.asarray(source_variance)
    masks = [~finite, source_rejected, ~np.isfinite(history_height), history_incompatible,
             final_rejected, stale_surface, quarantined_candidate, ~np.asarray(physical,bool),
             ~np.asarray(context,bool), occupied,
             finite & (~np.isfinite(variance) | (variance < 0)
                       | (variance > max_measurement_std_m**2))]
    flags = np.zeros(source.shape, np.uint16)
    for bit, mask in zip(EVIDENCE_FLAGS.values(), masks):
        if np.shape(mask) != source.shape:
            raise ValueError('Evidence trace geometry mismatch')
        flags[np.asarray(mask,bool)] |= bit
    return {
        'evidence_flags': flags,
        'source_height': source.astype(np.float32),
        'source_variance': variance.astype(np.float32),
        'source_observation_age_s': np.where(finite, source_age, np.nan).astype(np.float32),
        'selected_observation_age_s': relative_age(stamp_s, selected_time),
        'last_accepted_age_s': relative_age(stamp_s, last_accepted_time),
        'last_rejected_age_s': relative_age(stamp_s, last_rejected_time),
    }
