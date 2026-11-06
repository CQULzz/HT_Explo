"""Prepare a CMU AEDE world with the verified Scout simulation model."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

from scene_config import SceneConfig, verify_scene

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'experiments'))
from coverage_metrics import read_reference_ply


def prepare(workspace, template, output, world_name='indoor'):
    workspace=Path(workspace).resolve(strict=True)
    template=Path(template).resolve(strict=True)
    output=Path(output).resolve()
    if output.exists():raise FileExistsError(output)
    package=workspace/'src/vehicle_simulator'
    model_dir=package/'mesh'/world_name
    source_world=package/'world'/(world_name+'.world')
    native_world=ET.parse(source_world).getroot().find('world')
    includes=[node.findtext('uri') for node in native_world.findall('include')]
    if includes!=['model://'+world_name]:raise ValueError('Expected one native environment model')
    model=ET.parse(model_dir/'model.sdf').getroot().find('model')
    points=read_reference_ply(model_dir/'preview/pointcloud.ply')
    finite=points[np.isfinite(points).all(axis=1)]
    xmin,ymin=np.floor(finite[:,:2].min(axis=0))
    xmax,ymax=np.ceil(finite[:,:2].max(axis=0))
    config=SceneConfig(bounds_xy_m=(float(xmin),float(xmax),float(ymin),float(ymax)))
    near=finite[(np.linalg.norm(finite[:,:2],axis=1)<1.)&(finite[:,2]<.1)]
    if len(near)<20:raise ValueError('CMU origin requires measured ground reference')
    ground_z=float(np.median(near[:,2]))
    scene=ET.parse(template)
    scout=deepcopy(scene.find(".//world/model[@name='scout']"))
    if scout is None:raise ValueError('Scout template missing')
    pose=scout.find('pose')
    pose.text=f'0 0 {ground_z+.23479+.03:.17g} 0 0 0'
    # Carry the tested Scout physics/sensor systems into the complete native
    # environment geometry. AEDE's environment model and textures stay intact.
    target_world=scene.getroot().find('world')
    for child in list(target_world):
        if child.tag in ('model','include'):target_world.remove(child)
    model=deepcopy(model)
    target_world.append(model)
    target_world.append(scout)
    gravity=target_world.find('gravity')
    if gravity is None:gravity=ET.SubElement(target_world,'gravity')
    gravity.text='0 0 -9.8'
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='.'+output.name+'-') as temporary:
        staging=Path(temporary)/'runtime'
        staging.mkdir()
        asset_dir=staging/'assets'/('cmu_'+world_name)
        shutil.copytree(model_dir,asset_dir)
        for uri in model.iter('uri'):
            prefix='model://'+world_name+'/'
            if not uri.text.startswith(prefix):raise ValueError('Unsupported CMU model URI')
            relative=uri.text[len(prefix):]
            uri.text=(output/'assets'/('cmu_'+world_name)/relative).as_uri()
        scene.write(staging/'scene.sdf',encoding='utf-8',xml_declaration=True)
        np.save(staging/'local_map.npy',points)
        config.write(staging/'scene_config.json')
        for name in ('mapper_strict.py','mapper_execution.py','mapper_core.yaml',
                     'mapper_setup.yaml','candidate_extrinsics.yaml'):
            shutil.copy2(template.parent/name,staging/name)
        manifest={'scene_kind':'CMU AEDE native environment model with Scout physics',
            'cmu_workspace':str(workspace),'world':world_name,
            'source_world_sha256':hashlib.sha256(source_world.read_bytes()).hexdigest(),
            'source_model_sha256':hashlib.sha256((model_dir/'model.sdf').read_bytes()).hexdigest(),
            'scout_template_sha256':hashlib.sha256(template.read_bytes()).hexdigest(),
            'scene_config':config.to_dict(),'spawn_base_xyz':[0,0,ground_z+.23479+.03],
            'ground_reference_z':ground_z,'reference_points':len(points),
            'scene_sha256':hashlib.sha256((staging/'scene.sdf').read_bytes()).hexdigest(),
            'geometry_sha256':{str(path.relative_to(staging/'assets')):hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in (staging/'assets').rglob('*') if path.is_file()}}
        (staging/'SCENE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
        if output.exists():raise FileExistsError(output)
        staging.rename(output)
    verify_scene(output,config)
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cmu-workspace',type=Path,required=True)
    parser.add_argument('--template',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--world',choices=['indoor'],default='indoor')
    args=parser.parse_args()
    print(json.dumps(prepare(args.cmu_workspace,args.template,args.output,args.world),indent=2))
