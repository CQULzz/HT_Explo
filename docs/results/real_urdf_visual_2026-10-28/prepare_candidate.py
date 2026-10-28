#!/usr/bin/env python3
"""Reproduce the URDF-derived geometry candidate; no ROS/device startup.

Inputs are the immutable source bundle shipped in this experiment Release.
Use an empty --output directory; --old-profile must be the nine-box baseline.
"""
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import yaml

PAD = .02


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--repo', type=Path, required=True)
    cli.add_argument('--source', type=Path, required=True)
    cli.add_argument('--old-profile', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True)
    args = cli.parse_args()
    ROOT, SOURCE, PROFILE, OUT = args.repo.resolve(), args.source.resolve(), args.old_profile.resolve(), args.output.resolve()
    OUT.mkdir(parents=True, exist_ok=False)
    source_meta = json.loads((SOURCE / 'SOURCE_FILES.json').read_text())
    known = {row['name']: row for row in source_meta['files']}
    for name in ['base_link.dae', 'scout_sensor_rack.urdf.xacro', 'base_visual_gap.npz', 'visual_gap_raw_scan_check.json']:
        assert sha((SOURCE / name).read_bytes()) == known[name]['sha256'], name
    dae_bytes = (SOURCE / 'base_link.dae').read_bytes()
    urdf_bytes = (SOURCE / 'scout_sensor_rack.urdf.xacro').read_bytes()
    assert blob(urdf_bytes) == source_meta['urdf_git_blob']
    tree = ET.fromstring(dae_bytes)
    ns = {'c': tree.tag.split('}')[0][1:]}
    assert tree.find('c:asset/c:unit', ns).attrib['meter'] == '1.0'
    assert tree.find('c:asset/c:up_axis', ns).text == 'Z_UP'
    # Source scene instances contain no transform; the URDF visual has neither
    # origin nor mesh scale, so these positions are already in base_link.
    for node in tree.findall('.//c:visual_scene/c:node', ns):
        assert not any(child.tag.split('}')[-1] in ['matrix', 'translate', 'rotate', 'scale', 'lookat', 'skew'] for child in node)
        assert not node.findall('c:node', ns)
    visual = ET.fromstring(urdf_bytes).find("link[@name='base_link']/visual")
    assert visual is not None and visual.find('origin') is None
    assert visual.find('geometry/mesh').attrib == {'filename': 'package://ele_scout_kit/meshes/base_link.dae'}
    old_bytes = PROFILE.read_bytes()
    old = yaml.safe_load(old_bytes)
    assert len(old['lidar_self_filter']['boxes']) == 9
    assert len(old['lidar_self_filter']['cylinders']) == 4
    candidate = deepcopy(old)
    parts, all_points, new_boxes = [], [], []
    proposed = json.loads((SOURCE / 'visual_gap_raw_scan_check.json').read_text())['proposed_boxes']
    geometries = tree.findall('c:library_geometries/c:geometry', ns)
    assert len(geometries) == len(proposed) == 5
    for index, geometry in enumerate(geometries):
        mesh = geometry.find('c:mesh', ns)
        position_inputs = [item for item in mesh.findall('c:vertices/c:input', ns) if item.attrib['semantic'] == 'POSITION']
        assert len(position_inputs) == 1
        source_id = position_inputs[0].attrib['source'].removeprefix('#')
        positions = next(item for item in mesh.findall('c:source', ns) if item.attrib['id'] == source_id)
        values = positions.find('c:float_array', ns)
        accessor = positions.find('c:technique_common/c:accessor', ns)
        assert int(accessor.attrib['stride']) == 3 and int(accessor.attrib.get('offset', 0)) == 0
        assert accessor.attrib['source'] == '#' + values.attrib['id']
        raw = np.fromstring(values.text, sep=' ', dtype=np.float64)
        assert len(raw) == int(values.attrib['count']) == int(accessor.attrib['count']) * 3
        points = raw.reshape(-1, 3)
        assert np.isfinite(points).all()
        lower, upper = points.min(axis=0), points.max(axis=0)
        padded_lower, padded_upper = lower - PAD, upper + PAD
        # Confirm the prior proposal against untruncated DAE numeric data.
        np.testing.assert_array_equal(padded_lower, np.asarray(proposed[index]['min']))
        np.testing.assert_array_equal(padded_upper, np.asarray(proposed[index]['max']))
        box = {'name': 'base_visual_' + geometry.attrib['id'] + '_' + geometry.attrib['name'],
               'min_xyz': padded_lower.tolist(), 'max_xyz': padded_upper.tolist()}
        new_boxes.append(box)
        all_points.append(points)
        parts.append({'geometry_id': geometry.attrib['id'], 'geometry_name': geometry.attrib['name'],
                      'position_source_id': source_id, 'float_array_id': values.attrib['id'],
                      'position_vertices': len(points), 'raw_min_xyz': lower.tolist(), 'raw_max_xyz': upper.tolist(),
                      'padding_already_in_bounds_m': PAD, 'filter_box': box})
    candidate['lidar_self_filter']['boxes'].extend(new_boxes)
    provenance = {'repository': source_meta['repository'], 'commit': source_meta['fixed_commit'],
                  'urdf_git_blob': source_meta['urdf_git_blob'], 'urdf_sha256': sha(urdf_bytes),
                  'dae_repository_path': 'src/ele_scout_kit/meshes/base_link.dae',
                  'dae_git_blob': blob(dae_bytes), 'dae_sha256': sha(dae_bytes),
                  'candidate_old_config_sha256': sha(old_bytes),
                  'derivation': 'Per-geometry POSITION data in meter/Z_UP/base_link; no scene or URDF visual transform',
                  'padding_rule': '0.02m included exactly once in each new min/max; existing padding_m is descriptive and geometry.py does not add it again',
                  'parts': parts}
    candidate['lidar_self_filter']['visual_completion_candidate'] = provenance
    assert candidate['transforms'] == old['transforms']
    assert candidate['lidar_self_filter']['boxes'][:9] == old['lidar_self_filter']['boxes']
    assert candidate['lidar_self_filter']['cylinders'] == old['lidar_self_filter']['cylinders']
    target = OUT / 'candidate_scout_extrinsics.yaml'
    target.write_text('# Offline-tested candidate: five URDF base_link visual AABBs complete the existing filter.\n' + yaml.safe_dump(candidate, sort_keys=False, allow_unicode=True))
    spec = importlib.util.spec_from_file_location('candidate_geometry', ROOT / 'src/ht_scout_bridge/ht_scout_bridge/geometry.py')
    geometry_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(geometry_module)
    old_filter, new_filter = old['lidar_self_filter'], candidate['lidar_self_filter']
    apply = lambda points, profile: geometry_module.self_filter_keep_mask(points, profile, np.eye(4))
    points = np.concatenate(all_points)
    with np.load(SOURCE / 'base_visual_gap.npz', allow_pickle=False) as gap:
        np.testing.assert_array_equal(points, gap['points'])
        np.testing.assert_array_equal(apply(points, old_filter), gap['kept'])
    old_kept, new_kept = apply(points, old_filter), apply(points, new_filter)
    assert len(points) == 87098 and int(old_kept.sum()) == 6522 and not new_kept.any()
    # Full flat plane includes wheel contact areas already masked by original
    # cylinders. Added chassis boxes must not remove one more ground point.
    x, y = np.meshgrid(np.linspace(-1.5, 1.5, 301), np.linspace(-1.5, 1.5, 301), indexing='ij')
    ground = np.c_[x.ravel(), y.ravel(), np.full(x.size, -.23479)]
    old_ground, new_ground = apply(ground, old_filter), apply(ground, new_filter)
    np.testing.assert_array_equal(old_ground, new_ground)
    wheel_contacts = np.asarray([[item['center_xyz'][0], item['center_xyz'][1], -.23479] for item in old_filter['cylinders']])
    assert not apply(wheel_contacts, old_filter).any()
    assert not apply(wheel_contacts, new_filter).any()
    # Independent obstacle samples outside every body volume are retained.
    obstacle_xy = np.asarray([[.55, 0], [-.55, 0], [0, .43], [0, -.43],
                              [.55, .43], [.55, -.43], [-.55, .43], [-.55, -.43]])
    obstacles = np.asarray([[px, py, z] for px, py in obstacle_xy for z in [-.20, -.15, -.10, -.05, 0., .05]])
    assert apply(obstacles, old_filter).all() and apply(obstacles, new_filter).all()
    verification = {'scope': 'Pure NumPy geometry-only candidate checks; no ROS, replay, navigation or target ARM test',
                    'candidate_old_config_sha256': sha(old_bytes), 'candidate_sha256': sha(target.read_bytes()),
                    'production_geometry_sha256': sha((ROOT / 'src/ht_scout_bridge/ht_scout_bridge/geometry.py').read_bytes()),
                    'source': provenance, 'box_count_before': 9, 'box_count_candidate': 14, 'cylinders_unchanged': 4,
                    'all_existing_boxes_transforms_and_cylinders_identical': True,
                    'raw_dae_bounds_exactly_match_proposed_boxes': True,
                    'visual_vertices': len(points), 'old_visual_vertices_kept': int(old_kept.sum()),
                    'candidate_visual_vertices_kept': int(new_kept.sum()),
                    'ground_plane_base_z_m': -.23479, 'ground_plane_samples': len(ground),
                    'ground_old_kept': int(old_ground.sum()), 'ground_candidate_kept': int(new_ground.sum()),
                    'new_ground_removals': int((old_ground & ~new_ground).sum()),
                    'ground_masks_identical': True, 'original_wheel_contact_ground_points_masked': wheel_contacts.tolist(),
                    'ground_limit': 'Cannot claim full-plane 100% retained: original 2cm padded wheel cylinders intersect the plane; the candidate adds zero ground removals',
                    'external_near_ground_obstacle_samples': len(obstacles),
                    'external_obstacle_samples_all_retained': True,
                    'limits': ['AABB covers empty corners as well as mesh vertices; mesh coverage alone does not prove no real obstacle deletion',
                               '1032 saved returns inside proposed boxes are candidates, not labeled vehicle truth',
                               'No claim that lower HT probabilities or invalid starts are fixed without independent raw-to-map-to-HT rerun']}
    write_json(OUT / 'CANDIDATE_VALIDATION.json', verification)
    np.savez_compressed(OUT / 'geometry_test_samples.npz', ground=ground, ground_old_kept=old_ground,
                        ground_candidate_kept=new_ground, external_obstacles=obstacles, wheel_contacts=wheel_contacts)
    print(json.dumps({key: verification[key] for key in ['visual_vertices', 'old_visual_vertices_kept', 'candidate_visual_vertices_kept',
                                                        'ground_plane_samples', 'ground_old_kept', 'ground_candidate_kept', 'new_ground_removals',
                                                        'external_near_ground_obstacle_samples', 'external_obstacle_samples_all_retained']}))


if __name__ == '__main__':
    main()
