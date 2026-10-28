"""Compare two rebuilt fields using one frozen production C++ XYtheta gate.

This does not run a controller, TARE benefit selection, or a moving vehicle.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import json
import subprocess
import time


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--data', type=Path, required=True)
    cli.add_argument('--repo', type=Path, required=True)
    args = cli.parse_args()
    data, root = args.data.resolve(), args.repo.resolve()
    frozen = read(data / 'FREEZE.json')
    for item in frozen['sources']:
        assert sha(root / item['file']) == item['sha256'], item['file']
    binary = frozen['planner_binary']
    assert sha(binary) == frozen['planner_binary_sha256']
    manifest = {'started_utc': datetime.now(timezone.utc).isoformat(),
                'freeze_sha256': sha(data / 'FREEZE.json'),
                'script_sha256': sha(Path(__file__)), 'same_binary_both_roles': True,
                'scope': 'Same recorded raw scans/poses and fixed local goals; different geometry filters; no new driving'}
    write(data / 'PLANNER_MANIFEST.json', manifest)
    results = {}
    for role in ['before', 'after']:
        inputs = data / ('planner_input_' + role)
        metadata = read(inputs / 'metadata.json')
        assert metadata['recorded_frames'] == 208 and metadata['queries'] == 1667
        target = data / (role + '.json')
        assert not target.exists(), target
        started = time.monotonic()
        with (data / (role + '_planner.log')).open('w') as log:
            subprocess.run([binary, '--batch', str(inputs / 'queries.tsv'), '--output', str(target)],
                           cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
        manifest[role] = {'wall_s': time.monotonic() - started,
                          'query_sha256': sha(inputs / 'queries.tsv'),
                          'metadata_sha256': sha(inputs / 'metadata.json'),
                          'result_sha256': sha(target)}
        results[role] = read(target)
        print(role, 'actual C++ queries complete', manifest[role]['wall_s'], flush=True)
    before, after = results['before'], results['after']
    assert before['parameters'] == after['parameters']
    assert len(before['queries']) == len(after['queries']) == 1667
    paired = []
    file_hashes = {}
    for old, new in zip(before['queries'], after['queries'], strict=True):
        for key in ['label', 'map_stamp_ns', 'start', 'goal']:
            assert old[key] == new[key], (key, old['label'])
        for query in [old, new]:
            assert not query.get('error'), query
            assert query['clock_ns'] == query['map_stamp_ns']
            name = query['map_file']
            if name not in file_hashes:
                file_hashes[name] = sha(name)
            assert file_hashes[name] == query['map_sha256']
            if query['reached']:
                assert query['independent_recheck_passed'] and query['all_segments_permitted']
        paired.append({'label': old['label'], 'before_start_support': old['start_support'],
                       'after_start_support': new['start_support'], 'before_reached': old['reached'],
                       'after_reached': new['reached'], 'before_termination': old['termination'],
                       'after_termination': new['termination']})
    groups = {}
    for group, prefix in [('recorded', 'recorded_'), ('synthetic', 'synthetic_')]:
        groups[group] = {}
        for role, result in results.items():
            queries = [q for q in result['queries'] if q['label'].startswith(prefix)]
            groups[group][role] = {'queries': len(queries), 'reached': sum(q['reached'] for q in queries),
                                  'start_support': dict(Counter(q['start_support'] for q in queries)),
                                  'termination': dict(Counter(q['termination'] for q in queries))}
    for role in results:
        # Exactly one main heading/goal query per actual recorded map.
        main = [q for q in results[role]['queries']
                if q['label'].startswith('recorded_') and q['label'].endswith('_goal_000deg')]
        assert len(main) == 208
        groups['recorded'][role]['frames_start_support'] = dict(Counter(q['start_support'] for q in main))
    summary = {'scope': manifest['scope'], 'groups': groups, 'pairs': paired,
               'parameters': before['parameters'], 'same_fixed_cpp_binary': True,
               'source_clock_frozen_not_live_freshness_test': True,
               'source_stamps_poses_goals_paired': True, 'successful_paths_independently_rechecked': True}
    write(data / 'PLANNER_SUMMARY.json', summary)
    manifest['finished_utc'] = datetime.now(timezone.utc).isoformat()
    write(data / 'PLANNER_MANIFEST.json', manifest)
    print(json.dumps(groups, indent=2), flush=True)


if __name__ == '__main__':
    main()
