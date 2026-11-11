"""Install reviewed mapper overrides only onto the recorded, isolated base."""
import argparse,hashlib,json
from pathlib import Path

def apply(root):
    here=Path(__file__).resolve().parent
    manifest=json.loads((here/'MAPPER_BASE_FILES.json').read_text())
    source=Path(root)/manifest['source_root']
    for name,expected in manifest['sha256'].items():
        actual=hashlib.sha256((source/name).read_bytes()).hexdigest()
        revised=hashlib.sha256((here/'mapper_patch'/name).read_bytes()).hexdigest()
        if actual not in (expected,revised):
            raise RuntimeError(f'Refusing unknown mapper source: {source/name}')
    for name in manifest['sha256']:
        (source/name).write_bytes((here/'mapper_patch'/name).read_bytes())
    return {name:hashlib.sha256((source/name).read_bytes()).hexdigest()
            for name in manifest['sha256']}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source_root')
    print(json.dumps(apply(parser.parse_args().source_root),indent=2))
