#!/usr/bin/env python3
"""Infer the local eight-direction HT map from observed CuPy elevation cells."""

from copy import deepcopy
from collections import deque
from array import array as FloatArray
import json
import os
from pathlib import Path
import time

import numpy as np
import torch
from scipy.ndimage import distance_transform_edt, uniform_filter, maximum_filter

import rclpy
from grid_map_msgs.msg import GridMap
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from nav_msgs.msg import Odometry
from std_msgs.msg import Float32MultiArray, MultiArrayDimension, MultiArrayLayout

from model import load_student_model
from historical_elevation import HistoricalElevation
from elevation_quality import preprocess_elevation, retain_recent_obstacle_edges
from local_surface import SurfaceReferenceEstimator


class CupyToHt(Node):
    def __init__(self):
        super().__init__("cupy_to_ht_bridge")
        torch.set_num_threads(2)
        self.model = load_student_model(
            str(Path(__file__).with_name("student_best_epoch_weights.pth")), torch.device("cpu")
        )
        self.pub = self.create_publisher(GridMap, "/ht_traversability/global_local", 1)
        self.history_pub = self.create_publisher(GridMap, "/elevation_mapping/historical_local", 1)
        self.history = None
        offset = self.declare_parameter('surface_sensor_ground_offset_m', -1.0).value
        self.surface = SurfaceReferenceEstimator(sensor_ground_offset_m=offset if offset >= 0 else None)
        self.odometry = deque(maxlen=4000)
        self.diagnostics = []
        self.last_source_stamp = None
        self.create_subscription(
            Odometry, self.declare_parameter('surface_odometry_topic', '/state_estimation').value,
            self.on_odometry, QoSProfile(depth=100, reliability=ReliabilityPolicy.BEST_EFFORT))
        self.sub = self.create_subscription(
            GridMap, "/elevation_mapping/elevation_map_raw", self.on_map,
            QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE)
        )
        self.count = 0

    def on_odometry(self, msg):
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec*1e-9
        self.odometry.append((stamp, float(msg.pose.pose.position.z)))

    def robot_z_at(self, stamp):
        if not self.odometry:
            return None
        match = min(self.odometry, key=lambda v: abs(v[0]-stamp))
        return match[1] if abs(match[0]-stamp) <= .75 else None

    def on_map(self, source):
        started = time.monotonic()
        stamp_key = (source.header.stamp.sec, source.header.stamp.nanosec)
        if stamp_key == self.last_source_stamp:
            return
        if source.header.frame_id != "map" or "elevation" not in source.layers:
            self.get_logger().error("Expected a map-frame CuPy elevation layer")
            return
        resolution = float(source.info.resolution)
        if not 0.040 <= resolution <= 0.042:
            self.get_logger().error(f"HT model expects about 0.041 m cells; got {resolution}")
            return
        nx = round(source.info.length_x / resolution)
        ny = round(source.info.length_y / resolution)
        if nx != 291 or ny != 291:
            self.get_logger().error(f"HT bridge expects 291x291 input; got {nx}x{ny}")
            return
        raw = np.asarray(source.data[source.layers.index("elevation")].data, dtype=np.float32)
        if raw.size != nx * ny:
            self.get_logger().error("Invalid elevation array length")
            return
        # GridMap Float32MultiArray uses column-major storage.
        elevation = raw.reshape((nx, ny), order="F")
        if "variance" in source.layers:
            variance = np.asarray(
                source.data[source.layers.index("variance")].data, dtype=np.float32
            ).reshape((nx, ny), order="F")
        else:
            self.get_logger().error("CuPy elevation variance layer is required for historical fusion")
            return
        if 'observation_age' not in source.layers:
            self.get_logger().error('CuPy observation_age is required; enable it in the publisher setup')
            return
        age = np.asarray(source.data[source.layers.index('observation_age')].data,
                         dtype=np.float32).reshape((nx, ny), order='F')
        if self.history is None:
            self.history = HistoricalElevation(resolution)
        elif abs(self.history.resolution - resolution) > 1e-6:
            self.get_logger().error("Historical map resolution changed; refusing mixed-resolution fusion")
            return
        stamp_s = float(source.header.stamp.sec) + source.header.stamp.nanosec * 1e-9
        self.last_source_stamp = stamp_key
        try:
            # Decode the physical circular buffer once. The publisher/core has
            # already converted its coordinates into GridMap logical order.
            offset = (-source.outer_start_index, -source.inner_start_index)
            elevation, variance, age = (np.roll(v, offset, (0, 1))
                                        for v in (elevation, variance, age))
            source_quality = preprocess_elevation(elevation, variance, resolution)
            # Store original measured heights after quality rejection; denoise
            # only the selected historical crop, avoiding repeated smoothing.
            measured = np.where(source_quality.observed_quality, elevation, np.nan)
            observed_at = stamp_s-age.astype(np.float64)
            fused = self.history.fuse(
                measured, variance, source.info.pose.position.x, source.info.pose.position.y,
                stamp_s, observation_time=observed_at)
            align = lambda v, fill=np.nan: self.history.aligned_source_window(
                v, source.info.pose.position.x, source.info.pose.position.y, nx, fill_value=fill)
            current, current_var, current_age = (align(v) for v in (measured, variance, age))
            reference, surface_stats = self.surface.estimate(
                current, current_var, resolution, current_age, self.robot_z_at(stamp_s))
            # Old retained source heights cannot force selection of a floor.
            # A fresh source measurement, including a real obstacle top, can.
            preferred = np.where(np.isfinite(current_age) & (current_age >= -.001)
                                 & (current_age <= 2.), current, np.nan)
            elevation, variance, center_x, center_y = self.history.window(
                source.info.pose.position.x, source.info.pose.position.y, nx, stamp_s,
                reference_height=reference, preferred_elevation=preferred)
            elevation, variance, retained_edges = retain_recent_obstacle_edges(
                elevation, variance, current, current_var, current_age,
                align(source_quality.edge_mask.astype(np.float32), 0) >= .5)
            source_rejected = align(source_quality.rejected_mask.astype(np.float32), 0) >= .5
            source_rejected |= self.history.last_window_incompatible_mask
            elevation[source_rejected] = np.nan
            raw_history = elevation.copy()
            quality = preprocess_elevation(elevation, variance, resolution)
            elevation = quality.height_m
            rejected = source_rejected | quality.rejected_mask
        except (ValueError, MemoryError) as error:
            self.get_logger().error(f"Historical elevation update failed: {error}")
            return
        observed = quality.observed_quality
        if not np.any(observed):
            return

        local = GridMap()
        local.header = deepcopy(source.header)
        local.info = deepcopy(source.info)
        local.info.pose.position.x = center_x
        local.info.pose.position.y = center_y
        local.layers = ['elevation', 'variance', 'elevation_raw', 'input_valid', 'rejected']
        local.basic_layers = ["elevation"]
        local.outer_start_index = local.inner_start_index = 0
        for layer in (elevation, variance, raw_history, observed.astype(np.float32),
                      rejected.astype(np.float32)):
            data = Float32MultiArray()
            data.layout = MultiArrayLayout(dim=[
                MultiArrayDimension(label="column_index", size=ny, stride=nx * ny),
                MultiArrayDimension(label="row_index", size=nx, stride=nx)], data_offset=0)
            data.data = FloatArray('f', layer.flatten(order="F").tobytes())
            local.data.append(data)
        self.history_pub.publish(local)

        distance_cells, nearest = distance_transform_edt(~observed, return_indices=True)
        height = elevation[tuple(nearest)].astype(np.float32)
        near_observation = distance_cells * resolution <= 0.25
        support = uniform_filter(
            near_observation.astype(np.float32), size=51, mode="constant"
        )[25:-25, 25:-25] >= 0.9
        # Rejected height returns are unknown, not permission to reconstruct
        # traversable ground by nearest-neighbour network padding.
        support &= ~maximum_filter(rejected, size=51, mode='constant')[25:-25, 25:-25]
        with torch.inference_mode():
            probabilities = torch.softmax(
                self.model(torch.from_numpy(height[None, None])), dim=2
            )[0, :, 1].numpy()
        if probabilities.shape != (8, 241, 241):
            self.get_logger().error(f"Unexpected model output shape {probabilities.shape}")
            return

        result = GridMap()
        result.header = deepcopy(source.header)
        result.info = deepcopy(source.info)
        result.info.pose.position.x = center_x
        result.info.pose.position.y = center_y
        # The network's 51x51 receptive field cannot score the outer 25 cells.
        # Publish the 241x241 scored area directly instead of serializing nine
        # mostly-empty 291x291 layers over DDS each cycle.
        output_side = nx - 50
        result.info.length_x = output_side * resolution
        result.info.length_y = output_side * resolution
        result.layers = [f"ht_dir_{k}" for k in range(8)] + ["ht_valid"]
        result.basic_layers = ["ht_valid"]
        result.outer_start_index = 0
        result.inner_start_index = 0
        for k in range(9):
            if k < 8:
                layer = np.where(support, probabilities[k], np.nan).astype(np.float32)
            else:
                layer = support.astype(np.float32)
            data = Float32MultiArray()
            data.layout = MultiArrayLayout(
                dim=[
                    MultiArrayDimension(label="column_index", size=output_side, stride=output_side * output_side),
                    MultiArrayDimension(label="row_index", size=output_side, stride=output_side),
                ],
                data_offset=0,
            )
            data.data = FloatArray('f', layer.flatten(order="F").tobytes())
            result.data.append(data)
        self.pub.publish(result)
        self.count += 1
        self.diagnostics.append({'stamp_s': stamp_s, 'fused_cells': fused,
                                 'observed_cells': int(observed.sum()), 'supported_cells': int(support.sum()),
                                 'surface': surface_stats, 'quality': quality.stats,
                                 'source_rejected_cells': int(source_rejected.sum()),
                                 'retained_current_edge_cells': int(retained_edges.sum()),
                                 'elapsed_s': time.monotonic()-started})
        if self.count % 5 == 0:
            self.get_logger().info(
                f"maps={self.count} fused={fused} observed={observed.sum()} "
                f"history_tiles={len(self.history.tiles)} valid={support.sum()} "
                f"center_valid={bool(support[120, 120])} inference_s={time.monotonic() - started:.3f}"
            )


def main():
    rclpy.init()
    node = CupyToHt()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.history is not None and os.environ.get("HT_HISTORY_DUMP"):
            node.history.save(os.environ["HT_HISTORY_DUMP"])
            node.get_logger().info(f"Saved global historical elevation to {os.environ['HT_HISTORY_DUMP']}")
        if os.environ.get('HT_DIAGNOSTICS_DUMP'):
            Path(os.environ['HT_DIAGNOSTICS_DUMP']).write_text(json.dumps(node.diagnostics, indent=2)+'\n')
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
