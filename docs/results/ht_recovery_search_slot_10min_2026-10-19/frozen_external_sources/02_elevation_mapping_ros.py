#!/usr/bin/env python3
#
# Copyright (c) 2022, Takahiro Miki. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.
#
"""ROS 2 wrapper for the CuPy elevation mapping core."""

from functools import partial
from typing import Any
import json
import os
import time
import threading
import signal
from array import array as FloatArray
from pathlib import Path

import numpy as np
import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from grid_map_msgs.msg import GridMap
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from scipy.spatial.transform import Rotation
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Float32MultiArray, MultiArrayDimension, MultiArrayLayout
from tf2_ros import Buffer, ConnectivityException, ExtrapolationException, LookupException, TransformListener

from elevation_mapping_cupy import ElevationMap, Parameter


def _load_yaml(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def _resolve_package_paths(value: Any, share_dir: str) -> Any:
    if isinstance(value, str):
        return value.replace("$(rospack find elevation_mapping_cupy)", share_dir)
    if isinstance(value, list):
        return [_resolve_package_paths(item, share_dir) for item in value]
    if isinstance(value, dict):
        return {key: _resolve_package_paths(item, share_dir) for key, item in value.items()}
    return value


def _set_parameter_fields(param: Parameter, values: dict[str, Any]) -> None:
    aliases = {
        "drift_compensation_variance_inler": "drift_compensation_variance_inlier",
    }
    for key, value in values.items():
        field_name = aliases.get(key, key)
        if hasattr(param, field_name):
            setattr(param, field_name, value)


def _pointcloud_to_numpy(msg: PointCloud2, channels: list[str]) -> np.ndarray:
    points = point_cloud2.read_points(msg, field_names=channels, skip_nans=True)
    if isinstance(points, np.ndarray):
        if points.dtype.names:
            return np.column_stack([points[name] for name in channels]).astype(np.float32, copy=False)
        return np.asarray(points, dtype=np.float32)
    return np.asarray(list(points), dtype=np.float32)


def _pointcloud_qos(config: dict[str, Any], offline: bool):
    """Registered clouds use reliable transport; raw sensor QoS stays compatible."""
    if offline:
        return QoSProfile(depth=100, reliability=ReliabilityPolicy.RELIABLE)
    registered = bool(config.get("registered_cloud_sensor_frame"))
    reliability = config.get("qos_reliability", "reliable" if registered else "best_effort")
    if reliability not in ("reliable", "best_effort"):
        raise ValueError(f"Unsupported pointcloud qos_reliability: {reliability}")
    depth = int(config.get("queue_depth", 30 if registered else 5))
    if depth <= 0:
        raise ValueError("Pointcloud queue_depth must be positive")
    return QoSProfile(depth=depth, reliability=(
        ReliabilityPolicy.RELIABLE if reliability == "reliable" else ReliabilityPolicy.BEST_EFFORT
    ))


class ElevationMappingNode(Node):
    def __init__(self) -> None:
        super().__init__("elevation_mapping")
        self.share_dir = get_package_share_directory("elevation_mapping_cupy")
        self.declare_parameter("core_param_file", f"{self.share_dir}/config/core/core_param.yaml")
        self.declare_parameter("setup_file", f"{self.share_dir}/config/core/example_setup.yaml")

        core_param_file = self.get_parameter("core_param_file").value
        setup_file = self.get_parameter("setup_file").value
        self.config = _resolve_package_paths({**_load_yaml(core_param_file), **_load_yaml(setup_file)}, self.share_dir)

        self.param = Parameter()
        _set_parameter_fields(self.param, self.config)
        self.param.subscriber_cfg = self.config.get("subscribers", self.param.subscriber_cfg)
        self.param.update()

        self.subscriber_configs = self.config.get("subscribers", {})
        self.publisher_configs = self.config.get("publishers", {})
        self.map_frame = self.config.get("map_frame", self.param.map_frame if hasattr(self.param, "map_frame") else "map")
        self.base_frame = self.config.get("base_frame", "base_link")

        self.offline_tf_bag = os.environ.get("CUPY_OFFLINE_TF_BAG", "")
        self.tf_buffer = Buffer(cache_time=Duration(seconds=1800.0 if self.offline_tf_bag else 10.0))
        if self.offline_tf_bag:
            # Offline data already includes the entire trajectory. Preload TF
            # before playback so future transforms need not wait on ROS queues.
            import rosbag2_py
            from rclpy.serialization import deserialize_message
            from tf2_msgs.msg import TFMessage
            reader = rosbag2_py.SequentialReader()
            reader.open(rosbag2_py.StorageOptions(uri=self.offline_tf_bag, storage_id="mcap"),
                        rosbag2_py.ConverterOptions("", ""))
            reader.set_filter(rosbag2_py.StorageFilter(topics=["/tf", "/tf_static"]))
            count = 0
            while reader.has_next():
                topic, data, _ = reader.read_next()
                for transform in deserialize_message(data, TFMessage).transforms:
                    if topic == "/tf_static":
                        self.tf_buffer.set_transform_static(transform, "recorded_bag")
                    else:
                        self.tf_buffer.set_transform(transform, "recorded_bag")
                    count += 1
            self.tf_listener = None
            self.get_logger().info(f"Preloaded {count} recorded transforms for offline mapping")
        else:
            self.tf_listener = TransformListener(self.tf_buffer, self)
        self.map = ElevationMap(self.param)
        # Incoming scans and periodic work must be scheduled independently.
        # Protect the complete map operation (including move_to's center)
        # because the core lock does not cover every wrapper-visible field.
        self.map_access_lock = threading.RLock()
        self.scan_callback_group = MutuallyExclusiveCallbackGroup()
        self.timer_callback_group = MutuallyExclusiveCallbackGroup()
        self.publish_callback_group = MutuallyExclusiveCallbackGroup()
        self.map_data = np.zeros((self.map.cell_n - 2, self.map.cell_n - 2), dtype=np.float32)
        self.map_translation = None
        self.map_rotation = None
        self.last_stamp = None
        self.last_integrated_stamp = None
        self.pointcloud_process_counter = 0
        self.pointcloud_receive_counter = 0
        self.first_cloud_stamp_s = None
        self.last_cloud_stamp_s = None
        self.first_cloud_receive_clock_s = None
        self.last_cloud_receive_clock_s = None
        self.last_processed_cloud_stamp_s = None
        self.pointcloud_processing_total_s = 0.0
        self.pointcloud_processing_max_s = 0.0
        self.cloud_queue_ages_s = []
        self.timer_profile = {}

        self.pointcloud_subscriptions = []
        self.map_publishers = {}
        self.map_timers = []
        self.register_subscribers()
        self.register_publishers()
        self.register_timers()
        self.get_logger().info("[ElevationMappingCupy] ROS 2 node initialized")
        if os.environ.get("CUPY_READY_FILE"):
            Path(os.environ["CUPY_READY_FILE"]).write_text("ready\n")

    def register_subscribers(self) -> None:
        for key, config in self.subscriber_configs.items():
            if config.get("data_type") != "pointcloud":
                self.get_logger().warn(f"ROS 2 wrapper currently skips non-pointcloud subscriber [{key}]")
                continue
            topic_name = config["topic_name"]
            callback = partial(self.pointcloud_callback, sub_key=key)
            qos = _pointcloud_qos(config, bool(self.offline_tf_bag))
            sub = self.create_subscription(
                PointCloud2, topic_name, callback, qos,
                callback_group=self.scan_callback_group,
            )
            self.pointcloud_subscriptions.append(sub)
            self.get_logger().info(
                f"Subscribed to PointCloud2 topic: {topic_name} reliability={qos.reliability.name} depth={qos.depth}"
            )

    def register_publishers(self) -> None:
        for name, config in self.publisher_configs.items():
            self.map_publishers[name] = self.create_publisher(GridMap, f"~/{name}", 1)
            fps = float(config.get("fps", 1.0))
            self.map_timers.append(self.create_timer(
                1.0 / fps, partial(self.timed_timer, f"publish/{name}", partial(self.publish_map, name)),
                callback_group=self.publish_callback_group,
            ))

    def register_timers(self) -> None:
        for interval, name, callback in [
            (1.0 / float(self.config.get("update_variance_fps", 5.0)), "variance", self.update_variance),
            (1.0 / float(self.config.get("update_pose_fps", 10.0)), "pose", self.update_pose),
            (float(self.config.get("time_interval", 0.1)), "time", self.update_time),
        ]:
            self.create_timer(interval, partial(self.timed_timer, name, callback),
                              callback_group=self.timer_callback_group)
        if os.environ.get("CUPY_STATS_DUMP"):
            self.create_timer(5.0, self.write_processing_stats, callback_group=self.timer_callback_group)

    def timed_timer(self, name, callback):
        started = time.monotonic()
        try:
            return callback()
        finally:
            elapsed = time.monotonic()-started
            stats = self.timer_profile.setdefault(name, {"count": 0, "total_s": 0.0, "max_s": 0.0})
            stats["count"] += 1
            stats["total_s"] += elapsed
            stats["max_s"] = max(stats["max_s"], elapsed)

    def write_processing_stats(self) -> None:
        if not os.environ.get("CUPY_STATS_DUMP"):
            return
        ages = np.asarray(self.cloud_queue_ages_s, dtype=np.float64)
        stats = {
            "received_cloud_callbacks": self.pointcloud_receive_counter,
            "processed_clouds": self.pointcloud_process_counter,
            "first_cloud_source_stamp_s": self.first_cloud_stamp_s,
            "last_cloud_source_stamp_s": self.last_cloud_stamp_s,
            "last_processed_cloud_source_stamp_s": self.last_processed_cloud_stamp_s,
            "first_cloud_receive_clock_s": self.first_cloud_receive_clock_s,
            "last_cloud_receive_clock_s": self.last_cloud_receive_clock_s,
            "processing_mean_s": (self.pointcloud_processing_total_s/self.pointcloud_process_counter
                                  if self.pointcloud_process_counter else None),
            "processing_max_s": self.pointcloud_processing_max_s,
            "queue_age_median_s": float(np.median(ages)) if ages.size else None,
            "queue_age_p95_s": float(np.quantile(ages, .95)) if ages.size else None,
            "queue_age_max_s": float(ages.max()) if ages.size else None,
            "timer_profile": {name: {**profile, "mean_s": profile["total_s"]/profile["count"]}
                              for name, profile in self.timer_profile.items()},
        }
        Path(os.environ["CUPY_STATS_DUMP"]).write_text(json.dumps(stats, indent=2)+'\n')

    def pointcloud_callback(self, msg: PointCloud2, sub_key: str) -> None:
        processing_started = time.monotonic()
        self.pointcloud_receive_counter += 1
        source_stamp_s = msg.header.stamp.sec + msg.header.stamp.nanosec*1e-9
        receive_clock_s = self.get_clock().now().nanoseconds / 1e9
        if self.first_cloud_stamp_s is None:
            self.first_cloud_stamp_s = source_stamp_s
            self.first_cloud_receive_clock_s = receive_clock_s
        self.last_cloud_stamp_s = source_stamp_s
        self.last_cloud_receive_clock_s = receive_clock_s
        self.cloud_queue_ages_s.append(receive_clock_s-source_stamp_s)
        config = self.param.subscriber_cfg[sub_key]
        channels = ["x", "y", "z"] + config.get("channels", [])
        try:
            points = _pointcloud_to_numpy(msg, channels)
        except Exception as exc:
            self.get_logger().error(f"Failed to decode PointCloud2 for [{sub_key}]: {exc}")
            return
        if points.size == 0:
            return

        stamp = Time.from_msg(msg.header.stamp)
        self.last_stamp = stamp
        # The TF listener has its own executor thread. Keep scan waits bounded
        # so an unavailable transform cannot occupy the ingestion worker long.
        tf_wait = Duration(seconds=0.0 if self.offline_tf_bag else 0.05)
        try:
            transform = self.tf_buffer.lookup_transform(
                self.map_frame,
                msg.header.frame_id,
                stamp,
                timeout=tf_wait,
            )
        except (LookupException, ConnectivityException, ExtrapolationException) as exc:
            try:
                transform = self.tf_buffer.lookup_transform(
                    self.map_frame,
                    msg.header.frame_id,
                    Time(),
                    timeout=Duration(seconds=0.0),
                )
            except (LookupException, ConnectivityException, ExtrapolationException):
                self.get_logger().warn(f"TF lookup failed for pointcloud [{sub_key}]: {exc}")
                return

        translation, rotation = self.transform_to_arrays(transform)
        # CMU's registered scans contain world-frame points. Recover the
        # sensor-frame points expected by the elevation fusion kernels while
        # retaining the sensor origin used for ray and range calculations.
        sensor_frame = config.get("registered_cloud_sensor_frame")
        if sensor_frame:
            if msg.header.frame_id != self.map_frame:
                self.get_logger().error("registered_cloud_sensor_frame requires a map-frame cloud")
                return
            try:
                sensor_tf = self.tf_buffer.lookup_transform(
                    self.map_frame, sensor_frame, stamp, timeout=tf_wait
                )
            except (LookupException, ConnectivityException, ExtrapolationException) as exc:
                try:
                    sensor_tf = self.tf_buffer.lookup_transform(
                        self.map_frame, sensor_frame, Time(), timeout=Duration(seconds=0.0)
                    )
                    age = abs((stamp - Time.from_msg(sensor_tf.header.stamp)).nanoseconds) / 1e9
                    if age > 0.3:
                        self.get_logger().warn(f"Sensor pose too far from registered cloud: {age:.3f}s")
                        return
                except (LookupException, ConnectivityException, ExtrapolationException):
                    self.get_logger().warn(f"Sensor pose unavailable for registered cloud: {exc}")
                    return
            translation, rotation = self.transform_to_arrays(sensor_tf)
            points[:, :3] = (points[:, :3] - translation) @ rotation
        with self.map_access_lock:
            self.map.input_pointcloud(
                points, channels, rotation, translation, 0, 0,
                observation_stamp=stamp.nanoseconds / 1e9,
            )
            if self.last_integrated_stamp is None or stamp > self.last_integrated_stamp:
                self.last_integrated_stamp = stamp
        self.pointcloud_process_counter += 1
        self.last_processed_cloud_stamp_s = source_stamp_s
        elapsed = time.monotonic()-processing_started
        self.pointcloud_processing_total_s += elapsed
        self.pointcloud_processing_max_s = max(self.pointcloud_processing_max_s, elapsed)

    def update_pose(self) -> None:
        if self.last_stamp is None:
            return
        # Online rolling-window motion follows the latest available robot pose
        # without waiting on an old queued scan. Offline TF is preloaded through
        # the future trajectory, so replay must request the current scan stamp.
        pose_stamp = self.last_stamp if self.offline_tf_bag else Time()
        try:
            transform = self.tf_buffer.lookup_transform(
                self.map_frame,
                self.base_frame,
                pose_stamp,
                timeout=Duration(seconds=0.0),
            )
        except (LookupException, ConnectivityException, ExtrapolationException):
            return

        translation, rotation = self.transform_to_arrays(transform)
        with self.map_access_lock:
            self.map.move_to(translation, rotation)
            self.map_translation = transform.transform.translation
            self.map_rotation = transform.transform.rotation

    def update_variance(self) -> None:
        with self.map_access_lock:
            self.map.update_variance()

    def update_time(self) -> None:
        with self.map_access_lock:
            self.map.update_time()

    def publish_map(self, name: str) -> None:
        if self.map_translation is None or self.last_integrated_stamp is None:
            return
        config = self.publisher_configs[name]
        msg = GridMap()
        msg.header.frame_id = self.map_frame
        # Freeze geometry and every GPU layer under the same lock. Serialize
        # the CPU copies afterward, allowing new scans to update the map while
        # DDS prepares/publishes the previous coherent snapshot.
        snapshots = []
        with self.map_access_lock:
            # A timer heartbeat is not new perception. Preserve the last
            # successfully integrated scan time so downstream freshness gates
            # stop execution if input processing stalls.
            publication_time = self.last_integrated_stamp
            msg.header.stamp = publication_time.to_msg()
            msg.info.resolution = float(self.map.resolution)
            msg.info.length_x = float(self.map.map_length)
            msg.info.length_y = float(self.map.map_length)
            center = self.map.center.get()
            for layer in config.get("layers", []):
                try:
                    if layer == "observation_age":
                        self.map.get_observation_age_ref(publication_time.nanoseconds / 1e9, self.map_data)
                    else:
                        self.map.get_map_with_name_ref(layer, self.map_data)
                except Exception as exc:
                    if layer in config.get("basic_layers", []):
                        self.get_logger().warn(f"Missing basic layer [{layer}]: {exc}")
                    continue
                snapshots.append((layer, np.ascontiguousarray(self.map_data.T, dtype=np.float32)))
        msg.info.pose.position.x = float(center[0])
        msg.info.pose.position.y = float(center[1])
        msg.info.pose.position.z = 0.0
        msg.info.pose.orientation.w = 1.0
        msg.basic_layers = list(config.get("basic_layers", []))

        for layer, data in snapshots:
            msg.layers.append(layer)
            # Both core getters already flip their internal +X/+Y indexing
            # into GridMap's -X/-Y indexing. Only transpose for Eigen's
            # column-major wire layout; another flip mirrors world positions.
            array = Float32MultiArray()
            n = int(data.shape[0])
            array.layout = MultiArrayLayout(
                dim=[
                    MultiArrayDimension(label="column_index", size=n, stride=n * n),
                    MultiArrayDimension(label="row_index", size=n, stride=n),
                ],
                data_offset=0,
            )
            packed = FloatArray('f')
            packed.frombytes(data.tobytes())
            array.data = packed
            msg.data.append(array)

        msg.outer_start_index = 0
        msg.inner_start_index = 0
        self.map_publishers[name].publish(msg)

    @staticmethod
    def transform_to_arrays(transform) -> tuple[np.ndarray, np.ndarray]:
        t = transform.transform.translation
        q = transform.transform.rotation
        translation = np.array([t.x, t.y, t.z], dtype=np.float32)
        rotation = Rotation.from_quat([q.x, q.y, q.z, q.w]).as_matrix().astype(np.float32)
        return translation, rotation


def _stop_executor(executor) -> None:
    # This installed Jazzy executor lacks wait_for_threads and its base
    # shutdown destroys the guard before joining workers. Spin has already
    # stopped submitting work: drain the pool while the guard is still valid.
    workers = getattr(executor, "_executor", None)
    try:
        if workers is not None:
            workers.shutdown(wait=True)
        for future in getattr(executor, "_futures", []):
            if future.done() and not future.cancelled():
                future.result()  # Surface real callback errors; never hide them.
    finally:
        executor.shutdown()


def main(args=None) -> None:
    from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
    from rclpy.signals import SignalHandlerOptions
    previous_signals = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    # A signal requests loop exit first. Keep ROS context valid until worker
    # callbacks and entity destruction finish, then shut it down explicitly.
    for sig in previous_signals:
        signal.signal(sig, signal.default_int_handler)
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = ElevationMappingNode()
    executor = MultiThreadedExecutor(num_threads=4)
    try:
        # Separate workers serve TF, scans and timers. Map snapshots/mutations
        # stay serialized by the node lock while TF waits occur outside it.
        rclpy.spin(node, executor=executor)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        # Workers may still own GPU/map operations when spin is interrupted.
        # Join them before reading final statistics or destroying ROS entities.
        _stop_executor(executor)
        if os.environ.get("CUPY_STATS_DUMP"):
            node.write_processing_stats()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        for sig, handler in previous_signals.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    main()
