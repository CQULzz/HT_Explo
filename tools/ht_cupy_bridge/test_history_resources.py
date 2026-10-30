import numpy as np
from historical_elevation import HistoricalElevation


def test_history_reports_actual_arrays_and_does_not_claim_eviction():
    h=HistoricalElevation(.04,tile_size=4,max_tiles=10,max_layers=4,window_backend='numpy')
    h._tile(0,0)
    h.rejections[(0,0)]=np.zeros((4,4),np.float64)
    h.rejected_heights[(0,0)]=np.zeros((4,4),np.float32)
    r=h.resource_usage()
    assert r['tiles']==1 and r['max_tiles']==10 and r['allocated_xy_cells']==16
    assert r['surface_array_bytes']==4*4*4*(4+4+8)
    assert r['rejection_array_bytes']==4*4*(8+4)
    assert r['eviction_enabled'] is False
