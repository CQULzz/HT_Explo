#!/usr/bin/env python3
"""Export display-only surrounding LiDAR context at saved HT timestamps.

Raw inputs are read-only. This does not feed the scene points back to mapping,
change an HT score, publish a control topic, or replace the saved elevation map.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np
import rclpy
from rclpy.duration import Duration
from rclpy.serialization import deserialize_message
from rclpy.time import Time
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py.point_cloud2 import read_points_numpy
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src/ht_scout_bridge'))
from ht_scout_bridge.geometry import load_calibration, self_filter_keep_mask


def matrix(tf):
    t, q = tf.transform.translation, tf.transform.rotation
    m = np.eye(4)
    m[:3, :3] = Rotation.from_quat([q.x, q.y, q.z, q.w]).as_matrix()
    m[:3, 3] = [t.x, t.y, t.z]
    return m


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--bag', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    freeze = json.loads((a.input / 'FREEZE.json').read_text())
    profile, _, _ = load_calibration(Path(freeze['calibration_file']))
    source_results = json.loads((a.input / 'RESULTS.json').read_text())
    rows = {r['stamp_ns']: r for r in source_results['frames'] if r['output']}
    dbs = list(a.bag.glob('*.db3'))
    assert len(dbs) == 1
    c = sqlite3.connect('file:' + str(dbs[0]) + '?mode=ro&immutable=1', uri=True)
    topics = {name: i for i, name in c.execute('select id,name from topics')}
    rclpy.init()
    buf = Buffer(cache_time=Duration(seconds=180.))
    try:
        for topic in ['/tf_static', '/tf']:
            for (data,) in c.execute('select data from messages where topic_id=? order by timestamp', (topics[topic],)):
                for tf in deserialize_message(data, TFMessage).transforms:
                    if topic == '/tf_static':
                        buf.set_transform_static(tf, 'recorded')
                    else:
                        buf.set_transform(tf, 'recorded')
        chassis_from_lidar = np.array(freeze['recorded_chassis_from_lidar'])
        scene = {}
        records = []
        for (data,) in c.execute('select data from messages where topic_id=? order by timestamp', (topics['/rslidar_points'],)):
            msg = deserialize_message(data, PointCloud2)
            ns = msg.header.stamp.sec * 10**9 + msg.header.stamp.nanosec
            if ns not in rows:
                continue
            world = matrix(buf.lookup_transform('map', msg.header.frame_id, Time(nanoseconds=ns)))
            xyz = read_points_numpy(msg, field_names=('x', 'y', 'z'), skip_nans=False).reshape(-1, 3)
            keep = self_filter_keep_mask(xyz, profile['lidar_self_filter'], chassis_from_lidar)
            # Display only: 18 m measured radius, finite points, coarse voxel samples.
            use = keep & np.isfinite(xyz).all(axis=1) & (np.linalg.norm(xyz, axis=1) <= 18.)
            points = xyz[use] @ world[:3, :3].T + world[:3, 3]
            points = points[np.abs(points[:, 2] - world[2, 3]) <= 6.]
            keys, ix = np.unique(np.floor(points / .16).astype(np.int32), axis=0, return_index=True)
            for k, point in zip(keys, points[ix]):
                scene[tuple(k)] = point.astype(np.float32)
            accumulated = np.array(list(scene.values()), dtype=np.float32)
            name = rows[ns]['file']
            np.savez_compressed(a.output / name, scene_xyz=accumulated, stamp_ns=np.int64(ns))
            records.append({'file': name, 'stamp_ns': ns, 'scene_points': len(accumulated)})
        assert len(records) == len(rows)
        (a.output / 'SCENE_MANIFEST.json').write_text(json.dumps({
            'scope': 'Display-only accumulated filtered LiDAR context, not a terrain or occupancy map',
            'scene_radius_from_each_sensor_m': 18., 'display_voxel_m': .16,
            'max_absolute_z_from_sensor_m': 6.,
            'alignment': 'Recorded exact-time TF; map surface-registration correction is not applied to context points',
            'source': str(a.bag), 'frames': records,
        }, indent=2) + '\n')
        print(a.output, len(records), 'frames', len(scene), 'final context points', flush=True)
    finally:
        c.close()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
