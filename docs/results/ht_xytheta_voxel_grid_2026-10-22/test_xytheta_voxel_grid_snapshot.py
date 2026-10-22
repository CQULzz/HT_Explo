"""Representation checks: real cells, periodic channel lookup and unknown data."""
import numpy as np
import pytest
from rviz_xytheta_voxel_grid import voxel_field,theta_channels,kept_cells,boundary_edges

def native():
    p=np.broadcast_to(np.arange(8,dtype=float)[:,None,None]/7,(8,10,10)).copy()
    return dict(x=1.35-np.arange(10)*.3,y=1.35-np.arange(10)*.3,p=p,valid=np.ones((10,10),bool),source_resolution_m=.3,display_cell_m=.3)

def test_nearest_heading_is_periodic_and_not_interpolated():
    channels=theta_channels()
    np.testing.assert_array_equal(channels,[0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,6,6,6,6,7,7,7,7,0,0])
    g=native();before=g['p'].copy();xyz,v,ok,c=voxel_field(g,(0,0,0,0),side=4)
    assert ok.all();np.testing.assert_array_equal(v[1,1],channels/7)
    np.testing.assert_array_equal(g['p'],before)

def test_cells_fill_theta_axis_and_have_no_sheet_spacing():
    xyz,v,ok,c=voxel_field(native(),(0,0,0,0),side=4)
    assert xyz.shape==(4,4,32,3)
    np.testing.assert_allclose(np.diff(xyz[0,0,:,2]),.3)
    assert xyz[0,0,0,2]==pytest.approx(.15)
    assert xyz[0,0,-1,2]+.15==pytest.approx(9.6)

def test_unknown_and_outside_cells_never_get_safe_colors():
    g=native();g['valid'][:]=False
    xyz,v,ok,c=voxel_field(g,(0,0,0,0),side=4)
    assert not ok.any() and np.isnan(v).all()
    g=native();xyz,v,ok,c=voxel_field(g,(100,100,0,0),side=4)
    assert not ok.any() and np.isnan(v).all()

def test_display_stride_cache_rejected():
    g=native();g['display_cell_m']=.9
    with pytest.raises(ValueError,match='native'):voxel_field(g,(0,0,0,0))

def test_cutaway_is_geometric_subset_and_lattice_has_volume_edges():
    full=kept_cells(False,side=4);cut=kept_cells(True,side=4)
    assert full.sum()==4*4*32 and cut.sum()==12*32
    lines=boundary_edges(cut)
    assert lines.shape[1]==3 and len(lines)%2==0
    assert np.ptp(lines[:,2])==pytest.approx(9.6)
