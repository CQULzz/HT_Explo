#!/usr/bin/env python3
"""Run the independent installed CuPy mapper with timing observation only.

No map, TF, queue, timer, timestamp, locking policy or freshness rule changes.
The wrapper records per-thread lock wait/hold and callback wall/CPU durations.
"""
from contextlib import contextmanager
import inspect
import json
import os
from pathlib import Path
import threading
import time

from elevation_mapping_cupy import elevation_mapping_ros as mapper


class TimingRecorder:
    def __init__(self, path):
        self.stream = Path(path).open('x', buffering=1)
        self.lock = threading.Lock()

    def write(self, **event):
        event.update(wall_time=time.time(), thread=threading.get_ident())
        with self.lock:
            self.stream.write(json.dumps(event, separators=(',', ':')) + '\n')

    @contextmanager
    def callback(self, name, stamp=None):
        start, cpu = time.monotonic(), time.thread_time()
        try:
            yield
        finally:
            self.write(kind='callback', operation=name, source_stamp=stamp,
                       elapsed_s=time.monotonic()-start, cpu_s=time.thread_time()-cpu)


class ObservedLock:
    def __init__(self, lock, recorder):
        self.lock, self.recorder = lock, recorder
        self.local = threading.local()

    def __enter__(self):
        operation = inspect.currentframe().f_back.f_code.co_name
        start = time.monotonic()
        self.lock.__enter__()
        acquired = time.monotonic()
        if not hasattr(self.local, 'entries'):
            self.local.entries = []
        self.local.entries.append((operation, start, acquired, time.thread_time()))
        return self

    def __exit__(self, *args):
        operation, start, acquired, cpu = self.local.entries.pop()
        finished, cpu_elapsed = time.monotonic(), time.thread_time()-cpu
        result = self.lock.__exit__(*args)
        self.recorder.write(kind='map_lock', operation=operation, started_monotonic=start,
                            acquired_monotonic=acquired, released_monotonic=finished,
                            wait_s=acquired-start, hold_s=finished-acquired, cpu_s=cpu_elapsed)
        return result


def main():
    path = os.environ['CUPY_TIMING_TRACE']
    recorder = TimingRecorder(path)
    original = mapper.ElevationMappingNode

    class ProfiledNode(original):
        def __init__(self):
            super().__init__()
            self.map_access_lock = ObservedLock(self.map_access_lock, recorder)

        def pointcloud_callback(self, msg, sub_key):
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec*1e-9
            with recorder.callback('scan', stamp):
                return super().pointcloud_callback(msg, sub_key)

        def timed_timer(self, name, callback):
            with recorder.callback(name):
                return super().timed_timer(name, callback)

    mapper.ElevationMappingNode = ProfiledNode
    try:
        mapper.main()
    finally:
        recorder.stream.close()


if __name__ == '__main__':
    main()
