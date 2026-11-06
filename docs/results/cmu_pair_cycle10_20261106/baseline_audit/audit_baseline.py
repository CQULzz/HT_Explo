"""Read-only baseline provenance and configuration audit, without ROS execution."""
from pathlib import Path
import json
import hashlib
import difflib
import yaml
ROOT = Path(__file__).parent
PROJECT = Path('/home/lzz/HT_linux_cycle7_20261106/repo')
REFERENCE = Path('/home/lzz/HT_tare_reference_review_20261101')
UPSTREAM = REFERENCE/'upstream'
provenance = json.loads((REFERENCE/'UPSTREAM_SOURCES.json').read_text())
verified = []
for filename in ['UPSTREAM_SOURCES.json', 'ADDITIONAL_SOURCES.json', 'ARTIFACTS_SHA256.json']:
    payload = json.loads((REFERENCE/filename).read_text())
    def visit(value):
        if isinstance(value, dict):
            path = value.get('path', '')
            if path.endswith(('config/indoor.yaml', 'sensor_coverage_planner_ground.cpp')) and 'sha256' in value:
                candidate = REFERENCE/path if path.startswith('upstream/') else UPSTREAM/path
                if candidate.exists():
                    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
                    assert digest == value['sha256']
                    verified.append({'path': str(candidate), 'sha256': digest, 'source': filename})
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(payload)
assert any(x['path'].endswith('config/indoor.yaml') for x in verified)
assert any(x['path'].endswith('sensor_coverage_planner_ground.cpp') for x in verified)
actual_path = PROJECT/'src/ht_scout_bridge/config/tare_scout.yaml'
reference_path = UPSTREAM/'src/tare_planner/config/indoor.yaml'
actual = yaml.safe_load(actual_path.read_text())['/**']['ros__parameters']
reference = yaml.safe_load(reference_path.read_text())['tare_planner_node']['ros__parameters']
differences = {key: {'tested_scout_profile': actual.get(key), 'upstream_indoor': reference.get(key)} for key in sorted(actual.keys() | reference.keys()) if actual.get(key) != reference.get(key)}
source = Path('src/tare_planner/src/sensor_coverage_planner/sensor_coverage_planner_ground.cpp')
(ROOT/'PLANNER_DIFF.patch').write_text(''.join(difflib.unified_diff((UPSTREAM/source).read_text().splitlines(keepends=True), (PROJECT/source).read_text().splitlines(keepends=True), fromfile='upstream-b6760ad/'+str(source), tofile='tested-c6ca9c4/'+str(source))))
record = {'scope': 'Offline provenance audit of cycle10, no new simulator run and no production parameter mutation', 'upstream_repository': provenance['repository'], 'upstream_commit': provenance['commit'], 'verified_reference_files': verified, 'tested_launch': str(PROJECT/'tools/pcd_sim/tare_geometric.launch.py'), 'tested_profile': str(actual_path), 'upstream_profile': str(reference_path), 'profile_differences': differences, 'confirmed_design_differences': ['Launcher explicitly loads tare_scout.yaml with ht_enabled=False; upstream indoor profile is not selected.', 'Shared ConcatenateGlobalLocalPath return branch and checkedLookahead path remain active with HT disabled.', 'World is native indoor geometry plus Scout dynamic model and GPU scanner, not the complete native CMU vehicle/sensor stack.', 'Separate CMU terrain/command bridge parameters include deliberate safety and Scout geometry adaptation.'], 'causal_limit': 'This establishes a confounded baseline. It does not isolate which input, geometry, planner, or parameter caused zero eligible gain at20s, or which return prefix failed at36s.'}
(ROOT/'BASELINE_AUDIT.json').write_text(json.dumps(record, indent=2)+'\n')
print('Verified upstream', provenance['commit'], 'reference checks', len(verified), 'profile differences', len(differences))
print(json.dumps({k:v for k,v in differences.items() if k in ['kUseTerrainHeight','viewpoint_manager/resolution_x','kSurfaceCloudDwzLeafSize','kSensorRange','kViewPointCollisionMargin','kFrontierClusterMinSize']},indent=2))
