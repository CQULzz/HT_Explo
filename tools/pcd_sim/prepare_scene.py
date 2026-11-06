"""Rebuild a bounded measured PCD scene from exported XYZ arrays and a template."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial import Delaunay, cKDTree

from scene_config import SceneConfig


def measured_ground(points):
    near = points[(np.linalg.norm(points[:, :2], axis=1) < 8) &
                  (points[:, 2] > -1.05) & (points[:, 2] < -.65)]
    if len(near) < 3:
        raise ValueError('Insufficient measured ground near the original origin')
    plane = np.array([0., 0., np.median(near[:, 2])])
    design = np.column_stack([near[:, :2], np.ones(len(near))])
    for _ in range(8):
        keep = abs(near[:, 2]-design@plane) < .06
        if keep.sum() < 3 or np.linalg.matrix_rank(design[keep]) < 3:
            raise ValueError('Measured ground cannot determine a stable plane')
        plane = np.linalg.lstsq(design[keep], near[keep, 2], rcond=None)[0]
    heights = np.column_stack([points[:, :2], np.ones(len(points))])@plane
    floor = points[abs(points[:, 2]-heights) < .15]
    _, indices = np.unique(np.floor(floor[:, :2]/.08).astype(int), axis=0, return_index=True)
    floor = floor[indices]
    triangulation = Delaunay(floor[:, :2])
    triangles = floor[triangulation.simplices]
    edges = np.stack([np.linalg.norm(triangles[:, i, :2]-triangles[:, (i+1)%3, :2], axis=1)
                      for i in range(3)])
    valid = (edges.max(axis=0) <= .8) & (np.ptp(triangles[:, :, 2], axis=1) < .2)
    top = triangles[valid].copy()
    if not len(top):
        raise ValueError('No measured triangles meet the ground continuity limits')
    flip = np.cross(top[:, 1]-top[:, 0], top[:, 2]-top[:, 0])[:, 2] < 0
    top[flip] = top[flip][:, [0, 2, 1]]
    obstacle_points = points[(points[:, 2] > heights+.17) & (points[:, 2] < heights+3.5)]
    return plane, triangulation, valid, top, obstacle_points


def ground_prisms(top):
    faces = [top, top[:, [0, 2, 1]]-[0, 0, .12]]
    for index in range(3):
        first, second = top[:, index], top[:, (index+1)%3]
        bottom_first, bottom_second = first-[0, 0, .12], second-[0, 0, .12]
        faces.extend([np.stack([first, bottom_first, second], axis=1),
                      np.stack([second, bottom_first, bottom_second], axis=1)])
    return np.concatenate(faces)


def obstacle_faces(points, resolution=.16):
    cells = np.unique(np.floor(points/resolution).astype(int), axis=0)
    occupied = set(map(tuple, cells))
    definitions = [
        (0, 1, [(1,0,0), (1,1,0), (1,1,1), (1,0,1)]),
        (0, -1, [(0,0,0), (0,0,1), (0,1,1), (0,1,0)]),
        (1, 1, [(0,1,0), (0,1,1), (1,1,1), (1,1,0)]),
        (1, -1, [(0,0,0), (1,0,0), (1,0,1), (0,0,1)]),
        (2, 1, [(0,0,1), (1,0,1), (1,1,1), (0,1,1)]),
        (2, -1, [(0,0,0), (0,1,0), (1,1,0), (1,0,0)])]
    faces = []
    for cell in cells:
        for axis, sign, vertices in definitions:
            neighbour = cell.copy()
            neighbour[axis] += sign
            if tuple(neighbour) in occupied:
                continue
            face = (np.array(vertices)+cell)*resolution
            faces.extend([face[[0, 1, 2]], face[[0, 2, 3]]])
    return np.array(faces).reshape(-1, 3, 3)


def write_collada(path, triangles):
    namespace = 'http://www.collada.org/2005/11/COLLADASchema'
    ET.register_namespace('', namespace)
    def tag(name):return '{'+namespace+'}'+name
    root = ET.Element(tag('COLLADA'), version='1.4.1')
    asset = ET.SubElement(root, tag('asset'))
    ET.SubElement(asset, tag('unit'), name='meter', meter='1')
    ET.SubElement(asset, tag('up_axis')).text = 'Z_UP'
    geometry = ET.SubElement(ET.SubElement(root, tag('library_geometries')), tag('geometry'), id='mesh')
    mesh = ET.SubElement(geometry, tag('mesh'))
    vertices = triangles.reshape(-1, 3)
    normals = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    if np.any(lengths == 0):
        raise ValueError('Degenerate scene triangle')
    normals = np.repeat(normals/lengths[:, None], 3, axis=0)
    for name, values in [('positions', vertices), ('normals', normals)]:
        source = ET.SubElement(mesh, tag('source'), id=name)
        ET.SubElement(source, tag('float_array'), id=name+'-array', count=str(values.size)).text = ' '.join(
            f'{value:.9g}' for value in values.ravel())
        technique = ET.SubElement(source, tag('technique_common'))
        accessor = ET.SubElement(technique, tag('accessor'), source='#'+name+'-array', count=str(len(values)), stride='3')
        for axis in 'XYZ':ET.SubElement(accessor, tag('param'), name=axis, type='float')
    node = ET.SubElement(mesh, tag('vertices'), id='vertices')
    ET.SubElement(node, tag('input'), semantic='POSITION', source='#positions')
    node = ET.SubElement(mesh, tag('triangles'), count=str(len(triangles)))
    ET.SubElement(node, tag('input'), semantic='VERTEX', source='#vertices', offset='0')
    ET.SubElement(node, tag('input'), semantic='NORMAL', source='#normals', offset='1')
    ET.SubElement(node, tag('p')).text = ' '.join(f'{index} {index}' for index in range(len(vertices)))
    visual = ET.SubElement(ET.SubElement(root, tag('library_visual_scenes')), tag('visual_scene'), id='scene')
    ET.SubElement(ET.SubElement(visual, tag('node')), tag('instance_geometry'), url='#mesh')
    ET.SubElement(ET.SubElement(root, tag('scene')), tag('instance_visual_scene'), url='#scene')
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def prepare(points_path, template_path, output, config):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    source = np.load(points_path)
    if source.ndim != 2 or source.shape[1] < 3:
        raise ValueError('Expected an exported Nx3 or Nx4 point array')
    points = source[:, :3].astype(float)
    points = points[np.isfinite(points).all(axis=1) & config.contains_xy(points) &
                    (points[:, 2] > -2) & (points[:, 2] < 5)]
    plane, triangulation, valid, top, obstacles = measured_ground(points)
    scene = ET.parse(template_path)
    scout = scene.find(".//world/model[@name='scout']")
    if scout is None or scout.find('pose') is None:
        raise ValueError('Template must contain Scout with its verified spawn pose')
    spawn = np.array(list(map(float, scout.find('pose').text.split()))[:3])
    # Retain the original start, checking measured support instead of relocating
    # the robot when a larger crop happens to contain a different floor patch.
    dx, dy = np.meshgrid(np.linspace(-.8, .8, 17), np.linspace(-.8, .8, 17))
    disk = np.column_stack([dx.ravel(), dy.ravel()])
    disk = disk[np.linalg.norm(disk, axis=1) <= .8]
    simplex = triangulation.find_simplex(spawn[:2]+disk)
    if np.any(simplex < 0) or not valid[simplex].all():
        raise ValueError('Original spawn lacks a continuous measured floor footprint')
    if len(obstacles) and cKDTree(obstacles[:, :2]).query(spawn[:2])[0] < 1.05:
        raise ValueError('Original spawn is too close to measured obstacles')
    polygon = np.array(config.navigation_polygon)
    if not (polygon[:, 0].min() < spawn[0] < polygon[:, 0].max() and
            polygon[:, 1].min() < spawn[1] < polygon[:, 1].max()):
        raise ValueError('Original spawn falls outside the navigation boundary')
    models = [scene.find(f".//world/model[@name='{name}']") for name in ('ground', 'obstacles')]
    if any(model is None for model in models):
        raise ValueError('Template requires ground and obstacles models')
    destination=output
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.'+destination.name+'-',dir=destination.parent) as temporary:
        output=Path(temporary)/'scene'
        output.mkdir()
        (output/'assets').mkdir()
        for model, triangles in zip(models, (ground_prisms(top), obstacle_faces(obstacles))):
            mesh_path = output/'assets'/(model.get('name')+'.dae')
            write_collada(mesh_path, triangles)
            for uri in model.findall('.//mesh/uri'):uri.text = (destination/'assets'/mesh_path.name).as_uri()
        scene.write(output/'scene.sdf', encoding='utf-8', xml_declaration=True)
        shutil.copy2(points_path, output/'local_map.npy')
        config.write(output/'scene_config.json')
        for name in ('mapper_strict.py','mapper_execution.py','mapper_core.yaml',
                     'mapper_setup.yaml','candidate_extrinsics.yaml'):
            source_file=Path(template_path).parent/name
            if source_file.is_file():shutil.copy2(source_file,output/name)
        np.savez_compressed(output/'scene_meshes.npz', ground_top=top, spawn=spawn, ground_plane=plane)
        manifest = {'scene_config': config.to_dict(), 'source_array': str(Path(points_path).resolve()),
                    'source_sha256': hashlib.sha256(Path(points_path).read_bytes()).hexdigest(),
                    'template_sha256': hashlib.sha256(Path(template_path).read_bytes()).hexdigest(),
                    'ground_triangles': len(top), 'ground_max_bridge_edge_m': .8,
                    'obstacle_voxel_m': .16, 'spawn_base_xyz': spawn.tolist(),
                    'unmeshed_gaps': 'Retained as unknown',
                    'scene_sha256': hashlib.sha256((output/'scene.sdf').read_bytes()).hexdigest(),
                    'geometry_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                        for path in (output/'assets').glob('*.dae')}}
        (output/'SCENE_MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
        if destination.exists():raise FileExistsError(destination)
        output.rename(destination)
        return manifest



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--points', type=Path, required=True)
    parser.add_argument('--template', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bounds', type=float, nargs=4, metavar=('XMIN','XMAX','YMIN','YMAX'), required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.points, args.template, args.output,
                             SceneConfig(bounds_xy_m=tuple(args.bounds))), indent=2))
