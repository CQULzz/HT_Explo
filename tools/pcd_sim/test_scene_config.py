import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from scene_config import SceneConfig, load_scene_config, verify_scene
from prepare_scene import prepare


def test_large_shifted_scene_voxels_have_unique_keys():
    config = SceneConfig(bounds_xy_m=(-10, 10, -1, 250))
    points = np.array([[.1, 200.3, .1], [.3, .3, .1]])
    old = np.floor((points+[20,20,5])/.2).astype(np.int64)
    old_keys = old[:,0]*1000000+old[:,1]*1000+old[:,2]
    assert old_keys[0] == old_keys[1]
    assert len(np.unique(config.voxel_keys(points))) == 2


def test_default_metric_preserves_voxel_partition_and_handles_noncentral_bounds():
    points = np.random.default_rng(42).uniform([-14.99,-14.99,-1.49],[14.99,14.99,2.49],(10000,3))
    old = np.floor((points+[20,20,5])/.2).astype(np.int64)
    keys = old[:,0]*1000000+old[:,1]*1000+old[:,2]
    assert len(np.unique(keys)) == len(np.unique(SceneConfig().voxel_keys(points)))
    shifted = SceneConfig(bounds_xy_m=(20,80,-50,-10))
    assert shifted.contains_xy(np.array([[50,-30],[0,0]])).tolist() == [True,False]
    assert shifted.image_xy(50,-30) == (320,340)
    with pytest.raises(ValueError):shifted.voxel_keys(np.array([[0,0,0]]))


@pytest.mark.parametrize('values', [dict(bounds_xy_m=(1,0,0,10)),
    dict(bounds_xy_m=(-1,1,-1,1)),dict(metric_voxel_m=0),
    dict(bounds_xy_m=(-15,float('inf'),-15,15)),dict(navigation_inset_m=-1)])
def test_invalid_scene_parameters_are_rejected(values):
    with pytest.raises(ValueError):SceneConfig(**values)


def test_legacy_runtime_fallback_and_larger_bounds_require_real_geometry(tmp_path):
    assert load_scene_config(tmp_path) == SceneConfig()
    verify_scene(tmp_path,SceneConfig())
    with pytest.raises(ValueError,match='manifest'):
        verify_scene(tmp_path,SceneConfig(bounds_xy_m=(-30,30,-30,30)))


@pytest.fixture
def source(tmp_path):
    x,y = np.meshgrid(np.arange(-3.9,4,.2),np.arange(-3.9,4,.2))
    floor = np.column_stack([x.ravel(),y.ravel(),np.full(x.size,-.8)])
    floor = floor[~((floor[:,0]>1.5)&(floor[:,0]<3))]
    points = np.vstack([floor,[3.5,3.5,0]])
    array = tmp_path/'points.npy'
    np.save(array,points)
    template = tmp_path/'template.sdf'
    template.write_text('''<sdf version="1.10"><world name="test">
      <model name="scout"><pose>0 0 -.53521 0 0 0</pose></model>
      <model name="ground"><link name="link"><collision name="collision"><geometry><mesh><uri>old-ground</uri></mesh></geometry></collision></link></model>
      <model name="obstacles"><link name="link"><collision name="collision"><geometry><mesh><uri>old-obstacles</uri></mesh></geometry></collision></link></model>
      </world></sdf>''')
    return array,template


def test_prepare_scene_retains_measured_gaps_spawn_and_hashes(source,tmp_path):
    array,template = source
    output = tmp_path/'new scene'
    config = SceneConfig(bounds_xy_m=(-4,4,-4,4))
    receipt = prepare(array,template,output,config)
    verify_scene(output,load_scene_config(output))
    triangles = np.load(output/'scene_meshes.npz')['ground_top']
    edges = [np.linalg.norm(triangles[:,i,:2]-triangles[:,(i+1)%3,:2],axis=1) for i in range(3)]
    assert max(map(np.max,edges)) <= .8
    assert receipt['spawn_base_xyz'] == [0,0,-.53521]
    assert np.array_equal(np.load(output/'local_map.npy'),np.load(array))
    uris = [node.text for node in ET.parse(output/'scene.sdf').iter('uri')]
    from urllib.parse import unquote, urlparse
    assert all(Path(unquote(urlparse(uri).path)).parent == output/'assets' for uri in uris)
    with pytest.raises(FileExistsError):prepare(array,template,output,config)
    (output/'assets/ground.dae').write_text('changed mesh')
    with pytest.raises(ValueError,match='hash'):verify_scene(output,config)


def test_failed_scene_write_leaves_destination_available_for_retry(source,tmp_path,monkeypatch):
    import prepare_scene
    def fail(*args):raise OSError('injected mesh IO failure')
    monkeypatch.setattr(prepare_scene,'write_collada',fail)
    output = tmp_path/'failed'
    with pytest.raises(OSError):prepare(*source,output,SceneConfig(bounds_xy_m=(-4,4,-4,4)))
    assert not output.exists()
