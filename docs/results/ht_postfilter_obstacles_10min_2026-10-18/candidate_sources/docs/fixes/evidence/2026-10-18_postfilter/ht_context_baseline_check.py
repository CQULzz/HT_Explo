import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path.cwd()/'tools/ht_cupy_bridge'))
from ht_support import prepare_ht_context
p=Path('docs/results/ht_continuous_geometry_10min_2026-10-18/geometry_capture/stopped_snapshot.npz')
d=np.load(p);observed=d['history_input_valid']>=.5;rejected=d['history_rejected']>=.5
# Existing obstacle HEIGHTS are not in old snapshots. This reconstruction checks
# masks only; finite placeholders preserve their exact occupied/support masks.
obstacle=np.pad(np.where(d['ht_ht_obstacle']>=.5,1.7,np.nan),25,constant_values=np.nan)
_,support,occupied,physical=prepare_ht_context(d['history_elevation'],observed,rejected,obstacle,d['ht_geometry'][2])
# Old snapshots omit obstacle heights/masks in the outer25 input cells.
# Compare the inner field beyond that influence, never claim full reconstruction.
assert np.array_equal((support|occupied)[40:-40,40:-40],(d['ht_ht_valid']>=.5)[40:-40,40:-40])
print('Reproduced original INNER support mask exactly (outer obstacle context not recorded); root physical=%s predicted=%s' % (physical[120,120],support[120,120]),flush=True)
assert support[120,120], 'Desired consistent finite-rejection obstacle context is missing in original pipeline'
