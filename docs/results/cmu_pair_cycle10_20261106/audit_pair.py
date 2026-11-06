"""Offline audit of matched run configuration, commands, and preserved sources."""
from pathlib import Path
import sys
import json
import hashlib
import subprocess
import math
import csv
import numpy as np
sys.path.insert(0, '/home/lzz/HT_drive_audit_20261031_170105/decoder_deps')
from mcap.reader import make_reader
from rclpy.serialization import deserialize_message
from geometry_msgs.msg import Twist

ROOT = Path(__file__).parent
OUTPUT = ROOT / 'analysis'
OUTPUT.mkdir(exist_ok=True)
labels = ['p02_tare42', 'p03_ht42']
manifest = [json.loads((ROOT/'runs'/label/'manifest.json').read_text()) for label in labels]
left, right = [m['frozen_hashes'] for m in manifest]
common = sorted(left.keys() & right.keys())
changed = [p for p in common if left[p] != right[p]]
assert not changed
keys = ['scene_config', 'start_policy', 'seed', 'mapper_executor_mode', 'render_backend',
        'requested_duration_sim_s', 'install_base', 'isolated_ros_domain']
assert all(manifest[0][k] == manifest[1][k] for k in keys)
assert manifest[0]['frozen_hashes'][str(ROOT/'runs/p02_tare42/scene_config.json')] == manifest[1]['frozen_hashes'][str(ROOT/'runs/p03_ht42/scene_config.json')]
command_records = {}
for label in labels:
    run = ROOT / 'runs' / label
    result = json.loads((run/'RUN_RESULT.json').read_text())
    assert result['full_requested_duration'] and not result['frozen_files_changed']
    assert not result['managed_shutdown_nonzero'] and not result['ros_launch_child_nonzero']
    assert result['error'] is None and all(v == 0 for v in result['exit_codes'].values())
    commands = []
    for bag in sorted((run/'bag').glob('*.mcap')):
        with bag.open('rb') as stream:
            for schema, channel, message in make_reader(stream, validate_crcs=True).iter_messages(topics=['/sim/cmd_vel']):
                value = deserialize_message(message.data, Twist)
                commands.append((value.linear.x, value.angular.z))
    values = np.array(commands)
    assert np.isfinite(values).all()
    assert values[:,0].min() >= -.25 - 1e-8 and values[:,0].max() <= .4 + 1e-8
    assert abs(values[:,1]).max() <= .8 + 1e-8
    rows = [r for r in csv.DictReader((run/'metrics.csv').open()) if float(r['elapsed_sim']) >= 0]
    times = [float(r['elapsed_sim']) for r in rows]
    distance = [float(r['distance_m']) for r in rows]
    pose = np.load(run/'true_pose_yaw.npy')
    command_records[label] = {'recorded_command_count': len(commands),
        'linear_min_max_mps': [float(values[:,0].min()), float(values[:,0].max())],
        'max_abs_angular_rps': float(abs(values[:,1]).max()), 'all_finite_and_within_shared_limits': True,
        'first_recorded_pose_stamp_xyz_yaw': pose[0].tolist(),
        'start_gate': json.loads((run/'START_GATE.json').read_text()),
        'distance_interpolated_at_elapsed120_m': float(np.interp(120., times, distance)),
        'last30_distance_interpolated_at_elapsed120_m': float(np.interp(120., times, distance) - np.interp(90., times, distance)),
        'final_sampled_scans': int(rows[-1]['sampled_scans'])}
old = json.loads(Path('/home/lzz/HT_linux_cycle7_20261106/audit/LINUX_CUPY_PRESERVED.json').read_text())
cupy = Path(old['repo'])
source_check = {name: hashlib.sha256((cupy/name).read_bytes()).hexdigest() == info['sha256'] for name,info in old['files'].items()}
assert all(source_check.values())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=cupy,text=True).strip() == old['head']
cmu = Path('/home/lzz/autonomous_exploration_development_environment')
cmu_head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=cmu,text=True).strip()
cmu_status = subprocess.check_output(['git','status','--porcelain'],cwd=cmu,text=True)
assert cmu_head == '8314318d784c0db75b299b2c14161652c19275a5' and not cmu_status
record = {'pair': labels, 'common_frozen_file_count': len(common), 'changed_common_files': changed,
          'common_frozen_hashes': {p:left[p] for p in common}, 'equal_manifest_parameters': keys,
          'equal_normalized_scene_config': True,
          'manifest_differences': {k:[manifest[0][k],manifest[1][k]] for k in manifest[0].keys() & manifest[1].keys() if k != 'frozen_hashes' and manifest[0][k] != manifest[1][k]},
          'sources_changed_between_run_commits': subprocess.check_output(['git','diff','--name-only',manifest[0]['project_head'],manifest[1]['project_head']],cwd='/home/lzz/HT_linux_cycle7_20261106/repo',text=True).splitlines(),
          'commands': command_records, 'preserved_linux_cupy_files': source_check,
          'preserved_cmu_original': {'head':cmu_head,'git_status_porcelain':cmu_status},
          'interpretation': 'TARE additionally freezes 81 CMU install files. The two per-run scene_config paths differ but contents match. HT adds worker inference and sparse diagnostic contexts. Recorded volume sampling and scheduling are approximate, with 119 vs120 completed metric scans.'}
(OUTPUT/'PAIR_AUDIT.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k != 'common_frozen_hashes'},indent=2))
