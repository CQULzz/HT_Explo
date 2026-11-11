"""Independent statistical and observation-contract regressions on CUDA."""
from pathlib import Path
from types import SimpleNamespace
from array import array
from copy import deepcopy
import sys
import numpy as np
import cupy as cp
import pytest
from elevation_mapping_cupy import ElevationMap,Parameter
from elevation_mapping_cupy.deterministic_fusion import DeterministicFusion

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'ht_cupy_bridge'))

@pytest.fixture(scope='module')
def mapping(tmp_path_factory):
    plugins=tmp_path_factory.mktemp('mapper')/'plugins.yaml'
    plugins.write_text('min_filter:\n  enable: false\n')
    package=Path('/home/lzz/ht_quality_20261111/mapper_source/elevation_mapping_cupy_2204/elevation_mapping_cupy')
    p=Parameter(use_chainer=False,resolution=.1,map_length=4.,
        weight_file=str(package/'config/core/weights.dat'),plugin_config_file=str(plugins),
        enable_drift_compensation=False,enable_visibility_cleanup=False,
        enable_overlap_clearance=False,enable_deterministic_fusion=True,
        sensor_noise_factor=.05,mahalanobis_thresh=2.,outlier_variance=.01,
        time_variance=.0001,
        min_valid_distance=.5)
    p.subscriber_cfg={'scan':{'data_type':'pointcloud'}};p.update()
    return ElevationMap(p)

def reset(m,h=-.75,v=.0006):
    m.clear();i=int(1./m.resolution+m.cell_n/2);j=int(m.cell_n/2)
    m.elevation_map[0,i,j]=h;m.elevation_map[1,i,j]=v;m.elevation_map[2,i,j]=1
    m.observation_stamps[0,i,j]=100.;m.observation_variances[0,i,j]=v
    return i,j

def integrate(m,heights,stamp=101.):
    pts=np.c_[np.ones(len(heights)),np.zeros(len(heights)),heights].astype(np.float32)
    m.input_pointcloud(pts,['x','y','z'],np.eye(3,dtype=np.float32),
                      np.zeros(3,np.float32),0,0,observation_stamp=stamp)

def test_innovation_uses_combined_variance_and_gaussian_conditioning(mapping):
    m=mapping;i,j=reset(m);z=-.735
    integrate(m,[z])
    # 15mm is consistent with the independent 2-sigma innovation distribution,
    # while the former variance*2 gate would allow only 1.2mm.
    measurement=.05*z*z;prior=.0006
    expected_v=1/(1/prior+1/measurement)
    expected_h=expected_v*(-.75/prior+z/measurement)
    assert float(m.new_map[2,i,j])==1
    assert float(m.elevation_map[0,i,j])==pytest.approx(expected_h,abs=2e-7)
    assert float(m.elevation_map[1,i,j])==pytest.approx(expected_v,abs=2e-8)

@pytest.mark.parametrize('copies',[1,2,4])
def test_duplicate_rejected_returns_do_not_amplify_scan_variance(mapping,copies):
    m=mapping;i,j=reset(m);integrate(m,[-.25]*(115*copies))
    assert float(m.new_map[2,i,j])==0
    assert float(m.elevation_map[0,i,j])==pytest.approx(-.75)
    assert float(m.elevation_map[1,i,j])==pytest.approx(.0106,abs=2e-8)
    assert float(m.observation_stamps[0,i,j])==100.
    assert float(m.observation_variances[0,i,j])==pytest.approx(.0006)

def test_observation_quality_survives_process_ticks_but_new_evidence_updates_it(mapping):
    m=mapping;i,j=reset(m);integrate(m,[-.25]*115)
    for _ in range(30):m.update_variance()
    assert float(m.elevation_map[1,i,j])>.0106
    assert float(m.observation_variances[0,i,j])==pytest.approx(.0006)
    integrate(m,[-.75],stamp=102.)
    assert float(m.observation_stamps[0,i,j])==102.
    assert float(m.observation_variances[0,i,j])==float(m.elevation_map[1,i,j])

def test_observation_variance_roll_clear_and_wire_cell_identity(mapping):
    m=mapping;i,j=reset(m)
    a=np.empty((m.cell_n-2,m.cell_n-2),np.float32)
    z=np.empty_like(a);m.get_map_with_name_ref('observation_variance',a)
    m.get_map_with_name_ref('elevation',z)
    np.testing.assert_array_equal(np.isfinite(a),np.isfinite(z))
    assert a[np.isfinite(a)].tolist()==pytest.approx([.0006])
    before=m.observation_variances.get();m.shift_map_xy(cp.asarray([1,-2]))
    expected=np.roll(before,[1,-2],axis=(1,2));expected[:,:1,:]=np.nan;expected[:,:,-2:]=np.nan
    np.testing.assert_array_equal(m.observation_variances.get(),expected)
    m.clear();assert bool(cp.isnan(m.observation_variances).all())

def test_mapper_publishes_height_age_and_observation_quality_in_one_snapshot(mapping):
    import threading
    from rclpy.time import Time
    from elevation_mapping_cupy.elevation_mapping_ros import ElevationMappingNode
    m=mapping;i,j=reset(m);m.update_variance();published=[]
    layers=['elevation','variance','observation_age','observation_variance']
    node=SimpleNamespace(map_translation=True,map=m,
        last_integrated_stamp=Time(seconds=100.25),map_access_lock=threading.RLock(),
        map_data=np.empty((m.cell_n-2,m.cell_n-2),np.float32),map_frame='map',
        publisher_configs={'test':{'layers':layers,'basic_layers':['elevation']}},
        map_publishers={'test':SimpleNamespace(publish=published.append)})
    ElevationMappingNode.publish_map(node,'test');msg=published[0]
    assert msg.layers==layers and msg.header.stamp.nanosec==250000000
    side=m.cell_n-2
    z,total,age,observed=[np.asarray(d.data).reshape((side,side),order='F') for d in msg.data]
    valid=np.isfinite(z)
    np.testing.assert_array_equal(valid,np.isfinite(age))
    np.testing.assert_array_equal(valid,np.isfinite(observed))
    assert observed[valid].tolist()==pytest.approx([.0006])
    assert total[valid].tolist()==pytest.approx([.0007])
    assert age[valid].tolist()==pytest.approx([.25])

def test_true_large_height_change_is_not_averaged_into_old_ground(mapping):
    m=mapping;i,j=reset(m);integrate(m,[.75]*64)
    assert float(m.new_map[2,i,j])==0
    assert float(m.elevation_map[0,i,j])==pytest.approx(-.75)
    # A rejected return does not create an accepted or younger measurement.
    assert float(m.observation_stamps[0,i,j])==100.

def test_density_does_not_move_the_protected_edge_tolerance(mapping):
    m=mapping;results=[]
    for copies in [1,2,4]:
        i,j=reset(m,h=.84,v=.0006)
        integrate(m,np.tile(np.asarray([.81,.83,.84,.85]*8),copies))
        results.append([float(m.elevation_map[0,i,j]),float(m.elevation_map[1,i,j])])
    np.testing.assert_allclose(results,[results[0]]*3,rtol=0,atol=2e-7)

def test_accumulated_uncertainty_cannot_erode_an_observed_high_edge(mapping):
    m=mapping;i,j=reset(m,h=.84,v=.0006)
    for tick in range(40):integrate(m,[.35]*115,stamp=101.+tick*.2)
    assert float(m.elevation_map[0,i,j])==pytest.approx(.84)
    assert float(m.observation_stamps[0,i,j])==100.
    assert float(m.observation_variances[0,i,j])==pytest.approx(.0006)

def source_map():
    from grid_map_msgs.msg import GridMap
    from std_msgs.msg import Float32MultiArray,MultiArrayDimension,MultiArrayLayout
    m=GridMap();m.header.frame_id='map';m.header.stamp.sec=264
    m.info.resolution=.04093567251461988;m.info.length_x=m.info.length_y=291*m.info.resolution
    m.info.pose.orientation.w=1.
    m.layers=['elevation','variance','observation_age','observation_variance']
    for value in [.84,1.15,.2,.0006]:
        a=Float32MultiArray();a.layout=MultiArrayLayout(dim=[
            MultiArrayDimension(label='column_index',size=291,stride=291*291),
            MultiArrayDimension(label='row_index',size=291,stride=291)])
        a.data=array('f',np.full(291*291,value,np.float32).tobytes());m.data.append(a)
    return m

def test_ht_requires_and_decodes_the_quality_of_the_matching_observation():
    from cupy_to_ht import decode_elevation_source
    from elevation_quality import preprocess_elevation
    m=source_map();res,z,v,age=decode_elevation_source(m,variance_layer='observation_variance')
    assert np.all(v==np.float32(.0006))
    assert not preprocess_elevation(z,v,res,backend='numpy',denoise=False).rejected_mask.any()
    # A genuinely poor accepted observation is still rejected by the same
    # 0.25m² quality threshold; process variance is not relabelled as quality.
    m.data[3].data=array('f',np.full(291*291,.3,np.float32).tobytes())
    _,z,v,_=decode_elevation_source(m,variance_layer='observation_variance')
    assert preprocess_elevation(z,v,res,backend='numpy',denoise=False).rejected_mask.all()
    m.layers.pop();m.data.pop()
    with pytest.raises(ValueError,match='observation_variance'):
        decode_elevation_source(m,variance_layer='observation_variance')

def test_same_observation_quality_does_not_depend_on_intermediate_publication():
    from historical_elevation import HistoricalElevation
    from elevation_quality import preprocess_elevation
    outputs=[]
    for middle in [False,True]:
        h=HistoricalElevation(.04093567251461988,window_backend='numpy')
        z=np.full((3,3),np.nan,np.float32);v=np.full((3,3),np.inf,np.float32)
        z[1,1]=.84133;v[1,1]=.0006
        h.fuse(z,v,0,0,263.719,observation_time=263.719)
        if middle:
            z[1,1]=.841438;v[1,1]=.0004
            h.fuse(z,v,0,0,263.929,observation_time=263.929)
        z[1,1]=.841438;v[1,1]=.0004
        q=preprocess_elevation(z,v,.04093567251461988,backend='numpy',denoise=False)
        h.record_rejections(q.rejected_mask,0,0,264.129,np.full((3,3),263.929),elevation=z)
        h.fuse(np.where(q.observed_quality,z,np.nan),v,0,0,264.129,observation_time=263.929)
        h.window(0,0,3,264.129,reference_height=-.04)
        outputs.append([bool(h.last_window_incompatible_mask[1,1]),
                        bool(np.isfinite(h.last_window_obstacle_elevation[1,1]))])
    assert outputs==[[False,False],[False,False]]
