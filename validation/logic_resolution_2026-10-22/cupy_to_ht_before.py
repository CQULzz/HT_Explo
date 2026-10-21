#!/usr/bin/env python3
"""Infer the local eight-direction HT map from observed CuPy elevation cells."""

from copy import deepcopy
from collections import deque
from array import array as FloatArray
import json
import os
import signal
from pathlib import Path
import time

import numpy as np
import torch

import rclpy
from grid_map_msgs.msg import GridMap
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.signals import SignalHandlerOptions
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from nav_msgs.msg import Odometry
from std_msgs.msg import Float32, Float32MultiArray, MultiArrayDimension, MultiArrayLayout

from model import load_student_model
from historical_elevation import HistoricalElevation
from elevation_quality import preprocess_elevation, retain_recent_obstacle_edges
from local_surface import SurfaceReferenceEstimator
from cpu_threads import configure_cpu_threads
from ht_support import prepare_ht_context, preserve_rejected_obstacles
from inference_context_io import ContextCaptureSchedule, GracefulStop, save_immutable_npz


class CupyToHt(Node):
    def __init__(self):
        super().__init__("cupy_to_ht_bridge")
        threads=self.declare_parameter('ht_torch_threads',4).value
        self.channels_last=self.declare_parameter('ht_channels_last',True).value
        self.blas_limit, cpu_threads = configure_cpu_threads(threads)
        cpu_threads['model_memory_format']='channels_last' if self.channels_last else 'contiguous'
        self.get_logger().info(f'CPU pools: PyTorch={threads}, BLAS=1; {cpu_threads["model_memory_format"]}')
        if os.environ.get('HT_DIAGNOSTICS_DUMP'):
            Path(os.environ['HT_DIAGNOSTICS_DUMP']).with_name('ht_cpu_threads.json').write_text(
                json.dumps(cpu_threads, indent=2)+'\n')
        self.model = load_student_model(
            str(Path(__file__).with_name("student_best_epoch_weights.pth")), torch.device("cpu")
        )
        if self.channels_last:
            self.model=self.model.to(memory_format=torch.channels_last)
        self.pub = self.create_publisher(GridMap, "/ht_traversability/global_local", 1)
        self.history_pub = self.create_publisher(GridMap, "/elevation_mapping/historical_local", 1)
        self.history = None
        offset = self.declare_parameter('surface_sensor_ground_offset_m', -1.0).value
        self.surface = SurfaceReferenceEstimator(sensor_ground_offset_m=offset if offset >= 0 else None)
        self.odometry = deque(maxlen=4000)
        self.diagnostics = []
        self.last_source_stamp = None
        self.last_context_dump_stamp = None
        self.context_schedule = ContextCaptureSchedule()
        if os.environ.get('HT_CONTEXT_DUMP'):
            self.create_subscription(Float32, '/runtime',
                lambda _: self.context_schedule.begin_runtime(self.get_clock().now().nanoseconds/1e9), 2)
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
        source_age_at_start = self.get_clock().now().nanoseconds/1e9 - (
            source.header.stamp.sec + source.header.stamp.nanosec*1e-9)
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
            source_elevation, source_variance = elevation.copy(), variance.copy()
            source_age = age.copy()
            source_quality = preprocess_elevation(elevation, variance, resolution)
            # Store original measured heights after quality rejection; denoise
            # only the selected historical crop, avoiding repeated smoothing.
            measured = np.where(source_quality.observed_quality, elevation, np.nan)
            observed_at = stamp_s-age.astype(np.float64)
            rejected_updates=self.history.record_rejections(source_quality.rejected_mask,
                source.info.pose.position.x,source.info.pose.position.y,stamp_s,observed_at,
                elevation=elevation)
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
            source_rejected = self.history.last_window_incompatible_mask.copy()
            elevation[source_rejected] = np.nan
            raw_history = elevation.copy()
            quality = preprocess_elevation(elevation, variance, resolution)
            elevation = quality.height_m
            rejected = source_rejected | quality.rejected_mask
        except (ValueError, MemoryError) as error:
            self.get_logger().error(f"Historical elevation update failed: {error}")
            return
        observed = quality.observed_quality
        fusion_finished = time.monotonic()
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

        obstacle_context = preserve_rejected_obstacles(
            self.history.last_window_obstacle_elevation, raw_history, quality.rejected_mask)
        retained_filtered_obstacles = (np.isfinite(obstacle_context) &
            ~np.isfinite(self.history.last_window_obstacle_elevation))
        height, support, occupied, physical_support = prepare_ht_context(
            elevation, observed, rejected, obstacle_context, resolution)
        inference_started = time.monotonic()
        with torch.inference_mode():
            tensor=torch.from_numpy(height[None,None])
            if self.channels_last:tensor=tensor.contiguous(memory_format=torch.channels_last)
            probabilities = torch.softmax(self.model(tensor), dim=2)[0, :, 1].numpy()
        inference_finished = time.monotonic()
        if probabilities.shape != (8, 241, 241):
            self.get_logger().error(f"Unexpected model output shape {probabilities.shape}")
            return
        # A different observed surface is never selected as free ground. Its
        # own cell is forbidden in all directions, independently of the model;
        # neighbours can still use its measured height as real context.
        probabilities[:, occupied] = 0.
        support |= occupied

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
        # Keep measured obstacle geometry distinct from learned vehicle scores.
        result.layers = [f"ht_dir_{k}" for k in range(8)] + ["ht_valid", "ht_observation_valid", "ht_obstacle", "ht_elevation"]
        result.basic_layers = ["ht_valid"]
        result.outer_start_index = 0
        result.inner_start_index = 0
        for k in range(12):
            if k < 8:
                layer = np.where(support, probabilities[k], np.nan).astype(np.float32)
            elif k == 8:
                layer = support.astype(np.float32)
            elif k == 9:
                layer = physical_support.astype(np.float32)
            elif k == 10:
                layer = occupied.astype(np.float32)
            else:
                # Same world geometry, crop and physical observations as HT.
                layer = np.where(physical_support & ~occupied,
                                 elevation[25:-25, 25:-25], np.nan).astype(np.float32)
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
        published = time.monotonic()
        context_dump_s = 0.
        context_directory = os.environ.get('HT_CONTEXT_DUMP')
        if context_directory and self.context_schedule.due(stamp_s):
            dump_started = time.monotonic()
            directory = Path(context_directory)
            directory.mkdir(parents=True, exist_ok=True)
            filename = directory / f'{stamp_key[0]}_{stamp_key[1]:09d}.npz'
            # A source stamp identifies immutable inference inputs. Never
            # replace an earlier context if a node is accidentally restarted.
            save_immutable_npz(filename, source_stamp=stamp_s,
                    geometry=[center_x, center_y, resolution], height=height,
                    history_variance=variance,
                    source_elevation=source_elevation, source_variance=source_variance,
                    source_observation_age=source_age,
                    source_geometry=[source.info.pose.position.x, source.info.pose.position.y, resolution],
                    raw_history=raw_history, observed=observed, rejected=rejected,
                    quality_rejected=quality.rejected_mask, obstacle_context=obstacle_context,
                    support=support, physical_support=physical_support, occupied=occupied,
                    probabilities=probabilities)
            self.last_context_dump_stamp = stamp_s
            self.context_schedule.saved(stamp_s)
            context_dump_s = time.monotonic()-dump_started
        self.count += 1
        self.diagnostics.append({'stamp_s': stamp_s, 'fused_cells': fused,
                                 'observed_cells': int(observed.sum()), 'supported_cells': int(support.sum()),
                                 'surface': surface_stats, 'quality': quality.stats,
                                 'source_rejected_cells': int(source_rejected.sum()),
                                 'known_obstacle_cells': int(occupied.sum()),
                                 'retained_filtered_obstacle_cells': int(retained_filtered_obstacles.sum()),
                                 'new_rejected_observations': rejected_updates,
                                 'retained_current_edge_cells': int(retained_edges.sum()),
                                 'source_age_at_callback_s': source_age_at_start,
                                 'fusion_and_quality_s': fusion_finished-started,
                                 'support_and_history_publish_s': inference_started-fusion_finished,
                                 'network_inference_s': inference_finished-inference_started,
                                 'ht_serialize_publish_s': published-inference_finished,
                                 'context_dump_s': context_dump_s,
                                 'elapsed_s': time.monotonic()-started})
        if self.count % 5 == 0:
            self.get_logger().info(
                f"maps={self.count} fused={fused} observed={observed.sum()} "
                f"history_tiles={len(self.history.tiles)} valid={support.sum()} "
                f"center_valid={bool(support[120, 120])} map_processing_s={time.monotonic() - started:.3f} "
                f"network_s={inference_finished-inference_started:.3f}"
            )


def main():
    # Default SIGINT raises inside callbacks and can tear a diagnostic ZIP.
    # Request exit, finish this callback, then save history before shutdown.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    stop = GracefulStop()
    previous = signal.signal(signal.SIGINT, stop.request)
    node = None
    executor = SingleThreadedExecutor()
    try:
        node = CupyToHt()
        executor.add_node(node)
        while rclpy.ok() and not stop.requested:
            executor.spin_once(timeout_sec=.1)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            if node is not None:
                if node.history is not None and os.environ.get("HT_HISTORY_DUMP"):
                    node.history.save(os.environ["HT_HISTORY_DUMP"])
                    node.get_logger().info(f"Saved global historical elevation to {os.environ['HT_HISTORY_DUMP']}")
                if os.environ.get('HT_DIAGNOSTICS_DUMP'):
                    Path(os.environ['HT_DIAGNOSTICS_DUMP']).write_text(json.dumps(node.diagnostics, indent=2)+'\n')
                node.destroy_node()
        finally:
            try:
                executor.shutdown()
                rclpy.try_shutdown()
            finally:
                signal.signal(signal.SIGINT, previous)


if __name__ == "__main__":
    main()
