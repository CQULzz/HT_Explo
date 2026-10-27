#!/usr/bin/env python3
"""Infer the local eight-direction HT map from observed CuPy elevation cells."""

from copy import deepcopy
from array import array as FloatArray
import json
import math
import os
import signal
from pathlib import Path
import time
from threading import RLock

import numpy as np
import torch

import rclpy
from grid_map_msgs.msg import GridMap
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.signals import SignalHandlerOptions
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from nav_msgs.msg import Odometry
from std_msgs.msg import Float32, Float32MultiArray, MultiArrayDimension, MultiArrayLayout, String

from model import load_student_model
from historical_elevation import HistoricalElevation
from elevation_quality import preprocess_elevation, retain_recent_obstacle_edges, warmup_quality
from local_surface import SurfaceReferenceEstimator
from cpu_threads import configure_cpu_threads
from ht_support import prepare_ht_context, preserve_rejected_obstacles
from inference_context_io import ContextCaptureSchedule, GracefulStop, save_immutable_npz
from input_odometry import InputOdometry
from latest_input import LatestInput
from small_holes import repair_small_holes


def decode_elevation_source(source):
    """Validate the model's metric input contract before mutating history."""
    info = source.info
    resolution = float(info.resolution)
    if source.header.frame_id != 'map' or not 0.040 <= resolution <= 0.042:
        raise ValueError('HT requires map-frame elevation at about 0.041 m/cell')
    lengths = (info.length_x/resolution, info.length_y/resolution)
    if any(not math.isfinite(v) or not math.isclose(v, 291, rel_tol=0, abs_tol=1e-6)
           for v in lengths):
        raise ValueError(f'HT requires exact 291x291 input geometry; got {lengths}')
    q = info.pose.orientation
    if (not all(math.isfinite(v) for v in (info.pose.position.x, info.pose.position.y,
                                         info.pose.position.z, q.x, q.y, q.z, q.w))
            or max(abs(q.x), abs(q.y), abs(q.z)) > 1e-6 or abs(abs(q.w)-1) > 1e-6):
        raise ValueError('HT requires finite, axis-aligned map geometry')
    if (len(source.layers) != len(source.data) or len(set(source.layers)) != len(source.layers)
            or not 0 <= source.outer_start_index < 291 or not 0 <= source.inner_start_index < 291):
        raise ValueError('Invalid elevation layers/circular buffer indices')
    decoded = []
    for name in ('elevation', 'variance', 'observation_age'):
        if name not in source.layers:
            raise ValueError(f'Missing required elevation layer: {name}')
        data = source.data[source.layers.index(name)]
        dims = data.layout.dim
        if (len(dims) != 2 or dims[0].label != 'column_index' or dims[1].label != 'row_index'
                or dims[0].size != 291 or dims[1].size != 291
                or dims[0].stride != 291*291 or dims[1].stride != 291
                or data.layout.data_offset != 0 or len(data.data) != 291*291):
            raise ValueError(f'Invalid elevation array layout/length: {name}')
        layer = np.asarray(data.data, np.float32).reshape((291, 291), order='F')
        decoded.append(np.roll(layer, (-source.outer_start_index, -source.inner_start_index), (0, 1)))
    return resolution, *decoded


class CupyToHt(Node):
    def __init__(self):
        super().__init__("cupy_to_ht_bridge")
        threads=self.declare_parameter('ht_torch_threads',4).value
        requested_device=self.declare_parameter('ht_device','cpu').value
        self.channels_last=self.declare_parameter('ht_channels_last',requested_device!='cuda').value
        self.small_holes=self.declare_parameter('ht_small_hole_repair',False).value
        self.blas_limit, cpu_threads = configure_cpu_threads(threads)
        self.quality_backend=warmup_quality(self.declare_parameter('ht_quality_backend','auto').value)
        self.get_logger().info(f'Elevation quality backend: {self.quality_backend}')
        cpu_threads['model_memory_format']='channels_last' if self.channels_last else 'contiguous'
        self.get_logger().info(f'CPU pools: PyTorch={threads}, BLAS=1; {cpu_threads["model_memory_format"]}')
        if os.environ.get('HT_DIAGNOSTICS_DUMP'):
            Path(os.environ['HT_DIAGNOSTICS_DUMP']).with_name('ht_cpu_threads.json').write_text(
                json.dumps(cpu_threads, indent=2)+'\n')
        if requested_device not in ('cpu','cuda'):
            raise ValueError('ht_device must be cpu or cuda')
        if requested_device=='cuda' and not torch.cuda.is_available():
            raise RuntimeError('CUDA requested for HT but unavailable; refusing silent CPU fallback')
        if requested_device=='cuda':
            torch.backends.cuda.matmul.allow_tf32=False
            torch.backends.cudnn.allow_tf32=False
        self.device=torch.device(requested_device)
        self.get_logger().info(f'HT inference device: {self.device}')
        self.model = load_student_model(
            str(Path(__file__).with_name("student_best_epoch_weights.pth")), self.device
        )
        if self.channels_last:
            self.model=self.model.to(memory_format=torch.channels_last)
        if self.device.type=='cuda':
            # Complete CUDA initialization before subscribing to timestamped maps.
            with torch.inference_mode():
                warmup=torch.zeros((1,1,291,291),device=self.device)
                if self.channels_last:warmup=warmup.contiguous(memory_format=torch.channels_last)
                self.model(warmup)
                torch.cuda.synchronize()
        self.pub = self.create_publisher(GridMap, self.declare_parameter('ht_topic', '/ht_traversability/global_local').value, 1)
        self.history_pub = self.create_publisher(GridMap, "/elevation_mapping/historical_local", 1)
        self.history = None
        offset = self.declare_parameter('surface_sensor_ground_offset_m', -1.0).value
        self.surface = SurfaceReferenceEstimator(sensor_ground_offset_m=offset if offset >= 0 else None)
        self.input_odometry = InputOdometry(self.declare_parameter('odometry_child_frame', '').value)
        self.odometry_lock=RLock()
        self.pending_maps=LatestInput()
        self.odometry = self.input_odometry.samples
        self.input_status = self.create_publisher(String, '/ht_input_status', 1)
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
            GridMap, self.declare_parameter('elevation_topic', '/elevation_mapping/elevation_map_raw').value, self.enqueue_map,
            QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE)
        )
        self.count = 0
        self.processing_group=MutuallyExclusiveCallbackGroup()
        self.processing_timer=self.create_timer(.005,self.process_pending,callback_group=self.processing_group)

    def enqueue_map(self, msg):
        self.pending_maps.put(msg)

    def process_pending(self):
        source=self.pending_maps.take()
        if source is not None:self.on_map(source)

    def on_odometry(self, msg):
        with self.odometry_lock:
            self.input_odometry.add(msg, self.get_clock().now().nanoseconds/1e9)
            fault=self.input_odometry.fault
        if fault:self.input_status.publish(String(data=fault))

    def robot_z_at(self, stamp):
        with self.odometry_lock:
            return self.input_odometry.height_at(stamp)

    def on_map(self, source):
        started = time.monotonic()
        with self.odometry_lock:
            healthy=self.input_odometry.check_clock(self.get_clock().now().nanoseconds/1e9)
            fault=self.input_odometry.fault
        if not healthy:
            self.input_status.publish(String(data=fault))
            return
        source_age_at_start = self.get_clock().now().nanoseconds/1e9 - (
            source.header.stamp.sec + source.header.stamp.nanosec*1e-9)
        stamp_key = (source.header.stamp.sec, source.header.stamp.nanosec)
        if self.last_source_stamp is not None and stamp_key <= self.last_source_stamp:
            return
        try:
            resolution, elevation, variance, age = decode_elevation_source(source)
        except (ValueError, TypeError, OverflowError) as error:
            self.get_logger().error(f'Invalid elevation input: {error}')
            return
        nx = ny = 291
        if self.history is None:
            self.history = HistoricalElevation(resolution)
        elif abs(self.history.resolution - resolution) > 1e-6:
            self.get_logger().error("Historical map resolution changed; refusing mixed-resolution fusion")
            return
        stamp_s = float(source.header.stamp.sec) + source.header.stamp.nanosec * 1e-9
        self.last_source_stamp = stamp_key
        try:
            # Input arrays have already been decoded into logical GridMap order.
            source_elevation, source_variance = elevation.copy(), variance.copy()
            source_age = age.copy()
            source_quality = preprocess_elevation(elevation, variance, resolution, backend=self.quality_backend)
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
            quality = preprocess_elevation(elevation, variance, resolution, backend=self.quality_backend)
            elevation = quality.height_m
            rejected = source_rejected | quality.rejected_mask
        except (ValueError, MemoryError) as error:
            self.get_logger().error(f"Historical elevation update failed: {error}")
            return
        observed = quality.observed_quality
        fusion_finished = time.monotonic()
        if not np.any(observed):
            return

        # Historical display is optional; never serialize an unused 5-layer map.
        if self.history_pub.get_subscription_count()>0:
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
        inferred=np.zeros(elevation.shape,bool)
        hole_stats={'filled_cells':0,'filled_components':0,'candidate_components':0}
        inference_elevation=elevation
        if self.small_holes:
            inference_elevation,inferred,hole_stats=repair_small_holes(
                elevation,observed,rejected,obstacle_context,current,current_var,current_age,resolution,protected=quality.edge_mask)
        height, support, occupied, physical_support = prepare_ht_context(
            elevation, observed, rejected, obstacle_context, resolution)
        # Interpolated samples are not observations. Keep all support masks
        # based on measured inputs, and replace only the approved input pixels.
        height[inferred]=inference_elevation[inferred]
        inference_started = time.monotonic()
        with torch.inference_mode():
            tensor=torch.from_numpy(height[None,None]).to(self.device)
            if self.channels_last:tensor=tensor.contiguous(memory_format=torch.channels_last)
            probabilities = torch.softmax(self.model(tensor), dim=2)[0, :, 1].cpu().numpy()
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
        if self.small_holes:result.layers += ['ht_measured_valid','ht_interpolated']
        result.basic_layers = ["ht_valid"]
        result.outer_start_index = 0
        result.inner_start_index = 0
        for k in range(len(result.layers)):
            if k < 8:
                layer = np.where(support, probabilities[k], np.nan).astype(np.float32)
            elif k == 8:
                layer = support.astype(np.float32)
            elif k == 9:
                layer = physical_support.astype(np.float32)
            elif k == 10:
                layer = occupied.astype(np.float32)
            elif k == 11:
                # Same world geometry, crop and physical observations as HT.
                layer = np.where(physical_support & ~occupied,
                                 inference_elevation[25:-25, 25:-25], np.nan).astype(np.float32)
            elif k == 12:
                layer=observed[25:-25,25:-25].astype(np.float32)
            else:
                layer=inferred[25:-25,25:-25].astype(np.float32)
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
        # Receiving odometry continues during inference. Never publish a result
        # computed across a newly detected pose/time discontinuity.
        with self.odometry_lock:
            if not self.input_odometry.check_clock(self.get_clock().now().nanoseconds/1e9):
                self.input_status.publish(String(data=self.input_odometry.fault))
                return
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
                    inferred_ground=inferred,
                    probabilities=probabilities)
            self.last_context_dump_stamp = stamp_s
            self.context_schedule.saved(stamp_s)
            context_dump_s = time.monotonic()-dump_started
        self.count += 1
        self.diagnostics.append({'stamp_s': stamp_s, 'fused_cells': fused,
                                 'observed_cells': int(observed.sum()), 'supported_cells': int(support.sum()),
                                 'surface': surface_stats, 'quality': quality.stats,'small_holes':hole_stats,
                                 'source_rejected_cells': int(source_rejected.sum()),
                                 'known_obstacle_cells': int(occupied.sum()),
                                 'retained_filtered_obstacle_cells': int(retained_filtered_obstacles.sum()),
                                 'new_rejected_observations': rejected_updates,
                                 'retained_current_edge_cells': int(retained_edges.sum()),
                                 'source_age_at_callback_s': source_age_at_start,
                                 'pending_maps_replaced': self.pending_maps.replaced,
                                 'source_age_at_publish_s': self.get_clock().now().nanoseconds/1e9-stamp_s,
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
    executor = MultiThreadedExecutor(num_threads=2)
    try:
        node = CupyToHt()
        executor.add_node(node)
        while rclpy.ok() and not stop.requested:
            executor.spin_once(timeout_sec=.1)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            # Drain the in-flight processing callback before saving shared state.
            executor.shutdown()
            pool=getattr(executor,"_executor",None)
            if pool is not None:pool.shutdown(wait=True)
            if node is not None:
                if node.history is not None and os.environ.get("HT_HISTORY_DUMP"):
                    node.history.save(os.environ["HT_HISTORY_DUMP"])
                    node.get_logger().info(f"Saved global historical elevation to {os.environ['HT_HISTORY_DUMP']}")
                if os.environ.get('HT_DIAGNOSTICS_DUMP'):
                    Path(os.environ['HT_DIAGNOSTICS_DUMP']).write_text(json.dumps(node.diagnostics, indent=2)+'\n')
                node.destroy_node()
        finally:
            try:
                rclpy.try_shutdown()
            finally:
                signal.signal(signal.SIGINT, previous)


if __name__ == "__main__":
    main()
