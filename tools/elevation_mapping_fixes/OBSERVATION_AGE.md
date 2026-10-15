# Direct observation age and GridMap world coordinates

`trial_setup.yaml` now requests `observation_age` in
`/elevation_mapping/elevation_map_raw`. Its unit is seconds. Recover a cell's
accepted observation source time as:

```
cell_source_time = GridMap.header.stamp - observation_age[cell]
```

The source is `PointCloud2.header.stamp`. A cell's source time advances only
when the actual point-fusion kernel accepted at least one direct point in that
cell and the resulting elevation remains valid. Merely retaining an elevation
in the rolling window, publishing it again, updating variance, ray cleanup, or
rejecting a height outlier does not make it newly observed. Invalid or never
directly observed cells publish NaN. Out-of-order scans cannot move the latest
accepted source timestamp backwards.

The existing `time` layer remains available for the mapper's original cleanup
logic. That layer increments by a fixed interval per timer callback and must
not be used as a precise source timestamp, especially during accelerated or
delayed replay. The new timestamp buffer stores float64 internally to preserve
fractional UNIX epoch seconds, but publishes relative float32 ages for GridMap
compatibility. Its memory cost is about 0.66 MiB for the trial's 293×293 internal
grid. It shifts and clears together with the elevation map.

The ROS wrapper also removes a redundant coordinate flip. The core
`get_map_with_name_ref()` already flips its internal +X/+Y indexing into
GridMap's -X/-Y indexing. The wrapper now only transposes for column-major wire
serialization. Repeating the flip previously mirrored measurements about the
rolling map center. A real CUDA single-point regression placed a source point
at world `(1.01, 0.31)` m: the previous serializer decoded it at approximately
`(-1.0234, -0.3275)` m; the corrected serializer decodes it at approximately
`(1.0234, 0.3275)` m, inside its expected 4.09 cm cell.

Regression checks exercise actual GPU point fusion, source-time precision,
retained cells, outlier rejection, out-of-order scans, shifting, clearing and
the actual ROS GridMap publisher:

```
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export LD_LIBRARY_PATH=/home/lzz/.local/lib/python3.12/site-packages/nvidia/cuda_nvrtc/lib:/home/lzz/.local/lib/python3.12/site-packages/nvidia/cuda_runtime/lib:$LD_LIBRARY_PATH
python -m pytest -q src/elevation_mapping_cupy_2204/elevation_mapping_cupy/script/elevation_mapping_cupy/tests/test_observation_age.py
```

Rebuild the ROS executable after wrapper edits because CMake installs it as a
copied program rather than a source symlink:

```
colcon build --packages-select elevation_mapping_cupy
```

Previously recorded generated elevation/HT maps need regeneration from the
original registered-scan bag to apply the coordinate correction; moving the
final display image alone cannot repair historical fusion.

The registered-world-cloud subscriber now requests RELIABLE depth 30 in the
live trial. CMU's `/registered_scan` publisher uses the default rclcpp reliable
QoS. Raw sensor subscribers keep BEST_EFFORT depth 5 by default for compatibility
with hardware sensor publishers; offline playback uses RELIABLE depth 100.
`qos_reliability` and `queue_depth` can override the live selection explicitly.

`CUPY_STATS_DUMP` also reports source and callback receive timestamps, mean/max
processing time, and source-to-callback queue age. These distinguish missed
callbacks from accumulated old scans: a deeper reliable queue is useful only
when processing keeps up. Both delivery counts and queue age need checking.
