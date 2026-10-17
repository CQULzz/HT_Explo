# CMU Garage + CuPy elevation + HT bridge (local trial)

These components run in separate ROS 2 workspaces. This directory contains the
ROS-topic bridge, a local copy of the eight-direction student model and weights,
and simulation-only launch/SDF overrides. No build overlay is shared between
CMU, CuPy, and HT-Explo.

The bridge subscribes to `/elevation_mapping/elevation_map_raw` and publishes
`/ht_traversability/global_local`. It accepts only a 291 x 291 map at about
0.04094 m/cell in the `map` frame. It runs the trained Scout model on the
elevation layer and marks a prediction valid only when at least 90% of the
51 x 51 receptive field is within 0.25 m of a real observed elevation cell.
Interpolated heights alone never make an HT cell valid. The 241 x 241 scored
region is published with the original map center and cell size; the unsupported
outer border is omitted. The CuPy subscription uses reliable QoS, matching its
publisher for these large GridMap messages.

`ht_valid` is neural-context validity. `ht_observation_valid` records local
height support with the existing 0.25m observation-distance limit; consumers
apply the 0.6m body footprint to this layer, avoiding a second inflation of
the 51x51 neural receptive field. Missing under-body support, an invalid
current neural prediction, and any valid low-probability footprint cell
still forbid motion. Observed incompatible historical surfaces retain their
measured heights as model context and are hard blocked in all directions;
expired or unreferenced surfaces stay unknown. CPU inference defaults to
four PyTorch threads and channels-last layout; BLAS remains single-threaded.

Retained source variance may increase without a new lidar return. Such aging
does not invalidate the identical observation already accepted into history.
A genuinely newer rejected return supersedes older ground: if it has a finite
measured height, that height is kept solely as occupied context and its own
eight HT probabilities are forced to zero. A newer accepted return can clear
it. Missing measurements, expired evidence, and rejected returns lacking a
finite height remain unknown. Thus an uncertain wall does not invalidate a
whole neural receptive field, and cannot become traversable through padding.


Start each command in a separate terminal:

```bash
export ROS_DOMAIN_ID=164 GZ_PARTITION=ht_explo_cmu_trial_164
source '/home/lzz/my test/autonomous_exploration_development_environment/install/setup.bash'
ros2 launch '/home/lzz/my test/ht_cupy_bridge_ws/cmu_sim.launch.py'
```

```bash
export ROS_DOMAIN_ID=164
source '/home/lzz/my test/HT_Explo-fixposition/install_standalone/setup.bash'
ros2 launch tare_planner explore_ht.launch.py scenario:=garage use_sim_time:=false ht_config:='/home/lzz/my test/ht_cupy_bridge_ws/ht_trial.yaml'
```

```bash
export ROS_DOMAIN_ID=164
export LD_LIBRARY_PATH="/home/lzz/.local/lib/python3.12/site-packages/nvidia/cuda_nvrtc/lib:/home/lzz/.local/lib/python3.12/site-packages/nvidia/cuda_runtime/lib:${LD_LIBRARY_PATH:-}"
source /opt/ros/jazzy/setup.bash
source '/home/lzz/my test/elevation_mapping_cupy_ws/install/setup.bash'
ros2 run elevation_mapping_cupy elevation_mapping_node --ros-args \
  -p core_param_file:='/home/lzz/my test/elevation_mapping_cupy_ws/config/trial_core.yaml' \
  -p setup_file:='/home/lzz/my test/elevation_mapping_cupy_ws/config/trial_setup.yaml'
```

```bash
export ROS_DOMAIN_ID=164
source /opt/ros/jazzy/setup.bash
python3 '/home/lzz/my test/ht_cupy_bridge_ws/cupy_to_ht.py'
```

These trial launches replace only CMU's spawned SDF files with copies in
`assets/`. The simulated lidar has 64 vertical beams from -75 to +15 degrees,
and its rays ignore the vehicle's own visual meshes. Stock CMU has 16 beams
from -15 to +15 degrees; at a 0.75 m mount height this leaves the nearby ground
unobserved. The stock files in the CMU workspace are unchanged. This is a
simulation sensor adaptation, not the real Helios 32 optical specification or
a real-vehicle traversability validation. The HT model was trained for Scout
data, whereas the CMU vehicle model is simplified.

For Campus, replace `ROS_DOMAIN_ID=164` with `165`, set
`GZ_PARTITION=ht_explo_cmu_campus_165`, launch `cmu_campus.launch.py`, and use
`scenario:=campus` for TARE. Keep the other CuPy and bridge commands the same.
The original stock-sensor observations are in
`results/garage_campus_2026-10-10.json`. Neither original trial completed
exploration: Garage was blocked; Campus oscillated and eventually exhausted
the low-speed fallback budget. A stock raw scan in each world contained no
points within 2 m of the vehicle. With the downward sensor, a fresh Garage
trial had about 14,000 raw points within 2 m, a valid HT center, and moved
10.2 m net in one 50-second window. A Campus trial also had a valid HT center
and moved 6.35 m net in one 60-second warm window. Neither observation proves
mission completion. Earlier trials with a best-effort TARE subscription had
intermittent `HT_MAP_STALE` holds. TARE now subscribes reliably; a 900-second
Campus run observed zero stale holds, a 2.04-second maximum map arrival gap,
and a 2.31-second maximum sampled map age. This is a tested mitigation rather
than a packet-level guarantee; see `results/HT_long_run_report_2026-10-11.md`.
In a 35-second Campus window, reliable QoS plus the cropped HT map increased
received HT maps from 20 to 40 and reduced the maximum observed delivery gap
from 5.19 to 1.79 seconds. The windows occurred at different robot poses, so
these figures validate delivery behavior rather than a controlled navigation
performance comparison. See `results/downward_sensor_2026-10-10.json`.

A Campus control-chain smoke test with `ht_enabled=false` drove 22.3 m in
45 seconds from the HT trial endpoint. After that drive had pre-mapped the
ground, HT's center cell became valid, and the HT run traveled 7.9 m in
30 seconds but only 1.0 m net. It still did not complete exploration. These
runs have different initial maps and poses and must not be read as a matched
performance comparison. They do show that the stock Campus simulator can
drive and that filling the lidar blind area with past observations changes
HT map validity.

`model.py` and `student_best_epoch_weights.pth` are local copies from the
existing `eletranskit_scout` project, so this bridge has no runtime dependency
on that workspace. The copied source carries its MIT license in `LICENSE`.

To compare HT's eight directional probabilities on the **same terrain**, start
the simulation, elevation mapper, and HT bridge in one ROS domain, then run:

```bash
source /opt/ros/jazzy/setup.bash
ROS_DOMAIN_ID=172 python3 '/home/lzz/my test/ht_cupy_bridge_ws/ht_direction_terrain.py' \
  --output '/home/lzz/my test/ht_cupy_bridge_ws/results/ht_direction_terrain.png'
```

This captures an actual HT GridMap, saves its eight probability layers as an
NPZ, and draws eight fixed-XY heatmaps with one common 0–1 color scale. The
black dot marks the same cell in all panels; the lower plot compares its eight
directional values. The gray color represents unsupported cells. An actual
Campus snapshot is `results/campus_ht_direction_terrain_2026-10-11.png`.
These are model probabilities, not independently measured success rates.

To view the **whole XY-theta traversability field** rather than individual
XY maps or a single cell, stack those eight layers in one 3D coordinate
system:

```bash
python3 '/home/lzz/my test/ht_cupy_bridge_ws/ht_xytheta_volume.py' \
  --input '/home/lzz/my test/ht_cupy_bridge_ws/results/campus_ht_direction_terrain_2026-10-11.npz' \
  --output '/home/lzz/my test/ht_cupy_bridge_ws/results/campus_ht_xytheta_2026-10-11.html'
```

Open the HTML in a browser to rotate the XYθ volume, hover for P(x,y,θ),
or isolate one θ slice with the menu. A static two-view PNG is generated at
the same time. The saved source map is 241×241×8; the display samples every
second XY cell for responsiveness, preserving the original NPZ. The θ axis
is eight discrete **travel directions**, not an optimized robot yaw path.

For an actual local grid search in `(x, y, body yaw)` on that same snapshot:

```bash
python3 '/home/lzz/my test/ht_cupy_bridge_ws/xytheta_grid_planner.py' \
  --input '/home/lzz/my test/ht_cupy_bridge_ws/results/campus_ht_direction_terrain_2026-10-11.npz' \
  --output '/home/lzz/my test/ht_cupy_bridge_ws/results/campus_xytheta_grid_plan_2026-10-11.html' \
  --start 0 0 0 --goal -3 3 90
```

This runs A* over a 30×30×8 grid sampled conservatively from the native HT
map. Transitions are 45-degree pivots, heading-aligned forward motion, and
reverse motion with unchanged body yaw. Reverse travel queries HT's opposite
direction channel. Low-probability transitions and cells lacking body-footprint
support are rejected. The 3D lattice and computed route appear in HTML and a
static PNG. `--goal -2 0 0` produces a six-step reverse example. This is an
offline local-planning prototype: TARE and the vehicle do **not** yet execute
these paths. In-place rotation currently checks footprint support only,
because HT does not provide a rotational traversability prediction.

With the Campus ROS stack running, the same search can run live in shadow
mode, taking TARE's `/way_point` as an XY goal and accepting any arrival yaw:

```bash
source /opt/ros/jazzy/setup.bash
ROS_DOMAIN_ID=173 python3 '/home/lzz/my test/ht_cupy_bridge_ws/xytheta_grid_live.py'
```

It publishes `/xytheta_grid_path` (`nav_msgs/Path`, including yaw in each
pose) and `/xytheta_grid_status` at 2 Hz. It publishes an empty path when
input is missing, the HT map is stale, or no safe route exists. It does not
command the vehicle. In a 50-second Campus probe it published 35 valid paths,
with 0.14–1.08 ms A* times and a maximum accepted HT-map age of 1.55 seconds;
see `results/campus_xytheta_live_probe_2026-10-11.json`. The existing CMU
pathFollower copies only XY positions from `/path`, so executing pivot,
reverse, and yaw states requires a matching low-level controller.

For an inspection of the *published path* and measured robot pose, start the
normal simulation in its ROS domain, then run:

```bash
source /opt/ros/jazzy/setup.bash
ROS_DOMAIN_ID=171 python3 '/home/lzz/my test/ht_cupy_bridge_ws/xytheta_live.py' \
  --output '/home/lzz/my test/ht_cupy_bridge_ws/results/xytheta_live.mp4' \
  --duration 70 --show
```

The 3D display is deliberately labelled an **XY-theta embedding**, not a full
XY-theta planner: blue is the measured robot pose; orange is the published XY
local route with each edge lifted to its `atan2(dy,dx)` bearing, the angle used
for HT's nearest of eight heading channels; purple is the commanded waypoint.
The plotted path is a local candidate route, not a separately optimized yaw
trajectory. A close-up example is in
`results/campus_xytheta_closeup_2026-10-11.mp4`.

`HT_MAP_STALE` means that TARE's latest accepted HT GridMap header stamp is
more than `ht_map_timeout` seconds old when a planning cycle begins. The
CuPy ROS node stamps the map when it publishes it, so this checks delivery
and processing of HT map messages, not the age of each lidar observation.
The bridge preserves that stamp. On a stale cycle TARE publishes the robot's
current position as its waypoint and zero on `/speed`; a subsequent cycle
with a fresh map can resume navigation. The Campus trial uses a 3-second
timeout. In one diagnostic interval an independent subscriber received fresh
HT maps during all 13 TARE stale statuses. Changing TARE's HT subscription
from best-effort to reliable delivery then yielded 65 maps and 106
`HT_ASSISTED` status samples with zero stale statuses in a 55-second Campus
probe (`results/ht_qos_reliable_probe_2026-10-11.json`). This is a short
smoke test, not a guarantee against later stalls.
# CPU thread pools

The bridge additionally requires `threadpoolctl` (`python3 -m pip install threadpoolctl`).
It keeps PyTorch at two CPU threads and independently limits BLAS to one.
Small Nx3 surface fits otherwise wake NumPy's 28-worker OpenBLAS pool, whose
idle spin competes with mapping and planning. This changes resource scheduling,
not HT weights, terrain fitting or safety thresholds. `ht_cpu_threads.json`
records actual native pool settings when diagnostics are enabled. Per-map
diagnostics separate fusion, support preparation, neural inference, publication
and the source age on entry; `map_processing_s` is the complete callback time.

Latest stopped-map context/observation fix, its failed diagnostic attempt and
closed-loop recordings: [fix report](../../docs/fixes/2026-10-17_context_recovery.md).
Successful return-home checks are separate from complete terrain coverage.
