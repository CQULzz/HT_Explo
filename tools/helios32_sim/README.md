Corrected Scout / nominal Helios32 simulation

New experiments use `simulation.launch.py` in this directory with an isolated
`HT_HELIOS_ROOT`. Historical transparent 64-beam observations remain controls,
not a representation of real Scout near-ground visibility.

The user permits a nominal sensor approximation because the device suffix/RPM
is not known. `helios_5515.json` uses the manufacturer RS-Helios-5515 manual's
32 explicit, nonuniform vertical angles, -55..+15 degrees, 0.2-degree horizontal
spacing and a 10Hz simulated rotation (600rpm). This is not recovered DIFOP
calibration. No artificial -75-degree beams, calibrated intensity/noise, firing
times or intra-frame motion distortion are claimed.

Source: https://cdn.robosense.cn/20220923164517_61201.pdf (Table 5).
An actual device calibration requires its DIFOP/angle file; the local historical
exports inspected here contain configuration/documents but no recovered DIFOP.

Generate assets from the existing pinned `eletranskit_scout` package:

```sh
python3 tools/helios32_sim/prepare_assets.py \
  --package-dir /path/to/eletranskit_scout/src/ele_scout_kit \
  --output /path/to/new_runtime/common_sensor_optical
```

The generator refuses to overwrite an existing output directory. It preserves
original collision geometry and adds opaque collisions for every visual mesh,
including the chassis sides, wheels, rack and sensors. The single link is
kinematic, matching the existing CMU pose-driven actuator; this is not wheel
dynamics/contact-based driving. Camera pose updates use an empty anchor; the
physical camera mesh is already present in the Scout body.

The optical exit starts 1mm outside the radial bound of the Helios housing mesh
(about 0.051m), an explicit approximation rather than guessed device calibration.
Ray tracing starts there at zero trace distance. The configured 0.2m output
minimum is applied AFTER first intersection, so near-blind obstructions still
occlude farther surfaces. Do not start the ray at 0.2m or recast after a self hit.

The custom Gazebo CPU-ray plugin sets each physical ray endpoint to its nominal
channel angle, and publishes organized `rslidar_points` plus the self-filtered
CMU input `velodyne_points`. Self filtering removes owned-body returns while
retaining their shadows. The Gazebo-native uniform LaserScan angle metadata
must not be used as a nonuniform-channel point cloud; use these ROS clouds.

The pinned URDF aliases `rslidar` to the rack mounting plane. Treating this as
the optical plane causes immediate downward-ray intersections with the rack.
This nominal simulation uses the manual's 63.5mm base-to-optical-origin offset:
base_link to optical sensor (0.1725,0,0.6137)m, ground to optical sensor 0.84849m.
This mounting-datum interpretation is an explicit approximation, not a change
to real-vehicle calibrated TF. All body meshes retain their world placement.
Set `HT_HELIOS_ASSETS` to select another generated asset directory.
The carrier rotates the scanner with the vehicle
and applies the matching yaw in registration. The original CMU velocity
integration and terrain fitting remain unchanged. Raw Gazebo sensor timestamps
use simulation time; the existing CMU `use_gazebo_time=false` bridge stamps the
registered scan with odometry host time. Receipt-derived map ages are not a
physical sensor latency benchmark. Simulated scan rate and wall-clock throughput
are recorded separately; CPU ray tracing may run below real time.

Build `src/helios32_sim` with ROS Humble / Gazebo 11. The included carrier source
is derived from CMU AEDE 158e67b with provenance in vehicleSimulator.source.json;
the derivation script checks the exact baseline SHA256. Original license BSD,
new ray plugin Apache-2.0.

The separate `cupy_to_ht` bridge must use the generated manifest's
`lidar_height_above_ground_m` for `surface_sensor_ground_offset_m` (0.84849m for
this nominal profile), because the carrier odometry represents the scanner.
Do not reuse the historical 0.75m / development 0.78499m bridge height.

Validation: `validation/helios_collision_20261115/REPORT_zh.md`. Final geometry
and scan registration passed static / heading probes. The earlier 600s run used
the incorrect mounting-plane optical origin and is retained as development
evidence, not acceptance of the final navigation stack.

Runtime and evidence for this change:
`/home/lzz/ht_helios_collision_20261115` and `D:/HT-Helios-Collision-20261115`.
