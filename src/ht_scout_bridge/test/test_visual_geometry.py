"""Guard URDF shell coverage without expanding the filter onto nearby ground."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json

import numpy as np
import yaml

from ht_scout_bridge.geometry import self_filter_keep_mask,from_config


HERE = Path(__file__).resolve().parent
FIXTURES = HERE / 'fixtures' / 'urdf_visual_completion'
PROFILE = HERE.parent / 'config' / 'scout_extrinsics.yaml'


def profiles():
    old = yaml.safe_load((FIXTURES / 'old_scout_extrinsics.yaml').read_text())
    current = yaml.safe_load(PROFILE.read_text())
    return old, current


def mask(points, profile):
    # Fixture vertices are body-frame coordinates, not points from a sensor at
    # the body origin. Keep the calibrated lidar origin for ray visibility.
    transforms=profile['transforms']
    t=(from_config(transforms['base_link_to_sensor_kit'])
       @from_config(transforms['sensor_kit_to_helios'])
       @from_config(transforms['helios_to_lidar']))
    lidar=(points-t[:3,3])@t[:3,:3]
    return self_filter_keep_mask(lidar, profile['lidar_self_filter'], t)


def test_fixture_hashes_match_recorded_external_geometry_source():
    source = json.loads((FIXTURES / 'SOURCE.json').read_text())
    assert source['source']['commit'] == 'cf0b73d7d01b4b6a2718c7ff3124f4b7a3368c36'
    assert source['source']['urdf_git_blob'] == 'ec5bda24ffb53d8ecb9a97b2155dee0d1993a9c3'
    assert source['source']['dae_git_blob'] == '34799c4925eb67654b31421aad32629f1b4216a2'
    for entry in source['files']:
        data = (FIXTURES / entry['name']).read_bytes()
        assert len(data) == entry['bytes']
        assert hashlib.sha256(data).hexdigest() == entry['sha256']


def test_only_five_visual_boxes_added_and_calibration_unchanged():
    old, current = profiles()
    assert current['transforms'] == old['transforms']
    assert current['frames'] == old['frames']
    before, after = old['lidar_self_filter'], current['lidar_self_filter']
    assert len(before['boxes']) == 9
    assert len(after['boxes']) == 14
    assert after['boxes'][:9] == before['boxes']
    assert after['cylinders'] == before['cylinders']
    assert len(after['cylinders']) == 4
    assert after['padding_m'] == before['padding_m'] == .02
    assert after['frame'] == before['frame'] == 'base_link'
    assert after['enabled'] == before['enabled'] is True


def test_added_boxes_match_original_dae_bounds_with_single_padding():
    _, current = profiles()
    source = json.loads((FIXTURES / 'SOURCE.json').read_text())
    boxes = current['lidar_self_filter']['boxes'][9:]
    for box, part in zip(boxes, source['source']['parts'], strict=True):
        assert box == part['filter_box']
        np.testing.assert_allclose(box['min_xyz'], np.array(part['raw_min_xyz']) - .02,
                                   rtol=0, atol=1e-15)
        np.testing.assert_allclose(box['max_xyz'], np.array(part['raw_max_xyz']) + .02,
                                   rtol=0, atol=1e-15)


def test_all_87098_original_visual_vertices_covered():
    old, current = profiles()
    with np.load(FIXTURES / 'base_visual_vertices.npz', allow_pickle=False) as saved:
        assert saved['points'].shape == (87098, 3)
        np.testing.assert_array_equal(mask(saved['points'], old), saved['kept'])
        assert int(saved['kept'].sum()) == 6522
        assert not mask(saved['points'], current).any()


def test_added_geometry_removes_no_additional_flat_ground():
    old, current = profiles()
    with np.load(FIXTURES / 'geometry_test_samples.npz', allow_pickle=False) as saved:
        ground = saved['ground']
        assert np.all(ground[:, 2] == -.23479)
        before, after = mask(ground, old), mask(ground, current)
        np.testing.assert_array_equal(after, before)
        assert len(ground) == 90601 and int(after.sum()) == 89581
        # Existing padded wheel cylinders intersect this plane. The new shell
        # must add no deletions; this is not a claim of 100% ground retention.
        assert not mask(saved['wheel_contacts'], old).any()
        assert not mask(saved['wheel_contacts'], current).any()


def test_external_fixture_retains_all_physically_unobscured_points():
    old, current = profiles()
    with np.load(FIXTURES / 'geometry_test_samples.npz', allow_pickle=False) as saved:
        points=saved['external_obstacles']
        assert points.shape == (48, 3)
        assert mask(points, old).all()
        # These old fixtures were outside the body, but four lie *behind*
        # actual wheel collision solids. Check that distinction independently
        # using dense finite-segment samples and the unpadded source dimensions.
        transforms=current['transforms']
        t=(from_config(transforms['base_link_to_sensor_kit'])
           @from_config(transforms['sensor_kit_to_helios'])
           @from_config(transforms['helios_to_lidar']))
        origin=t[:3,3]
        rays=origin+(points[:,None]-origin)*np.linspace(.001,.999,2001)[None,:,None]
        hidden=np.zeros(len(points),bool)
        for cylinder in current['lidar_self_filter']['cylinders']:
            local=rays-np.asarray(cylinder['center_xyz'])
            radius=cylinder['radius']-.02
            half=cylinder['half_length']-.02
            hidden|=((local[:,:,0]**2+local[:,:,2]**2<radius**2)
                     &(np.abs(local[:,:,1])<half)).any(axis=1)
        assert hidden.sum()==4
        naive=deepcopy(current)
        naive['lidar_self_filter']['wheel_occlusion']['preserve_vertical_support']=False
        # Padded shadows alone also erase two physically unobscured points.
        # The visible upper parts of these fixture posts must protect all
        # their lower returns, including those geometrically behind a wheel.
        naive_kept=mask(points,naive)
        assert (~naive_kept & ~hidden).sum()==2
        assert (~naive_kept).sum()==6
        assert mask(points,current).all()
