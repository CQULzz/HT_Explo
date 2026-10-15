#!/usr/bin/env python3
"""Save the latest HT field even when no executable path is published."""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import rclpy
from capture_xytheta_planning import Capture


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Capture(args.output, 5, 0)

    def save():
        if node.latest_map is None or node.odom is None:
            return
        p, valid, center, resolution, stamp, map_yaw = node.latest_map
        np.savez_compressed(args.output/'stopped_ht.npz', probabilities=p,
                            valid=valid, center=center, resolution=resolution,
                            robot=node.odom.copy(), stamp=np.array([int(stamp), int((stamp%1)*1e9)]),
                            map_yaw=map_yaw)
        (args.output/'stopped_ht.json').write_text(json.dumps({
            'status': node.status, 'mission': node.mission,
            'robot_xytheta': node.odom.tolist(), 'map_stamp': stamp,
            'map_age_s': time.time()-stamp}, indent=2)+'\n')

    node.create_timer(1., save)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        save()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
