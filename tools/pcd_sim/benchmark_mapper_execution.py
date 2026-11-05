"""ROS scheduling load check, not a mapper/physics/closed-loop experiment.

Three callback groups share one mutex; payload sleeps 4ms to represent a native
operation releasing the GIL. Never loads point clouds or sends robot commands.
"""
import argparse
import json
from pathlib import Path
import threading
import time
import resource
import statistics

import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.node import Node
from tf2_ros import Buffer, TransformListener
from mapper_execution import TfListenerWorker, make_executor


def one(mode, duration):
    node = Node('mapper_scheduler_benchmark')
    executor = make_executor(mode, node.context)
    executor.add_node(node)
    buffer = Buffer()
    worker = TfListenerWorker(buffer, node) if mode == 'single' else None
    listener = worker.listener if worker else TransformListener(buffer, node)
    mutex = threading.Lock(); counts = [0, 0, 0]; busy = [0, 0, 0]
    groups = [MutuallyExclusiveCallbackGroup() for _ in counts]
    def callback(index):
        def run():
            with mutex:
                busy[index] += 1
                time.sleep(.004)
                counts[index] += 1
        return run
    timers = [node.create_timer(.02, callback(i), callback_group=groups[i]) for i in range(3)]
    # Settle discovery and warm Python/ROS before resetting counters/windows.
    deadline = time.monotonic() + .3
    while time.monotonic() < deadline:
        executor.spin_once(timeout_sec=.02)
    # Drain multi-worker jobs before the measurement boundary.
    with mutex:
        initial = counts.copy()
    cpu_start = time.process_time(); start = time.monotonic()
    try:
        while time.monotonic() - start < duration:
            executor.spin_once(timeout_sec=.02)
    finally:
        for timer in timers:
            timer.cancel()
        pool = getattr(executor, '_executor', None)
        if pool is not None:
            pool.shutdown(wait=True)
        executor.shutdown()
        if worker:
            worker.close()
        else:
            listener.unregister()
        node.destroy_node()
    wall = time.monotonic() - start; cpu = time.process_time() - cpu_start
    return {'mode': mode, 'wall_s': wall, 'process_cpu_s': cpu,
            'cpu_core_equivalents': cpu / wall,
            'completed_callbacks': [counts[i] - initial[i] for i in range(3)],
            'completed_callbacks_per_s': sum(counts[i] - initial[i] for i in range(3)) / wall}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=2.)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error('Duration must be positive')
    rclpy.init()
    rows = []
    try:
        for pair in range(3):
            for mode in (['multi', 'single'] if pair % 2 == 0 else ['single', 'multi']):
                row = one(mode, args.seconds); row['pair'] = pair
                rows.append(row); print(json.dumps(row), flush=True)
    finally:
        rclpy.shutdown()
    summary = {mode: {metric: statistics.median(x[metric] for x in rows if x['mode'] == mode)
               for metric in ['process_cpu_s', 'cpu_core_equivalents', 'completed_callbacks_per_s']}
               for mode in ['multi', 'single']}
    args.output.write_text(json.dumps({'scope': __doc__, 'seconds_per_window': args.seconds,
        'pairs': 3, 'period_s': .02, 'payload_sleep_s': .004,
        'rows': rows, 'median': summary,
        'limitations': 'Synthetic scheduler load; no map/HT/GPU or transport pipeline. Not evidence that the 1s map source-age acceptance passes.'}, indent=2))


if __name__ == '__main__':
    main()
