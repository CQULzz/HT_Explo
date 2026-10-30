"""Identify the modules actually imported, without dumping argv or environment."""
import hashlib
import json
from pathlib import Path
import platform
import sys


def file_identity(path):
    p=Path(path).resolve()
    try:
        return {'path':str(p),'bytes':p.stat().st_size,
                'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    except OSError as exc:
        return {'path':str(p),'error':type(exc).__name__}


def collect_runtime_manifest(entry_path,weights_path,parameters,actual,topics,modules):
    sources={name:file_identity(getattr(module,'__file__',None))
             if getattr(module,'__file__',None) else {'error':'module_has_no_file'}
             for name,module in modules.items()}
    manifest={'schema_version':1,'scope':'HT process only; upstream mapper/TF/vehicle not attested',
              'entry':file_identity(entry_path),'weights':file_identity(weights_path),
              'modules':sources,'parameters':dict(parameters),'actual':dict(actual),
              'topics':dict(topics),'python_executable':sys.executable,
              'python_version':platform.python_version(),'machine':platform.machine()}
    canonical=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()
    manifest['runtime_id']=hashlib.sha256(canonical).hexdigest()
    return manifest
