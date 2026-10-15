#!/usr/bin/env python3
"""Show eight HT traversal probabilities over the same fixed XY terrain.

The theta axis here denotes the direction queried from the HT map. It is not
a vehicle heading trajectory or an XY-theta route search.
"""

import argparse
import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def capture(path, timeout):
    import rclpy
    from grid_map_msgs.msg import GridMap
    from nav_msgs.msg import Odometry
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy

    class Receiver(Node):
        def __init__(self):
            super().__init__("ht_direction_terrain_capture")
            self.robot = None
            self.done = False
            self.create_subscription(Odometry, "/state_estimation", self.on_odom, 10)
            self.create_subscription(GridMap, "/ht_traversability/global_local", self.on_map,
                                     QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE))

        def on_odom(self, msg):
            p = msg.pose.pose.position
            self.robot = (p.x, p.y)

        def on_map(self, msg):
            if self.robot is None or self.done:
                return
            n = round(msg.info.length_x / msg.info.resolution)
            if n <= 0 or n != round(msg.info.length_y / msg.info.resolution):
                return
            if any(f"ht_dir_{k}" not in msg.layers for k in range(8)) or "ht_valid" not in msg.layers:
                return
            def layer(name):
                return np.asarray(msg.data[msg.layers.index(name)].data,
                                  dtype=np.float32).reshape((n, n), order="F")
            probs = np.stack([layer(f"ht_dir_{k}") for k in range(8)])
            valid = layer("ht_valid") >= 0.5
            if valid.sum() < 100:
                return
            np.savez_compressed(path, probabilities=probs, valid=valid,
                                center=np.array([msg.info.pose.position.x,
                                                 msg.info.pose.position.y]),
                                robot=np.asarray(self.robot),
                                resolution=msg.info.resolution,
                                stamp=np.array([msg.header.stamp.sec,
                                                msg.header.stamp.nanosec]))
            self.done = True

    rclpy.init()
    node = Receiver()
    try:
        deadline = time.monotonic() + timeout
        while not node.done and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.2)
        if not node.done:
            raise RuntimeError("No valid HT map and robot pose within timeout")
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


def render(input_path, output_path, radius):
    with np.load(input_path) as data:
        probs = data["probabilities"]
        valid = data["valid"].astype(bool)
        center = data["center"]
        robot = data["robot"]
        resolution = float(data["resolution"])
        stamp = data["stamp"].tolist()
    n = valid.shape[0]
    # GridMap row and column indices run from high X/Y to low X/Y.
    x = center[0] + (n / 2 - np.arange(n) - .5) * resolution
    y = center[1] + (n / 2 - np.arange(n) - .5) * resolution
    # Keep the same world-fixed crop and probability scale in all eight panels.
    r, c = np.ogrid[:n, :n]
    roi = ((x[:, None] - robot[0]) ** 2 + (y[None, :] - robot[1]) ** 2 <= radius ** 2)
    eligible = valid & roi & np.all(np.isfinite(probs), axis=0)
    if not eligible.any():
        raise RuntimeError("No valid HT cells in the requested crop")
    spread = np.ptp(probs, axis=0)
    # A cell with strong directional contrast makes the eight-way comparison legible.
    i, j = np.unravel_index(np.argmax(np.where(eligible, spread, -1)), spread.shape)
    px, py = x[i], y[j]
    ix = np.where(abs(x - robot[0]) <= radius)[0]
    iy = np.where(abs(y - robot[1]) <= radius)[0]
    rows = slice(ix.min(), ix.max() + 1)
    cols = slice(iy.min(), iy.max() + 1)
    extent = [x[ix.max()] - resolution / 2, x[ix.min()] + resolution / 2,
              y[iy.max()] - resolution / 2, y[iy.min()] + resolution / 2]

    fig = plt.figure(figsize=(15, 10), dpi=150)
    grid = fig.add_gridspec(3, 4, height_ratios=[1, 1, .85], hspace=.31, wspace=.18)
    cmap = plt.get_cmap("RdYlGn").copy()
    cmap.set_bad("#c5c5c5")
    im = None
    for k in range(8):
        ax = fig.add_subplot(grid[k // 4, k % 4])
        plane = np.where(valid[rows, cols], probs[k, rows, cols], np.nan)
        im = ax.imshow(np.flipud(np.fliplr(plane.T)), extent=extent, origin="lower",
                       cmap=cmap, vmin=0, vmax=1, interpolation="nearest")
        ax.plot(px, py, "ko", ms=5)
        ax.plot(robot[0], robot[1], marker="+", color="#2862cb", ms=10, mew=2)
        ax.set_title(f"HT direction {k}  ({k * 45}°)")
        ax.set_xlim(robot[0] - radius, robot[0] + radius)
        ax.set_ylim(robot[1] - radius, robot[1] + radius)
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")
    fig.colorbar(im, ax=fig.axes[:8], shrink=.63, pad=.01,
                 label="HT traversability probability (0–1)")

    ax = fig.add_subplot(grid[2, :2])
    angles = np.arange(8) * 45
    values = probs[:, i, j]
    ax.plot(angles, values, "o-", color="#b13e13", lw=2)
    ax.set(xticks=angles, xlim=(-5, 320), ylim=(0, 1),
           xlabel="Travel direction θ in map frame (degrees)",
           ylabel="HT traversability probability",
           title=f"Same marked ground cell ({px:.2f}, {py:.2f})")
    ax.grid(alpha=.3)
    ax = fig.add_subplot(grid[2, 2:])
    spread_plane = np.where(valid[rows, cols], spread[rows, cols], np.nan)
    im2 = ax.imshow(np.flipud(np.fliplr(spread_plane.T)), extent=extent, origin="lower",
                    cmap="magma", vmin=0, vmax=1, interpolation="nearest")
    ax.plot(px, py, "co", ms=6)
    ax.set(xlim=(robot[0] - radius, robot[0] + radius),
           ylim=(robot[1] - radius, robot[1] + radius),
           xlabel="X (m)", ylabel="Y (m)", title="Direction sensitivity: max(P) − min(P)")
    fig.colorbar(im2, ax=ax, shrink=.8)
    fig.suptitle("One HT terrain map, eight travel directions (black dot = same cell; blue + = robot)\n"
                 "Gray = not supported by observations; probabilities are model estimates",
                 fontsize=14)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    metadata = {"map_stamp": stamp, "robot_xy": robot.tolist(),
                "marked_xy": [float(px), float(py)],
                "probabilities_at_marked_cell": values.tolist(),
                "spread_at_marked_cell": float(spread[i, j]),
                "valid_cells_in_crop": int(eligible.sum()),
                "resolution_m": resolution, "crop_radius_m": radius}
    output_path.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="Captured map NPZ; capture live if omitted")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--radius", type=float, default=3.5)
    args = parser.parse_args()
    input_path = args.input or args.output.with_suffix(".npz")
    if args.input is None:
        capture(input_path, args.timeout)
    render(input_path, args.output, args.radius)


if __name__ == "__main__":
    main()
