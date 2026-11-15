# Scout / nominal Helios32 simulation

The default generated profile is now **crop_box**: a transparent vehicle with
endpoint removal inside the full URDF bounding box. Detailed visual meshes remain
visible but are not used as vehicle collision shapes in this profile.

```sh
python3 tools/helios32_sim/prepare_assets.py \
  --package-dir /path/to/eletranskit_scout/src/ele_scout_kit \
  --output /path/to/runtime/common_sensor_crop_box
```

The generator derives the union of all fixed URDF visual/collision geometry.
Pinned source: CQULzz/eletranskit_scout@cf0b73d. In base_link the box is about
0.930 x 0.700 x 0.885m. It is converted to the aligned rslidar frame using the
nominal optical transform (0.1725, 0, 0.6137)m. There is no extra padding.
Bounds and source hashes are in MANIFEST.json. Unsupported rotated base/sensor
axes are rejected instead of applying an incorrect axis-aligned crop.

The plugin retains /rslidar_points as raw organized data and publishes the
cropped cloud on /velodyne_points, the existing registration/mapping input.
Points on or inside the box have XYZ set to NaN; frame, stamp, organization,
channel metadata and all outside points are retained. This also removes real
obstacles inside the bounding box, a limitation of whole-body box cropping.
/helios_sim/scan_status records self_filter_mode and cropped_points separately
from collision-identity self_hits.

**Box cropping does not simulate vehicle shadows.** With transparent vehicle
geometry, external points seen through the body remain if they lie outside the
box. These observations can make ground support more optimistic. This profile
is an explicitly requested approximation, not physical near-ground acceptance.
It does not provide wheel/contact dynamics. Navigation footprint checks, HT
thresholds, TTL and TARE policy are unchanged.

The Helios launch now applies initial_support_prior.yaml to localPlanner and
pathFollower: a 0.65m-radius support prior anchored once at the first actual
base_link odometry pose in map coordinates. It stays at that initial location
without automatic expiry or expansion. Only missing support is supplied by this
user-authorized prior; obstacle, neural score/context, boundary and map-age
checks remain active. Measured GridMap layers are never rewritten. Command and
gate diagnostics record the anchor, radius and prior-supplied cell count.
The generic gate defaults to prior disabled, so other entry points do not opt in.
When copying simulation.launch.py to a runtime, also copy initial_support_prior.yaml.

To generate the previous opaque geometry in a separate folder:

```sh
python3 tools/helios32_sim/prepare_assets.py \
  --package-dir /path/to/eletranskit_scout/src/ele_scout_kit \
  --output /path/to/new_opaque_assets --self-filter collision_identity
```

That mode retains 18 opaque collisions, removes returns by collision identity
and keeps their shadows without recasting. Existing SDFs lacking a filter-mode
setting keep legacy collision_identity behavior with the new plugin. Existing
asset directories are never overwritten.

Both modes use the user-authorized RS-Helios-5515 nominal approximation:
32 nonuniform channels (-55 to +15 degrees), 1800 azimuths, simulated 10Hz
(600rpm), 0.2m output minimum applied after intersection, 51mm nominal optical
exit radius, and optical height 0.84849m above nominal ground. Set the mapping
bridge surface_sensor_ground_offset_m to the manifest height. No physical
DIFOP calibration, noise/intensity calibration or firing-time distortion is
claimed. The CPU ray sensor can run slower than wall-clock real time.

Build src/helios32_sim in an isolated Humble/Gazebo 11 workspace, source its
install/setup.bash, and prepend its lib directory to GAZEBO_PLUGIN_PATH.
Set HT_HELIOS_ROOT to a runtime with scene_assets/ and runtime/ planner files.
simulation.launch.py defaults to HT_HELIOS_ROOT/common_sensor_crop_box;
HT_HELIOS_ASSETS can select another asset directory explicitly.
Raw sensor stamps use simulation time; the inherited CMU bridge uses host
odometry time for registered clouds. Host map age is not physical sensor latency.

A bounded static probe is available:

```sh
python3 tools/helios32_sim/probe_crop_box.py \
  --assets /path/to/runtime/common_sensor_crop_box --output /path/to/new_probe
```

Use an isolated ROS domain and Gazebo master. It checks actual plugin output
against an independent XYZ mask, including removal, preservation of outside
points and no-return handling. It is not a navigation or real-time test.

Historical opaque evidence: validation/helios_collision_20261115/REPORT_zh.md.
Current crop evidence: validation/helios_crop_box_20261116/REPORT_zh.md.
