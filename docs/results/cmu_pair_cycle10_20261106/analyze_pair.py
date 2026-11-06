"""Read saved telemetry only. No ROS, simulator, or production file mutations."""
from pathlib import Path
import csv
import json
import collections
import numpy as np

ROOT = Path(__file__).parent
LABELS = ['p01_tare42', 'p02_tare42', 'p03_ht42']

def summarize(label):
    run = ROOT / 'runs' / label
    rows = [r for r in csv.DictReader((run / 'metrics.csv').open()) if float(r['elapsed_sim']) >= 0]
    events = [json.loads(line) for line in (run / 'events.jsonl').open()]
    states = {}
    transitions = []
    reasons = collections.Counter()
    completion = []
    performance = []
    runtime = []
    for event in events:
        topic = event['topic']
        if topic in ['mission_state', 'ht_execution_status', 'ht_follower_status']:
            if states.get(topic) != event['data']:
                transitions.append([event['time'], topic, event['data']])
                states[topic] = event['data']
        try:
            payload = json.loads(event['data'])
        except (TypeError, json.JSONDecodeError):
            continue
        if topic == 'runtime_status':
            reasons[payload.get('reason', '?')] += 1
            runtime.append((event['time'], payload.get('reason', '?')))
        if topic == 'ht_performance':
            performance.append(payload)
        if topic == 'tare_decision_diagnostics' and payload.get('stage') == 'completion':
            completion.append(payload)
    times = np.array([float(r['elapsed_sim']) for r in rows])
    simulation = np.array([float(r['sim_time']) for r in rows])
    distance = np.array([float(r['distance_m']) for r in rows])
    linear = np.array([float(r['v_cmd']) for r in rows])
    angular = np.array([float(r['w_cmd']) for r in rows])
    durations = np.diff(np.append(simulation, simulation[-1] + .5))
    masks = {'forward': linear > .01, 'reverse': linear < -.01,
             'rotation': (abs(linear) <= .01) & (abs(angular) > .01),
             'zero': (abs(linear) <= .01) & (abs(angular) <= .01)}
    reason_time = collections.Counter()
    start, end = simulation[0] - times[0], simulation[-1]
    for index, (timestamp, reason) in enumerate(runtime):
        next_stamp = runtime[index+1][0] if index+1 < len(runtime) else end
        reason_time[reason] += max(0., min(next_stamp, end) - max(timestamp, start))
    manifest = json.loads((run / 'manifest.json').read_text())
    result = {'label': label, 'tested_commit': manifest['project_head'],
              'done': json.loads((run / 'DONE.json').read_text()),
              'run_result': json.loads((run / 'RUN_RESULT.json').read_text()),
              'final_states': states, 'transitions': transitions,
              'runtime_reason_event_counts': dict(reasons),
              'runtime_reason_sim_seconds': dict(reason_time),
              'command_sample_duration_s': {k: float(durations[v].sum()) for k,v in masks.items()},
              'command_abs_max_v_w': [float(max(abs(linear))), float(max(abs(angular)))],
              'first_ready_sample_distance_m': float(distance[0]),
              'distance_after_first_ready_sample_m': float(distance[-1] - distance[0]),
              'last30s_distance_m': float(distance[-1] - np.interp(times[-1]-30, times, distance)),
              'final_xy': [float(rows[-1]['x']), float(rows[-1]['y'])],
              'completion_diagnostics_count': len(completion),
              'completion_ready_count': sum(bool(x['completion_ready']) for x in completion),
              'first_completion_ready': next((x for x in completion if x['completion_ready']), None),
              'final_completion_diagnostic': completion[-1] if completion else None,
              'ht_source_age_p95_max_s': [float(np.percentile([p['source_age_at_publish_s'] for p in performance],95)),float(max(p['source_age_at_publish_s'] for p in performance))] if performance else None,
              'metric_note': 'Distance is ground-truth cumulative XY including settling/slip. Free volume is sampled source-second LiDAR ray-voxel union. Commands are ~2Hz samples. Runtime durations are clipped sample-and-hold simulation time, not raw event counts.'}
    (run / 'PAIR_SUMMARY.json').write_text(json.dumps(result, indent=2)+'\n')
    return result

if __name__ == '__main__':
    results = [summarize(label) for label in LABELS if (ROOT/'runs'/label/'DONE.json').exists()]
    (ROOT/'SUMMARY.json').write_text(json.dumps(results, indent=2)+'\n')
    for result in results:
        print(result['label'], result['done'], result['final_states'], result['last30s_distance_m'])
