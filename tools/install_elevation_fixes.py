#!/usr/bin/env python3
"""Apply the versioned mapping patch to a separate CuPy workspace."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import yaml


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--build',action='store_true')
    args=parser.parse_args()
    workspace=args.workspace.expanduser().resolve()
    repository=workspace/'src/elevation_mapping_cupy_2204'
    bundle=Path(__file__).resolve().parent/'elevation_mapping_fixes'
    patch=bundle/'cupy_ht_mapping.patch'
    if not (repository/'.git').exists():raise RuntimeError(f'Missing independent checkout: {repository}')
    check=subprocess.run(['git','apply','--reverse','--check',str(patch)],cwd=repository,capture_output=True)
    if check.returncode:
        subprocess.run(['git','apply','--check',str(patch)],cwd=repository,check=True)
        subprocess.run(['git','apply',str(patch)],cwd=repository,check=True)
    config=workspace/'config';config.mkdir(exist_ok=True)
    core=yaml.safe_load((bundle/'trial_core.yaml').read_text())
    core['weight_file']='$(rospack find elevation_mapping_cupy)/config/core/weights.dat'
    core['plugin_config_file']=str(config/'trial_plugins.yaml')
    (config/'trial_core.yaml').write_text(yaml.safe_dump(core,sort_keys=False))
    for name in ['trial_setup.yaml','trial_plugins.yaml']:shutil.copy2(bundle/name,config/name)
    if args.build:
        subprocess.run(['colcon','build','--packages-select','elevation_mapping_cupy'],cwd=workspace,check=True)
    print(json.dumps({'workspace':str(workspace),'patched':True,'built':args.build},indent=2))


if __name__=='__main__':main()
